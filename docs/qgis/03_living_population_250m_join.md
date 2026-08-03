# 250m 생활인구 격자 조인

## 목적

보유한 생활인구 CSV에는 `250M격자` 코드가 있지만 공간좌표가 직접 들어 있지 않다. 따라서 250m 격자 메타데이터 또는 격자 polygon을 확보한 뒤, 격자코드 기준으로 조인해야 한다.

## 입력

- 250m 생활인구 CSV: `data/250_LOCAL_RESD_202511/*.csv`
- 250m 격자 메타데이터 또는 polygon 레이어
- 분석영역 마스크: `out_analysis_mask_5179`
- 행정동 경계

## 작업 절차

1. 250m 격자 polygon을 `raw_livingpop_250m_grid`로 불러온다.
2. 격자 레이어 CRS를 확인하고 `EPSG:5179`로 변환해 `wrk_livingpop_250m_grid_5179`로 저장한다.
3. 생활인구 CSV를 QGIS에서 delimited text table로 불러온다.
4. 조인키가 `250M격자`와 정확히 대응하는지 확인한다.
5. 조인키가 숫자로 변환되어 앞자리 또는 한글 코드가 깨지지 않았는지 확인한다.
6. `Layer Properties > Joins` 또는 `Processing Toolbox > Vector general > Join attributes by field value`를 사용해 격자 polygon에 생활인구 값을 붙인다.
7. 조인 실패 격자를 `qa_livingpop_join_unmatched.gpkg`로 저장한다.
8. 중복 조인키가 있으면 `qa_livingpop_duplicate_join_check.gpkg`로 저장한다.
9. 분석영역 마스크로 clip하거나, 마스크 밖 격자에 `analysis_status = excluded`를 부여한다.
10. 최종 조인 레이어를 `qgis/out_livingpop_250m_join_5179.gpkg`로 저장한다.

## 출력

```text
qgis/wrk_livingpop_250m_grid_5179.gpkg
qgis/wrk_livingpop_250m_joined.gpkg
qgis/qa/qa_livingpop_join_unmatched.gpkg
qgis/qa/qa_livingpop_duplicate_join_check.gpkg
qgis/out_livingpop_250m_join_5179.gpkg
```

## 합격 기준

- 격자 polygon과 최종 조인 레이어가 `EPSG:5179`이다.
- `250M격자` 조인키가 문자열로 유지된다.
- 조인 실패 건수가 0이거나, 실패 원인이 설명되어 있다.
- 생활인구 값이 문자열이 아니라 숫자형으로 변환 가능하다.
- 분석영역 밖 격자는 삭제 또는 제외 표시가 일관되게 적용되어 있다.

## 자주 생기는 문제

- 격자코드가 숫자로 읽혀 leading zero 또는 한글 코드가 깨지는 경우
- 생활인구 CSV 인코딩을 `utf-8`로 읽어 깨지는 경우
- 시간대별 여러 행을 그대로 조인해 polygon이 중복되는 경우
- 격자 메타데이터 없이 생활인구를 hex에 직접 붙이려는 경우

## 현재 프로젝트 주의사항

현재 확인 결과 생활인구 파일은 `cp949` 또는 `euc-kr`로 읽어야 한다. `configs/data_sources.yaml`에는 `cp949`로 반영되어 있다.

## 현재 완료 기록

2026-05-13 기준 `match` 레이어를 서울 250m 격자 polygon으로 확인했고, 다음 파일로 저장했다.

```text
qgis/wrk_livingpop_250m_grid_5179.gpkg
```

격자 polygon의 조인키는 `CELL_ID`이며, 생활인구 CSV의 `250M격자`와 같은 코드 체계다.

Python 하네스에서 30일치 CSV를 격자당 1행으로 집계한 뒤 조인했다.

```text
data/interim/local_resident_250m_grid_summary.parquet
qgis/out_livingpop_250m_join_5179.gpkg
qgis/qa_livingpop_grid_without_population.gpkg
outputs/reports/livingpop_250m_join_qa.json
```

QA 결과:

```text
격자 polygon: 10,125개
생활인구 요약 격자: 8,600개
조인 성공: 8,599개
생활인구 없는 polygon: 1,526개
CSV에는 있으나 polygon에는 없는 격자: 1개(다사67254075)
```
