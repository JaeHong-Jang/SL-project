// 보행부담 경로 프로토타입 — docs/prototype_plan.md v2 §4·§7
// 상태 머신: waiting_origin → waiting_destination → ready → loading → displayed / error

import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import demoDoc from "./demo-cases.json";

const SEOUL_CENTER = [126.978, 37.5665];
const WEATHER_LABEL = { clear: "맑음", cloudy: "흐림", rain: "비", snow: "눈" };
const WEATHER_VALUES = {
  clear: "강수 0 · 적설 0", cloudy: "강수 0 · 적설 0 (비용은 맑음과 동일)",
  rain: "강수 2mm", snow: "적설 1cm (기상강도 5)",
};

// ---- 상태 ----
const state = {
  phase: "waiting_origin", // waiting_origin | waiting_destination | ready | loading | displayed | error
  origin: null,            // {lng, lat}
  stop: null,              // {stop_id, name}
  weather: "clear",
  requestToken: 0,         // 늦게 도착한 응답 무시
  result: null,            // 최신 응답
  prevWeatherResult: null, // 직전 날씨 응답 (경로 변화 배지용)
};

// ---- 지도 ----
const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors",
      },
    },
    layers: [{ id: "osm", type: "raster", source: "osm" }],
  },
  center: SEOUL_CENTER,
  zoom: 11,
  attributionControl: { compact: false },
});
map.addControl(new maplibregl.NavigationControl(), "top-right");

let originMarker = null;
let destMarker = null;
let stopsData = null; // /api/stops GeoJSON 원본 (내부 API 의존 없이 좌표 조회용)

function findStopFeature(stopId) {
  if (!stopsData) return null;
  return stopsData.features.find((f) => f.properties.stop_id === stopId) || null;
}

// 네이버 지도식 핀 마커 (출/도)
function makePin(label, color) {
  const el = document.createElement("div");
  el.className = "pin";
  el.innerHTML =
    `<svg width="34" height="44" viewBox="0 0 34 44" aria-hidden="true">` +
    `<path d="M17 43C17 43 3 24.5 3 15a14 14 0 1 1 28 0c0 9.5-14 28-14 28z" fill="${color}" stroke="#fff" stroke-width="2.5"/>` +
    `<text x="17" y="20.5" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">${label}</text></svg>`;
  return el;
}

function setDestPin(coords) {
  if (destMarker) destMarker.remove();
  destMarker = null;
  if (coords) {
    destMarker = new maplibregl.Marker({ element: makePin("도", "#ef4444"), anchor: "bottom" })
      .setLngLat(coords).addTo(map);
  }
}

