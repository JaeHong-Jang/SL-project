# v2.2 S1/S3/S4 반사실 runner 팀 검토 결론

실행일: 2026-05-31

## 팀장 결론

새 runner 기반 레이어를 기준으로 하면 이제 QGIS 시각화 검수 단계로 넘어갈 수 있다. 다만 지도 제목과 보고서 문장은 반드시 manifest의 claim label을 따라야 한다.

- S1은 최종 정책효과가 아니다. 48개 후보 정류장을 모두 동시에 목적지로 추가한 Dijkstra 재탐색 상한선이다.
- S3은 하나의 명확한 가정에 대해서는 공식 반사실 효과로 볼 수 있다. 가정은 `grade_abs_percent > 30`인 모든 edge를 15% 경사 cap으로 재계산하고 Dijkstra를 다시 돌린다는 것이다. 하지만 실제 hidden 해소 효과는 0이다.
- S4는 국지적 쉘터, 제설, 배수시설 효과가 아니다. M3 baseline에서 기상항을 제거한 M1 비용으로 재탐색한 도시 전체 weather-component 상한선이다.

따라서 결론은 "시각화는 가능하지만, 해석은 제한적으로 해야 한다"이다. S1/S4는 효과가 아니라 상한선이고, S3은 효과 산출물 형식은 갖췄지만 결과가 부정적이다.

## 팀원별 검토 결론

| 역할 | 판정 | 근거 |
|---|---|---|
| 팀원1. 데이터 분석·시각화 | PASS with label 조건 | 새 QGIS runner 레이어는 모두 4,383행, EPSG:5179, empty geometry 0이다. resolved hidden 행의 행정 라벨 누락도 없다. |
| 팀원2. 분석 방향 | PASS | 결과는 고정된 잠재수요 위에서 접근비용·취약부담이 얼마나 바뀌는지 보는 것이다. 승하차 수요예측이나 실제 수요 분산 예측이 아니다. |
| 팀원3. 데이터 전처리 | PASS with caveat | 공통 네트워크 입력은 충분하다. S3 개선 edge도 `qgis/S3_improved_edges_cap15.gpkg`로 2,970개 명시됐다. |
| 팀원4. 모델 설계 | PASS | `FrozenBaseline`이 runner와 연결됐고, hex별 `ΔV`, `Δrank`, manifest가 생성됐다. |
| 팀원5. 방법론 비판 | CONDITIONAL PASS | S1/S4는 여전히 상한선이다. S3은 형식상 반사실 효과지만 효과 크기가 사실상 매우 작고 hidden 해소가 없다. |
| 팀원6. 참고문헌·외부 근거 | PASS | 접근성 반사실 평가는 수요예측 없이도 가능하다. 단, claim은 travel cost/accessibility 변화에 한정해야 한다. |

## runner 산출 결과

| 시나리오 | output label | path re-search | hidden baseline -> scenario | resolved hidden | 고령가중 평균 비용 감소 | 해석 |
|---|---|---:|---:|---:|---:|---|
| S1 | `upper_bound` | true | 632 -> 583 | 49 | 4.746 m | 48개 후보를 모두 동시에 넣으면 일부 hidden 부담이 줄어든다. 하지만 설치 가능성·운영 가능성은 검증되지 않았다. |
| S3 | `counterfactual_effect` | true | 632 -> 632 | 0 | 0.200 m | 도시 전체 grade>30 edge를 cap15로 낮춰도 비용이 바뀌는 hex는 45개뿐이고 hidden 해소는 없다. |
| S4 | `upper_bound` | true | 632 -> 530 | 102 | 12.408 m | 기상항을 도시 전체에서 제거하면 부담 완화가 크다. 하지만 이 값은 지역별 쉘터·제설·배수 정책효과로 직접 주장하면 안 된다. |

## 생성된 산출물

- `outputs/reports/scenario_counterfactual/scenario_counterfactual_registry.csv`
- `outputs/reports/scenario_counterfactual/S1_delta_vulnerability.csv`
- `outputs/reports/scenario_counterfactual/S3_delta_vulnerability.csv`
- `outputs/reports/scenario_counterfactual/S4_weather_off_delta_vulnerability.csv`
- `outputs/reports/scenario_counterfactual/*manifest.json`
- `qgis/S1_delta_vulnerability_runner.gpkg`
- `qgis/S3_delta_vulnerability_runner.gpkg`
- `qgis/S3_improved_edges_cap15.gpkg`
- `qgis/S4_weather_off_delta_vulnerability_runner.gpkg`

