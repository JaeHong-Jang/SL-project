"""기상만 따로 볼 때 쓰는 간단한 보행 마찰 계수 모델.

현재 핵심 M0-M3 비용함수는 `accessibility.costs`에 있다. 이 모듈은 ASOS
강수/적설을 별도 factor로 빠르게 확인하거나 향후 기상 민감도 실험을 분리할 때
사용하기 위한 보조 모델이다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherFrictionModel:
    """강수와 적설을 하나의 기상강도 단위로 바꾸는 보조 모델."""

    rain_weight: float = 1.0
    snow_weight: float = 5.0
    additive_beta: float = 0.03
    missing_factor: float = 1.0

    def intensity(self, rain_mm: float | None = 0.0, snow_cm: float | None = 0.0) -> float:
        """강수량과 적설량을 합성 기상강도로 환산한다."""
        rain = float(rain_mm or 0.0)
        snow = float(snow_cm or 0.0)
        return self.rain_weight * max(rain, 0.0) + self.snow_weight * max(snow, 0.0)

    def factor(self, rain_mm: float | None = 0.0, snow_cm: float | None = 0.0) -> float:
        """기상강도를 거리/시간 비용에 곱할 배율로 변환한다."""
        return max(self.missing_factor, 1.0 + self.additive_beta * self.intensity(rain_mm, snow_cm))


def weather_impedance_factor(temp_c=None, rain_mm=0.0, snow_cm=0.0, wind_ms=None) -> float:
    """이전 코드와 호환되는 함수형 wrapper."""
    return WeatherFrictionModel().factor(rain_mm=rain_mm, snow_cm=snow_cm)
