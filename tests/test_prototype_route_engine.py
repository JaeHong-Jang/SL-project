"""단계 3 경로 엔진 테스트 — 합성 아티팩트 (docs/prototype_plan.md v2)."""

import json

import numpy as np
import pandas as pd
import pytest
from pyproj import Transformer

from sl_accessibility.prototype import artifacts
from sl_accessibility.prototype.route_engine import RouteEngine, RouteError

TO_4326 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

# 서울 부근의 실제 EPSG:5179 좌표 기준점 위에 소형 그래프를 얹는다.
X0, Y0 = 955000.0, 1950000.0
NODE_COORDS = {10: (X0, Y0), 20: (X0 + 90, Y0), 30: (X0 + 140, Y0), 40: (X0 + 220, Y0), 99: (X0, Y0 + 5000)}


def _wkt(u, v, reverse=False):
    a, b = NODE_COORDS[u], NODE_COORDS[v]
    if reverse:
        a, b = b, a
    return f"LINESTRING ({a[0]} {a[1]}, {b[0]} {b[1]})"


@pytest.fixture
def engine(tmp_path):
    edges = pd.DataFrame(
        {
            "edge_id": [0, 1, 2, 3, 4],
            "u": [10, 10, 20, 30, 10],
            "v": [20, 20, 30, 40, 30],
            "key": [0, 1, 0, 0, 0],
            "length_m": [100.0, 90.0, 50.0, 80.0, 200.0],
            "grade_percent_cop": [0.0, 12.0, 45.0, 3.0, 1.0],
            "grade_abs_percent_cop": [0.0, 12.0, 45.0, 3.0, 1.0],
            # edge_id 2는 좌표열을 역방향으로 저장해 방향 정합 로직을 검증한다.
            "geometry_wkt": [
                _wkt(10, 20), _wkt(10, 20), _wkt(20, 30, reverse=True), _wkt(30, 40), _wkt(10, 30),
            ],
        }
    )
    used = sorted(NODE_COORDS)
    ni = pd.DataFrame(
        {
            "node_id": used,
            "node_idx": np.arange(len(used), dtype="int64"),
            "x": [NODE_COORDS[n][0] for n in used],
            "y": [NODE_COORDS[n][1] for n in used],
        }
    )
    lon, lat = TO_4326.transform(ni["x"].to_numpy(), ni["y"].to_numpy())
    ni["lon"], ni["lat"] = lon, lat

    np.savez_compressed(
        tmp_path / "nodes.npz",
        node_id=ni["node_id"].to_numpy(),
        x=ni["x"].to_numpy(), y=ni["y"].to_numpy(),
        lon=ni["lon"].to_numpy(), lat=ni["lat"].to_numpy(),
    )
    for profile in artifacts.PROFILES:
        np.savez_compressed(tmp_path / f"graph_{profile}.npz", **artifacts.build_profile_csr(edges, ni, profile))
    idx = ni.set_index("node_id")["node_idx"]
    edges_out = edges.assign(u_idx=edges["u"].map(idx), v_idx=edges["v"].map(idx))
    edges_out.to_parquet(tmp_path / "edges.parquet", index=False)

    stop_lon, stop_lat = TO_4326.transform(NODE_COORDS[40][0] + 10, NODE_COORDS[40][1])
    pd.DataFrame(
        {
            "stop_id": ["bus:stop40"], "name": ["도착정류장"], "kind": ["버스"],
            "lon": [stop_lon], "lat": [stop_lat],
            "node_idx": [int(idx[40])], "node_id": [40], "snap_m": [10.0],
        }
    ).set_index("stop_id").reset_index().to_parquet(tmp_path / "stops_snap.parquet", index=False)
    with open(tmp_path / "build_report.json", "w", encoding="utf-8") as f:
        json.dump({"generated_at": "test"}, f)
    return RouteEngine(tmp_path)


def _origin_lnglat():
    return TO_4326.transform(NODE_COORDS[10][0] + 5, NODE_COORDS[10][1])


