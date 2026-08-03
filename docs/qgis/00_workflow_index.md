# QGIS 작업 흐름 인덱스

이 폴더는 Python으로 자동화하기보다 QGIS에서 직접 확인하는 편이 더 안전한 GIS 작업을 정리한 매뉴얼이다. 원본 데이터는 수정하지 않고, QGIS에서 만든 결과는 `qgis/` 아래에 저장한다.

## QGIS가 담당하는 작업

QGIS에서 처리하거나 확인할 작업은 다음과 같다.

1. 프로젝트 좌표계(`EPSG:5179`) 설정과 레이어 그룹 정리
2. EGIS 토지피복도를 이용한 분석영역 마스크 생성과 육안 검수
3. 250m 생활인구 격자 메타데이터와 생활인구 CSV의 조인 검수
4. 보행 네트워크 경사 이상치 확인과 `keep/cap/exclude` 판단
5. Python 산출물을 이용한 최종 지도 제작
6. TAAS, 보행환경 개선사업, 현장확인 후보지 등 외부 검증 레이어 overlay

Python이 담당하는 작업은 다음과 같다.

1. 반복 가능한 표 정리, 데이터 계약 검증, 인코딩 처리
2. 비용함수, Dijkstra 접근성 계산, 시나리오 지표, `S0-M3` 고정 정규화
3. QGIS에서 바로 열 수 있는 GeoPackage, GeoJSON, CSV 산출

## 권장 작업 순서

1. `01_project_setup.md`: QGIS 프로젝트와 좌표계 설정
2. `02_analysis_mask_egis_landcover.md`: EGIS 토지피복도 기반 분석영역 마스크
3. `03_living_population_250m_join.md`: 250m 생활인구 격자 조인
4. `04_network_slope_outlier_qc.md`: 보행 네트워크 경사 이상치 검수
5. Python에서 접근성/취약성/시나리오 산출
6. `05_result_maps.md`: 결과 지도 제작
7. `06_validation_overlays.md`: 외부 검증 레이어 overlay

## 공통 설정

- 프로젝트 CRS: `EPSG:5179`
- 원본 레이어는 읽기 전용으로 취급
- QGIS 임시 레이어는 최종 분석에 사용하지 않음
- 비교 지도는 `S0-M3` 기준 class break를 고정
- 분석 제외/NoData 영역은 낮은 접근성 영역과 다른 스타일로 표시

## 레이어 이름 규칙

- `raw_`: 원본 또는 원본 복사본
- `wrk_`: 처리 중간 산출물
- `qa_`: 검수, 오류, 의심 후보 레이어
- `out_`: 분석/보고서에 들어가는 최종 산출물
- `map_`: 레이아웃 또는 지도 export 산출물

예시:

```text
raw_egis_landcover
wrk_analysis_mask_classes
qa_slope_outliers
out_vulnerability_S0_M3
map_hidden_vulnerable_areas
```

## Python에서 QGIS로 넘겨야 하는 파일

최종 지도 작업 전에는 다음 파일이 `qgis/` 또는 `outputs/` 아래에 준비되어 있어야 한다.

```text
out_analysis_hex.gpkg
out_walking_cost_M0_M3.gpkg
out_vulnerability_S0_M3.gpkg
out_hidden_vulnerable_areas.gpkg
out_scenario_results.gpkg
qa_slope_outliers.gpkg
```

이 파일들이 아직 없다면 QGIS 작업은 최종 지도 제작이 아니라 마스크, 격자 조인, 네트워크 경사 QC까지만 진행한다.

## 현재 QGIS 검수 대상

2026-05-12 기준 Python 하네스에서 다음 레이어를 생성했다.

```text
qgis/out_analysis_hex_h3res9.gpkg
  - out_analysis_hex_h3res9: H3 res 9 분석 hex 4,551개
  - out_analysis_hex_centroids_h3res9: O 스냅 후보 중심점 4,551개

qgis/out_transit_d_candidates.gpkg
  - out_transit_d_candidates: 서울 경계 내부 버스/지하철 D 후보 10,967개
  - qa_transit_d_candidates_outside_boundary: 서울 경계 밖 QA 후보 84개
```

QGIS에서는 이 레이어들이 `out_analysis_mask_5179_fixed` 안팎에 합리적으로 배치되는지 먼저 확인한다. 메인 D 후보는 서울 경계 안으로 제한하고, 경계 밖 후보는 QA 레이어로 남겨 경계 buffer 시나리오나 자료 오류 검토에 사용한다.
