from pathlib import Path
from uuid import uuid4

import geopandas as gpd
from shapely.geometry import box

from sl_accessibility.geo.hex_grid import build_analysis_hexes, hex_centroids, h3_cell_polygon


def test_h3_cell_polygon_is_valid():
    polygon = h3_cell_polygon("8930e1d8b93ffff")
    assert polygon.is_valid
    assert polygon.area > 0


def test_build_analysis_hexes_from_small_mask():
    tmp_dir = Path(".pytest-tmp")
    tmp_dir.mkdir(exist_ok=True)
    mask_path = tmp_dir / f"mask_{uuid4().hex}.gpkg"
    mask = gpd.GeoDataFrame(
        {"name": ["sample"]},
        geometry=[box(126.97, 37.55, 126.99, 37.57)],
        crs="EPSG:4326",
    )
    mask.to_file(mask_path, layer="mask", driver="GPKG")

    hexes = build_analysis_hexes(mask_path, resolution=9, mask_layer="mask")
    centroids = hex_centroids(hexes)

    assert not hexes.empty
    assert hexes.crs == "EPSG:5179"
    assert len(centroids) == len(hexes)
