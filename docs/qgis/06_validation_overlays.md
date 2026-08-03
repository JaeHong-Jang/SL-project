# 외부 검증 레이어 Overlay

## 목적

TAAS 보행자 사고다발지역, 보행환경 개선사업 위치, 민원/제설 취약구간 등 외부 자료와 취약지역 결과를 겹쳐 본다. 이 작업은 정답 검증이 아니라 외부 타당도와 해석 보강을 위한 것이다.

## 입력

- `out_vulnerability_S0_M3.gpkg`
- `out_hidden_vulnerable_areas.gpkg`
- `out_scenario_results.gpkg`
- TAAS 보행자 사고다발지역
- 보행환경 개선사업 위치
- 필요 시 민원, 제설취약구간, 현장확인 후보지

## 작업 절차

1. 외부 검증 레이어를 `raw_validation_[topic]`으로 불러온다.
2. CRS를 확인하고 `EPSG:5179`로 변환해 `wrk_validation_[topic]_5179`로 저장한다.
3. 취약지역 결과 레이어와 함께 overlay한다.
4. 점 자료는 `Join attributes by location`으로 hex에 붙인다.
5. 면 자료는 `Intersection` 또는 `Join attributes by location summary`를 사용한다.
6. 겹치는 지역, 겹치지 않는 고취약 지역, 외부자료는 있으나 취약도가 낮은 지역을 각각 분리한다.
7. 불일치 후보를 `qa_validation_mismatches_[topic].gpkg`로 저장한다.
8. 결과 해석에는 “접근성 취약성과 사고 발생은 1:1 정답 관계가 아님”을 명시한다.

## 출력

```text
qgis/wrk_validation_taas_5179.gpkg
qgis/qa/qa_validation_mismatches_taas.gpkg
qgis/qa/qa_validation_summary_taas.gpkg
qgis/exports/map_validation_taas_overlay.png
```

## 합격 기준

- 외부 검증 레이어와 취약지역 레이어가 모두 `EPSG:5179`이다.
- overlay 방식과 predicate가 기록되어 있다.
- 일치/불일치 사례가 모두 남아 있다.
- 검증 결과를 정답률처럼 표현하지 않는다.
- 지도와 표에 자료 기준연도와 출처가 적혀 있다.

## 자주 생기는 문제

- 사고다발지역을 접근성 취약지역의 정답지처럼 해석하는 경우
- 좌표계가 다른 점 자료를 그대로 overlay하는 경우
- 겹치지 않는 결과를 모두 오류로 취급하는 경우
- 외부자료의 기준연도와 분석연도가 맞지 않는 점을 누락하는 경우
