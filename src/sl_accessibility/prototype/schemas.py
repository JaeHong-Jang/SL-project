"""단계 4 — API 요청 스키마 (docs/prototype_plan.md v2 §7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# 서울 + 여유 범위. 밖이면 422.
SEOUL_BBOX = {"min_lng": 126.60, "max_lng": 127.30, "min_lat": 37.35, "max_lat": 37.75}


class OriginPoint(BaseModel):
    lng: float = Field(..., description="경도 (EPSG:4326)")
    lat: float = Field(..., description="위도 (EPSG:4326)")

    @field_validator("lng")
    @classmethod
    def _lng_in_seoul(cls, v: float) -> float:
        if not SEOUL_BBOX["min_lng"] <= v <= SEOUL_BBOX["max_lng"]:
            raise ValueError("서울 범위 밖의 경도입니다.")
        return v

    @field_validator("lat")
    @classmethod
    def _lat_in_seoul(cls, v: float) -> float:
        if not SEOUL_BBOX["min_lat"] <= v <= SEOUL_BBOX["max_lat"]:
            raise ValueError("서울 범위 밖의 위도입니다.")
        return v


class Destination(BaseModel):
    stop_id: str = Field(..., min_length=1, description="stops.geojson의 정류장 ID")


class RouteRequest(BaseModel):
    origin: OriginPoint
    destination: Destination
    weather: Literal["clear", "cloudy", "rain", "snow"]
