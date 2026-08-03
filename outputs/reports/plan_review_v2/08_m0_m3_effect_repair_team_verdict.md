# 0.9947 보완 및 시나리오 효과 claim 재검토

작성일: 2026-05-31

대상:
- `.omx/plans/demand-scenario-redesign-v2_2-2026-05-31.md`
- `scripts/build_v2_2_execution_artifacts.py`
- `outputs/reports/v2_2_execution/*`

## 팀장 판정

0.9947 문제는 "해결 불가"가 아니라 **claim을 두 층으로 분리해야 해결된다.**

1. **순위 재정렬 claim**: 현재 M0-M3 Spearman 0.994695이므로 "경사·기상이 서울 전체 접근성 순위를 크게 바꿨다"는 주장은 금지.
2. **환경부담 claim**: M3는 M0보다 접근비용을 평균 15.4%, 고령인구 가중 15.8% 증가시키고, 400m 기준 crossing 167개와 고정 threshold 신규 취약 275개를 만든다. 따라서 "경사·기상 반영 시 접근비용·취약도 부담이 증가하는 후보가 있다"는 주장은 가능.

즉 정책 제안의 근거는 "탑승수요 예측"이 아니라 **접근성 부담 변화의 조건부 진단/forecast**로 써야 한다.

## 새 산출물

| 산출물 | 경로 | 판정 |
|---|---|---|
| M0→M3 환경부담 CSV | `outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.csv` | 생성 |
| M0→M3 환경부담 JSON | `outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.json` | 생성 |
| M0→M3 manifest | `outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.manifest.json` | 생성 |
| M0→M3 QGIS | `qgis/m0_m3_environment_burden_shift.gpkg` | 생성 |
| 행정동별 burden 요약 | `outputs/reports/v2_2_execution/hidden_environment_burden_admin_summary.csv` | 생성 |
| scenario registry 갱신 | `outputs/reports/v2_2_execution/scenario_effect_registry_v2_2.csv` | E0 추가 |

## 실행 수치

| 항목 | 값 | 해석 |
|---|---:|---|
| valid hex | 4,383 | final analysis universe |
| M0-M3 Spearman | 0.994695 | 전체 순위 재정렬은 작음 |
| M0-M3 Pearson | 0.991933 | 비용 수준도 강한 거리 지배 |
| 평균 M3-M0 증가 | 28.39m | 환경비용으로 일반화 거리 증가 |
| p90 M3-M0 증가 | 66.39m | 상위 부담 후보는 더 크게 증가 |
| 평균 비용 증가율 | 15.4% | 경사·기상 전제의 절대효과 근거 |
| 고령가중 비용 증가율 | 15.8% | 고령 노출 기준에서도 부담 증가 |
| M0 ≤ 400m, M3 > 400m | 167 hex | 현행 400m 기준 crossing |
| 그중 M3 hidden vulnerable | 109 hex | 400m 기준 양호이나 M3 취약 |
| M0 고정 threshold 신규 취약 | 275 hex | 환경비용 추가 시 threshold crossing |
| 신규 취약 등록/고령인구 | 643,039 / 130,153 | 수요예측이 아니라 노출 규모 |

## 팀원별 검토

| 역할 | 판정 | 근거와 이유 |
|---|---|---|
| 팀원1 데이터/시각화 | WEAK → 보완 | 전체 순위 재정렬 지도는 약하지만, `delta_cost`, 400m crossing, threshold crossing, robust-core 구분 지도는 방어 가능. 이번에 `m0_m3_environment_burden_shift.gpkg`로 보완했다. |
| 팀원2 분석 방향 | PASS | "예측"을 쓰려면 탑승수요가 아니라 접근비용·취약도 부담의 조건부 forecast로 제한해야 한다. |
| 팀원3 전처리 | WEAK/PENDING | ASOS 단일 관측소와 경사 cap 때문에 공간 재정렬이 작다. 장기 해결은 AWS/격자 기상, route decomposition, slope audit이다. |
| 팀원4 모델 | PASS with 조건 | `FrozenBaseline`은 이미 있고 E0에는 적용 가능하다. S1/S3/S4 정책효과에는 runner, scenario cost, path re-search, ΔV/Δrank가 더 필요하다. |
| 팀원5 방법론 | PASS with 제한 | 0.9947과 경사·기상 영향 전제는 양립 가능하다. 단, 영향은 순위 재배열이 아니라 edge/generalized-cost 증가로 해석해야 한다. |
| 팀원6 문헌 | PASS | 경사·계단·날씨가 보행 접근성 조건이라는 근거는 충분하다. 접근성 정책평가는 ridership 없이도 시간/기회/격차 변화로 claim 가능하다. |

