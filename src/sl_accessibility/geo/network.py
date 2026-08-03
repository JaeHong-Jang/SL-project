"""경사 반영 보행 접근성 분석에 필요한 보행망 처리 도구."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from sl_accessibility.accessibility.costs import cost_m3, sanitize_grade_abs


@dataclass
class WalkingGraph:
    graph: nx.MultiDiGraph


def edge_is_usable(grade_abs_percent: float | int | None, *, error_threshold: float = 100.0) -> bool:
    """라우팅 전에 데이터 오류로 보이는 경사 이상치를 제외한다."""
    return sanitize_grade_abs(grade_abs_percent, error_threshold=error_threshold) is not None


def edge_cost_minutes(
    length_m: float,
    grade_abs_percent: float,
    *,
    rain_mm: float = 0.0,
    snow_cm: float = 0.0,
    walking_speed_m_per_min: float = 67.0,
) -> float:
    """M3의 거리 환산 링크 비용을 보행 시간(분)으로 바꾼다."""
    cost_m = cost_m3(length_m, grade_abs_percent, rain_mm=rain_mm, snow_cm=snow_cm)
    return cost_m / walking_speed_m_per_min


def build_graph(edges: Iterable[dict]) -> WalkingGraph:
    graph = nx.MultiDiGraph()
    for row in edges:
        if not edge_is_usable(row.get("grade_abs_percent")):
            continue
        graph.add_edge(
            row["u"],
            row["v"],
            key=row.get("key", 0),
            length_m=float(row["length_m"]),
            grade_percent=float(row.get("grade_percent", 0.0)),
            grade_abs_percent=float(row.get("grade_abs_percent", 0.0)),
        )
    return WalkingGraph(graph=graph)
