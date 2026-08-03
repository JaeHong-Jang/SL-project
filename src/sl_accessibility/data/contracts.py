"""원천 데이터가 최소한 갖춰야 할 컬럼 계약.

이 프로젝트는 파일 크기가 큰 CSV를 많이 다루므로, 매번 전체 데이터를 읽기 전에
샘플과 스키마만으로 필수 컬럼이 살아 있는지 먼저 확인한다. 여기의 계약은
분석 결과를 보장하는 검증이 아니라 “다음 처리 단계로 넘어갈 수 있는 최소 조건”이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class DataContract:
    """한 데이터셋의 필수 컬럼, 선택 컬럼, 컬럼명 alias 정의."""

    name: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...] = ()
    aliases: dict[str, str] = field(default_factory=dict)

    def missing_columns(self, columns: Iterable[str]) -> list[str]:
        """현재 컬럼 목록에서 빠진 필수 컬럼을 반환한다."""
        present = set(columns)
        return [column for column in self.required_columns if column not in present]

    def normalize_name(self, column: str) -> str:
        """보고서나 후처리에서 쓸 표준 컬럼명으로 alias를 적용한다."""
        return self.aliases.get(column, column)


WALKING_EDGE = DataContract(
    name="walking_edges",
    required_columns=(
        "u",
        "v",
        "key",
        "osmid",
        "highway",
        "length_m",
        "elev_u_m",
        "elev_v_m",
        "elevation_diff_m",
        "grade_percent",
        "grade_abs_percent",
        "slope_available",
        "geometry_wkt",
    ),
    optional_columns=("name", "elevation_source"),
)

WALKING_NODE = DataContract(
    name="walking_nodes",
    required_columns=(
        "node_id",
        "x",
        "y",
        "elevation_copernicus_m",
        "elevation_google_m",
        "geometry_wkt",
    ),
)

BUS_RIDERSHIP = DataContract(
    name="bus_ridership",
    required_columns=(
        "사용년월",
        "표준버스정류장ID",
        "버스정류장ARS번호",
        "역명",
        "hour",
        "ride_type",
        "passengers",
        "route_count",
        "lon",
        "lat",
        "coord_valid",
        "location_matched",
    ),
)

SUBWAY_RIDERSHIP = DataContract(
    name="subway_ridership",
    required_columns=("사용월", "호선명", "지하철역", "hour", "ride_type", "passengers", "lon", "lat", "location_matched"),
)

ASOS_WEATHER = DataContract(
    name="asos_weather",
    required_columns=("지점", "지점명", "일시", "기온(°C)", "강수량(mm)", "풍속(m/s)", "습도(%)", "적설(cm)"),
    aliases={
        "지점": "station_id",
        "지점명": "station_name",
        "일시": "observed_at",
        "기온(°C)": "temp_c",
        "강수량(mm)": "rain_mm",
        "풍속(m/s)": "wind_ms",
        "습도(%)": "humidity_pct",
        "적설(cm)": "snow_cm",
    },
)

LOCAL_RESIDENT_250M = DataContract(
    name="local_resident_250m",
    required_columns=("일자", "시간", "행정동코드", "250M격자", "생활인구합계"),
)

POI = DataContract(name="poi", required_columns=("lon", "lat"))

CONTRACTS = {
    contract.name: contract
    for contract in (
        WALKING_EDGE,
        WALKING_NODE,
        BUS_RIDERSHIP,
        SUBWAY_RIDERSHIP,
        ASOS_WEATHER,
        LOCAL_RESIDENT_250M,
        POI,
    )
}
