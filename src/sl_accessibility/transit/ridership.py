"""버스/지하철 승하차 원자료를 공통 정류장 record로 정리한다."""

from __future__ import annotations


def truthy(value) -> bool:
    """문자열과 불리언으로 섞인 유효성 플래그를 공통 bool로 해석한다."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def has_valid_coordinates(row: dict, valid_columns: tuple[str, ...] = ("coord_valid", "location_matched")) -> bool:
    """서울 주변 좌표 범위와 좌표 매칭 플래그를 함께 확인한다."""
    try:
        lon = float(row["lon"])
        lat = float(row["lat"])
    except (KeyError, TypeError, ValueError):
        return False
    if not (126.70 <= lon <= 127.25 and 37.40 <= lat <= 37.75):
        return False
    present_valid_flags = [column for column in valid_columns if column in row]
    return all(truthy(row[column]) for column in present_valid_flags) if present_valid_flags else True


def normalize_transit_record(row: dict, mode: str) -> dict:
    """버스/지하철별 다른 컬럼명을 공통 D 후보 스키마로 맞춘다."""
    if mode == "bus":
        stop_id = row.get("standard_bus_stop_id") or row.get("표준버스정류장ID")
        stop_name = row.get("bus_stop_name") or row.get("역명")
        month = row.get("사용년월")
    else:
        stop_id = row.get("지하철역")
        stop_name = row.get("지하철역")
        month = row.get("사용월")
    return {
        "mode": mode,
        "stop_id": stop_id,
        "stop_name": stop_name,
        "month": month,
        "hour": row.get("hour"),
        "ride_type": row.get("ride_type"),
        "passengers": row.get("passengers"),
        "lon": row.get("lon"),
        "lat": row.get("lat"),
    }
