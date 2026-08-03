# 결과 지도 제작

## 목적

Python에서 계산한 접근비용, 취약도, 숨은 취약지역(hidden vulnerable areas), 시나리오 개선 효과를 지도화한다. 비교 지도는 반드시 같은 기준으로 분류해야 한다.

## 입력

- `out_analysis_hex.gpkg`
- `out_vulnerability_S0_M3.gpkg`
- `out_walking_cost_M0_M3.gpkg`
- `out_hidden_vulnerable_areas.gpkg`
- `out_scenario_results.gpkg`
- 정류장/지하철 출입구/엘리베이터 레이어
- 분석영역 마스크

## 작업 절차

1. Python 산출물을 `04_outputs` 그룹에 불러온다.
2. 각 레이어 CRS가 `EPSG:5179`인지 확인한다.
3. `S0-M3` 기준 취약 threshold와 class break를 확인한다.
4. 비교 지도에는 QGIS 자동분류를 매번 새로 쓰지 않는다.
5. 지도 종류별 스타일을 적용한다.
   - 접근비용: sequential ramp
   - 취약도: sequential ramp
   - 개선효과: diverging ramp
   - 숨은 취약지역(hidden vulnerable areas): 강조색 + 투명 배경
   - 분석 제외 영역: 회색 hatch
6. 정류장/출입구/엘리베이터는 작고 어두운 점으로 표시해 결과 격자를 가리지 않게 한다.
7. `Layout Manager`에서 지도 레이아웃을 만든다.
8. 제목, 범례, 축척, 북쪽 화살표, CRS, 데이터 기준일, 주석을 넣는다.
9. `qgis/exports/`에 PNG와 PDF를 모두 export한다.

## 출력

```text
qgis/exports/map_accessibility_M0_vs_M3.png
qgis/exports/map_hidden_vulnerable_areas.png
qgis/exports/map_scenario_S1_S3_S4_comparison.png
qgis/exports/map_elderly_weighted_vulnerability.png
```

## 합격 기준

- 비교되는 지도끼리 class break가 동일하다.
- NoData/분석 제외 영역이 낮은 접근성 영역과 구분된다.
- 색상 범례에 단위와 기준선이 적혀 있다.
- 지도에는 `EPSG:5179`, 데이터 기준시점, 시나리오명이 들어 있다.
- export 해상도가 발표/보고서에 사용할 수 있을 정도로 충분하다.

## 자주 생기는 문제

- 각 지도에서 자동분류를 새로 해서 시나리오 비교가 왜곡되는 경우
- 취약도 낮음과 분석 제외가 같은 색으로 보이는 경우
- 정류장 점이 너무 커서 hex 결과를 가리는 경우
- `M0`, `M3`, `S0-M3` 기준을 지도 제목에 명시하지 않는 경우
