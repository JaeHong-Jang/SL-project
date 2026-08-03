"""250m 생활인구, 등록인구, POI를 H3 분석 hex 단위로 재집계하는 도구.

생활인구는 250m 격자 polygon에 붙어 있고, 접근성 분석 단위는 H3 res 9다.
이 모듈은 두 격자가 서로 다른 문제를 면적가중 overlay로 풀어 H3별
생활인구 피처를 만든다. 등록인구는 행정동 polygon이 준비된 뒤 같은 방식으로
H3에 배분하고, POI는 좌표 point를 H3 polygon에 공간 조인해 count한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import geopandas as gpd
import numpy as np
import pandas as pd


LIVING_POPULATION_COLUMNS = (
    "mean_living_population",
    "mean_senior_population",
    "daytime_mean_population",
    "nighttime_mean_population",
    "commute_mean_population",
)

REGISTERED_POPULATION_COLUMNS = (
    "registered_population",
    "registered_senior_population",
)


def _read_gpkg(path: str | Path, layer: str | None = None) -> gpd.GeoDataFrame:
    return gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)


def _minmax(values: pd.Series) -> pd.Series:
    """0~1 정규화를 적용하되, 상수열은 0으로 둔다."""
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    minimum = numeric.min()
    maximum = numeric.max()
    if maximum == minimum:
        return pd.Series(np.zeros(len(numeric)), index=numeric.index)
    return (numeric - minimum) / (maximum - minimum)


def _fill_numeric_columns(frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """geometry와 식별자를 제외한 숫자 컬럼의 결측을 0으로 맞춘다."""
    numeric_columns = [
        column
        for column in frame.columns
        if column != "h3_res" and column != "geometry" and pd.api.types.is_numeric_dtype(frame[column])
    ]
    frame[numeric_columns] = frame[numeric_columns].fillna(0.0)
    return frame


def area_weight_living_population_to_hex(
    living_grid: gpd.GeoDataFrame,
    hexes: gpd.GeoDataFrame,
    *,
    value_columns: Sequence[str] = LIVING_POPULATION_COLUMNS,
    grid_key: str = "CELL_ID",
    hex_key: str = "hex_id",
) -> pd.DataFrame:
    """250m 생활인구 값을 H3 hex로 면적가중 재집계한다.

    각 250m 격자 값은 해당 격자가 H3와 겹치는 면적 비율만큼 나누어 배분한다.
    생활인구 값이 없는 격자는 0으로 보고, 조인 coverage 지표는 별도로 남긴다.
    """
    if living_grid.crs != hexes.crs:
        living_grid = living_grid.to_crs(hexes.crs)

    grid_cols = [grid_key, "livingpop_joined", *value_columns, "geometry"]
    available_grid_cols = [column for column in grid_cols if column in living_grid.columns]
    grid = living_grid.loc[:, available_grid_cols].copy()
    grid["livingpop_joined"] = grid.get("livingpop_joined", False).fillna(False).astype(bool)
    for column in value_columns:
        if column not in grid.columns:
            grid[column] = 0.0
        grid[column] = pd.to_numeric(grid[column], errors="coerce").fillna(0.0)
    grid["_grid_area_m2"] = grid.geometry.area

    hex_base = hexes.loc[:, [hex_key, "geometry"]].copy()
    hex_base["_hex_area_m2"] = hex_base.geometry.area

    intersections = gpd.overlay(
        grid,
        hex_base,
        how="intersection",
        keep_geom_type=False,
    )
    if intersections.empty:
        return pd.DataFrame({hex_key: hexes[hex_key]})

    intersections["_intersection_area_m2"] = intersections.geometry.area
    intersections["_grid_weight"] = intersections["_intersection_area_m2"] / intersections["_grid_area_m2"]
    intersections["_hex_coverage_weight"] = intersections["_intersection_area_m2"] / intersections["_hex_area_m2"]
    intersections["_joined_intersection_area_m2"] = np.where(
        intersections["livingpop_joined"],
        intersections["_intersection_area_m2"],
        0.0,
    )

    weighted_columns: dict[str, pd.Series] = {}
    for column in value_columns:
        weighted_columns[f"living_{column}"] = intersections[column] * intersections["_grid_weight"]
    weighted = pd.DataFrame(
        {
            hex_key: intersections[hex_key],
            "living_intersection_area_m2": intersections["_intersection_area_m2"],
            "living_joined_intersection_area_m2": intersections["_joined_intersection_area_m2"],
            "living_hex_coverage_weight": intersections["_hex_coverage_weight"],
            **weighted_columns,
        }
    )
    aggregated = weighted.groupby(hex_key, as_index=False).sum(numeric_only=True)

    hex_area = hex_base[[hex_key, "_hex_area_m2"]]
    aggregated = aggregated.merge(hex_area, on=hex_key, how="left")
    aggregated["living_hex_coverage_ratio"] = aggregated["living_intersection_area_m2"] / aggregated["_hex_area_m2"]
    aggregated["living_joined_coverage_ratio"] = aggregated["living_joined_intersection_area_m2"] / aggregated["_hex_area_m2"]
    return aggregated.drop(columns=["_hex_area_m2"])


def area_weight_registered_population_to_hex(
    registered_admin: gpd.GeoDataFrame,
    hexes: gpd.GeoDataFrame,
    *,
    value_columns: Sequence[str] = REGISTERED_POPULATION_COLUMNS,
    hex_key: str = "hex_id",
) -> pd.DataFrame:
    """행정동 polygon에 붙은 등록인구/고령인구를 H3 hex로 면적가중 배분한다.

    분석 마스크로 만든 H3가 행정동 전체를 덮지 않을 수 있으므로, 행정동 인구는
    행정동과 분석 hex가 실제로 겹친 면적 안에서 다시 정규화해 배분한다. 이렇게
    해야 산지/하천을 마스크로 제외해도 행정동 등록인구 총량이 사라지지 않는다.
    행정동 polygon이 각 H3를 얼마나 덮었는지는 `registered_hex_coverage_ratio`로 함께 남긴다.
    """
    value_columns = tuple(value_columns)
    if registered_admin.crs != hexes.crs:
        registered_admin = registered_admin.to_crs(hexes.crs)

    admin_cols = [*value_columns, "geometry"]
    available_admin_cols = [column for column in admin_cols if column in registered_admin.columns]
    admin = registered_admin.loc[:, available_admin_cols].copy()
    for column in value_columns:
        if column not in admin.columns:
            admin[column] = 0.0
        admin[column] = pd.to_numeric(admin[column], errors="coerce").fillna(0.0)
    admin["_admin_id"] = np.arange(len(admin))
    admin["_admin_area_m2"] = admin.geometry.area
    admin = admin[admin["_admin_area_m2"] > 0].copy()

    hex_base = hexes.loc[:, [hex_key, "geometry"]].copy()
    hex_base["_hex_area_m2"] = hex_base.geometry.area

    aggregated_columns = [hex_key, "registered_intersection_area_m2", *value_columns]
    if admin.empty or hex_base.empty:
        aggregated = pd.DataFrame(columns=aggregated_columns)
    else:
        intersections = gpd.overlay(
            admin,
            hex_base,
            how="intersection",
            keep_geom_type=False,
        )
        if intersections.empty:
            aggregated = pd.DataFrame(columns=aggregated_columns)
        else:
            intersections["_intersection_area_m2"] = intersections.geometry.area
            intersections["_covered_admin_area_m2"] = intersections.groupby("_admin_id")[
                "_intersection_area_m2"
            ].transform("sum")
            intersections["_admin_weight"] = intersections["_intersection_area_m2"] / intersections[
                "_covered_admin_area_m2"
            ].where(intersections["_covered_admin_area_m2"] > 0)
            intersections["_admin_weight"] = intersections["_admin_weight"].fillna(0.0)

            weighted_columns: dict[str, pd.Series] = {}
            for column in value_columns:
                weighted_columns[column] = intersections[column] * intersections["_admin_weight"]
            weighted = pd.DataFrame(
                {
                    hex_key: intersections[hex_key],
                    "registered_intersection_area_m2": intersections["_intersection_area_m2"],
                    **weighted_columns,
                }
            )
            aggregated = weighted.groupby(hex_key, as_index=False).sum(numeric_only=True)

    result = hex_base[[hex_key, "_hex_area_m2"]].merge(aggregated, on=hex_key, how="left")
    fill_columns = ["registered_intersection_area_m2", *value_columns]
    result[fill_columns] = result[fill_columns].fillna(0.0)
    result["registered_hex_coverage_ratio"] = result["registered_intersection_area_m2"].divide(
        result["_hex_area_m2"].where(result["_hex_area_m2"] != 0)
    )
    result["registered_hex_coverage_ratio"] = result["registered_hex_coverage_ratio"].fillna(0.0)
    return result.drop(columns=["_hex_area_m2"])


def count_poi_by_hex(
    hexes: gpd.GeoDataFrame,
    poi_sources: Mapping[str, str | Path],
    *,
    hex_key: str = "hex_id",
    lon_col: str = "lon",
    lat_col: str = "lat",
) -> pd.DataFrame:
    """POI CSV들을 H3 hex별 count로 집계한다."""
    hex_base = hexes.loc[:, [hex_key, "geometry"]].copy()
    result = pd.DataFrame({hex_key: hex_base[hex_key]})
    for poi_name, path in poi_sources.items():
        table = pd.read_csv(path, usecols=lambda column: column in {lon_col, lat_col})
        table[lon_col] = pd.to_numeric(table[lon_col], errors="coerce")
        table[lat_col] = pd.to_numeric(table[lat_col], errors="coerce")
        table = table.dropna(subset=[lon_col, lat_col])
        points = gpd.GeoDataFrame(
            table,
            geometry=gpd.points_from_xy(table[lon_col], table[lat_col]),
            crs="EPSG:4326",
        ).to_crs(hex_base.crs)
        joined = gpd.sjoin(points, hex_base, how="inner", predicate="within")
        counts = joined.groupby(hex_key).size().rename(f"{poi_name}_poi_count").reset_index()
        result = result.merge(counts, on=hex_key, how="left")
    count_columns = [column for column in result.columns if column.endswith("_poi_count")]
    result[count_columns] = result[count_columns].fillna(0).astype(int)
    result["poi_total_count"] = result[count_columns].sum(axis=1) if count_columns else 0
    return result


def build_preliminary_hex_demand_features(
    *,
    hex_path: str | Path,
    living_grid_path: str | Path,
    poi_sources: Mapping[str, str | Path],
    hex_layer: str = "out_analysis_hex_h3res9",
    living_layer: str | None = "out_livingpop_250m_join_5179",
) -> gpd.GeoDataFrame:
    """생활인구와 POI만 사용한 H3 수요 피처 초안을 만든다.

    등록인구/행정동 고령인구 dasymetric 분배는 아직 붙지 않았으므로 결과 이름에
    `prelim`을 붙여 최종 demand index와 구분한다.
    """
    hexes = _read_gpkg(hex_path, layer=hex_layer)
    living_grid = _read_gpkg(living_grid_path, layer=living_layer)
    living_features = area_weight_living_population_to_hex(living_grid, hexes)
    poi_features = count_poi_by_hex(hexes, poi_sources)

    features = hexes.merge(living_features, on="hex_id", how="left").merge(poi_features, on="hex_id", how="left")
    features = _fill_numeric_columns(features)

    features["living_senior_share_mean"] = features["living_mean_senior_population"].divide(
        features["living_mean_living_population"].where(features["living_mean_living_population"] != 0)
    )
    features["living_senior_share_mean"] = features["living_senior_share_mean"].fillna(0.0)

    features["living_population_norm"] = _minmax(features["living_mean_living_population"])
    features["senior_population_norm"] = _minmax(features["living_mean_senior_population"])
    features["poi_total_norm"] = _minmax(features["poi_total_count"])
    features["demand_index_prelim"] = (
        features["living_population_norm"] + features["senior_population_norm"] + features["poi_total_norm"]
    ) / 3.0
    return features


def build_final_hex_demand_features(
    *,
    hex_path: str | Path,
    living_grid_path: str | Path,
    registered_admin_path: str | Path,
    poi_sources: Mapping[str, str | Path],
    hex_layer: str = "out_analysis_hex_h3res9",
    living_layer: str | None = "out_livingpop_250m_join_5179",
    registered_admin_layer: str | None = None,
) -> gpd.GeoDataFrame:
    """등록인구까지 포함한 H3 최종 수요 피처를 만든다.

    최종 수요지수는 연구계획의 4요소 구조에 맞춰 `등록인구`, `65세 이상
    등록인구`, `생활인구`, `시설밀도(POI)`를 같은 초기 가중치로 평균한다.
    행정동 경계가 아직 확정되지 않은 상태에서는 이 함수가 바로 실행되지는
    않지만, 신뢰 가능한 행정동 polygon이 들어오면 동일한 하네스로 재현된다.
    """
    hexes = _read_gpkg(hex_path, layer=hex_layer)
    living_grid = _read_gpkg(living_grid_path, layer=living_layer)
    registered_admin = _read_gpkg(registered_admin_path, layer=registered_admin_layer)

    living_features = area_weight_living_population_to_hex(living_grid, hexes)
    registered_features = area_weight_registered_population_to_hex(registered_admin, hexes)
    poi_features = count_poi_by_hex(hexes, poi_sources)

    features = (
        hexes.merge(living_features, on="hex_id", how="left")
        .merge(registered_features, on="hex_id", how="left")
        .merge(poi_features, on="hex_id", how="left")
    )
    features = _fill_numeric_columns(features)

    features["living_senior_share_mean"] = features["living_mean_senior_population"].divide(
        features["living_mean_living_population"].where(features["living_mean_living_population"] != 0)
    )
    features["living_senior_share_mean"] = features["living_senior_share_mean"].fillna(0.0)
    features["registered_senior_share"] = features["registered_senior_population"].divide(
        features["registered_population"].where(features["registered_population"] != 0)
    )
    features["registered_senior_share"] = features["registered_senior_share"].fillna(0.0)

    features["living_population_norm"] = _minmax(features["living_mean_living_population"])
    features["registered_population_norm"] = _minmax(features["registered_population"])
    features["registered_senior_population_norm"] = _minmax(features["registered_senior_population"])
    features["poi_total_norm"] = _minmax(features["poi_total_count"])
    features["demand_index_final"] = (
        features["registered_population_norm"]
        + features["registered_senior_population_norm"]
        + features["living_population_norm"]
        + features["poi_total_norm"]
    ) / 4.0
    return features