## 방법론적으로 방어 가능한 이유

runner는 `demand_index_final`을 고정하고 공급·비용 측면만 바꾼다. 그래서 이 분석이 답하는 질문은 다음이다.

> 같은 잠재 수요압력에서 정책 네트워크 또는 비용 조건을 바꾸면 보행 접근비용과 취약부담이 줄어드는가?

반대로 이 분석이 답하지 않는 질문은 다음이다.

> 실제 승객이 증가하는가? 이용수요가 다른 정류장으로 분산되는가? 모드 전환이 발생하는가?

사용한 수식은 프로젝트 목적에 맞다.

- `FrozenBaseline`은 S0-M3 기준 정규화와 취약 threshold를 고정한다. 그래서 시나리오마다 척도를 다시 맞춰서 개선이 생기는 착시를 막는다.
- `ΔV = V_baseline - V_scenario`는 같은 수요척도에서 취약부담이 얼마나 줄었는지 측정한다.
- `Δrank`는 `ΔV`와 함께 보고한다. 절대 변화가 작아도 정책 우선순위에서 위치가 바뀔 수 있기 때문이다.
- destination set이나 edge cost가 바뀌는 경우 Dijkstra를 다시 돌렸다. 따라서 단순히 기존 경로 위 cost만 바꾼 route-fixed 결과가 아니다.
- manifest에는 baseline/scenario cost hash, demand hash, row count, path re-search 여부, effect label을 기록했다.

## 남은 해석 경계

- S1: "49개 hidden이 해결된다"라고 쓰면 안 된다. "48개 후보를 모두 동시에 반영한 네트워크 상한선에서 49개 hidden hex가 해소된다"라고 써야 한다.
- S3: 공식 반사실 효과 산출물로는 쓸 수 있지만 결론은 부정적이다. "grade>30 cap15 개선만으로는 hidden vulnerability가 해소되지 않았다"가 안전하다.
- S4: "쉘터나 제설 대응으로 102개 hidden이 해결된다"라고 쓰면 안 된다. "기상항을 도시 전체에서 제거하는 상한선에서는 102개 hidden이 해소된다"라고 써야 한다.
- S1/S3/S4 어느 것도 승하차 증가, 이용수요 분산, 모드 전환, 실제 행동변화를 예측하지 않는다.

## QGIS 확인 기준

QGIS에서는 `outputs/reports/scenario_counterfactual/scenario_counterfactual_qgis_checklist.md`를 기준으로 확인한다.

이미 통과한 레이어 검증:

- S1 runner layer: 4,383행, resolved hidden 49개, resolved hidden 행정 라벨 누락 0, empty geometry 0
- S3 runner layer: 4,383행, resolved hidden 0개, empty geometry 0
- S4 runner layer: 4,383행, resolved hidden 102개, resolved hidden 행정 라벨 누락 0, empty geometry 0

QGIS 지도 제목 권장:

- S1: "S1 후보 정류장 48개 동시 반영 상한선"
- S3: "S3 경사 30% 초과 edge cap15 반사실 효과"
- S4: "S4 기상항 제거 weather-component 상한선"

## 참고문헌 근거

- UK DfT TAG Unit A4.2 Distributional Impact Appraisal: https://www.gov.uk/government/publications/tag-unit-a42-distributional-impact-appraisal
- UK DfT TAG Unit A4.1 Social Impact Appraisal: https://www.gov.uk/government/publications/tag-unit-a4-1-social-impact-appraisal
- NCHRP, Accessibility Measures in Practice: https://nap.nationalacademies.org/catalog/26793/accessibility-measures-in-practice-a-guide-for-transportation-agencies
- Geurs & van Wee (2004), Accessibility evaluation of land-use and transport strategies: https://doi.org/10.1016/j.jtrangeo.2003.10.005
- Handy & Niemeier (1997), Measuring accessibility: https://doi.org/10.1177/1087724X9700100205
- Conveyal Analysis scenario/network accessibility tooling: https://docs.conveyal.com/analysis
