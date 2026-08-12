"""단계 2 아티팩트 생성 로직 테스트 (합성 데이터, docs/prototype_plan.md v2)."""

import numpy as np
import pandas as pd
import pytest

from sl_accessibility.accessibility.costs import cost_by_model
from sl_accessibility.prototype import artifacts


@pytest.fixture
def edges():
    # 병렬 엣지(1-2 두 개), 30% 초과 경사(cap 검증), 평지 포함
    return pd.DataFrame(
        {
            "edge_id": [0, 1, 2, 3, 4],
            "u": [10, 10, 20, 30, 10],
            "v": [20, 20, 30, 40, 30],
            "key": [0, 1, 0, 0, 0],
            "length_m": [100.0, 90.0, 50.0, 80.0, 200.0],
            "grade_abs_percent_cop": [0.0, 12.0, 45.0, 3.0, 1.0],
        }
    )


def test_profile_costs_match_reference(edges):
    for profile, (model, rain, snow) in artifacts.PROFILES.items():
        vec = artifacts.profile_costs(
            edges["length_m"].to_numpy(), edges["grade_abs_percent_cop"].to_numpy(), profile
        )
        for i, row in enumerate(edges.itertuples()):
            ref = cost_by_model(
                model, row.length_m, row.grade_abs_percent_cop, rain_mm=rain, snow_cm=snow
            )
            assert vec[i] == pytest.approx(ref, rel=1e-12), (profile, row.edge_id)


def test_grade_cap_applied(edges):
    # 45% 경사는 30%로 cap: M1 = 50 × (1 + 0.03×30) = 95
    vec = artifacts.profile_costs(
        edges["length_m"].to_numpy(), edges["grade_abs_percent_cop"].to_numpy(), "m3_dry"
    )
    assert vec[2] == pytest.approx(95.0)


def _node_index(edges):
    used = np.union1d(edges["u"].unique(), edges["v"].unique())
    return pd.DataFrame(
        {
            "node_id": used,
            "node_idx": np.arange(len(used), dtype="int64"),
            "x": np.zeros(len(used)),
            "y": np.zeros(len(used)),
            "lon": np.zeros(len(used)),
            "lat": np.zeros(len(used)),
        }
    )


def test_parallel_edge_representative_and_symmetry(edges):
    ni = _node_index(edges)
    csr = artifacts.build_profile_csr(edges, ni, "m0")
    # 노드 10(idx 0) → 20(idx 1): 병렬 엣지 중 길이 90(edge_id 1)이 대표
    a = ni.set_index("node_id")["node_idx"]
    start, end = csr["indptr"][a[10]], csr["indptr"][a[10] + 1]
    row = {csr["indices"][i]: (csr["data"][i], csr["edge_ids"][i]) for i in range(start, end)}
    assert row[a[20]] == (90.0, 1)
    # 역방향도 동일 비용·동일 대표
    start, end = csr["indptr"][a[20]], csr["indptr"][a[20] + 1]
    rev = {csr["indices"][i]: (csr["data"][i], csr["edge_ids"][i]) for i in range(start, end)}
    assert rev[a[10]] == (90.0, 1)


def test_representative_may_differ_by_profile(edges):
    # m0에서는 길이 90(경사 12%)이 이기지만, 경사 반영 시 길이 100(경사 0%)이 이긴다
    ni = _node_index(edges)
    a = ni.set_index("node_id")["node_idx"]
    csr = artifacts.build_profile_csr(edges, ni, "m3_dry")
    start, end = csr["indptr"][a[10]], csr["indptr"][a[10] + 1]
    row = {csr["indices"][i]: (csr["data"][i], csr["edge_ids"][i]) for i in range(start, end)}
    cost, eid = row[a[20]]
    assert eid == 0 and cost == pytest.approx(100.0)


def test_csr_shortest_path(edges):
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra

    ni = _node_index(edges)
    a = ni.set_index("node_id")["node_idx"]
    arrays = artifacts.build_profile_csr(edges, ni, "m0")
    g = csr_matrix(
        (arrays["data"], arrays["indices"], arrays["indptr"]),
        shape=(len(ni), len(ni)),
    )
    dist = dijkstra(g, indices=a[10])
    # 10→30: 직결 200 vs 10→20(90)→30(50) = 140
    assert dist[a[30]] == pytest.approx(140.0)
    assert dist[a[40]] == pytest.approx(220.0)


def test_snap_stops_limit():
    ni = pd.DataFrame(
        {
            "node_id": [1, 2],
            "node_idx": [0, 1],
            "x": [0.0, 1000.0],
            "y": [0.0, 0.0],
            "lon": [0.0, 0.0],
            "lat": [0.0, 0.0],
        }
    )
    from pyproj import Transformer

    tf = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
    lon0, lat0 = tf.transform(30.0, 0.0)     # 노드1에서 30m
    lon1, lat1 = tf.transform(500.0, 0.0)    # 어느 노드에서도 100m 초과
    stops = pd.DataFrame(
        {
            "stop_id": ["bus:a", "bus:b"],
            "name": ["가", "나"],
            "kind": ["버스", "버스"],
            "lon": [lon0, lon1],
            "lat": [lat0, lat1],
        }
    )
    snapped = artifacts.snap_stops(stops, ni, max_distance_m=100.0)
    assert list(snapped["stop_id"]) == ["bus:a"]
    assert snapped.iloc[0]["node_id"] == 1
    assert snapped.iloc[0]["snap_m"] == pytest.approx(30.0, abs=1.0)
