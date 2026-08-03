"""H3 분석 격자와 QGIS 검수용 레이어를 만드는 도구."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union


def _polygon_to_latlng_poly(polygon: Polygon) -> h3.LatLngPoly:
    """Shapely polygon을 h3가 요구하는 위도/경도 순서로 바꾼다."""
    outer = [(lat, lon) for lon, lat in polygon.exterior.coords]
    holes = [[(lat, lon) for lon, lat in ring.coords] for ring in polygon.interiors]
    return h3.LatLngPoly(outer, *holes)


def h3_cells_from_geometries(geometries: Iterable[Polygon], resolution: int) -> set[str]:
    """분석영역 polygon들을 덮는 H3 cell id 집합을 만든다."""
    cells: set[str] = set()
    for geometry in geometries:
        if geometry.is_empty:
            continue
        if geometry.geom_type == "Polygon":
            cells.update(h3.polygon_to_cells(_polygon_to_latlng_poly(geometry), resolution))
        elif geometry.geom_type == "MultiPolygon":
            for polygon in geometry.geoms:
                cells.update(h3.polygon_to_cells(_polygon_to_latlng_poly(polygon), resolution))
    return cells


def h3_cell_polygon(cell_id: str) -> Polygon:
    """H3 cell 경계를 Shapely polygon으로 변환한다."""
    boundary = h3.cell_to_boundary(cell_id)
    return Polygon([(lon, lat) for lat, lon in boundary])


def build_analysis_hexes(
    mask_path: str | Path,
    *,
    resolution: int = 9,
    mask_layer: str | None = None,
    mask_crs: str = "EPSG:5179",
    output_crs: str = "EPSG:5179",
) -> gpd.GeoDataFrame:
    """분석영역 마스크를 기준으로 H3 hex polygon GeoDataFrame을 만든다.

    H3 연산은 WGS84 위경도에서 수행하고, QGIS 검수와 거리 기반 스냅을 위해
    최종 결과는 프로젝트 기준 좌표계(`EPSG:5179`)로 되돌린다.
    """
    mask = gpd.read_file(mask_path, layer=mask_layer) if mask_layer else gpd.read_file(mask_path)
    if mask.empty:
        raise ValueError(f"분석영역 마스크가 비어 있습니다: {mask_path}")
    if mask.crs is None:
        mask = mask.set_crs(mask_crs)

    mask_4326 = mask.to_crs("EPSG:4326")
    # QGIS에서 보이는 polygon도 Python union에서는 invalid geometry로 실패할 수 있다.
    # H3 polyfill 전에 geometry를 정리해 재현 가능한 격자 생성을 보장한다.
    mask_4326 = mask_4326.set_geometry(mask_4326.geometry.make_valid())
    merged = unary_union(mask_4326.geometry).buffer(0)
    cells = sorted(h3_cells_from_geometries([merged], resolution))
    hexes = gpd.GeoDataFrame(
        {
            "hex_id": cells,
            "h3_res": [resolution] * len(cells),
        },
        geometry=[h3_cell_polygon(cell_id) for cell_id in cells],
        crs="EPSG:4326",
    )

    # H3 polyfill은 경계 밖으로 걸치는 cell도 만든다.
    # centroid가 분석영역 안에 있는 hex만 남겨 분석 후보를 보수적으로 잡는다.
    centers = [Point(lon, lat) for lat, lon in (h3.cell_to_latlng(cell_id) for cell_id in cells)]
    keep = [point.within(merged) for point in centers]
    return hexes.loc[keep].to_crs(output_crs).reset_index(drop=True)


def hex_centroids(hexes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """hex polygon에서 O 후보로 사용할 중심점 레이어를 만든다."""
    points = hexes.copy()
    points["geometry"] = points.geometry.centroid
    return gpd.GeoDataFrame(points[["hex_id", "h3_res", "geometry"]], crs=hexes.crs)


def write_analysis_hex_outputs(
    hexes: gpd.GeoDataFrame,
    output_path: str | Path,
    *,
    hex_layer: str = "out_analysis_hex_h3res9",
    centroid_layer: str = "out_analysis_hex_centroids_h3res9",
) -> None:
    """QGIS에서 바로 열 수 있도록 hex와 중심점을 같은 GeoPackage에 저장한다."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    hexes.to_file(output_path, layer=hex_layer, driver="GPKG")
    hex_centroids(hexes).to_file(output_path, layer=centroid_layer, driver="GPKG")


def hex_summary(hexes: gpd.GeoDataFrame) -> dict[str, int | str]:
    """CLI 출력과 테스트에서 쓰는 작은 요약 정보."""
    return {
        "rows": int(len(hexes)),
        "crs": str(hexes.crs),
    }
