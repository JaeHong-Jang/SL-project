# v2.2 프로젝트 적합성 재감사: 의심-방어장치와 수식 타당성

검토일: 2026-05-31

대상:
- `.omx/plans/demand-scenario-redesign-v2_2-2026-05-31.md`
- `outputs/reports/plan_review_v2/*`
- `data/derived/hex_vulnerability_final.parquet`
- `src/sl_accessibility/accessibility/*`, `src/sl_accessibility/population/hex_features.py`
- `docs/methods/cost_function_parameters.md`, `configs/model_params.yaml`

## 1. 팀장 판정

v2.2는 프로젝트 목적에 맞게 수정하는 것이 맞다. 단, v2.2의 지위는 "최종 결론"이 아니라 **고령자 접근성 취약지점 주장을 방어하기 위한 검증 프로토콜**이다.

이 분석이 제거해야 하는 핵심 의심은 다음 하나로 요약된다.

> 우리가 찾은 취약지역이 정말 고령자 접근성 문제인가, 아니면 임의 가중치·정규화·거리 기준·시나리오 이름 때문에 만들어진 결과인가?

v2.2는 이 의심을 숨기지 않고, 다음처럼 분해한다.
- 실제 수요예측이 아니라 잠재 수요압력이다.
- M0-M3는 고령자 전용 임피던스가 아니라 연령공통 접근비용이다.
- 고령 보행속도·경사 민감도·계단 barrier는 M4-senior에서 새로 열어야 한다.
- 시나리오 산출물은 엔진·manifest·ΔV가 없으면 정책효과가 아니라 후보 진단표다.
- hidden 632 같은 간판 수치는 정규화·결합·threshold 민감도와 함께 보고해야 한다.

따라서 채택 판정은 **조건부 승인**이다. 계획으로는 맞고, 최종 보고서 주장으로는 아직 닫히지 않았다.

## 2. 신선한 검증 근거

로컬 데이터와 코드에서 직접 확인한 수치:

| 항목 | 확인값 | 의미 |
|---|---:|---|
| `hex_vulnerability_final.parquet` row | 4,551 | universe-A 전체 hex |
| valid analysis row | 4,383 | universe-B |
| vulnerable hex | 877 | M3 취약 상위 20% |
| hidden vulnerable hex | 632 | M0 400m 이내이면서 M3 취약 |
| hidden 등록인구 합 | 1,660,654 | 반올림 기준 |
| hidden 등록고령인구 합 | 342,012 | 반올림 기준 |
| M0-M3 Spearman | 0.994695 | M3가 순수거리 순위를 거의 재정렬하지 못함 |
| M0-M3 Pearson | 0.991933 | 거리 지배 구조 확인 |
| vulnerable 중 cost/demand 둘 다 상위 20% | 98/877 = 11.17% | product AND 해석 약화 |
| walking edge row | 467,556 | 네트워크 규모 |
| `highway`에 steps 포함 edge | 5,632 | 계단 barrier를 M4에 넣을 데이터 단서 있음 |
| 테스트 | 71 passed in 0.99s | workspace temp 지정 후 통과 |

주의: 첫 pytest 실행은 `<system-temp>/pytest` 권한 문제로 65 passed, 6 setup errors가 났다. `TEMP/TMP=.omx/tmp_pytest`로 재실행하니 71개 전부 통과했다. 코드 실패가 아니라 Windows temp 권한 이슈로 판단한다.

## 3. 팀별 독립 검토 통합

| 역할 | 핵심 판정 |
|---|---|
| 팀원1 데이터/시각화 | 정규화 robust core, quadrant, S4 admin label QA, diagnostic/effect registry가 빠지면 시각 산출물 방어가 약함 |
| 팀원2 분석 방향 | v2.2는 잠재 접근성·부담 재배치로 제한하면 연구목적에 맞음. 실제 수요예측·탑승분산 표현은 금지 |
| 팀원3 전처리 | universe, POI 손실, CRS/geometry는 방향이 좋지만 전체 데이터 손실 ledger와 admin label QA가 필요 |
| 팀원4 모델/수식 | M0-M3는 baseline으로 적절하나 고령자 전용이 아님. M4 시간기반 비용은 방향이 적절하지만 미구현 |
| 팀원5 방법론 타당성 | Monte Carlo 오해와 claim scope는 방어됨. 가중치, 시나리오 효과, M4, 문서 동기화는 아직 계획상 방어 |
| 팀원6 문헌/인터넷 | 접근성 screening, 고령 보행속도, slope/ramp, weather, composite indicator sensitivity의 큰 근거는 방어 가능. 계수 절대값은 약함 |
| 팀장 독립 비판 | v2.2 채택. 단, "계획에 적었다"와 "산출물로 검증했다"를 분리해야 함 |

