"""Dijkstra 목적지로 쓸 대중교통 D 후보를 정리하는 도구."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import polars as pl
from shapely.ops import unary_union


SEOUL_LON_MIN = 126.70
SEOUL_LON_MAX = 127.25
SEOUL_LAT_MIN = 37.40
SEOUL_LAT_MAX = 37.75


def _truthy_expr(column: str) -> pl.Expr:
    """문자열/불리언 플래그를 공통 truthy 조건으로 해석한다."""
    return (
        pl.col(column)
        .cast(pl.Utf8, strict=False)
        .str.to_lowercase()
        .str.strip_chars()
        .is_in(["true", "1", "yes", "y"])
    )


def _valid_lonlat_filter() -> pl.Expr:
    lon = pl.col("lon").cast(pl.Float64, strict=False)
    lat = pl.col("lat").cast(pl.Float64, strict=False)
    return lon.is_between(SEOUL_LON_MIN, SEOUL_LON_MAX) & lat.is_between(SEOUL_LAT_MIN, SEOUL_LAT_MAX)


def _coalesce_existing(columns: list[str], available_columns: set[str]) -> pl.Expr:
    """원자료마다 다른 한글/영문 alias 중 실제 존재하는 컬럼만 고른다."""
    expressions = [
        pl.col(column).cast(pl.Utf8, strict=False)
        for column in columns
        if column in available_columns
    ]
    if not expressions:
        return pl.lit(None, dtype=pl.Utf8)
    return pl.coalesce(expressions)


def build_bus_d_candidates(frame: pl.LazyFrame) -> pl.LazyFrame:
    """버스 승하차 원자료에서 좌표가 유효한 정류장 D 후보를 만든다."""
    available_columns = set(frame.collect_schema().names())
    return (
        frame.with_columns(
            [
                _coalesce_existing(["standard_bus_stop_id", "표준버스정류장ID"], available_columns).alias(
                    "stop_id"
                ),
                _coalesce_existing(["bus_stop_name", "역명"], available_columns).alias("stop_name"),
                pl.col("lon").cast(pl.Float64, strict=False).alias("lon"),
                pl.col("lat").cast(pl.Float64, strict=False).alias("lat"),
                pl.col("passengers").cast(pl.Float64, strict=False).fill_null(0.0).alias("passengers"),
            ]
        )
        .filter(_valid_lonlat_filter() & _truthy_expr("coord_valid") & _truthy_expr("location_matched"))
        .group_by(["stop_id", "stop_name"])
        .agg(
            [
                pl.col("lon").mean().alias("lon"),
                pl.col("lat").mean().alias("lat"),
                pl.col("passengers").sum().alias("passengers_sum"),
                pl.len().alias("source_rows"),
            ]
        )
        .with_columns(pl.lit("bus").alias("mode"))
        .select(["mode", "stop_id", "stop_name", "lon", "lat", "passengers_sum", "source_rows"])
    )


def build_subway_d_candidates(frame: pl.LazyFrame) -> pl.LazyFrame:
    """지하철 승하차 원자료에서 좌표가 유효한 역 D 후보를 만든다."""
    return (
        frame.with_columns(
            [
                pl.col("지하철역").cast(pl.Utf8, strict=False).alias("stop_id"),
                pl.col("지하철역").cast(pl.Utf8, strict=False).alias("stop_name"),
                pl.col("lon").cast(pl.Float64, strict=False).alias("lon"),
                pl.col("lat").cast(pl.Float64, strict=False).alias("lat"),
                pl.col("passengers").cast(pl.Float64, strict=False).fill_null(0.0).alias("passengers"),
            ]
        )
        .filter(_valid_lonlat_filter() & _truthy_expr("location_matched"))
        .group_by(["stop_id", "stop_name"])
        .agg(
            [
                pl.col("lon").mean().alias("lon"),
                pl.col("lat").mean().alias("lat"),
                pl.col("passengers").sum().alias("passengers_sum"),
                pl.len().alias("source_rows"),
            ]
        )
        .with_columns(pl.lit("subway").alias("mode"))
        .select(["mode", "stop_id", "stop_name", "lon", "lat", "passengers_sum", "source_rows"])
    )


def transit_candidates_to_gdf(frame: pl.DataFrame, *, output_crs: str = "EPSG:5179") -> gpd.GeoDataFrame:
    """정리된 D 후보 테이블을 QGIS 검수용 point GeoDataFrame으로 바꾼다."""
    pdf = frame.to_pandas()
    gdf = gpd.GeoDataFrame(
        pdf,
        geometry=gpd.points_from_xy(pdf["lon"], pdf["lat"]),
        crs="EPSG:4326",
    )
    return gdf.to_crs(output_crs)


def split_candidates_by_boundary(
    candidates: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
    *,
    buffer_m: float = 0.0,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """서울 경계 안 D 후보와 경계 밖 QA 후보를 분리한다."""
    boundary_in_candidate_crs = boundary.to_crs(candidates.crs)
    boundary_geom = unary_union(boundary_in_candidate_crs.geometry.make_valid())
    if buffer_m:
        boundary_geom = boundary_geom.buffer(buffer_m)

    # lon/lat bounding box는 수도권 외곽 점을 일부 통과시킨다.
    # 메인 D 후보는 서울 경계로 다시 자르고, 제외된 점은 QA 레이어로 남긴다.
    inside_mask = candidates.geometry.apply(boundary_geom.covers)
    return candidates.loc[inside_mask].copy(), candidates.loc[~inside_mask].copy()


def write_transit_d_candidates(
    frame: pl.DataFrame,
    output_path: str | Path,
    *,
    layer: str = "out_transit_d_candidates",
    boundary_path: str | Path | None = None,
    boundary_layer: str | None = None,
    boundary_buffer_m: float = 0.0,
    outside_layer: str = "qa_transit_d_candidates_outside_boundary",
) -> tuple[int, int]:
    """버스/지하철 D 후보를 GeoPackage로 저장하고, 경계 밖 후보는 QA로 분리한다."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    candidates = transit_candidates_to_gdf(frame)
    outside_count = 0
    if boundary_path is not None:
        boundary = (
            gpd.read_file(boundary_path, layer=boundary_layer)
            if boundary_layer
            else gpd.read_file(boundary_path)
        )
        candidates, outside = split_candidates_by_boundary(
            candidates,
            boundary,
            buffer_m=boundary_buffer_m,
        )
        outside_count = int(len(outside))
        outside.to_file(output_path, layer=outside_layer, driver="GPKG")

    candidates.to_file(output_path, layer=layer, driver="GPKG")
    return int(len(candidates)), outside_count
