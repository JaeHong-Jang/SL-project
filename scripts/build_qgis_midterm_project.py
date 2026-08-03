from __future__ import annotations

from pathlib import Path

from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsGraduatedSymbolRenderer,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsPalLayerSettings,
    QgsPrintLayout,
    QgsProject,
    QgsRectangle,
    QgsRendererCategory,
    QgsRendererRange,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)


ROOT = Path(__file__).resolve().parents[1]
LAYERS = ROOT / "outputs" / "qgis_midterm_layers"
MAPS = ROOT / "outputs" / "qgis_midterm_maps"
PROJECT_PATH = ROOT / "qgis" / "midterm_paper_maps.qgz"

MM = QgsUnitTypes.LayoutMillimeters
FONT = "Malgun Gothic"

PAGE_W = 338.7
PAGE_H = 190.5
MAP_X = 8
MAP_Y = 18
MAP_W = 249
MAP_H = 161
LEGEND_X = 263
LEGEND_Y = 28
LEGEND_W = 68


def gpkg_uri(stem: str) -> str:
    return str((LAYERS / f"{stem}.gpkg").resolve())


def add_layer(project: QgsProject, stem: str, name: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(gpkg_uri(stem), name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"Failed to load {stem}: {layer.error().message()}")
    project.addMapLayer(layer)
    return layer


def fill_symbol(
    fill: str,
    outline: str = "#ffffff",
    width: float = 0.0,
    opacity: float = 1.0,
) -> QgsFillSymbol:
    params = {
        "color": "#ffffff" if fill == "none" else fill,
        "outline_color": outline,
        "outline_width": str(width),
        "outline_width_unit": "MM",
    }
    if fill == "none":
        params["style"] = "no"
    symbol = QgsFillSymbol.createSimple(params)
    symbol.setOpacity(opacity)
    return symbol


def single_fill(
    layer: QgsVectorLayer,
    fill: str,
    outline: str = "#ffffff",
    width: float = 0.0,
    opacity: float = 1.0,
) -> None:
    category = QgsRendererCategory(None, fill_symbol(fill, outline, width, opacity), "")
    layer.setRenderer(QgsCategorizedSymbolRenderer("", [category]))


def categorized(layer: QgsVectorLayer, field: str, specs: list[tuple[object, str, str, float]]) -> None:
    categories = [
        QgsRendererCategory(value, fill_symbol(color, "#ffffff", 0.04, opacity), label)
        for value, label, color, opacity in specs
    ]
    layer.setRenderer(QgsCategorizedSymbolRenderer(field, categories))


def graduated(layer: QgsVectorLayer, field: str, specs: list[tuple[float, float, str, str, float]]) -> None:
    ranges = [
        QgsRendererRange(lower, upper, fill_symbol(color, "#ffffff", 0.025, opacity), label)
        for lower, upper, label, color, opacity in specs
    ]
    renderer = QgsGraduatedSymbolRenderer(field, ranges)
    renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
    layer.setRenderer(renderer)


def fit_extent_to_item(layer: QgsVectorLayer, width_mm: float, height_mm: float, margin: float = 0.09) -> QgsRectangle:
    rect = QgsRectangle(layer.extent())
    rect.grow(max(rect.width(), rect.height()) * margin)

    target_aspect = width_mm / height_mm
    current_aspect = rect.width() / rect.height()
    cx = (rect.xMinimum() + rect.xMaximum()) / 2
    cy = (rect.yMinimum() + rect.yMaximum()) / 2

    if current_aspect < target_aspect:
        half_width = rect.height() * target_aspect / 2
        return QgsRectangle(cx - half_width, rect.yMinimum(), cx + half_width, rect.yMaximum())

    half_height = rect.width() / target_aspect / 2
    return QgsRectangle(rect.xMinimum(), cy - half_height, rect.xMaximum(), cy + half_height)


def add_text(
    layout: QgsPrintLayout,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    size: int,
    bold: bool = False,
    color: str = "#1f2937",
) -> None:
    label = QgsLayoutItemLabel(layout)
    label.setText(text)
    label.setFont(QFont(FONT, size, QFont.Bold if bold else QFont.Normal))
    label.setFontColor(QColor(color))
    label.attemptMove(QgsLayoutPoint(x, y, MM))
    label.attemptResize(QgsLayoutSize(w, h, MM))
    layout.addLayoutItem(label)


def add_manual_legend(
    layout: QgsPrintLayout,
    title: str,
    items: list[tuple[str, str]],
    x: float = LEGEND_X,
    y: float = LEGEND_Y,
) -> None:
    add_text(layout, title, x, y, LEGEND_W, 7, 8, True)
    cursor = y + 9
    for label, color in items:
        add_text(layout, "■", x, cursor - 0.3, 5, 5, 11, True, color)
        add_text(layout, label, x + 7, cursor, LEGEND_W - 7, 6, 7, False, "#273142")
        cursor += 7


def enable_district_labels(layer: QgsVectorLayer) -> None:
    text_format = QgsTextFormat()
    text_format.setFont(QFont(FONT, 6))
    text_format.setSize(6)
    text_format.setColor(QColor("#5f6b7a"))

    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.8)
    buffer.setColor(QColor("#ffffff"))
    text_format.setBuffer(buffer)

    settings = QgsPalLayerSettings()
    settings.fieldName = "district_name"
    settings.enabled = True
    settings.setFormat(text_format)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def value_counts(layer: QgsVectorLayer, field: str) -> dict[object, int]:
    counts: dict[object, int] = {}
    for feature in layer.getFeatures():
        value = feature[field]
        counts[value] = counts.get(value, 0) + 1
    return counts