## 4. 의심-방어장치 판정

| 의심 | v2.2 방어장치 | 판정 |
|---|---|---|
| 실제 수요예측 없이 정책제안 가능한가 | 잠재 접근성·형평성 screening으로 범위 제한 | PASS |
| 부담 재배치와 수요 분산을 혼동하는가 | 금지/허용 문장 표와 Track A/B/C 분리 | PASS |
| 가중치가 임의인가 | 계수는 scenario parameter, robustness 필수화 | WEAK until output |
| 정규화가 결과를 만든 것 아닌가 | log/rank/winsor/additive/threshold 민감도 의무화 | WEAK until output |
| M3가 거리와 거의 같으면 연구 실패 아닌가 | M3를 baseline으로 낮추고 M4에서 재검증 | PASS as reframed |
| 고령자 보행속도·계단이 반영됐는가 | M4-senior 선행조건 신설 | WEAK until M4 |
| 시나리오가 실제 정책효과인가 | FrozenBaseline, ΔV+Δrank, manifest 조건 | WEAK until engine |
| 전처리 손실이 숨겨졌는가 | universe/손실/CRS QA 요구 | WEAK until ledger |
| S4 후보표가 보고서에서 읽히는가 | rank-stability는 있으나 admin label QA 필요 | WEAK |

## 5. 수식 타당성

### M0

`M0 = length_m`

적절하다. 연구 질문이 "현행 거리 기준이 놓치는 취약지를 찾는 것"이므로, 순수거리 기준선이 있어야 한다. 다만 M0는 고령자 보행부담을 반영하지 않는다.

### M3

`M3 = length_m × slope_factor × weather_interaction_factor`

조건부로 적절하다. 경사·기상이 있는 연령공통 접근비용 baseline이다. 그러나 M0-M3 Spearman 0.994695이므로 "경사·기상이 순위를 크게 재정렬했다"는 주장은 불가하다. M3의 역할은 실패가 아니라 **현재 계수·자료로는 거리 지배가 강하다는 진단 기준선**이다.

### M4-senior

`M4_senior = base_time × slope_time_factor × weather_factor × step_factor`

프로젝트 목적에 가장 적절한 방향이다. 고령자 접근성은 같은 거리라도 보행속도, 경사, 계단, 기상 조건에 따라 체감 시간이 달라지기 때문이다. 단, 현재 미구현이며 관측 보정모형이 아니다. 따라서 0.70/0.80/0.90/1.07 m/s, step allowed/penalty/barrier, dry/rain/snow는 **profile sensitivity**로 보고해야 한다.

### Demand Index

`demand_index_final = 평균(registered_population_norm, registered_senior_population_norm, living_population_norm, poi_total_norm)`

잠재 수요압력 proxy로는 적절하다. 관측 탑승·OD가 없고, 승하차를 다시 수요에 넣으면 순환논리가 생기기 때문이다. 그러나 고령등록인구는 등록인구의 부분집합이라 이중계상 의심이 있다. 최종 보고서는 senior share 분리형, 고령축 제거형, POI 재분류형 민감도를 함께 내야 한다.

### Vulnerability Product

`vulnerability = cost_norm × demand_norm`

screening 수식으로는 조건부 적절하다. 고비용과 고수요압력이 동시에 높은 곳을 우선검토 후보로 올리는 AND형 지표다. 그러나 현재 vulnerable 877개 중 cost/demand 둘 다 상위 20%인 hex는 98개뿐이라 product만으로 "둘 다 높다"고 설명하면 약하다. quadrant를 1차 산출물로 병행해야 한다.

