from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.sax.saxutils import escape

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from sl_accessibility.population.registered import (
    REGISTERED_POPULATION_COLUMNS,
    build_registered_population_admin_layer,
    parse_registered_population_xlsx,
)
import sl_accessibility.population.registered as registered_module


RAW_POPULATION_XLSX = (
    Path(__file__).resolve().parents[1] / "data" / "raw" / "서울시등록인구_2025_4분기.xlsx"
)


def test_parse_registered_population_xlsx_extracts_admin_dongs():
    workbook = _build_xlsx(
        [
            ("목차", {}),
            (
                "2-1. 세대 및 인구상세",
                {
                    5: {"B": "구 분", "D": "총     인     구", "O": "65세 이상 총인구"},
                    6: {"D": "계", "O": "계"},
                    7: {"B": "서울특별시", "D": 10000, "O": 2000},
                    8: {"B": "종로구", "D": 1000, "O": 300},
                    9: {"B": "사직동", "D": 100, "O": 25},
                    10: {"B": "삼청동", "D": "2,000", "O": "400"},
                    11: {"B": "중구", "D": 900, "O": 90},
                    12: {"B": "소공동", "D": 300, "O": 30},
                },
            ),
        ],
    )

    frame = parse_registered_population_xlsx(workbook)

    assert frame.columns.to_list() == REGISTERED_POPULATION_COLUMNS
    assert frame["admin_name"].to_list() == ["사직동", "삼청동", "소공동"]
    assert frame["district_name"].to_list() == ["종로구", "종로구", "중구"]
    assert frame["registered_population"].to_list() == [100, 2000, 300]
    assert frame["registered_senior_population"].to_list() == [25, 400, 30]
    assert frame["registered_senior_share"].to_list() == pytest.approx([0.25, 0.2, 0.1])


def test_parse_registered_population_xlsx_real_2025_q4_totals():
    if not RAW_POPULATION_XLSX.exists():
        pytest.skip("로컬 원본 등록인구 XLSX가 없으면 통합 안정성 테스트를 건너뜁니다.")

    frame = parse_registered_population_xlsx(RAW_POPULATION_XLSX)

    assert len(frame) == 428
    assert int(frame["registered_population"].sum()) == 9_579_177
    assert int(frame["registered_senior_population"].sum()) == 1_912_751


def test_build_registered_population_admin_layer_joins_seoul_boundary(monkeypatch):
    boundary = gpd.GeoDataFrame(
        {
            "BASE_DATE": ["20250630", "20250630", "20250630"],
            "ADM_CD": ["11060810", "11130620", "26000000"],
            "ADM_NM": ["용신동", "홍제1동", "부산동"],
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)],
        crs="EPSG:5186",
    )
    monkeypatch.setattr(registered_module.gpd, "read_file", lambda *args, **kwargs: boundary)
    population = pd.DataFrame(
        {
            "district_name": ["동대문구", "동대문구", "동대문구", "서대문구"],
            "admin_name": ["용신동", "용두동", "신설동", "홍제제1동"],
            "registered_population": [10, 20, 30, 40],
            "registered_senior_population": [1, 2, 3, 4],
            "registered_senior_share": [0.1, 0.1, 0.1, 0.1],
        }
    )

    joined, report = build_registered_population_admin_layer(
        "boundary.gpkg",
        population,
        target_crs=5179,
    )

    assert len(joined) == 2
    assert int(joined["registered_population"].sum()) == 100
    assert int(joined["registered_senior_population"].sum()) == 10
    yongsin = joined.loc[joined["admin_name"] == "용신동"].iloc[0]
    assert yongsin["registered_population"] == 60
    assert yongsin["registered_source_names"] == "신설동,용두동,용신동"
    hongje = joined.loc[joined["admin_name"] == "홍제1동"].iloc[0]
    assert hongje["registered_population"] == 40
    assert report["seoul_admin_count"] == 2
    assert report["population_only_keys"] == []
    assert report["boundary_only_keys"] == []


def _build_xlsx(sheets: list[tuple[str, dict[int, dict[str, object]]]]) -> BytesIO:
    shared_index: dict[str, int] = {}
    shared_strings: list[str] = []
    sheet_xml = [_sheet_xml(rows, shared_index, shared_strings) for _, rows in sheets]

    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_relationships())
        archive.writestr("xl/workbook.xml", _workbook_xml([name for name, _ in sheets]))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships(len(sheets)))
        archive.writestr("xl/sharedStrings.xml", _shared_strings_xml(shared_strings))
        for index, xml in enumerate(sheet_xml, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", xml)
    buffer.seek(0)
    return buffer


def _sheet_xml(
    rows: dict[int, dict[str, object]],
    shared_index: dict[str, int],
    shared_strings: list[str],
) -> str:
    row_xml = []
    for row_number, cells in sorted(rows.items()):
        cell_xml = []
        for column, value in sorted(cells.items(), key=lambda item: _column_index(item[0])):
            ref = f"{column}{row_number}"
            if isinstance(value, str):
                index = _shared_string_index(value, shared_index, shared_strings)
                cell_xml.append(f'<c r="{ref}" t="s"><v>{index}</v></c>')
            else:
                cell_xml.append(f'<c r="{ref}"><v>{value}</v></c>')
        row_xml.append(f'<row r="{row_number}">{"".join(cell_xml)}</row>')

    return (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def _shared_string_index(value: str, shared_index: dict[str, int], shared_strings: list[str]) -> int:
    if value not in shared_index:
        shared_index[value] = len(shared_strings)
        shared_strings.append(value)
    return shared_index[value]


def _column_index(column: str) -> int:
    index = 0
    for letter in column:
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index


def _content_types(sheet_count: int) -> str:
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        f"{sheet_overrides}</Types>"
    )


def _root_relationships() -> str:
    return (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    quote_entities = {'"': "&quot;"}
    sheets = "".join(
        f'<sheet name="{escape(name, quote_entities)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    return (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets}</sheets></workbook>"
    )


def _workbook_relationships(sheet_count: int) -> str:
    sheet_relationships = "".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{sheet_relationships}"
        '<Relationship Id="rIdSharedStrings" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/>'
        "</Relationships>"
    )


def _shared_strings_xml(shared_strings: list[str]) -> str:
    items = "".join(f"<si><t>{escape(value)}</t></si>" for value in shared_strings)
    return (
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">'
        f"{items}</sst>"
    )