// 직선거리 (법정 기준 방식) — haversine
function straightM(a, b) {
  const R = 6371000, rad = Math.PI / 180;
  const dLat = (b[1] - a[1]) * rad, dLng = (b[0] - a[0]) * rad;
  const h = Math.sin(dLat / 2) ** 2 +
    Math.cos(a[1] * rad) * Math.cos(b[1] * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

// 정류장 중심 반경 400m 원 (법정 커버리지 방식)
function circleCoords(lng, lat, radiusM = 400, n = 64) {
  const rad = Math.PI / 180;
  const dLat = radiusM / 111320;
  const dLng = radiusM / (111320 * Math.cos(lat * rad));
  const out = [];
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * 2 * Math.PI;
    out.push([lng + dLng * Math.cos(t), lat + dLat * Math.sin(t)]);
  }
  return out;
}

// 경사 → 색: 뚜렷한 단계 구분 (범례와 반드시 동기화 — index.html legend-steps)
const GRADE_CLASSES = [
  { max: 5, color: "#2e7d32" },   // 0–5% 초록
  { max: 10, color: "#fbc02d" },  // 5–10% 노랑
  { max: 20, color: "#f57c00" },  // 10–20% 주황
  { max: 30, color: "#d32f2f" },  // 20–30% 빨강
  { max: Infinity, color: "#7f1d1d" }, // 30%+ 진빨강
];
function gradeColor(g) {
  const t = Math.abs(g);
  for (const c of GRADE_CLASSES) if (t < c.max) return c.color;
  return GRADE_CLASSES[GRADE_CLASSES.length - 1].color;
}

map.on("load", async () => {
  // 소스
  map.addSource("stops", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addSource("legal", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addSource("m0-route", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addSource("m3-route", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addSource("snap-lines", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

  // 법정 기준 시각화: 정류장 반경 400m 원 + 출발지-정류장 직선 (경로 아래에 깔림)
  map.addLayer({
    id: "legal-fill", type: "fill", source: "legal",
    filter: ["==", ["geometry-type"], "Polygon"],
    paint: { "fill-color": "#2563eb", "fill-opacity": 0.08 },
  });
  map.addLayer({
    id: "legal-line", type: "line", source: "legal",
    paint: { "line-color": "#2563eb", "line-width": 2, "line-dasharray": [2, 2], "line-opacity": 0.85 },
  });

  // 정류장 (줌 13부터)
  map.addLayer({
    id: "stops", type: "circle", source: "stops", minzoom: 13,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 13, 3, 16, 6],
      "circle-color": ["match", ["get", "kind"], "지하철", "#2563eb", "#f59e0b"],
      "circle-stroke-color": "#fff", "circle-stroke-width": 1,
    },
  });
  // 스냅 연결선
  map.addLayer({
    id: "snap-lines", type: "line", source: "snap-lines",
    paint: { "line-color": "#9aa2ad", "line-width": 1.5, "line-dasharray": [1, 1.5] },
  });

  // M0: 흰 casing + 세그먼트별 경사색 "점선" (점선 = 거리 기준 경로, 실선 = 부담 최소경로)
  map.addLayer({
    id: "m0-casing", type: "line", source: "m0-route",
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#fff", "line-width": 7 },
  });
  map.addLayer({
    id: "m0-line", type: "line", source: "m0-route",
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": ["get", "color"], "line-width": 3.5, "line-dasharray": [1.4, 1.6] },
  });

  // M3: 흰 casing + 세그먼트별 경사색 실선
  map.addLayer({
    id: "m3-casing", type: "line", source: "m3-route",
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#fff", "line-width": 9 },
  });
  map.addLayer({
    id: "m3-line", type: "line", source: "m3-route",
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": ["get", "color"], "line-width": 5 },
  });

  // 정류장 로드
  try {
    const res = await fetch("/api/stops");
    stopsData = await res.json();
    map.getSource("stops").setData(stopsData);
  } catch {
    showError("정류장 목록을 불러오지 못했습니다. API 서버(포트 8000)가 실행 중인지 확인하세요.");
  }

  // 정류장 클릭 = 도착지 선택
  map.on("click", "stops", (e) => {
    if (!["waiting_destination", "ready", "displayed", "error"].includes(state.phase)) return;
    if (state.phase !== "waiting_destination" && state.stop) return; // 변경 버튼을 통해서만 재선택
    const f = e.originalEvent._stopHandled = e.features[0];
    selectStop({ stop_id: f.properties.stop_id, name: f.properties.name }, f.geometry.coordinates);
  });
  map.on("mouseenter", "stops", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "stops", () => (map.getCanvas().style.cursor = ""));

  // 지면 클릭
  map.on("click", (e) => {
    if (e.originalEvent._stopHandled) return; // 정류장 클릭이 이미 처리
    if (state.phase === "waiting_origin") {
      setOrigin([e.lngLat.lng, e.lngLat.lat]);
    } else if (state.phase === "waiting_destination") {
      hint("도착지는 정류장 마커를 클릭해 선택하세요.");
    }
  });
});

// ---- 상태 전이 ----
function setOrigin(lnglat) {
  state.origin = { lng: lnglat[0], lat: lnglat[1] };
  if (originMarker) originMarker.remove();
  originMarker = new maplibregl.Marker({ element: makePin("출", "#2563eb"), anchor: "bottom" })
    .setLngLat(lnglat).addTo(map);
  document.getElementById("origin-label").textContent =
    `출발지 (${lnglat[0].toFixed(5)}, ${lnglat[1].toFixed(5)})`;
  document.getElementById("edit-origin").hidden = false;
  state.phase = state.stop ? "ready" : "waiting_destination";
  hint(state.stop ? "" : "정류장 마커를 클릭해 도착지를 정하세요. (줌 13부터 표시)");
  maybeRoute();
}

function selectStop(stop, coords) {
  state.stop = stop;
  document.getElementById("dest-label").textContent = `${stop.name} (${stop.stop_id.split(":")[0] === "subway" ? "지하철" : "버스"})`;
  document.getElementById("edit-dest").hidden = false;
  if (coords) setDestPin(coords);
  state.phase = state.origin ? "ready" : "waiting_origin";
  hint(state.origin ? "" : "지도를 클릭해 출발지를 정하세요.");
  maybeRoute();
}

function maybeRoute() {
  updateButtons();
  if (state.origin && state.stop) requestRoute({ resetPrev: true });
}

// ---- API ----
async function requestRoute({ resetPrev = false } = {}) {
  const token = ++state.requestToken;
  state.phase = "loading";
  document.getElementById("spinner").hidden = false;
  document.getElementById("error-box").hidden = true;
  try {
    const res = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        origin: state.origin,
        destination: { stop_id: state.stop.stop_id },
        weather: state.weather,
      }),
    });
    if (token !== state.requestToken) return; // 최신 요청만 반영
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      const detail = body && body.detail;
      const msg = detail && detail.message
        ? detail.message
        : (Array.isArray(detail) ? "입력값이 올바르지 않습니다." : "서버 오류가 발생했습니다.");
      throw new Error(msg);
    }
    const data = await res.json();
    if (token !== state.requestToken) return;
    if (resetPrev) state.prevWeatherResult = null;
    render(data);
  } catch (err) {
    if (token !== state.requestToken) return;
    state.phase = "error";
    showError(err.message || "요청에 실패했습니다.");
  } finally {
    if (token === state.requestToken) document.getElementById("spinner").hidden = true;
  }
}