### Hidden

`hidden = official_400m_ok_m0 AND vulnerable_m3`

적절하다. 현행 거리 기준이 양호로 본 곳 중 환경비용·수요압력 기준에서 취약한 후보를 직접 드러낸다. 단, M4 전에는 "고령자 전용 hidden"이 아니라 "고령 인구가 노출된 연령공통 hidden"이다.

### FrozenBaseline

`V_scenario = norm_S0(cost_scenario) × norm_S0(demand)`

적절하다. baseline min/max와 threshold를 고정해 시나리오마다 척도가 바뀌어 개선이 생기는 착시를 막는다. 다만 실행 스크립트가 `evaluate_scenario`를 호출하고 `scenario_cost`, `delta_vulnerability`, manifest를 남기기 전에는 정책효과가 아니라 후보 진단이다.

## 6. 계획 반영 사항

이번 재감사 후 v2.2 계획에 다음을 반영했다.

- `§0-quinquies` 추가: 의심-방어장치 매트릭스와 수식별 claim scope.
- `§10 #8` 수정: S1/S3/S4 성과표에 `diagnostic_or_effect` 열 필수.
- `§10 #10` 수정: S4 Top20은 admin label 결측 0건 전 주표 사용 금지.
- `§10 #17` 추가: `hidden_vulnerable_robust_core.csv/gpkg`.
- `§10 #18` 추가: 전체 데이터 손실 ledger.
- `§10 #19` 추가: scenario effect registry.
- `§10 #20` 추가: S4 admin label QA.

## 7. 최종 결론

v2.2는 v2보다 낫고, 프로젝트에 맞다. 특히 "수요예측을 하지 않는다", "M3를 고령자 전용이라고 부르지 않는다", "M4를 별도 선행조건으로 둔다", "시나리오 효과와 후보 진단표를 분리한다"는 점이 방법론적으로 안전하다.

하지만 최종 보고서의 강한 주장은 다음 4개 산출물이 생긴 뒤에만 가능하다.

1. 정규화·결합·threshold robustness 표와 robust core 지도.
2. M4-senior Dijkstra 재탐색 및 M0/M3/M4 Jaccard·Spearman 비교.
3. FrozenBaseline 기반 시나리오 ΔV+Δrank와 manifest.
4. 전체 데이터 손실 ledger와 S4 admin label QA.

이 네 가지가 없으면 최종 표현은 "정책효과"가 아니라 "현장검토 우선순위 스크리닝"으로 제한해야 한다.

## 8. 참고 근거

- Hansen, 1959, *How Accessibility Shapes Land Use*: https://doi.org/10.1080/01944365908978307
- Geurs & van Wee, 2004, accessibility review: https://doi.org/10.1016/j.jtrangeo.2003.10.005
- OECD/ITF, *Measuring Accessibility*: https://www.itf-oecd.org/measuring-accessibility
- OECD/EC-JRC, *Handbook on Constructing Composite Indicators*: https://www.oecd.org/en/publications/handbook-on-constructing-composite-indicators-methodology-and-user-guide_9789264043466-en.html
- EPA EJSCREEN screening index: https://www.epa.gov/ejscreen
- FHWA older pedestrians guidance: https://highways.dot.gov/safety/pedestrian-bicyclist/step/step-older-pedestrians
- FHWA pedestrian course, older walking speed and slopes: https://www.fhwa.dot.gov/publications/research/safety/pedbike/05085/chapt8.cfm
- U.S. Access Board ADA accessible routes: https://www.access-board.gov/ada/guides/chapter-4-accessible-routes/
- U.S. Access Board PROWAG: https://www.access-board.gov/prowag/
- MUTCD 11th Edition Part 4: https://mutcd.fhwa.dot.gov/pdfs/11th_Edition/part4.pdf
- Asher et al., 2012, older adult walking speed: https://pubmed.ncbi.nlm.nih.gov/22695790/
- Clarke et al., snow/rain and older adult walkability: https://pmc.ncbi.nlm.nih.gov/articles/PMC5423849/
- Korea law search portal, accessibility/ramp standards: https://www.law.go.kr/
