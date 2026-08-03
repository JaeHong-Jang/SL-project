"""기상청 ASOS 원자료 컬럼을 하네스 내부 표준명으로 정리한다.

서울 관측소 108의 시간자료는 공간적으로 균일한 기상 시나리오로 쓰인다.
강수/적설은 비용함수 입력으로 들어가고, 기온/풍속/습도는 향후 민감도나
설명 변수로 확장할 수 있게 표준명만 맞춰 둔다.
"""

from __future__ import annotations

import polars as pl


ASOS_COLUMN_MAP = {
    "지점": "station_id",
    "지점명": "station_name",
    "일시": "observed_at",
    "기온(°C)": "temp_c",
    "강수량(mm)": "rain_mm",
    "풍속(m/s)": "wind_ms",
    "습도(%)": "humidity_pct",
    "적설(cm)": "snow_cm",
}


def normalize_asos_columns(frame: pl.LazyFrame | pl.DataFrame) -> pl.LazyFrame | pl.DataFrame:
    """ASOS 한글 컬럼명을 영어 표준명으로 바꾸고 숫자형으로 변환한다."""
    existing = {source: target for source, target in ASOS_COLUMN_MAP.items() if source in frame.columns}
    renamed = frame.rename(existing)
    numeric_cols = [column for column in ("temp_c", "rain_mm", "wind_ms", "humidity_pct", "snow_cm") if column in renamed.columns]
    expressions = [pl.col(column).cast(pl.Float64, strict=False).fill_null(0.0).alias(column) for column in numeric_cols]
    if expressions:
        renamed = renamed.with_columns(expressions)
    if "observed_at" in renamed.columns:
        renamed = renamed.with_columns(pl.col("observed_at").str.strptime(pl.Datetime, strict=False))
    return renamed