// ---- 렌더 ----
function fmtM(v) { return `${v.toLocaleString("ko-KR", { maximumFractionDigits: 1 })}m`; }

function render(data) {
  const prev = state.result;
  state.prevWeatherResult = prev;
  state.result = data;
  state.phase = "displayed";

  // 경로 지오메트리 (M0도 세그먼트별 경사색 — 점선으로 구분)
  map.getSource("m0-route").setData({
    type: "FeatureCollection",
    features: data.m0.segments.map((s) => ({
      type: "Feature",
      geometry: { type: "LineString", coordinates: s.geometry },
      properties: { color: gradeColor(s.grade_abs_percent), grade: s.grade_abs_percent },
    })),
  });
  map.getSource("m3-route").setData({
    type: "FeatureCollection",
    features: data.m3.segments.map((s) => ({
      type: "Feature",
      geometry: { type: "LineString", coordinates: s.geometry },
      properties: { color: gradeColor(s.grade_abs_percent), grade: s.grade_abs_percent },
    })),
  });
  // 법정 기준: 정류장 400m 원 + 직선, 카드의 직선거리 행
  const o = [state.origin.lng, state.origin.lat];
  // 도착 핀이 아직 없으면 (사례 버튼 등) 정류장 좌표를 찾아 생성
  if (!destMarker && state.stop) {
    const f = findStopFeature(state.stop.stop_id);
    if (f) setDestPin(f.geometry.coordinates);
  }
  let straightText = "—";
  if (destMarker) {
    const d = destMarker.getLngLat();
    const s = straightM(o, [d.lng, d.lat]);
    straightText = `${s.toFixed(0)}m ${s <= 400 ? "(400m 이내 — 법정 기준 양호)" : "(400m 초과)"}`;
    map.getSource("legal").setData({
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: { type: "Polygon", coordinates: [circleCoords(d.lng, d.lat)] }, properties: {} },
        { type: "Feature", geometry: { type: "LineString", coordinates: [o, [d.lng, d.lat]] }, properties: {} },
      ],
    });
  }
  document.getElementById("cmp-straight").textContent = straightText;

  // 스냅 연결선 (입력점 → 스냅 노드)
  map.getSource("snap-lines").setData({
    type: "FeatureCollection",
    features: [{
      type: "Feature",
      geometry: {
        type: "LineString",
        coordinates: [
          [state.origin.lng, state.origin.lat],
          [data.snapping.origin.node_lng, data.snapping.origin.node_lat],
        ],
      },
      properties: {},
    }],
  });

  // 경로 전체가 보이도록
  const all = data.m0.geometry.concat(...data.m3.segments.map((s) => s.geometry));
  const b = all.reduce(
    (acc, c) => [Math.min(acc[0], c[0]), Math.min(acc[1], c[1]), Math.max(acc[2], c[0]), Math.max(acc[3], c[1])],
    [Infinity, Infinity, -Infinity, -Infinity],
  );
  map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 80, maxZoom: 16.5 });

  // 결과 카드
  document.getElementById("result").hidden = false;
  const verdict = document.getElementById("verdict");
  const st = data.comparison.threshold_status;
  verdict.className = `verdict ${st}`;
  verdict.textContent =
    st === "reclassified" ? "⚠️ 부담 반영 후 400m 초과 — 현행 기준으로는 양호로 분류되는 지점"
    : st === "within" ? "✅ 400m 이내 — 부담을 반영해도 접근성 양호"
    : "🚫 두 기준 모두 400m 초과";

  // 날씨로 경로가 바뀌었는지 (직전 결과와 비교)
  const badge = document.getElementById("reroute-badge");
  if (prev && JSON.stringify(prev.m3.edge_ids) !== JSON.stringify(data.m3.edge_ids)) {
    const diff = (data.m3.equivalent_distance_m - prev.m3.equivalent_distance_m).toFixed(1);
    badge.textContent = `날씨(${WEATHER_LABEL[state.weather]})로 부담 최소경로가 바뀌었습니다 (부담 ${diff > 0 ? "+" : ""}${diff}m)`;
    badge.hidden = false;
  } else {
    badge.hidden = true;
  }

  document.getElementById("cmp-m0").textContent = fmtM(data.m0.network_distance_m);
  document.getElementById("cmp-m3-phys").textContent = fmtM(data.m3.physical_distance_m);
  document.getElementById("cmp-m3-eq").textContent = fmtM(data.m3.equivalent_distance_m);
  document.getElementById("cmp-detour").textContent = data.comparison.path_changed
    ? `+${data.comparison.detour_m}m (+${data.comparison.detour_percent}%)`
    : "동일 경로, 비용만 증가";
  document.getElementById("cmp-grades").textContent =
    `최단경로 ${data.m0.max_grade_abs_percent}% · 부담경로 ${data.m3.max_grade_abs_percent}%`;

  const bd = data.breakdown;
  document.getElementById("bd-physical").textContent = fmtM(bd.physical_m);
  document.getElementById("bd-slope").textContent = `+${fmtM(bd.slope_m)}`;
  document.getElementById("bd-weather").textContent = `+${fmtM(bd.weather_m)}`;
  document.getElementById("bd-interaction").textContent = `+${fmtM(bd.interaction_m)}`;
  document.getElementById("bd-total").textContent = fmtM(bd.total_m);

  document.getElementById("snap-info").textContent =
    `스냅거리 — 출발 ${data.snapping.origin.snap_m}m · 도착 ${data.snapping.destination.snap_m}m`;
  document.getElementById("model-info").textContent =
    `적용 날씨: ${WEATHER_LABEL[state.weather]} (${WEATHER_VALUES[state.weather]})`;
  updateButtons();
}

