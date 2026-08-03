"""데이터 계약과 기본 품질 규칙을 검사하는 작은 검증 함수들.

현재 CLI의 `validate-data`는 필수 컬럼 존재 여부를 중심으로 확인한다.
좌표 범위와 수치 범위 함수는 더 강한 QA가 필요할 때 연결하기 위한 준비물이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from sl_accessibility.data.contracts import DataContract


SEOUL_BOUNDS = {"lon_min": 126.70, "lon_max": 127.25, "lat_min": 37.40, "lat_max": 37.75}


@dataclass
class ValidationIssue:
    """검증 중 발견한 문제 한 건."""

    level: str
    message: str
    column: str | None = None


@dataclass
class ValidationReport:
    """한 데이터셋에 대한 검증 결과 묶음."""

    dataset: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.level == "error" for issue in self.issues)

    def add(self, level: str, message: str, column: str | None = None) -> None:
        self.issues.append(ValidationIssue(level=level, message=message, column=column))

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "ok": self.ok,
            "issues": [issue.__dict__ for issue in self.issues],
        }


def frame_columns(frame) -> list[str]:
    """Polars/Pandas처럼 서로 다른 frame 객체에서 컬럼 목록을 꺼낸다."""
    columns = getattr(frame, "columns", None)
    if columns is None and hasattr(frame, "schema"):
        columns = list(frame.schema.keys())
    return list(columns or [])


def validate_contract(frame, contract: DataContract) -> ValidationReport:
    """필수 컬럼 누락 여부를 검사한다."""
    report = ValidationReport(dataset=contract.name)
    for column in contract.missing_columns(frame_columns(frame)):
        report.add("error", f"Missing required column: {column}", column)
    return report


def validate_coordinates(
    records: Iterable[dict],
    lon_col: str = "lon",
    lat_col: str = "lat",
    bounds: dict[str, float] = SEOUL_BOUNDS,
) -> ValidationReport:
    """서울 주변 bounding box 안에 들어오는 좌표인지 샘플 단위로 검사한다."""
    report = ValidationReport(dataset="coordinates")
    total = 0
    invalid = 0
    out_of_bounds = 0
    for row in records:
        total += 1
        try:
            lon = float(row[lon_col])
            lat = float(row[lat_col])
        except (KeyError, TypeError, ValueError):
            invalid += 1
            continue
        if not (bounds["lon_min"] <= lon <= bounds["lon_max"] and bounds["lat_min"] <= lat <= bounds["lat_max"]):
            out_of_bounds += 1
    if invalid:
        report.add("warning", f"{invalid}/{total} records have invalid coordinates")
    if out_of_bounds:
        report.add("warning", f"{out_of_bounds}/{total} records are outside Seoul bounds")
    return report


def validate_numeric_ranges(rows: Sequence[dict], rules: dict[str, tuple[float | None, float | None]]) -> ValidationReport:
    """컬럼별 허용 수치 범위를 벗어나는 값이 있는지 검사한다."""
    report = ValidationReport(dataset="numeric_ranges")
    for column, (minimum, maximum) in rules.items():
        bad = 0
        for row in rows:
            value = row.get(column)
            if value in (None, ""):
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                bad += 1
                continue
            if minimum is not None and number < minimum:
                bad += 1
            if maximum is not None and number > maximum:
                bad += 1
        if bad:
            report.add("warning", f"{bad} values outside expected range", column)
    return report
