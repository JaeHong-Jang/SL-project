"""단계 6 — 발표용 대표 사례 3개 자동 탐색·검증 (docs/prototype_plan.md v2).

사례:
1. slope_avoidance  — 맑음에서 M0와 M3 경로가 다르고 우회가 최대인 곳
2. weather_reroute  — 건조 M3와 눈 M3의 경로 격차가 최대인 곳
3. reclassified_400 — 시흥5동 시드: M0 ≤ 400m < M3 부담 (Copernicus 데이터로 재검증)
4. senior_facility  — 노인 시설 중 400m 재분류이면서 부담 증가가 최대인 곳

실행:
    python scripts/find_prototype_demo_cases.py           # 탐색 + demo-cases.json 생성
    python scripts/find_prototype_demo_cases.py --verify  # 저장된 사례 재현 검증 (데이터버전 가드)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔에서 한글·대시 출력 보장

from sl_accessibility.prototype.route_engine import RouteEngine, RouteError  # noqa: E402

ART = ROOT / "data" / "processed" / "prototype"
OUT = ROOT / "prototype" / "frontend" / "src" / "demo-cases.json"
SEED_RECLASSIFIED = {"origin": [126.912379, 37.455297], "hint": "삼성산자연공원"}


def data_version() -> str:
    with open(ART / "build_report.json", encoding="utf-8") as f:
        return json.load(f)["generated_at"]


def nearest_stops(
    engine: RouteEngine, lng: float, lat: float, k: int = 3, max_m: float = 800.0
) -> list[str]:
    """가까운 정류장 최대 k곳 (경로 분기 사례를 넓게 탐색하기 위함)."""
    from pyproj import Transformer
    from scipy.spatial import cKDTree

    if not hasattr(engine, "_stop_tree"):
        tf = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
        sx, sy = tf.transform(engine.stops["lon"].to_numpy(), engine.stops["lat"].to_numpy())
        engine._stop_tree = cKDTree(np.c_[sx, sy])
        engine._stop_ids = engine.stops.index.to_numpy()
        engine._tf_to5179 = tf
    x, y = engine._tf_to5179.transform(lng, lat)
    d, i = engine._stop_tree.query([x, y], k=k, distance_upper_bound=max_m)
    d, i = np.atleast_1d(d), np.atleast_1d(i)
    return [str(engine._stop_ids[j]) for dj, j in zip(d, i) if np.isfinite(dj)]


def case_payload(case_id: str, title: str, description: str, origin, stop_id, weather, r) -> dict:
    return {
        "id": case_id,
        "title": title,
        "description": description,
        "origin": {"lng": round(float(origin[0]), 6), "lat": round(float(origin[1]), 6)},
        "stop_id": stop_id,
        "weather": weather,
        "expect": {
            "m0_m": r["m0"]["network_distance_m"],
            "m3_equivalent_m": r["m3"]["equivalent_distance_m"],
            "path_changed": r["comparison"]["path_changed"],
            "threshold_status": r["comparison"]["threshold_status"],
        },
    }


def find_cases(engine: RouteEngine) -> list[dict]:
    edges = pd.read_parquet(ART / "edges.parquet")
    steep = edges[(edges["grade_abs_percent_cop"] >= 10) & (edges["grade_abs_percent_cop"] <= 30)]
    rng = np.random.default_rng(20260812)
    sample = steep.sample(min(400, len(steep)), random_state=20260812)

    # 첫 발견이 아니라 전체 표본에서 가장 극적인 사례를 고른다.
    best1 = None  # (점수, payload) — 경사 회피가 가장 명백한 곳
    best2 = None  # (경로 격차, payload) — 눈 재경로가 가장 명백한 곳
    best3 = None  # (우회 m, payload) — 경로가 갈라지는 400m 재분류
    for row in sample.itertuples():
        lng, lat = float(engine.node_lonlat[row.u_idx][0]), float(engine.node_lonlat[row.u_idx][1])
        for si, stop_id in enumerate(nearest_stops(engine, lng, lat)):
            try:
                r_clear = engine.route(lng, lat, stop_id, "clear")
            except RouteError:
                continue
            cmp_ = r_clear["comparison"]
            m0_max = r_clear["m0"]["max_grade_abs_percent"]
            m3_max = r_clear["m3"]["max_grade_abs_percent"]

            # 사례 3 후보: 재분류 + 경로 분기 (두 선이 실제로 갈라져 보여야 함)
            if cmp_["threshold_status"] == "reclassified" and cmp_["path_changed"] and cmp_["detour_m"] >= 15:
                if best3 is None or cmp_["detour_m"] > best3[0]:
                    best3 = (cmp_["detour_m"], case_payload(
                        "reclassified_400",
                        "400m 재분류 — 기준으로는 양호, 부담으로는 초과",
                        "지도상 거리는 400m 이내라 현행 기준으로는 양호지만, 부담을 반영하면 400m를 넘고 "
                        "짧은 길 대신 완만한 길로 우회한다.",
                        (lng, lat), stop_id, "clear", r_clear,
                    ))

            if si != 0 or r_clear["m0"]["network_distance_m"] < 150:
                continue

            # 사례 1: 경사 대비 최대 (짧은 길은 가파르고, 추천 길은 완만)
            det = cmp_["detour_percent"]
            if cmp_["path_changed"] and det >= 3 and r_clear["m0"]["network_distance_m"] >= 250 and m0_max >= 15:
                score = (m0_max - m3_max) + det * 0.5
                if best1 is None or score > best1[0]:
                    best1 = (score, case_payload(
                        "slope_avoidance",
                        "경사 회피 — 돌아가더라도 완만한 길",
                        f"맑음 기준. 거리 최단경로는 최대 경사 {m0_max:.0f}% 구간(빨강 점선)을 지나지만, "
                        f"부담 최소경로는 최대 {m3_max:.0f}%의 완만한 길(초록 실선)로 우회한다.",
                        (lng, lat), stop_id, "clear", r_clear,
                    ))

            # 사례 2: 눈에서 경로가 바뀌는 곳 (격차 최대)
            try:
                r_snow = engine.route(lng, lat, stop_id, "snow")
            except RouteError:
                continue
            if r_snow["m3"]["edge_ids"] != r_clear["m3"]["edge_ids"]:
                gap = abs(r_snow["m3"]["physical_distance_m"] - r_clear["m3"]["physical_distance_m"])
                if best2 is None or gap > best2[0]:
                    best2 = (gap, case_payload(
                        "weather_reroute",
                        "악천후 경로 변화 — 눈이 오면 다른 길",
                        "같은 출발지·정류장인데 맑음일 때와 눈이 올 때의 부담 최소경로가 서로 다르다.",
                        (lng, lat), stop_id, "snow", r_snow,
                    ))
    case1 = best1[1] if best1 else None
    case2 = best2[1] if best2 else None
    searched_case3 = best3[1] if best3 else None

    # 경로가 갈라지는 재분류 사례를 우선하고, 없을 때만 시흥5동 시드로 폴백
    if searched_case3 is not None:
        case3 = searched_case3
    else:
        origin = SEED_RECLASSIFIED["origin"]
        cand = engine.stops[engine.stops["name"].str.contains(SEED_RECLASSIFIED["hint"], na=False)]
        stop_id = str(cand.index[0])
        r = engine.route(origin[0], origin[1], stop_id, "clear")
        assert r["comparison"]["threshold_status"] == "reclassified", "시드 사례가 reclassified가 아님"
        case3 = case_payload(
            "reclassified_400",
            "400m 재분류 — 기준으로는 양호, 부담으로는 초과",
            "금천구 시흥5동(호암산 자락). 지도상 거리는 400m 이내지만 경사·날씨 부담을 반영하면 400m를 넘는다.",
            origin, stop_id, "clear", r,
        )

    case4 = find_senior_case(engine)

    cases = [c for c in [case1, case2, case3, case4] if c is not None]
    if len(cases) < 4:
        missing = {"slope_avoidance": case1, "weather_reroute": case2, "senior_facility": case4}
        raise SystemExit(f"사례 탐색 실패: {[k for k, v in missing.items() if v is None]}")
    return cases


def find_senior_case(engine: RouteEngine):
    """노인 시설 출발 400m 재분류 사례. 경로가 갈라지는 시설을 우선, 없으면 부담 증가 최대."""
    fac = pd.read_csv(ROOT / "data" / "senior_welfare_with_coords.csv", low_memory=False).dropna(
        subset=["lon", "lat"]
    )
    best_changed = None  # (우회 m, 이름) — 재분류 + 경로 분기
    best_same = None     # (부담 증가, 이름) — 재분류 (폴백)
    for row in fac.itertuples():
        for stop_id in nearest_stops(engine, float(row.lon), float(row.lat)):
            try:
                r = engine.route(float(row.lon), float(row.lat), stop_id, "clear")
            except RouteError:
                continue
            if r["comparison"]["threshold_status"] != "reclassified":
                continue
            payload = case_payload(
                "senior_facility",
                f"노인시설 400m 재분류 — {row.기관명칭}",
                f"{row.관할_자치구} {row.기관명칭}({row.시설종류}). 현행 기준으로는 정류장 접근 양호지만 "
                "경사·날씨 부담을 반영하면 400m를 넘는다.",
                (float(row.lon), float(row.lat)), stop_id, "clear", r,
            )
            if r["comparison"]["path_changed"] and r["comparison"]["detour_m"] >= 10:
                key = (r["comparison"]["detour_m"], str(row.기관명칭))
                if best_changed is None or key > best_changed[0]:
                    best_changed = (key, payload)
            else:
                inc = r["m3"]["equivalent_distance_m"] - r["m0"]["network_distance_m"]
                key = (inc, str(row.기관명칭))
                if best_same is None or key > best_same[0]:
                    best_same = (key, payload)
    if best_changed:
        return best_changed[1]
    print("[알림] 경로가 갈라지는 노인시설 재분류 사례 없음 — 부담 증가 최대 시설로 폴백")
    return best_same[1] if best_same else None


def verify(engine: RouteEngine) -> None:
    with open(OUT, encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["data_version"] == data_version(), (
        f"데이터 버전 불일치: 사례={doc['data_version']} 현재={data_version()} — 사례 재탐색 필요"
    )
    for c in doc["cases"]:
        r = engine.route(c["origin"]["lng"], c["origin"]["lat"], c["stop_id"], c["weather"])
        for key, expected in c["expect"].items():
            actual = {
                "m0_m": r["m0"]["network_distance_m"],
                "m3_equivalent_m": r["m3"]["equivalent_distance_m"],
                "path_changed": r["comparison"]["path_changed"],
                "threshold_status": r["comparison"]["threshold_status"],
            }[key]
            if isinstance(expected, float):
                assert abs(actual - expected) < 0.1, (c["id"], key, expected, actual)
            else:
                assert actual == expected, (c["id"], key, expected, actual)
        print(f"verify OK: {c['id']} ({c['title']})")


def main() -> None:
    engine = RouteEngine(ART)
    if "--verify" in sys.argv:
        verify(engine)
        return
    cases = find_cases(engine)
    doc = {"data_version": data_version(), "cases": cases}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    for c in cases:
        print(f"{c['id']}: {c['title']} | M0 {c['expect']['m0_m']}m → M3 {c['expect']['m3_equivalent_m']}m | {c['stop_id']}")
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