function showError(msg) {
  const box = document.getElementById("error-box");
  box.textContent = msg;
  box.hidden = false;
}

function hint(msg) { document.getElementById("hint").textContent = msg; }

function updateButtons() {
  document.getElementById("swap").disabled = !(state.origin && state.stop);
}

// ---- 컨트롤 ----
document.querySelectorAll(".weather-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".weather-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.weather = btn.dataset.weather;
    document.getElementById("weather-note").hidden = state.weather !== "cloudy";
    if (state.origin && state.stop) requestRoute(); // 직전 결과 보관 → 경로 변화 배지
  });
});

document.getElementById("edit-origin").addEventListener("click", () => {
  state.phase = "waiting_origin";
  hint("지도를 클릭해 출발지를 다시 정하세요.");
});
document.getElementById("edit-dest").addEventListener("click", () => {
  state.stop = null;
  state.phase = "waiting_destination";
  setDestPin(null);
  document.getElementById("dest-label").textContent = "정류장 마커를 클릭해 도착지를 정하세요";
  hint("정류장 마커를 클릭해 도착지를 다시 정하세요. (줌 13부터 표시)");
});

document.getElementById("swap").addEventListener("click", () => {
  // 도착지(정류장) 위치가 새 출발지가 되고, 도착지는 다시 선택 (O는 자유점, D는 정류장 제약)
  if (!destMarker) return;
  const p = destMarker.getLngLat();
  state.stop = null;
  document.getElementById("dest-label").textContent = "정류장 마커를 클릭해 도착지를 정하세요";
  setDestPin(null);
  setOrigin([p.lng, p.lat]);
  hint("교환: 이전 도착 정류장이 출발지가 되었습니다. 새 도착 정류장을 클릭하세요.");
});

