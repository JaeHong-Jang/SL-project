"""서울시 등록인구 XLSX를 추가 Excel 엔진 없이 읽는 파서.

서울시 등록인구 원본은 여러 시트와 병합 헤더를 가진 XLSX다. 현재 환경에는
`openpyxl`이 필수 의존성으로 들어 있지 않으므로, 이 모듈은 XLSX 내부의 ZIP/XML
구조를 직접 읽어 행정동 단위 총등록인구와 65세 이상 등록인구를 정규화한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import posixpath
import re
from typing import BinaryIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import geopandas as gpd
import pandas as pd


REGISTERED_POPULATION_COLUMNS = [
    "admin_name",
    "district_name",
    "registered_population",
    "registered_senior_population",
    "registered_senior_share",
]

REGISTERED_ADMIN_LAYER_COLUMNS = [
    "BASE_DATE",
    "district_code",
    "district_name",
    "admin_code",
    "admin_name",
    "registered_population",
    "registered_senior_population",
    "registered_senior_share",
    "registered_source_names",
]

SEOUL_DISTRICT_CODE_TO_NAME = {
    "11010": "종로구",
    "11020": "중구",
    "11030": "용산구",
    "11040": "성동구",
    "11050": "광진구",
    "11060": "동대문구",
    "11070": "중랑구",
    "11080": "성북구",
    "11090": "강북구",
    "11100": "도봉구",
    "11110": "노원구",
    "11120": "은평구",
    "11130": "서대문구",
    "11140": "마포구",
    "11150": "양천구",
    "11160": "강서구",
    "11170": "구로구",
    "11180": "금천구",
    "11190": "영등포구",
    "11200": "동작구",
    "11210": "관악구",
    "11220": "서초구",
    "11230": "강남구",
    "11240": "송파구",
    "11250": "강동구",
}

REGISTERED_ADMIN_JOIN_ALIASES = {
    # 등록인구 표에는 동대문구 용신동의 일부가 용두동/신설동으로 따로 잡힌다.
    # 현재 행정동 경계는 용신동 하나만 있으므로 세 행을 합산해 공간 배분한다.
    ("동대문구", "용두동"): ("동대문구", "용신동"),
    ("동대문구", "신설동"): ("동대문구", "용신동"),
}

SEOUL_DISTRICTS = {
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구",
}
SEOUL_TOTAL_NAMES = {"서울시", "서울특별시"}

_SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS = {"x": _SPREADSHEET_NS, "r": _REL_NS, "pr": _PACKAGE_REL_NS}
_REL_ID_ATTR = f"{{{_REL_NS}}}id"
_CELL_REF_RE = re.compile(r"([A-Z]+)")


@dataclass(frozen=True)
class _Sheet:
    """워크북 안의 시트 이름과 실제 XML 경로를 함께 보관한다."""

    name: str
    path: str


@dataclass(frozen=True)
class _PopulationLayout:
    """등록인구 표에서 필요한 열 위치와 데이터 시작 행을 나타낸다."""

    name_col: int
    population_col: int
    senior_col: int
    data_start: int


def parse_registered_population_xlsx(
    path: str | Path | BinaryIO,
    *,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """서울시 등록인구 XLSX에서 행정동별 총인구와 65세 이상 인구를 추출한다.

    원본의 ``2-1. 세대 및 인구상세`` 시트는 자치구 소계 행 다음에 행정동 행이
    이어지는 구조다. 그래서 자치구명은 직전 자치구 소계 행에서 물려받고,
    서울시 합계와 자치구 합계는 제외한 행정동 428개만 반환한다.
    """
    with ZipFile(path) as workbook:
        return _parse_registered_population_workbook(workbook, sheet_name=sheet_name, source=str(path))


def build_registered_population_admin_layer(
    boundary_path: str | Path,
    population: pd.DataFrame,
    *,
    boundary_layer: str | None = None,
    boundary_encoding: str = "cp949",
    target_crs: int | str = 5179,
) -> tuple[gpd.GeoDataFrame, dict[str, object]]:
    """전국 행정동 경계에서 서울만 남기고 등록인구 표를 조인한다.

    SGIS 행정동 경계는 `ADM_CD` 앞 두 자리가 11이면 서울이다. 등록인구 원표는
    `가양제1동`처럼 "제"가 들어간 표기와 동대문구 `용두동`/`신설동` 보조 행을
    포함하므로, 공간 배분 전에 경계명과 맞는 형태로 정리한 뒤 합산한다.
    """
    boundary_path = Path(boundary_path)
    read_kwargs = {}
    if boundary_layer is not None:
        read_kwargs["layer"] = boundary_layer
    if boundary_path.suffix.lower() == ".shp":
        read_kwargs["encoding"] = boundary_encoding

    boundary = gpd.read_file(boundary_path, **read_kwargs)
    _require_columns(boundary, ["ADM_CD", "ADM_NM", "geometry"], "admin boundary")
    _require_columns(population, REGISTERED_POPULATION_COLUMNS, "registered population")

    seoul = boundary[boundary["ADM_CD"].astype(str).str.startswith("11")].copy()
    seoul["district_code"] = seoul["ADM_CD"].astype(str).str[:5]
    seoul["district_name"] = seoul["district_code"].map(SEOUL_DISTRICT_CODE_TO_NAME)
    seoul["admin_code"] = seoul["ADM_CD"].astype(str)
    seoul["admin_name"] = seoul["ADM_NM"].astype(str).str.strip()
    seoul["admin_name_key"] = seoul["admin_name"].map(_boundary_admin_name_key)

    prepared_population = _prepare_registered_population_for_boundary(population)
    aggregated_population = _aggregate_registered_population_for_boundary(prepared_population)

    joined = seoul.merge(
        aggregated_population,
        left_on=["district_name", "admin_name_key"],
        right_on=["district_name", "admin_name_key"],
        how="left",
        validate="one_to_one",
    )
    missing_population = joined["registered_population"].isna()
    if missing_population.any():
        missing_rows = joined.loc[missing_population, ["district_name", "admin_name"]].to_dict("records")
        raise ValueError(f"Registered population is missing for admin boundaries: {missing_rows}")

    joined["registered_population"] = joined["registered_population"].astype(float)
    joined["registered_senior_population"] = joined["registered_senior_population"].astype(float)
    joined["registered_senior_share"] = (
        joined["registered_senior_population"] / joined["registered_population"].where(joined["registered_population"] > 0)
    )
    output = joined[[*REGISTERED_ADMIN_LAYER_COLUMNS, "geometry"]].to_crs(target_crs)

    boundary_keys = set(zip(seoul["district_name"], seoul["admin_name_key"]))
    population_keys = set(zip(aggregated_population["district_name"], aggregated_population["admin_name_key"]))
    qa_report = {
        "boundary_source": boundary_path.as_posix(),
        "source_crs": str(boundary.crs),
        "output_crs": str(output.crs),
        "national_admin_count": int(len(boundary)),
        "seoul_admin_count": int(len(seoul)),
        "joined_admin_count": int(len(output)),
        "registered_population_input_rows": int(len(population)),
        "registered_population_join_rows": int(len(aggregated_population)),
        "registered_population_input_sum": int(population["registered_population"].sum()),
        "registered_senior_population_input_sum": int(population["registered_senior_population"].sum()),
        "registered_population_joined_sum": int(output["registered_population"].sum()),
        "registered_senior_population_joined_sum": int(output["registered_senior_population"].sum()),
        "population_only_keys": sorted([list(key) for key in population_keys - boundary_keys]),
        "boundary_only_keys": sorted([list(key) for key in boundary_keys - population_keys]),
        "alias_rules": [
            {"from": list(source), "to": list(target)}
            for source, target in REGISTERED_ADMIN_JOIN_ALIASES.items()
        ],
        "status": "joined: Seoul admin boundary + registered population",
    }
    return output, qa_report


def _parse_registered_population_workbook(
    workbook: ZipFile,
    *,
    sheet_name: str | None = None,
    source: str = "<workbook>",
) -> pd.DataFrame:
    """워크북에서 등록인구 표가 있는 시트를 찾아 표준 컬럼 DataFrame으로 만든다."""
    shared_strings = _read_shared_strings(workbook)
    sheets = _read_workbook_sheets(workbook)
    candidates = _candidate_sheets(sheets, sheet_name)

    for sheet in candidates:
        rows = list(_iter_sheet_rows(workbook, sheet.path, shared_strings))
        layout = _find_population_layout(rows)
        if layout is None:
            continue
        return pd.DataFrame(_parse_population_rows(rows, layout), columns=REGISTERED_POPULATION_COLUMNS)

    target = f" named {sheet_name!r}" if sheet_name else ""
    raise ValueError(f"Could not find a registered population sheet{target} in {source}.")


def _read_workbook_sheets(workbook: ZipFile) -> list[_Sheet]:
    """workbook.xml 관계 정보를 풀어 각 시트의 XML 파트를 찾는다."""
    workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
    relationships_xml = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    relationship_targets = {
        relationship.attrib["Id"]: _resolve_part_path("xl/workbook.xml", relationship.attrib["Target"])
        for relationship in relationships_xml.findall("pr:Relationship", _NS)
    }

    sheets: list[_Sheet] = []
    for sheet in workbook_xml.findall(".//x:sheet", _NS):
        relationship_id = sheet.attrib[_REL_ID_ATTR]
        sheets.append(_Sheet(name=sheet.attrib["name"], path=relationship_targets[relationship_id]))
    return sheets


def _candidate_sheets(sheets: list[_Sheet], sheet_name: str | None) -> list[_Sheet]:
    """명시 시트가 없으면 등록인구 원본에서 쓰는 2-1 시트를 먼저 시도한다."""
    if sheet_name is not None:
        matches = [sheet for sheet in sheets if sheet.name == sheet_name]
        if not matches:
            raise ValueError(f"Sheet {sheet_name!r} was not found.")
        return matches

    preferred = [
        sheet
        for sheet in sheets
        if ("세대" in sheet.name and "인구상세" in sheet.name) or sheet.name.startswith("2-1")
    ]
    preferred_paths = {sheet.path for sheet in preferred}
    return preferred + [sheet for sheet in sheets if sheet.path not in preferred_paths]


def _resolve_part_path(base_path: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(base_path), target))


def _read_shared_strings(workbook: ZipFile) -> list[str]:
    """XLSX sharedStrings.xml을 읽어 셀 문자열 인덱스를 실제 값으로 바꿀 준비를 한다."""
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []

    shared_xml = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    return [
        "".join(text_node.text or "" for text_node in item.findall(".//x:t", _NS))
        for item in shared_xml.findall("x:si", _NS)
    ]


def _iter_sheet_rows(workbook: ZipFile, sheet_path: str, shared_strings: list[str]) -> list[list[object]]:
    """시트 XML의 셀 주소를 0 기반 열 위치로 맞춰 행 단위 값을 생성한다."""
    sheet_xml = ET.fromstring(workbook.read(sheet_path))
    for row in sheet_xml.findall(".//x:sheetData/x:row", _NS):
        values: list[object] = []
        for cell in row.findall("x:c", _NS):
            cell_ref = cell.attrib.get("r", "")
            column_index = _column_index(cell_ref)
            while len(values) <= column_index:
                values.append("")
            values[column_index] = _cell_value(cell, shared_strings)
        yield values


def _column_index(cell_ref: str) -> int:
    match = _CELL_REF_RE.match(cell_ref)
    if match is None:
        return 0

    index = 0
    for letter in match.group(1):
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index - 1


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> object:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text_node.text or "" for text_node in cell.findall(".//x:t", _NS))

    value = cell.find("x:v", _NS)
    if value is None or value.text is None:
        return ""

    text = value.text
    if cell_type == "s":
        return shared_strings[int(text)]
    if cell_type == "b":
        return text == "1"
    return _parse_number(text)


def _parse_number(text: str) -> object:
    try:
        value = float(text)
    except ValueError:
        return text
    if math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def _find_population_layout(rows: list[list[object]]) -> _PopulationLayout | None:
    """상단 헤더에서 행정동명, 총인구, 65세 이상 총인구 열을 찾아낸다."""
    for row_index, row in enumerate(rows[:40]):
        normalized = [_normalize_header(value) for value in row]
        name_col = _first_matching_index(normalized, {"구분", "지역", "행정동"})
        population_col = _first_matching_index(normalized, {"총인구", "총계", "전체"})
        senior_col = next(
            (
                index
                for index, value in enumerate(normalized)
                if value.startswith("65세이상") and "총인구" in value
            ),
            None,
        )
        if name_col is None or population_col is None or senior_col is None:
            continue

        next_row = rows[row_index + 1] if row_index + 1 < len(rows) else []
        data_start = row_index + 2 if _is_subheader_row(next_row, population_col, senior_col) else row_index + 1
        return _PopulationLayout(
            name_col=name_col,
            population_col=population_col,
            senior_col=senior_col,
            data_start=data_start,
        )
    return None


def _first_matching_index(values: list[str], targets: set[str]) -> int | None:
    for index, value in enumerate(values):
        if value in targets:
            return index
    return None


def _normalize_header(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def _is_subheader_row(row: list[object], population_col: int, senior_col: int) -> bool:
    subheaders = {"계", "소계", "총계"}
    return (
        _normalize_header(_value_at(row, population_col)) in subheaders
        or _normalize_header(_value_at(row, senior_col)) in subheaders
    )


def _parse_population_rows(rows: list[list[object]], layout: _PopulationLayout) -> list[dict[str, object]]:
    """서울시/자치구 합계 행을 제외하고 행정동 레코드만 추출한다."""
    records: list[dict[str, object]] = []
    current_district: str | None = None

    for row in rows[layout.data_start :]:
        name = str(_value_at(row, layout.name_col) or "").strip()
        population = _to_int(_value_at(row, layout.population_col))
        senior_population = _to_int(_value_at(row, layout.senior_col))
        if not name or (population is None and senior_population is None):
            continue
        if name in SEOUL_TOTAL_NAMES:
            current_district = None
            continue
        if name in SEOUL_DISTRICTS:
            # 자치구 소계 행은 이후 행정동의 district_name으로만 사용한다.
            current_district = name
            continue

        records.append(
            {
                "admin_name": name,
                "district_name": current_district,
                "registered_population": population,
                "registered_senior_population": senior_population,
                "registered_senior_share": _safe_share(senior_population, population),
            }
        )

    return records


def _value_at(row: list[object], index: int) -> object:
    return row[index] if index < len(row) else ""


def _to_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else None

    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _safe_share(senior_population: int | None, population: int | None) -> float | None:
    if senior_population is None or not population:
        return None
    return senior_population / population


def _require_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def _boundary_admin_name_key(value: object) -> str:
    """경계 레이어 이름을 조인용 키로 정리한다."""
    return _standardize_admin_name(value)


def _registered_admin_name_key(value: object) -> str:
    """등록인구 표의 `제1동` 표기를 경계 레이어의 `1동` 표기로 맞춘다."""
    standardized = _standardize_admin_name(value)
    return re.sub(r"제(?=\d)", "", standardized)


def _standardize_admin_name(value: object) -> str:
    return str(value or "").strip().replace(" ", "").replace("·", ".").replace("ㆍ", ".")


def _prepare_registered_population_for_boundary(population: pd.DataFrame) -> pd.DataFrame:
    prepared = population.copy()
    join_districts: list[str] = []
    join_admin_keys: list[str] = []

    for row in prepared.itertuples(index=False):
        district_name = str(row.district_name)
        admin_name = str(row.admin_name)
        target_district, target_admin = REGISTERED_ADMIN_JOIN_ALIASES.get(
            (district_name, admin_name),
            (district_name, admin_name),
        )
        join_districts.append(target_district)
        join_admin_keys.append(_registered_admin_name_key(target_admin))

    prepared["join_district_name"] = join_districts
    prepared["admin_name_key"] = join_admin_keys
    return prepared


def _aggregate_registered_population_for_boundary(population: pd.DataFrame) -> pd.DataFrame:
    """경계 하나에 여러 등록인구 행이 대응되면 합산해 총량을 보존한다."""
    grouped = (
        population.groupby(["join_district_name", "admin_name_key"], as_index=False)
        .agg(
            registered_population=("registered_population", "sum"),
            registered_senior_population=("registered_senior_population", "sum"),
            registered_source_names=("admin_name", lambda names: ",".join(sorted(set(map(str, names))))),
        )
        .rename(columns={"join_district_name": "district_name"})
    )
    grouped["registered_senior_share"] = (
        grouped["registered_senior_population"]
        / grouped["registered_population"].where(grouped["registered_population"] > 0)
    )
    return grouped
