"""보행망 edge 레코드에 M0-M3 비용 컬럼을 붙이는 순수 함수."""

from __future__ import annotations

from typing import Any, Iterable

import polars as pl

from sl_accessibility.accessibility.costs import CostParameters, cost_by_model, sanitize_grade_abs


COST_MODELS = ("M0", "M1", "M2", "M3")


def build_edge_cost_table(
    edges: Iterable[dict[str, Any]],
    *,
    rain_mm: float = 0.0,
    snow_cm: float = 0.0,
    params: CostParameters | None = None,
) -> list[dict[str, Any]]:
    """edge 레코드를 복사해 모델별 보행 비용 컬럼을 추가한 리스트를 만든다.

    물리적으로 사용할 수 없는 경사값은 제외한다. 경사값의 비용 cap은
    `cost_by_model`이 호출하는 비용 함수 내부에서만 적용되며, 출력 row의
    원본 `grade_abs_percent` 값은 변경하지 않는다.
    """
    p = params or CostParameters()
    rows: list[dict[str, Any]] = []

    for edge in edges:
        grade_abs_percent = sanitize_grade_abs(
            edge.get("grade_abs_percent"),
            error_threshold=p.error_grade_abs_percent,
        )
        if grade_abs_percent is None:
            continue

        length_m = edge["length_m"]
        row = dict(edge)
        for model in COST_MODELS:
            row[f"cost_{model.lower()}"] = cost_by_model(
                model,
                length_m,
                grade_abs_percent,
                rain_mm=rain_mm,
                snow_cm=snow_cm,
                params=p,
            )
        rows.append(row)

    return rows


def add_edge_cost_columns_lazy(
    frame: pl.LazyFrame,
    *,
    rain_mm: float = 0.0,
    snow_cm: float = 0.0,
    params: CostParameters | None = None,
) -> pl.LazyFrame:
    """대용량 edge 테이블에 lazy 방식으로 M0-M3 비용 컬럼을 붙인다.

    전체 보행망 CSV는 크기 때문에 dict 리스트로 변환하지 않는다.
    Polars expression으로 필터와 비용 계산을 정의해 두고, 실제 쓰기는
    CLI에서 Parquet sink 단계에 맡긴다.
    """
    p = params or CostParameters()
    grade_abs = pl.col("grade_abs_percent").cast(pl.Float64, strict=False).abs()
    length = pl.col("length_m").cast(pl.Float64, strict=False)
    grade_for_cost = grade_abs.clip(upper_bound=p.cap_grade_abs_percent)
    weather_intensity = max(float(rain_mm or 0.0), 0.0) + p.snow_weight * max(float(snow_cm or 0.0), 0.0)
    slope_factor = 1.0 + p.slope_alpha * grade_for_cost
    additive_weather_factor = 1.0 + p.weather_beta * weather_intensity
    interaction_weather_factor = additive_weather_factor + (
        p.interaction_beta * weather_intensity * grade_for_cost / 100.0
    )

    return (
        frame.with_columns(
            [
                length.alias("_length_m_float"),
                grade_abs.alias("_grade_abs_percent_float"),
            ]
        )
        .filter(
            pl.col("_length_m_float").is_not_null()
            & pl.col("_grade_abs_percent_float").is_not_null()
            & (pl.col("_grade_abs_percent_float") <= p.error_grade_abs_percent)
        )
        .with_columns(
            [
                pl.col("_length_m_float").alias("cost_m0"),
                (pl.col("_length_m_float") * slope_factor).alias("cost_m1"),
                (pl.col("_length_m_float") * slope_factor * additive_weather_factor).alias("cost_m2"),
                (pl.col("_length_m_float") * slope_factor * interaction_weather_factor).alias("cost_m3"),
            ]
        )
        .drop(["_length_m_float", "_grade_abs_percent_float"])
    )
