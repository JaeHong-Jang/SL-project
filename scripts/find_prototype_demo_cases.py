"""단계 6 — 발표용 대표 사례 3개 자동 탐색·검증 (docs/prototype_plan.md v2).

사례:
1. slope_avoidance  — 맑음에서 M0와 M3 경로가 다르고 우회가 5% 이상
2. weather_reroute  — 건조 M3와 눈 M3의 경로가 다름
3. reclassified_400 — 시흥5동 시드: M0 ≤ 400m < M3 부담 (Copernicus 데이터로 재검증)

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


def nearest_stop(engine: RouteEngine, lng: float, lat: float, max_m: float = 800.0) -> str | None:
    from pyproj import Transformer
    from scipy.spatial import cKDTree

    if not hasattr(engine, "_stop_tree"):
        tf = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
        sx, sy = tf.transform(engine.stops["lon"].to_numpy(), engine.stops["lat"].to_numpy())
        engine._stop_tree = cKDTree(np.c_[sx, sy])
        engine._stop_ids = engine.stops.index.to_numpy()
        engine._tf_to5179 = tf
    x, y = engine._tf_to5179.transform(lng, lat)
    d, i = engine._stop_tree.query([x, y], distance_upper_bound=max_m)
    return str(engine._stop_ids[i]) if np.isfinite(d) else None


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

    case1 = case2 = None
    for row in sample.itertuples():
        lng, lat = float(engine.node_lonlat[row.u_idx][0]), float(engine.node_lonlat[row.u_idx][1])
        stop_id = nearest_stop(engine, lng, lat)
        if stop_id is None:
            continue
        try:
            r_clear = engine.route(lng, lat, stop_id, "clear")
        except RouteError:
            continue
        if r_clear["m0"]["network_distance_m"] < 150:
            continue
        if case1 is None and r_clear["comparison"]["path_changed"] and r_clear["comparison"]["detour_percent"] >= 5:
            case1 = case_payload(
                "slope_avoidance",
                "경사 회피 — 돌아가더라도 완만한 길",
                "맑음 기준. 거리 최단경로(M0)와 부담 최소경로(M3)가 갈라지고, M3가 5% 이상 우회한다.",
                (lng, lat), stop_id, "clear", r_clear,
            )
        if case2 is None:
            try:
                r_snow = engine.route(lng, lat, stop_id, "snow")
            except RouteError:
                continue
            if r_snow["m3"]["edge_ids"] != r_clear["m3"]["edge_ids"]:
                case2 = case_payload(
                    "weather_reroute",
                    "악천후 경로 변화 — 눈이 오면 다른 길",
                    "같은 출발지·정류장에서 맑음 M3와 눈 M3의 경로가 달라진다.",
                    (lng, lat), stop_id, "snow", r_snow,
                )
        if case1 is not None and case2 is not None:
            break

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

    cases = [c for c in [case1, case2, case3] if c is not None]
    if len(cases) < 3:
        missing = {"slope_avoidance": case1, "weather_reroute": case2}
        raise SystemExit(f"사례 탐색 실패: {[k for k, v in missing.items() if v is None]}")
    return cases


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
