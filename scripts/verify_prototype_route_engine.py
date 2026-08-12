"""단계 3 실데이터 검증 — docs/prototype_plan.md v2.

1) 엔진 cold start 시간
2) 대표 사례(시흥5동 → 삼성산자연공원.삼성체육공원) 3개 날씨 재계산 (Copernicus 데이터 기준)
3) NetworkX 독립 교차검증: m0/m3_rain 두 프로필, 무작위 정류장 20개 거리 1e-6 일치
4) 무작위 OD 30개 warm 타이밍 (p50/p95)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sl_accessibility.prototype import artifacts  # noqa: E402
from sl_accessibility.prototype.route_engine import RouteEngine  # noqa: E402

ART = ROOT / "data" / "processed" / "prototype"
ORIGIN = (126.912379, 37.455297)  # 시흥5동 격자 스냅 노드 (발표 대본 검증 사례)


def main() -> None:
    t0 = time.perf_counter()
    engine = RouteEngine(ART)
    cold = time.perf_counter() - t0
    print(f"cold_start_s={cold:.1f}")

    # --- 대표 사례 ---
    stops = engine.stops
    cand = stops[stops["name"].str.contains("삼성산자연공원", na=False)]
    stop_id = cand.index[0]
    print(f"demo_stop={stop_id} ({cand.iloc[0]['name']})")
    for weather in ["clear", "rain", "snow"]:
        r = engine.route(*ORIGIN, stop_id, weather)
        print(
            f"  {weather:6s} M0={r['m0']['network_distance_m']:7.1f} "
            f"M3부담={r['m3']['equivalent_distance_m']:7.1f} "
            f"실보행={r['m3']['physical_distance_m']:7.1f} "
            f"분해={r['breakdown']} 상태={r['comparison']['threshold_status']} "
            f"경로변경={r['comparison']['path_changed']}"
        )

    # --- NetworkX 독립 교차검증 ---
    import networkx as nx

    edges = pd.read_parquet(ART / "edges.parquet")
    rng = np.random.default_rng(7)
    targets = stops.sample(20, random_state=7)
    src_idx, _ = engine.snap(*ORIGIN)
    src_id = int(engine.node_id[src_idx])

    for profile in ["m0", "m3_rain_2mm"]:
        cost = artifacts.profile_costs(
            edges["length_m"].to_numpy(), edges["grade_abs_percent_cop"].to_numpy(), profile
        )
        G = nx.Graph()
        for u, v, c in zip(edges["u"].to_numpy(), edges["v"].to_numpy(), cost):
            if G.has_edge(u, v):
                if c < G[u][v]["w"]:
                    G[u][v]["w"] = c
            else:
                G.add_edge(u, v, w=c)
        nx_dist = nx.single_source_dijkstra_path_length(G, src_id, weight="w")

        from scipy.sparse.csgraph import dijkstra

        sp_dist = dijkstra(engine.graphs[profile].matrix, indices=src_idx)
        worst = 0.0
        for sid, row in targets.iterrows():
            d_nx = nx_dist.get(int(row["node_id"]), float("inf"))
            d_sp = float(sp_dist[int(row["node_idx"])])
            if np.isfinite(d_nx) or np.isfinite(d_sp):
                worst = max(worst, abs(d_nx - d_sp))
        assert worst < 1e-6, f"{profile}: NetworkX 대비 최대 오차 {worst}"
        print(f"nx_crosscheck[{profile}]: 20개 정류장 최대 오차 {worst:.2e} OK")

    # --- warm 타이밍 ---
    lon = rng.uniform(126.85, 127.10, 30)
    lat = rng.uniform(37.45, 37.65, 30)
    stop_ids = stops.sample(30, random_state=11).index.tolist()
    times = []
    ok = 0
    for i in range(30):
        t = time.perf_counter()
        try:
            engine.route(float(lon[i]), float(lat[i]), stop_ids[i], "rain")
            ok += 1
        except Exception:
            pass
        times.append(time.perf_counter() - t)
    times = np.array(times) * 1000
    print(
        f"warm_timing_ms p50={np.percentile(times, 50):.0f} "
        f"p95={np.percentile(times, 95):.0f} max={times.max():.0f} 성공={ok}/30"
    )
    print("VERIFY OK")


if __name__ == "__main__":
    main()