def create_map_layout(
    project: QgsProject,
    name: str,
    title: str,
    subtitle: str,
    map_layers: list[QgsVectorLayer],
    extent_layer: QgsVectorLayer,
    legend_title: str,
    legend_items: list[tuple[str, str]],
    definition: str,
    export_name: str,
    aliases: list[str] | None = None,
) -> None:
    manager = project.layoutManager()
    old = manager.layoutByName(name)
    if old:
        manager.removeLayout(old)

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)
    layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(PAGE_W, PAGE_H, MM))
    manager.addLayout(layout)

    add_text(layout, title, 8, 5, 220, 8, 12, True)
    add_text(layout, subtitle, 8, 12, 235, 5, 7, False, "#667085")

    item = QgsLayoutItemMap(layout)
    item.attemptMove(QgsLayoutPoint(MAP_X, MAP_Y, MM))
    item.attemptResize(QgsLayoutSize(MAP_W, MAP_H, MM))
    item.setExtent(fit_extent_to_item(extent_layer, MAP_W, MAP_H))
    item.setLayers(map_layers)
    item.setFrameEnabled(False)
    layout.addLayoutItem(item)

    add_manual_legend(layout, legend_title, legend_items)
    add_text(layout, definition, LEGEND_X, 136, LEGEND_W, 28, 7, False, "#475467")
    add_text(layout, "H3 res9 / EPSG:5179", LEGEND_X, 174, LEGEND_W, 5, 6, False, "#98a2b3")

    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = 240

    export_names = [export_name] + (aliases or [])
    for name_part in export_names:
        out_path = MAPS / f"{name_part}.png"
        out_path.unlink(missing_ok=True)
        result = exporter.exportToImage(str(out_path), settings)
        if result != QgsLayoutExporter.Success:
            raise RuntimeError(f"Failed to export {name_part}: {result}")


