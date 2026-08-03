# QGIS 처리 레시피

모든 거리, buffer, 면적, overlay, 지도 export 작업은 `EPSG:5179`에서 수행한다.

## 원본 레이어 재투영

1. `Processing Toolbox > Vector general > Reproject layer`를 연다.
2. 입력 레이어는 `raw_*` 레이어를 사용한다.
3. Target CRS는 `EPSG:5179`로 설정한다.
4. 출력은 `qgis/wrk_[주제]_5179.gpkg`로 저장한다.
5. 합격 기준: layer properties에서 `EPSG:5179`가 보이고, clip을 같이 하지 않았다면 feature 수가 원본과 같다.

## Geometry 수정

1. `Processing Toolbox > Vector geometry > Fix geometries`를 연다.
2. 입력은 `wrk_*_5179` 레이어를 사용한다.
3. 출력은 `qgis/wrk_[주제]_fixed.gpkg`로 저장한다.
4. feature 수가 변하면 QA 메모에 기록한다.

## EGIS 토지피복도 마스크

1. EGIS 토지피복도를 `EPSG:5179`로 변환한다.
2. 서울시 또는 연구대상 경계로 clip한다.
3. 공식 코드표를 보고 시가지 분석 class를 선택한다.
4. 선택 결과를 `wrk_analysis_mask_classes.gpkg`로 저장한다.
5. `Vector geometry > Dissolve`로 선택 polygon을 dissolve한다.
6. `Fix geometries`를 실행한다.
7. 최종 마스크를 `qgis/out_analysis_mask_5179.gpkg`로 저장한다.
8. 제외된 산림, 수역, 산지 영역은 회색 hatch로 표시한다.

## 250m 생활인구 격자 조인

1. 250m 격자 메타데이터 polygon을 `raw_livingpop_250m_grid`로 불러온다.
2. 일별 또는 월별 생활인구 CSV를 delimited text table로 불러온다.
3. 조인 전에 `250M격자` 키의 자료형과 앞자리 보존 여부를 확인한다.
4. `Layer Properties > Joins` 또는 `Processing > Join attributes by field value`를 사용한다.
5. 조인키는 `250M격자`와 대응되는 격자코드 필드다.
6. 출력은 `qgis/wrk_livingpop_250m_joined.gpkg`로 저장한다.
7. 조인 실패 또는 중복 key는 `qa_livingpop_join_unmatched.gpkg`로 분리한다.

## 경사 이상치 QC

1. `grade_percent`, `grade_abs_percent`, `length_m` 필드가 있는 보행 edge를 불러온다.
2. 다음 조건으로 필터한다.
   - `grade_abs_percent > 100`: 오류 후보
   - `grade_abs_percent > 30 AND grade_abs_percent <= 100`: 비용 cap 또는 수동 검토 후보
   - `length_m <= 0 OR slope_available IS false`: 무효 edge 후보
3. 필터 결과를 `qgis/qa_slope_outliers.gpkg`처럼 실제 저장 위치와 맞는 경로로 저장한다.
4. `qa_reason`, `review_status`, `review_note` 필드를 추가한다.
5. `qa_reason`으로 categorized style을 적용한다.
6. QGIS에서 edge를 삭제한 경우 Python 입력에도 같은 결정을 반영해야 한다. 그렇지 않으면 지도와 계산 결과가 달라진다.

## 결과 지도 export

1. Python 산출물 `out_vulnerability_S0_M3`, `out_hidden_vulnerable_areas`, `out_scenario_results`를 불러온다.
2. `S0-M3`에서 정한 class break를 고정한다. 시나리오마다 자동분류를 새로 하지 않는다.
3. 분석 제외 cell은 회색 hatch로 표시한다.
4. 비용/취약도는 sequential ramp, 개선효과는 diverging ramp를 사용한다.
5. 지도는 `qgis/exports/` 아래 PNG와 PDF로 저장한다.
6. 제목, 날짜, CRS, 자료 출처, 범례, 축척, 북쪽 화살표를 포함한다.

## 외부 검증 overlay

1. TAAS 또는 보행환경 개선사업 위치 레이어를 `EPSG:5179`로 변환한다.
2. 취약지역 결과와 `Join attributes by location` 또는 `Intersection`으로 overlay한다.
3. 불일치 후보를 `qgis/qa/qa_validation_mismatches_[주제].gpkg`로 저장한다.
4. 검증 레이어는 정답지가 아니라 외부 타당도 확인용으로 해석한다.
