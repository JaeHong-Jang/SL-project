"""서로 다른 POI 원자료를 공통 시설 record로 정리한다."""

from __future__ import annotations


def normalize_poi_record(row: dict, poi_type: str) -> dict:
    """상권/의료/복지 POI의 다른 컬럼명을 공통 스키마로 맞춘다."""
    return {
        "poi_id": row.get("기관ID") or row.get("상가업소번호") or row.get("연번"),
        "poi_type": poi_type,
        "name": row.get("기관명") or row.get("상호명") or row.get("기관명칭"),
        "category": row.get("병원분류명") or row.get("상권업종대분류명") or row.get("시설종류"),
        "lon": row.get("lon"),
        "lat": row.get("lat"),
    }