## v2.2 반영 상태

v2.2 계획은 대체로 잘 반영되어 있다. 이번에 추가로 §14를 붙여 다음 점을 명확히 했다.

- `M0-M3 0.9947`은 순위 재정렬 실패가 아니라 거리 지배 구조의 진단으로 해석.
- 전제 검증용 E0: M0→M3 환경부담 진단을 신규 필수 산출물로 추가.
- 정책 시나리오 효과는 아직 S1/S3/S4에서 불가. runner + path re-search + manifest 전까지 후보/상한선/진단으로만 표기.
- "수요예측" 대신 "접근성 부담 변화의 조건부 forecast"를 사용.

## 코드 정리/주석

`scripts/build_v2_2_execution_artifacts.py`를 downstream-only 산출물 생성기로 유지했다. production pipeline은 건드리지 않았다.

추가한 코드 설명:

- `frame_hash`: 효과 manifest에 들어갈 baseline/scenario cost·demand hash 생성 이유 설명.
- `weighted_average`: 인구/고령인구 가중 비용 증가율 계산 용도 설명.
- `build_m0_m3_environment_burden`: 0.9947을 어떻게 해석해야 하는지, rank shift가 왜 post-hoc multiplier가 아닌 route-cost 비교인지 주석으로 명시.
- robust-core 출력에는 `delta_cost_m3_minus_m0`, `delta_pct_m3_over_m0`를 추가해 hidden 후보의 환경부담 증가를 바로 볼 수 있게 했다.

## 정책 제안 문장

권장:

> 본 연구는 탑승수요를 예측하지 않고, M0 순수거리 기준과 M3 경사·기상 반영 기준을 비교해 접근비용·취약도 부담의 조건부 변화를 진단한다. M0-M3 순위 상관은 0.994695로 높아 전체 순위 재배열은 작지만, M3는 평균 접근비용을 15.4% 증가시키고 400m 기준 밖으로 넘어가는 후보 167개 및 고정 threshold 신규 취약 275개를 만든다. 따라서 정책 제안은 이용수요 증가가 아니라 현장검토가 필요한 접근성 부담 후보의 우선순위로 해석한다.

금지:

- "경사·기상이 서울 접근성 순위를 크게 바꿨다."
- "시나리오로 탑승수요 증가/분산을 예측했다."
- "S4 Top20은 기상 대응 시설 설치 효과를 검증했다."
- "M3는 고령자가 실제로 느끼는 보행시간이다."

## 다음 구현 조건

정책효과 claim을 실제로 열려면 다음이 필요하다.

1. S1/S3/S4 runner가 `evaluate_scenario`와 `FrozenBaseline`을 호출.
2. 개입 후 `scenario_cost`를 재산출.
3. 경로가 바뀔 수 있는 개입은 Dijkstra path re-search 수행.
4. hex별 `delta_cost`, `delta_vulnerability`, `delta_rank`, `resolved_hidden`, `new_hidden` 저장.
5. manifest에 `baseline_cost_hash`, `scenario_cost_hash`, `path_research_run`, `effect_output_label=counterfactual_effect` 기록.
6. no-op, untouched-route, random/shuffle intervention 반증 테스트 통과.

## 참고 근거

- OECD/ITF, Accessibility and Transport Appraisal: https://www.oecd.org/en/publications/accessibility-and-transport-appraisal_61af7bd8-en.html
- ITF, accessibility indicators for planning/investment: https://www.itf-oecd.org/transport-planning-investment-accessibility-indicators
- Geurs & van Wee, 2004 accessibility evaluation review: https://research.utwente.nl/en/publications/accessibility-evaluation-of-land-use-and-transport-strategies-rev/
- 한국 접근로 기울기 1/18, 1/12 완화 기준 검색 근거: https://www.law.go.kr/
- ADA 2010 Standards: https://www.ada.gov/law-and-regs/design-standards/2010-stds/
- PROWAG Technical Requirements: https://www.access-board.gov/prowag/technical.html
- FHWA older road user handbook: https://highways.dot.gov/safety/other/older-road-user/handbook-designing-roadways-aging-population/chapter-7-intersections
- Snow/rain and older-adult walkability: https://pmc.ncbi.nlm.nih.gov/articles/PMC5423849/