document.getElementById("reset").addEventListener("click", () => {
  state.origin = null; state.stop = null; state.result = null; state.prevWeatherResult = null;
  state.phase = "waiting_origin";
  state.requestToken++;
  if (originMarker) { originMarker.remove(); originMarker = null; }
  setDestPin(null);
  ["m0-route", "m3-route", "snap-lines", "legal"].forEach((s) =>
    map.getSource(s)?.setData({ type: "FeatureCollection", features: [] }));
  document.getElementById("result").hidden = true;
  document.getElementById("error-box").hidden = true;
  document.getElementById("origin-label").textContent = "지도를 클릭해 출발지를 정하세요";
  document.getElementById("dest-label").textContent = "정류장 마커를 클릭해 도착지를 정하세요";
  document.getElementById("edit-origin").hidden = true;
  document.getElementById("edit-dest").hidden = true;
  hint("");
  updateButtons();
});

// 레이어 토글
const toggles = [
  ["toggle-m0", ["m0-casing", "m0-line"]],
  ["toggle-m3", ["m3-casing", "m3-line"]],
  ["toggle-legal", ["legal-fill", "legal-line"]],
  ["toggle-stops", ["stops"]],
];
toggles.forEach(([id, layers]) => {
  document.getElementById(id).addEventListener("change", (e) => {
    layers.forEach((l) =>
      map.getLayer(l) && map.setLayoutProperty(l, "visibility", e.target.checked ? "visible" : "none"));
  });
});

// ---- 대표 사례 ----
const demoBox = document.getElementById("demo-buttons");
const demoCases = (demoDoc && demoDoc.cases) || [];
if (!demoCases.length) {
  demoBox.innerHTML = '<p class="hint">대표 사례가 아직 없습니다 (단계 6에서 채워짐).</p>';
} else {
  demoCases.forEach((c) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = c.title;
    btn.title = c.description;
    btn.addEventListener("click", () => {
      state.weather = c.weather;
      document.querySelectorAll(".weather-btn").forEach((b) =>
        b.classList.toggle("active", b.dataset.weather === c.weather));
      document.getElementById("weather-note").hidden = c.weather !== "cloudy";
      // 정류장 좌표는 보관해둔 stops GeoJSON에서 찾는다
      const f = findStopFeature(c.stop_id);
      const coords = f ? f.geometry.coordinates : null;
      const name = f ? f.properties.name : c.stop_id;
      state.stop = { stop_id: c.stop_id, name };
      document.getElementById("dest-label").textContent = name;
      document.getElementById("edit-dest").hidden = false;
      if (coords) setDestPin(coords);
      setOrigin([c.origin.lng, c.origin.lat]);
    });
    demoBox.appendChild(btn);
  });
}
