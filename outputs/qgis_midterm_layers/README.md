# QGIS Midterm Layer Pack

중간발표/논문형 지도 제작을 위해 원본 QGIS 레이어를 발표용으로 정리한 패키지입니다.
QGIS에서 아래 순서로 로드하고, `docs/qgis_논문형_시각화_제작안.md`의 스타일을 적용하세요.

## 권장 레이어 순서

1. `00_seoul_boundary.gpkg`
2. `00_admin_dong.gpkg`
3. `00_admin_gu.gpkg`
4. `01_valid_hex_base.gpkg`
5. 지도 목적에 따라 `02_environment_burden_hex.gpkg`, `03_hidden_candidates.gpkg`, `04_hidden_reason_diagnostics.gpkg`, `05_policy_review_candidates.gpkg`, `06_district_hidden_summary.gpkg` 중 하나

## 주의

- `hidden`은 확정 취약지역이 아니라 현장검토 후보입니다.
- `05_policy_review_candidates`는 정책효과 입증이 아니라 상한·진단 후보입니다.
- OSM 배경지도는 발표용 메인 지도에서는 끄는 것을 권장합니다.

## 자동 생성 지도

- `../qgis_midterm_maps/S6_environment_burden.png`
- `../qgis_midterm_maps/S7_hidden_candidates.png`
- `../qgis_midterm_maps/S8_reason_diagnostics.png`
- `../qgis_midterm_maps/S9_policy_review_candidates.png`
