# 보행 네트워크 경사 이상치 QC

## 목적

보행망 edge의 경사값에는 DEM 오차, 짧은 edge, 교량/터널, 계단, 좌표 불일치 때문에 비정상 값이 섞일 수 있다. 실제 확인 결과 `grade_abs_percent` 최대값이 600% 이상으로 나타났으므로, 이상치 확인 절차가 반드시 필요하다.

## 입력

- `data/walking_network_edges_with_slope_google.csv`
- `data/walking_network_nodes_with_elevation.csv`
- 분석영역 마스크
- 필요 시 DEM, 등고선, 도로/보행로 기준 레이어

## 작업 절차

1. edge CSV를 QGIS에 불러오고 `geometry_wkt`를 line geometry로 인식시킨다.
2. 레이어 CRS를 `EPSG:5179`로 지정한다.
3. `grade_percent`, `grade_abs_percent`, `length_m`, `slope_available` 필드를 확인한다.
4. 다음 조건으로 필터를 만든다.
   - `grade_abs_percent > 100`: 오류 후보, 기본 분석 제외
   - `grade_abs_percent > 30 AND grade_abs_percent <= 100`: 비용함수 cap 후보
   - `length_m <= 0`: 잘못된 edge 후보
   - `slope_available = false`: 경사 미확보 후보
5. 필터 결과를 `qgis/qa_slope_outliers_gt100.gpkg`, `qgis/qa_slope_outliers_30_100.gpkg`로 나누어 저장한다.
6. `qa_reason`, `review_status`, `review_note` 필드를 추가한다.
7. `qa_reason` 기준으로 categorized style을 적용한다.
8. outlier가 교량, 터널, 산지, 짧은 edge, DEM 경계에서 집중되는지 육안 검수한다.
9. 판단은 `keep`, `cap`, `exclude`, `field_check` 중 하나로 기록한다.
10. Python 쪽 cost function에서는 `>100%` edge를 제외하고, `30~100%` edge는 원본 값은 보존하되 비용 산정에만 30% cap을 적용한다.

## 출력

```text
qgis/wrk_network_5179.gpkg
qgis/qa_slope_outliers_gt100.gpkg
qgis/qa_slope_outliers_30_100.gpkg
qgis/qa_network_slope_review_decisions.gpkg
qgis/out_network_slope_qc_5179.gpkg
```

## 현재 QC 결과 기록

2026-05-12 QGIS에서 보행망 edge CSV를 WKT 라인 레이어로 불러와 이상치 후보를 분리했다.

| 저장 레이어 | 조건 | 피처 수 | 해석 |
|---|---:|---:|---|
| `qgis/qa_slope_outliers_gt100.gpkg` | `grade_abs_percent > 100` | 30 | 데이터 오류 후보. 기본 분석에서는 제외한다. |
| `qgis/qa_slope_outliers_30_100.gpkg` | `grade_abs_percent > 30 AND grade_abs_percent <= 100` | 2,970 | 삭제하지 않고 비용 산정 시 30% cap을 적용할 후보. 지도에서는 경사 검토 후보로 유지한다. |

## Python 하네스 연계

- `qa_slope_outliers_gt100.gpkg`의 30개 edge는 비용 계산에서 제외한다.
- `qa_slope_outliers_30_100.gpkg`의 2,970개 edge는 삭제하지 않고 비용 계산에서 30% cap을 적용한다.
- 다음 하네스 단계는 전체 walking edges CSV를 chunk/lazy 방식으로 읽어 `data/interim/walking_edge_costs.parquet`를 생성하는 것이다.
- Parquet 생성 후 Dijkstra용 O/D 스냅으로 넘어간다.

Python 전체 비용 테이블 생성 결과:

```text
원본 edge: 467,556행
제외: grade_abs_percent > 100 후보 30행 + 경사 결측 900행
비용 테이블: data/interim/walking_edge_costs.parquet, 466,626행
```

## 합격 기준

- outlier 조건과 임계값이 문서에 기록되어 있다.
- `>100%` edge는 오류 후보로 별도 분리되어 있다.
- `30~100%` edge는 자동 삭제하지 않고 30% cap/manual review 후보로 남아 있다.
- edge 삭제가 필요한 경우 Python 입력에도 같은 결정이 반영된다.
- 네트워크 연결성이 무너지는 수동 삭제를 하지 않는다.

## 자주 생기는 문제

- percent 경사를 degree 경사로 오해하는 경우
- 아주 짧은 edge에서 경사가 과장되는 경우
- 교량/터널이 지표면 DEM 값을 받아 비정상 경사가 되는 경우
- QGIS에서 edge를 삭제했지만 Python 입력 CSV에는 반영하지 않는 경우