def test_m0_and_m3_routes(engine):
    lng, lat = _origin_lnglat()
    r = engine.route(lng, lat, "bus:stop40", "clear")
    # M0: 10→20(e1,90)→30(e2,50)→40(e3,80) = 220
    assert r["m0"]["network_distance_m"] == pytest.approx(220.0)
    assert r["m0"]["edge_ids"] == [1, 2, 3]
    # M3(dry): 병렬 대표가 e0(평지 100)으로 바뀜 → 100 + 95 + 87.2 = 282.2
    assert r["m3"]["edge_ids"] == [0, 2, 3]
    assert r["m3"]["equivalent_distance_m"] == pytest.approx(282.2)
    assert r["comparison"]["path_changed"] is True
    assert r["comparison"]["threshold_status"] == "within"
    # M0에도 경사색 세그먼트가 있어야 한다 (경사 45% 원값 유지 — cap은 비용에만)
    assert len(r["m0"]["segments"]) == 3
    assert r["m0"]["max_grade_abs_percent"] == pytest.approx(45.0)
    assert r["m3"]["max_grade_abs_percent"] == pytest.approx(45.0)


def test_breakdown_sums_and_ordering(engine):
    lng, lat = _origin_lnglat()
    for weather in ["clear", "rain", "snow"]:
        r = engine.route(lng, lat, "bus:stop40", weather)
        b = r["breakdown"]
        # 표시값 자체가 정합해야 한다 (최대잔여 보정 후 합계 == 총계)
        assert b["total_m"] == pytest.approx(
            b["physical_m"] + b["slope_m"] + b["weather_m"] + b["interaction_m"], abs=1e-9
        )
        assert b["weather_m"] >= 0 and b["interaction_m"] >= 0
        assert r["m3"]["equivalent_distance_m"] >= r["m0"]["network_distance_m"]


def test_clear_equals_cloudy(engine):
    lng, lat = _origin_lnglat()
    a = engine.route(lng, lat, "bus:stop40", "clear")
    b = engine.route(lng, lat, "bus:stop40", "cloudy")
    assert a["m3"]["edge_ids"] == b["m3"]["edge_ids"]
    assert a["m3"]["equivalent_distance_m"] == b["m3"]["equivalent_distance_m"]
    assert a["breakdown"]["weather_m"] == 0.0


def test_geometry_orientation(engine):
    lng, lat = _origin_lnglat()
    r = engine.route(lng, lat, "bus:stop40", "clear")
    # 첫 세그먼트의 시작 좌표는 출발 노드(10) 근처여야 한다 (e2는 WKT가 역방향이어도 정합)
    first = r["m3"]["segments"][0]["geometry"][0]
    lon10, lat10 = TO_4326.transform(*NODE_COORDS[10])
    assert first[0] == pytest.approx(lon10, abs=1e-4)
    assert first[1] == pytest.approx(lat10, abs=1e-4)
    # 연속 세그먼트: 이전 끝점 == 다음 시작점
    segs = r["m3"]["segments"]
    for s1, s2 in zip(segs[:-1], segs[1:]):
        assert s1["geometry"][-1] == s2["geometry"][0]


def test_errors(engine):
    lng, lat = _origin_lnglat()
    with pytest.raises(RouteError) as e:
        engine.route(lng, lat, "bus:없는정류장", "clear")
    assert e.value.code == "unknown_stop"

    far_lng, far_lat = TO_4326.transform(X0 + 900, Y0 + 900)
    with pytest.raises(RouteError) as e:
        engine.route(far_lng, far_lat, "bus:stop40", "clear")
    assert e.value.code == "origin_snap_failed"

    iso_lng, iso_lat = TO_4326.transform(*NODE_COORDS[99])
    with pytest.raises(RouteError) as e:
        engine.route(iso_lng, iso_lat, "bus:stop40", "clear")
    assert e.value.code == "no_path"


def test_meta(engine):
    m = engine.meta()
    assert m["scenario_parameters_not_calibrated"] is True
    assert m["model_params"]["slope_alpha"] == 0.03
    assert "© OpenStreetMap contributors" in m["attribution"][0]
