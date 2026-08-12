"""단계 4 API 계약 테스트 — 합성 아티팩트 (docs/prototype_plan.md v2 §7)."""

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pyproj import Transformer

from sl_accessibility.prototype import artifacts
from sl_accessibility.prototype.api import create_app

TO_4326 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
X0, Y0 = 955000.0, 1950000.0
NODE_COORDS = {10: (X0, Y0), 20: (X0 + 90, Y0), 30: (X0 + 140, Y0), 40: (X0 + 220, Y0), 99: (X0, Y0 + 5000)}


@pytest.fixture
def client(tmp_path):
    edges = pd.DataFrame(
        {
            "edge_id": [0, 1, 2, 3],
            "u": [10, 20, 30, 10],
            "v": [20, 30, 40, 30],
            "key": [0, 0, 0, 0],
            "length_m": [90.0, 50.0, 80.0, 200.0],
            "grade_percent_cop": [1.0, 5.0, 3.0, 1.0],
            "grade_abs_percent_cop": [1.0, 5.0, 3.0, 1.0],
            "geometry_wkt": [
                f"LINESTRING ({NODE_COORDS[u][0]} {NODE_COORDS[u][1]}, {NODE_COORDS[v][0]} {NODE_COORDS[v][1]})"
                for u, v in [(10, 20), (20, 30), (30, 40), (10, 30)]
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
        node_id=ni["node_id"].to_numpy(), x=ni["x"].to_numpy(), y=ni["y"].to_numpy(),
        lon=ni["lon"].to_numpy(), lat=ni["lat"].to_numpy(),
    )
    for profile in artifacts.PROFILES:
        np.savez_compressed(
            tmp_path / f"graph_{profile}.npz", **artifacts.build_profile_csr(edges, ni, profile)
        )
    idx = ni.set_index("node_id")["node_idx"]
    edges.assign(u_idx=edges["u"].map(idx), v_idx=edges["v"].map(idx)).to_parquet(
        tmp_path / "edges.parquet", index=False
    )
    stop_lon, stop_lat = TO_4326.transform(NODE_COORDS[40][0], NODE_COORDS[40][1])
    pd.DataFrame(
        {
            "stop_id": ["bus:stop40"], "name": ["도착정류장"], "kind": ["버스"],
            "lon": [stop_lon], "lat": [stop_lat],
            "node_idx": [int(idx[40])], "node_id": [40], "snap_m": [0.0],
        }
    ).to_parquet(tmp_path / "stops_snap.parquet", index=False)
    with open(tmp_path / "stops.geojson", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": []}, f)
    with open(tmp_path / "build_report.json", "w", encoding="utf-8") as f:
        json.dump({"generated_at": "test-version"}, f)
    return TestClient(create_app(tmp_path))


def _origin():
    lng, lat = TO_4326.transform(NODE_COORDS[10][0] + 5, NODE_COORDS[10][1])
    return {"lng": lng, "lat": lat}


def test_meta_and_health(client):
    m = client.get("/api/meta").json()
    assert m["scenario_parameters_not_calibrated"] is True
    assert m["public_safe_data"] is True
    h = client.get("/api/health").json()
    assert h["status"] == "ok"
    assert h["data_version"] == "test-version"
    assert h["graphs_loaded"] == ["m0", "m3_dry", "m3_rain_2mm", "m3_snow_1cm"]


def test_stops_geojson(client):
    r = client.get("/api/stops")
    assert r.status_code == 200
    assert r.json()["type"] == "FeatureCollection"


def test_route_ok(client):
    body = {"origin": _origin(), "destination": {"stop_id": "bus:stop40"}, "weather": "rain"}
    r = client.post("/api/route", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["m0"]["network_distance_m"] == pytest.approx(220.0)
    b = data["breakdown"]
    assert b["total_m"] == pytest.approx(
        b["physical_m"] + b["slope_m"] + b["weather_m"] + b["interaction_m"], abs=1e-9
    )
    assert data["metadata"]["profile_id"] == "m3_rain_2mm"
    assert data["comparison"]["threshold_status"] in {"within", "reclassified", "both_over"}


def test_validation_errors(client):
    body = {"origin": _origin(), "destination": {"stop_id": "bus:stop40"}, "weather": "storm"}
    assert client.post("/api/route", json=body).status_code == 422

    body = {"origin": {"lng": 100.0, "lat": 37.5}, "destination": {"stop_id": "bus:stop40"}, "weather": "rain"}
    assert client.post("/api/route", json=body).status_code == 422


def test_domain_errors(client):
    body = {"origin": _origin(), "destination": {"stop_id": "bus:없음"}, "weather": "rain"}
    r = client.post("/api/route", json=body)
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "unknown_stop"

    iso_lng, iso_lat = TO_4326.transform(*NODE_COORDS[99])
    body = {"origin": {"lng": iso_lng, "lat": iso_lat}, "destination": {"stop_id": "bus:stop40"}, "weather": "rain"}
    r = client.post("/api/route", json=body)
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "no_path"