def main() -> None:
    MAPS.mkdir(parents=True, exist_ok=True)

    qgs = QgsApplication([], False)
    qgs.initQgis()
    try:
        project = QgsProject.instance()
        project.clear()
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:5179"))

        gu = add_layer(project, "00_admin_gu", "자치구 경계")
        base = add_layer(project, "01_valid_hex_base", "유효 분석 격자")
        burden = add_layer(project, "02_environment_burden_hex", "접근비용 증가량")
        hidden = add_layer(project, "03_hidden_candidates", "hidden 후보")
        reasons = add_layer(project, "04_hidden_reason_diagnostics", "hidden 원인")
        policy = add_layer(project, "05_policy_review_candidates", "현장검토 후보")
        district_hidden = add_layer(project, "06_district_hidden_summary", "구별 hidden 후보 밀도")

        single_fill(gu, "none", "#b3bcc9", 0.16, 0.9)
        enable_district_labels(gu)
        single_fill(base, "#eef1f5", "#ffffff", 0.0, 0.38)
        graduated(
            district_hidden,
            "hidden_count",
            [
                (0, 1, "0", "#ffffff", 0.0),
                (1, 15, "1-14", "#fee2e2", 0.22),
                (15, 30, "15-29", "#fecaca", 0.32),
                (30, 45, "30-44", "#fca5a5", 0.38),
                (45, 1000, "45+", "#ef4444", 0.30),
            ],
        )
        graduated(
            burden,
            "cost_gap_m3_minus_m0",
            [
                (0, 25, "0-25m", "#edf1f7", 0.30),
                (25, 50, "25-50m", "#9ecae1", 0.58),
                (50, 75, "50-75m", "#f2b84b", 0.86),
                (75, 100, "75-100m", "#e25d4f", 0.94),
                (100, 10000, "100m 이상", "#8f1d1d", 0.98),
            ],
        )
        categorized(
            hidden,
            "hidden_class",
            [
                ("baseline-only hidden", "hidden 후보", "#ef9a9a", 0.82),
                ("robust-core 429", "robust-core", "#b11226", 0.98),
            ],
        )
        categorized(
            reasons,
            "reason_label",
            [
                ("경사·기상 부담형", "경사·기상", "#e76f51", 0.92),
                ("수요집중형", "수요집중", "#2b6cb0", 0.90),
                ("복합형", "복합", "#7b2cbf", 0.96),
                ("혼합형", "기타/혼합", "#6b7280", 0.70),
                ("400m 경계형", "400m 경계", "#f6bd60", 0.80),
                ("수요+경계형", "수요+경계", "#fb923c", 0.86),
            ],
        )
        categorized(
            policy,
            "policy_review_type",
            [
                ("S1 정류장·접근로 검토", "정류장·접근로", "#2563eb", 0.92),
                ("S4 기상 민감 후보", "기상 민감", "#f97316", 0.94),
                ("계단·눈 대체경로 없음", "계단·눈 대체경로 없음", "#dc2626", 0.98),
                ("계단 사용 경로", "계단 사용 경로", "#8b5cf6", 0.84),
            ],
        )

        hidden_counts = value_counts(hidden, "hidden_class")
        reason_counts = value_counts(reasons, "reason_label")
        policy_counts = value_counts(policy, "policy_review_type")
        hidden_baseline = hidden_counts.get("baseline-only hidden", 0)
        hidden_robust = hidden_counts.get("robust-core 429", 0)
        reason_misc = (
            reason_counts.get("혼합형", 0)
            + reason_counts.get("400m 경계형", 0)
            + reason_counts.get("수요+경계형", 0)
        )

        create_map_layout(
            project,
            "S6_environment_burden",
            "경사·기상 반영 시 접근비용 증가 지역",
            "붉을수록 M0 대비 M3 접근비용 증가가 큰 격자",
            [burden, gu],
            base,
            "증가량(등가 m)",
            [
                ("0-25m", "#edf1f7"),
                ("25-50m", "#9ecae1"),
                ("50-75m", "#f2b84b"),
                ("75-100m", "#e25d4f"),
                ("100m 이상", "#8f1d1d"),
            ],
            "M0=거리 기준, M3=경사·기상 반영. 단위는 등가 보행거리(m).",
            "S6_environment_burden",
        )
        create_map_layout(
            project,
            "S7_hidden_candidates",
            "현행 400m 기준이 놓칠 수 있는 hidden 후보",
            "현행 기준은 양호하지만 M3+수요 기준에서 취약 후보로 전환된 격자",
            [district_hidden, base, hidden, gu],
            base,
            "hidden 후보",
            [
                (f"hidden 후보 {hidden_baseline}", "#ef9a9a"),
                (f"robust-core {hidden_robust}", "#b11226"),
                ("구별 후보 밀집", "#fca5a5"),
            ],
            "hidden=현행 400m 양호 + M3·수요 취약. 확정이 아니라 현장검토 후보.",
            "S7_hidden_candidates",
            aliases=["S7_hidden_before_after"],
        )
        create_map_layout(
            project,
            "S8_reason_diagnostics",
            "hidden 후보의 주요 원인 유형",
            "색은 각 hidden 후보의 1차 진단 원인",
            [reasons, gu],
            base,
            "주요 원인",
            [
                (f"경사·기상 {reason_counts.get('경사·기상 부담형', 0)}", "#e76f51"),
                (f"수요집중 {reason_counts.get('수요집중형', 0)}", "#2b6cb0"),
                (f"복합 {reason_counts.get('복합형', 0)}", "#7b2cbf"),
                (f"혼합/경계 {reason_misc}", "#6b7280"),
            ],
            "원인 확정이 아니라 진단 분류. 정책 유형화 전 단계의 screening 지도.",
            "S8_reason_diagnostics",
        )
        create_map_layout(
            project,
            "S9_policy_review_candidates",
            "현장검토 우선순위 후보",
            "정책 효과 입증이 아니라 어떤 유형을 먼저 확인할지 좁힌 후보",
            [policy, gu],
            base,
            "검토 유형",
            [
                (f"기상 민감 {policy_counts.get('S4 기상 민감 후보', 0)}", "#f97316"),
                (f"계단 사용 {policy_counts.get('계단 사용 경로', 0)}", "#8b5cf6"),
                (f"정류장·접근로 {policy_counts.get('S1 정류장·접근로 검토', 0)}", "#2563eb"),
                (f"대체경로 없음 {policy_counts.get('계단·눈 대체경로 없음', 0)}", "#dc2626"),
            ],
            "시나리오 기반 상한·진단 후보. 설치 위치 확정이나 효과 입증 지도가 아님.",
            "S9_policy_review_candidates",
        )

        if not project.write(str(PROJECT_PATH)):
            raise RuntimeError(f"Failed to write {PROJECT_PATH}")
        print(f"created {PROJECT_PATH}")
        print(f"exported maps to {MAPS}")
    finally:
        QgsApplication.exitQgis()


if __name__ == "__main__":
    main()
