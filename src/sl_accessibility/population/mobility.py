"""행정동급 생활이동 OD를 보수적으로 집계하는 보조 분석 모듈.

생활이동 OD는 출발/도착 행정동 코드는 있지만 행정동 내부 좌표가 없다. 따라서 이
모듈은 OD를 H3 수요지수에 직접 섞지 않고, 행정동 단위 이동압력(activity pressure)
을 만든 뒤 H3 취약지역 해석을 보강하는 별도 `mobility_` 레이어로 배분한다.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import geopandas as gpd
import numpy as np
import pandas as pd

from sl_accessibility.io.csv_reader import read_csv_schema


LIFE_MOBILITY_REQUIRED_COLUMNS = (
    "대상연월",
    "요일",
    "도착시간",
    "출발 행정동 코드",
    "도착 행정동 코드",
    "성별",
    "나이",
    "이동유형",
    "move_pop",
    "masked_count",
    "avg_move_time_min",
)

MOBILITY_ADMIN_COLUMNS = (
    "mobility_admin_code",
    "mobility_departures",
    "mobility_arrivals",
    "mobility_internal_trips",
    "mobility_seoul_internal_departures",
    "mobility_seoul_internal_arrivals",
    "mobility_outbound_to_nonseoul",
    "mobility_inbound_from_nonseoul",
    "mobility_peak_departures",
    "mobility_peak_arrivals",
    "mobility_home_work_departures",
    "mobility_home_work_arrivals",
    "mobility_total_trips",
    "mobility_peak_total_trips",
    "mobility_net_inflow",
    "mobility_origin_avg_move_time_min",
    "mobility_destination_avg_move_time_min",
)

MOBILITY_ADDITIVE_COLUMNS = (
    "mobility_departures",
    "mobility_arrivals",
    "mobility_internal_trips",
    "mobility_seoul_internal_departures",
    "mobility_seoul_internal_arrivals",
    "mobility_outbound_to_nonseoul",
    "mobility_inbound_from_nonseoul",
    "mobility_peak_departures",
    "mobility_peak_arrivals",
    "mobility_home_work_departures",
    "mobility_home_work_arrivals",
    "mobility_total_trips",
    "mobility_peak_total_trips",
)


def profile_life_mobility_header(path: str | Path, encoding: str = "utf-8") -> dict[str, str]:
    """전체를 읽지 않고 헤더/스키마만 확인한다."""
    return read_csv_schema(path, encoding=encoding, n_rows=10)


def mobility_code_from_admin_code(value: object) -> str:
    """행정동 경계 8자리 코드를 생활이동 OD의 7자리 코드로 맞춘다."""
    text = str(value or "").strip()
    return text[:7]


def build_mobility_admin_geography(
    admin_boundary: gpd.GeoDataFrame,
    *,
    admin_code_col: str = "admin_code",
) -> gpd.GeoDataFrame:
    """행정동 경계를 생활이동 OD 코드 단위로 dissolve한다.

    생활이동 OD 코드는 7자리이고 SGIS 행정동 경계는 8자리다. 대부분 1:1이지만
    일부 최신 분동 지역은 같은 7자리 prefix를 공유하므로, OD와 맞는 공간 단위로
    합쳐야 중복 배분을 피할 수 있다.
    """
    if admin_code_col not in admin_boundary.columns:
        raise ValueError(f"admin boundary is missing {admin_code_col!r}.")

    boundary = admin_boundary.copy()
    boundary["mobility_admin_code"] = boundary[admin_code_col].map(mobility_code_from_admin_code)
    grouped = boundary.dissolve(by="mobility_admin_code", as_index=False)

    name_columns = [
        column for column in ("district_name", "admin_name", "admin_code") if column in boundary.columns
    ]
    if name_columns:
        attrs = (
            boundary.groupby("mobility_admin_code", as_index=False)
            .agg({column: lambda values: ",".join(sorted(set(map(str, values)))) for column in name_columns})
            .rename(columns={"admin_name": "mobility_admin_names", "admin_code": "source_admin_codes"})
        )
        if "district_name" in attrs.columns:
            attrs["district_name"] = attrs["district_name"].str.split(",").str[0]
        grouped = grouped.drop(
            columns=[
                column
                for column in attrs.columns
                if column in grouped.columns and column != "mobility_admin_code"
            ]
        )
        grouped = grouped.merge(attrs, on="mobility_admin_code", how="left")
    return grouped


def aggregate_life_mobility_od_admin_csv(
    path: str | Path,
    admin_codes: Iterable[str],
    *,
    encoding: str = "utf-8",
    chunksize: int = 500_000,
    max_rows: int | None = None,
    peak_hours: Sequence[int] = (7, 8, 9, 17, 18, 19),
    progress_every_chunks: int | None = None,
    progress_callback: Callable[[dict[str, object]], None] | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """생활이동 OD CSV를 행정동별 이동압력 지표로 chunk 집계한다.

    반환값의 행은 생활이동 7자리 행정동 코드 단위다. `max_rows`는 89GB 원본을
    전부 돌리기 전 스모크 테스트를 할 때만 사용한다.
    """
    path = Path(path)
    admin_code_set = {str(code) for code in admin_codes}
    _ensure_life_mobility_columns(path, encoding)

    stats: dict[str, defaultdict[str, float]] = {
        column: defaultdict(float)
        for column in MOBILITY_ADMIN_COLUMNS
        if column != "mobility_admin_code" and not column.endswith("_avg_move_time_min")
    }
    origin_time_num: defaultdict[str, float] = defaultdict(float)
    origin_time_den: defaultdict[str, float] = defaultdict(float)
    destination_time_num: defaultdict[str, float] = defaultdict(float)
    destination_time_den: defaultdict[str, float] = defaultdict(float)

    qa = _initial_mobility_qa(path, max_rows=max_rows)
    peak_hour_set = {int(hour) for hour in peak_hours}
    od_pairs: set[tuple[str, str]] = set()
    unmatched_origin: defaultdict[str, float] = defaultdict(float)
    unmatched_destination: defaultdict[str, float] = defaultdict(float)

    reader = pd.read_csv(
        path,
        encoding=encoding,
        usecols=list(LIFE_MOBILITY_REQUIRED_COLUMNS),
        chunksize=chunksize,
        nrows=max_rows,
    )
    for chunk_index, chunk in enumerate(reader, start=1):
        qa["input_row_count"] += int(len(chunk))
        prepared = _prepare_life_mobility_chunk(chunk)
        qa["used_row_count"] += int(len(prepared))
        qa["zero_or_negative_move_pop_count"] += int((prepared["move_pop"] <= 0).sum())
        qa["total_move_pop"] += float(prepared["move_pop"].sum())
        qa["total_masked_count"] += float(prepared["masked_count"].sum())
        qa["date_values"].update(map(str, prepared["month"].dropna().unique()))
        qa["weekday_values"].update(map(str, prepared["weekday"].dropna().unique()))
        qa["hour_values"].update(map(int, prepared["hour"].dropna().unique()))
        qa["trip_type_values"].update(map(str, prepared["trip_type"].dropna().unique()))

        origin_code = prepared["origin_code"]
        destination_code = prepared["destination_code"]
        move = prepared["move_pop"]
        origin_in = origin_code.isin(admin_code_set)
        destination_in = destination_code.isin(admin_code_set)
        same_admin = origin_code == destination_code
        both_seoul = origin_in & destination_in
        peak = prepared["hour"].isin(peak_hour_set)
        home_work = prepared["trip_type"].isin({"HW", "WH"})
        valid_time = prepared["avg_move_time_min"].notna() & (prepared["move_pop"] > 0)

        _add_grouped(stats["mobility_departures"], origin_code[origin_in], move[origin_in])
        _add_grouped(stats["mobility_arrivals"], destination_code[destination_in], move[destination_in])
        _add_grouped(
            stats["mobility_internal_trips"],
            origin_code[origin_in & same_admin],
            move[origin_in & same_admin],
        )
        _add_grouped(stats["mobility_seoul_internal_departures"], origin_code[both_seoul], move[both_seoul])
        _add_grouped(
            stats["mobility_seoul_internal_arrivals"],
            destination_code[both_seoul],
            move[both_seoul],
        )
        _add_grouped(
            stats["mobility_outbound_to_nonseoul"],
            origin_code[origin_in & ~destination_in],
            move[origin_in & ~destination_in],
        )
        _add_grouped(
            stats["mobility_inbound_from_nonseoul"],
            destination_code[destination_in & ~origin_in],
            move[destination_in & ~origin_in],
        )
        _add_grouped(stats["mobility_peak_departures"], origin_code[origin_in & peak], move[origin_in & peak])
        _add_grouped(stats["mobility_peak_arrivals"], destination_code[destination_in & peak], move[destination_in & peak])
        _add_grouped(
            stats["mobility_home_work_departures"],
            origin_code[origin_in & home_work],
            move[origin_in & home_work],
        )
        _add_grouped(
            stats["mobility_home_work_arrivals"],
            destination_code[destination_in & home_work],
            move[destination_in & home_work],
        )

        time_weight = prepared["move_pop"] * prepared["avg_move_time_min"]
        _add_grouped(origin_time_num, origin_code[origin_in & valid_time], time_weight[origin_in & valid_time])
        _add_grouped(origin_time_den, origin_code[origin_in & valid_time], move[origin_in & valid_time])
        _add_grouped(
            destination_time_num,
            destination_code[destination_in & valid_time],
            time_weight[destination_in & valid_time],
        )
        _add_grouped(
            destination_time_den,
            destination_code[destination_in & valid_time],
            move[destination_in & valid_time],
        )

        active_od_mask = origin_in | destination_in
        for pair in zip(origin_code[active_od_mask], destination_code[active_od_mask], strict=False):
            od_pairs.add((str(pair[0]), str(pair[1])))

        unmatched_origin_mask = origin_code.str.startswith("11") & ~origin_in
        unmatched_destination_mask = destination_code.str.startswith("11") & ~destination_in
        _add_grouped(unmatched_origin, origin_code[unmatched_origin_mask], move[unmatched_origin_mask])
        _add_grouped(
            unmatched_destination,
            destination_code[unmatched_destination_mask],
            move[unmatched_destination_mask],
        )
        if progress_callback and progress_every_chunks and chunk_index % progress_every_chunks == 0:
            progress_callback(
                {
                    "chunk_index": int(chunk_index),
                    "input_row_count": int(qa["input_row_count"]),
                    "used_row_count": int(qa["used_row_count"]),
                    "total_move_pop": float(qa["total_move_pop"]),
                    "od_pair_count_so_far": int(len(od_pairs)),
                    "unmatched_origin_seoul_code_count_so_far": int(len(unmatched_origin)),
                    "unmatched_destination_seoul_code_count_so_far": int(len(unmatched_destination)),
                }
            )

    frame = _stats_to_admin_frame(admin_code_set, stats)
    frame["mobility_total_trips"] = frame["mobility_departures"] + frame["mobility_arrivals"]
    frame["mobility_peak_total_trips"] = frame["mobility_peak_departures"] + frame["mobility_peak_arrivals"]
    frame["mobility_net_inflow"] = frame["mobility_arrivals"] - frame["mobility_departures"]
    frame["mobility_origin_avg_move_time_min"] = frame["mobility_admin_code"].map(
        lambda code: _safe_divide(origin_time_num[code], origin_time_den[code])
    )
    frame["mobility_destination_avg_move_time_min"] = frame["mobility_admin_code"].map(
        lambda code: _safe_divide(destination_time_num[code], destination_time_den[code])
    )

    qa.update(
        {
            "admin_code_count": int(len(admin_code_set)),
            "origin_admin_count": int((frame["mobility_departures"] > 0).sum()),
            "destination_admin_count": int((frame["mobility_arrivals"] > 0).sum()),
            "od_pair_count": int(len(od_pairs)),
            "unmatched_origin_seoul_code_count": int(len(unmatched_origin)),
            "unmatched_destination_seoul_code_count": int(len(unmatched_destination)),
            "top_unmatched_origin_seoul_codes": _top_weighted_codes(unmatched_origin),
            "top_unmatched_destination_seoul_codes": _top_weighted_codes(unmatched_destination),
            "date_values": sorted(qa["date_values"]),
            "weekday_values": sorted(qa["weekday_values"]),
            "hour_values": sorted(qa["hour_values"]),
            "trip_type_values": sorted(qa["trip_type_values"]),
            "status": "sample" if max_rows is not None else "complete",
        }
    )
    return frame.loc[:, MOBILITY_ADMIN_COLUMNS], qa


def build_hex_mobility_aux(
    *,
    hexes: gpd.GeoDataFrame,
    admin_boundary: gpd.GeoDataFrame,
    mobility_admin: pd.DataFrame,
    hex_key: str = "hex_id",
) -> gpd.GeoDataFrame:
    """행정동 이동압력 지표를 분석 H3에 면적가중 배분한다."""
    mobility_geography = build_mobility_admin_geography(admin_boundary)
    mobility_geography = mobility_geography.merge(mobility_admin, on="mobility_admin_code", how="left")
    for column in MOBILITY_ADDITIVE_COLUMNS:
        mobility_geography[column] = pd.to_numeric(mobility_geography[column], errors="coerce").fillna(0.0)

    allocated = area_weight_mobility_admin_to_hex(
        mobility_geography,
        hexes,
        value_columns=MOBILITY_ADDITIVE_COLUMNS,
        hex_key=hex_key,
    )
    result = hexes.merge(allocated, on=hex_key, how="left")
    for column in MOBILITY_ADDITIVE_COLUMNS:
        result[column] = result[column].fillna(0.0)
    result["mobility_net_inflow"] = result["mobility_arrivals"] - result["mobility_departures"]
    result["mobility_total_norm"] = _minmax(result["mobility_total_trips"])
    result["mobility_peak_norm"] = _minmax(result["mobility_peak_total_trips"])
    result["mobility_aux_index"] = result[["mobility_total_norm", "mobility_peak_norm"]].mean(axis=1)
    return result


def area_weight_mobility_admin_to_hex(
    mobility_admin: gpd.GeoDataFrame,
    hexes: gpd.GeoDataFrame,
    *,
    value_columns: Sequence[str] = MOBILITY_ADDITIVE_COLUMNS,
    hex_key: str = "hex_id",
) -> pd.DataFrame:
    """생활이동 행정동 지표를 H3에 배분하되, 분석마스크 안에서 총량을 보존한다."""
    value_columns = tuple(value_columns)
    if mobility_admin.crs != hexes.crs:
        mobility_admin = mobility_admin.to_crs(hexes.crs)

    admin = mobility_admin.loc[:, ["mobility_admin_code", *value_columns, "geometry"]].copy()
    for column in value_columns:
        admin[column] = pd.to_numeric(admin[column], errors="coerce").fillna(0.0)
    admin["_admin_area_m2"] = admin.geometry.area
    admin = admin[admin["_admin_area_m2"] > 0].copy()

    hex_base = hexes.loc[:, [hex_key, "geometry"]].copy()
    hex_base["_hex_area_m2"] = hex_base.geometry.area
    if admin.empty or hex_base.empty:
        return _empty_hex_mobility_frame(hexes, value_columns=value_columns, hex_key=hex_key)

    intersections = gpd.overlay(admin, hex_base, how="intersection", keep_geom_type=False)
    if intersections.empty:
        return _empty_hex_mobility_frame(hexes, value_columns=value_columns, hex_key=hex_key)

    intersections["_intersection_area_m2"] = intersections.geometry.area
    intersections["_covered_admin_area_m2"] = intersections.groupby("mobility_admin_code")[
        "_intersection_area_m2"
    ].transform("sum")
    intersections["_admin_weight"] = intersections["_intersection_area_m2"] / intersections[
        "_covered_admin_area_m2"
    ].where(intersections["_covered_admin_area_m2"] > 0)
    intersections["_admin_weight"] = intersections["_admin_weight"].fillna(0.0)

    weighted_columns = {
        column: intersections[column] * intersections["_admin_weight"] for column in value_columns
    }
    weighted = pd.DataFrame(
        {
            hex_key: intersections[hex_key],
            "mobility_intersection_area_m2": intersections["_intersection_area_m2"],
            **weighted_columns,
        }
    )
    aggregated = weighted.groupby(hex_key, as_index=False).sum(numeric_only=True)
    result = hex_base[[hex_key, "_hex_area_m2"]].merge(aggregated, on=hex_key, how="left")
    result[["mobility_intersection_area_m2", *value_columns]] = result[
        ["mobility_intersection_area_m2", *value_columns]
    ].fillna(0.0)
    result["mobility_hex_coverage_ratio"] = result["mobility_intersection_area_m2"].divide(
        result["_hex_area_m2"].where(result["_hex_area_m2"] != 0)
    )
    return result.drop(columns=["_hex_area_m2"])


def _ensure_life_mobility_columns(path: Path, encoding: str) -> None:
    schema = read_csv_schema(path, encoding=encoding, n_rows=10)
    missing = [column for column in LIFE_MOBILITY_REQUIRED_COLUMNS if column not in schema]
    if missing:
        raise ValueError(f"life mobility OD file is missing columns: {missing}")


def _empty_hex_mobility_frame(
    hexes: gpd.GeoDataFrame,
    *,
    value_columns: Sequence[str],
    hex_key: str,
) -> pd.DataFrame:
    data = {hex_key: hexes[hex_key], "mobility_intersection_area_m2": 0.0, "mobility_hex_coverage_ratio": 0.0}
    data.update({column: 0.0 for column in value_columns})
    return pd.DataFrame(data)


def _initial_mobility_qa(path: Path, *, max_rows: int | None) -> dict[str, object]:
    return {
        "source": path.as_posix(),
        "source_size_bytes": int(path.stat().st_size),
        "max_rows": max_rows,
        "input_row_count": 0,
        "used_row_count": 0,
        "zero_or_negative_move_pop_count": 0,
        "total_move_pop": 0.0,
        "total_masked_count": 0.0,
        "date_values": set(),
        "weekday_values": set(),
        "hour_values": set(),
        "trip_type_values": set(),
    }


def _prepare_life_mobility_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    prepared = pd.DataFrame(
        {
            "month": chunk["대상연월"],
            "weekday": chunk["요일"],
            "hour": pd.to_numeric(chunk["도착시간"], errors="coerce").astype("Int64"),
            "origin_code": _normalize_mobility_code_series(chunk["출발 행정동 코드"]),
            "destination_code": _normalize_mobility_code_series(chunk["도착 행정동 코드"]),
            "trip_type": chunk["이동유형"].astype(str).str.strip(),
            "move_pop": pd.to_numeric(chunk["move_pop"], errors="coerce").fillna(0.0),
            "masked_count": pd.to_numeric(chunk["masked_count"], errors="coerce").fillna(0.0),
            "avg_move_time_min": pd.to_numeric(chunk["avg_move_time_min"], errors="coerce"),
        }
    )
    return prepared.dropna(subset=["hour"])


def _normalize_mobility_code_series(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype("Int64")
    return numeric.astype(str).str.replace("<NA>", "", regex=False)


def _add_grouped(accumulator: defaultdict[str, float], keys: pd.Series, values: pd.Series) -> None:
    if len(keys) == 0:
        return
    grouped = values.groupby(keys).sum()
    for key, value in grouped.items():
        if key:
            accumulator[str(key)] += float(value)


def _stats_to_admin_frame(
    admin_codes: Iterable[str],
    stats: Mapping[str, Mapping[str, float]],
) -> pd.DataFrame:
    frame = pd.DataFrame({"mobility_admin_code": sorted(map(str, admin_codes))})
    for column, values in stats.items():
        frame[column] = frame["mobility_admin_code"].map(lambda code: float(values.get(code, 0.0)))
    return frame


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return float("nan")
    return numerator / denominator


def _top_weighted_codes(values: Mapping[str, float], *, limit: int = 10) -> list[dict[str, object]]:
    return [
        {"code": code, "move_pop": float(move_pop)}
        for code, move_pop in sorted(values.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def _minmax(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    minimum = numeric.min()
    maximum = numeric.max()
    if maximum == minimum:
        return pd.Series(np.zeros(len(numeric)), index=numeric.index)
    return (numeric - minimum) / (maximum - minimum)
