"""250m 생활인구 CSV를 안전하게 읽고 격자 단위로 집계하는 모듈.

현재 보유 CSV에는 `250M격자` 코드만 있고 polygon/좌표가 없다.
따라서 이 모듈은 시간대별 생활인구 집계까지만 맡고, H3 결합은 250m 격자
메타데이터를 확보한 뒤 별도 단계에서 수행한다.
"""

from __future__ import annotations

from glob import glob
from pathlib import Path

import geopandas as gpd
import pandas as pd
import polars as pl

from sl_accessibility.io.csv_reader import CsvReadOptions, scan_csv


LOCAL_RESIDENT_REQUIRED_COLUMNS = ("일자", "시간", "행정동코드", "250M격자", "생활인구합계")
SENIOR_COLUMNS = ("남자 65~69세", "남자 70세 이상", "여자 65~69세", "여자 70세 이상")


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.divide(denominator.where(denominator != 0))


def scan_local_resident_daily(pattern: str, encoding: str = "utf-8") -> pl.LazyFrame:
    """월 단위 생활인구 CSV glob을 lazy scan으로 읽는다."""
    return scan_csv(pattern, CsvReadOptions(encoding=encoding, columns=list(LOCAL_RESIDENT_REQUIRED_COLUMNS)))


def aggregate_population_by_grid_hour(frame: pl.LazyFrame) -> pl.LazyFrame:
    """`250M격자`와 시간대별 평균 생활인구를 계산한다."""
    return (
        frame.with_columns(pl.col("생활인구합계").cast(pl.Float64, strict=False).fill_null(0.0))
        .group_by(["250M격자", "시간"])
        .agg(pl.col("생활인구합계").mean().alias("mean_living_population"))
    )


def aggregate_local_resident_250m_csvs(
    pattern: str | Path,
    *,
    encoding: str = "cp949",
    chunksize: int = 250_000,
) -> pd.DataFrame:
    """30일치 250m 생활인구 CSV를 격자당 1행으로 집계한다.

    QGIS 조인을 위해 원자료의 `일자×시간×격자` 구조를 `250M격자`별 요약
    테이블로 줄인다. 원자료 전체를 한 번에 메모리에 올리지 않고 파일/청크별
    부분 집계를 만든 뒤 마지막에 다시 합친다.
    """
    paths = sorted(glob(str(pattern)))
    if not paths:
        raise FileNotFoundError(str(pattern))

    usecols = list(LOCAL_RESIDENT_REQUIRED_COLUMNS + SENIOR_COLUMNS)
    partials: list[pd.DataFrame] = []
    for path in paths:
        for chunk in pd.read_csv(path, encoding=encoding, usecols=usecols, chunksize=chunksize):
            chunk["생활인구합계"] = pd.to_numeric(chunk["생활인구합계"], errors="coerce").fillna(0.0)
            chunk["시간"] = pd.to_numeric(chunk["시간"], errors="coerce")
            senior = chunk.loc[:, list(SENIOR_COLUMNS)].apply(pd.to_numeric, errors="coerce").fillna(0.0)
            chunk["_senior_population"] = senior.sum(axis=1)
            chunk["_daytime_count"] = chunk["시간"].between(9, 17, inclusive="both").astype(int)
            chunk["_nighttime_count"] = (
                chunk["시간"].between(0, 5, inclusive="both") | chunk["시간"].between(20, 23, inclusive="both")
            ).astype(int)
            chunk["_commute_count"] = (
                chunk["시간"].between(7, 9, inclusive="both") | chunk["시간"].between(18, 20, inclusive="both")
            ).astype(int)
            chunk["_daytime_living"] = chunk["생활인구합계"] * chunk["_daytime_count"]
            chunk["_nighttime_living"] = chunk["생활인구합계"] * chunk["_nighttime_count"]
            chunk["_commute_living"] = chunk["생활인구합계"] * chunk["_commute_count"]

            grouped = chunk.groupby("250M격자", dropna=False).agg(
                observed_rows=("생활인구합계", "size"),
                living_sum=("생활인구합계", "sum"),
                living_max=("생활인구합계", "max"),
                senior_sum=("_senior_population", "sum"),
                senior_max=("_senior_population", "max"),
                daytime_living_sum=("_daytime_living", "sum"),
                daytime_count=("_daytime_count", "sum"),
                nighttime_living_sum=("_nighttime_living", "sum"),
                nighttime_count=("_nighttime_count", "sum"),
                commute_living_sum=("_commute_living", "sum"),
                commute_count=("_commute_count", "sum"),
            )
            partials.append(grouped.reset_index())

    combined = pd.concat(partials, ignore_index=True).groupby("250M격자", dropna=False).agg(
        observed_rows=("observed_rows", "sum"),
        living_sum=("living_sum", "sum"),
        living_max=("living_max", "max"),
        senior_sum=("senior_sum", "sum"),
        senior_max=("senior_max", "max"),
        daytime_living_sum=("daytime_living_sum", "sum"),
        daytime_count=("daytime_count", "sum"),
        nighttime_living_sum=("nighttime_living_sum", "sum"),
        nighttime_count=("nighttime_count", "sum"),
        commute_living_sum=("commute_living_sum", "sum"),
        commute_count=("commute_count", "sum"),
    )
    combined["mean_living_population"] = combined["living_sum"] / combined["observed_rows"]
    combined["max_living_population"] = combined["living_max"]
    combined["mean_senior_population"] = combined["senior_sum"] / combined["observed_rows"]
    combined["max_senior_population"] = combined["senior_max"]
    combined["senior_share_mean"] = _safe_divide(combined["mean_senior_population"], combined["mean_living_population"])
    combined["daytime_mean_population"] = _safe_divide(combined["daytime_living_sum"], combined["daytime_count"])
    combined["nighttime_mean_population"] = _safe_divide(combined["nighttime_living_sum"], combined["nighttime_count"])
    combined["commute_mean_population"] = _safe_divide(combined["commute_living_sum"], combined["commute_count"])
    combined = combined.reset_index().rename(columns={"250M격자": "grid_id"})
    return combined[
        [
            "grid_id",
            "observed_rows",
            "mean_living_population",
            "max_living_population",
            "mean_senior_population",
            "max_senior_population",
            "senior_share_mean",
            "daytime_mean_population",
            "nighttime_mean_population",
            "commute_mean_population",
        ]
    ]


def join_summary_to_grid(
    grid_path: str | Path,
    summary: pd.DataFrame,
    *,
    grid_layer: str | None = None,
    grid_key: str = "CELL_ID",
    summary_key: str = "grid_id",
) -> gpd.GeoDataFrame:
    """250m 격자 polygon에 격자별 생활인구 요약값을 붙인다."""
    grid = gpd.read_file(grid_path, layer=grid_layer) if grid_layer else gpd.read_file(grid_path)
    joined = grid.merge(summary, how="left", left_on=grid_key, right_on=summary_key)
    joined["livingpop_joined"] = joined[summary_key].notna()
    return joined


def spatial_status_message() -> str:
    """생활인구가 아직 공간 조인 전 상태임을 사용자에게 알려준다."""
    return "250m 생활인구는 격자 메타데이터 확보 전까지 좌표 미해결 상태입니다."
