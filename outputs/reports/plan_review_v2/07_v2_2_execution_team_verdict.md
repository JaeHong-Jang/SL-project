# v2.2 실행 검증 팀 판정

작성일: 2026-05-31

대상 계획: `.omx/plans/demand-scenario-redesign-v2_2-2026-05-31.md`

## 팀장 총평

v2.2 계획은 프로젝트에 맞게 수정하는 방향이 맞다. 다만 최종 논문 주장은 아래처럼 제한해야 한다.

- 가능: 잠재 수요압력과 보행 접근비용을 결합한 접근성 부담 스크리닝, 현장검토 우선순위, 정규화/threshold 민감도 공개.
- 불가: 실제 탑승수요 증가/감소 예측, 정책 개입에 따른 수요 분산 입증, 고령자 전용 접근비용 효과 입증.

이번 실행으로 v2.2의 핵심 방어 산출물은 생성됐다. 가장 중요한 결과는 `hidden 632`를 그대로 단정하지 않고, 정규화 4종 공통으로 잡히는 `robust-core hidden 429`와 정규화에 따라 흔들리는 후보 `624`를 분리했다는 점이다.

## 생성 산출물

| 산출물 | 경로 | 용도 |
|---|---|---|
| 생성 스크립트 | `scripts/build_v2_2_execution_artifacts.py` | v2.2 방어 산출물 재현 |
| robustness 표 | `outputs/reports/v2_2_execution/normalization_combination_threshold_robustness.csv` | 정규화/결합/threshold 민감도 |
| robust core CSV | `outputs/reports/v2_2_execution/hidden_vulnerable_robust_core.csv` | 정규화 공통 hidden 후보 |
| robust core 지도 | `qgis/hidden_vulnerable_robust_core.gpkg` | QGIS 검토 레이어 |
| quadrant 4x4 | `outputs/reports/v2_2_execution/quadrant_4x4_matrix.csv` | cost/demand 축 분리 |
| quadrant 지도 | `qgis/quadrant_primary_output.gpkg` | product 점수 의존 완화 |
| data loss ledger | `outputs/reports/v2_2_execution/data_loss_ledger_v2_2.csv` | 전처리 손실/집계/threshold 구분 |
| scenario registry | `outputs/reports/v2_2_execution/scenario_effect_registry_v2_2.csv` | 효과 주장 가능/불가 범위 |
| S4 admin QA | `outputs/reports/v2_2_execution/s4_top20_admin_label_qa.json` | S4 라벨 결측 검증 |
| S4 fixed 지도 | `qgis/scenario3_weather_response_top20_admin_fixed.gpkg` | 행정동 라벨 가능한 QGIS 레이어 |

## 팀원별 판정

| 역할 | 판정 | 근거와 이유 |
|---|---|---|
| 팀원1 데이터 분석/시각화 | PASS | QGIS 레이어 3개를 생성하고 row count를 검증했다. `robust=1,053`, `quadrant=4,383`, `S4=20`, S4 라벨 결측 0건. 지도 산출물에서 바로 검토 가능하다. |
| 팀원2 분석 방향 | PASS | 최종 claim은 실제 수요예측이 아니라 잠재 접근성 부담 스크리닝이어야 한다. OD와 승하차를 final demand에 넣지 않은 현재 보수적 설계와 일관된다. |
| 팀원3 전처리 | PASS | ledger에서 삭제, 집계, 보조자료 분리, threshold를 분리했다. 예: 보행망 edge는 `467,556 -> 466,626`, 결측 grade 900행과 grade>100 30행 제외이며 30~100% 급경사는 cap이지 삭제가 아니다. |
| 팀원4 모델 | WEAK/PENDING | M0-M3는 고령자 전용 비용이 아니다. M4는 추가 가능하지만 `cost_m4 = M3 / senior_speed`만 하면 모든 edge에 같은 상수가 곱해져 경로가 바뀌지 않는다. 계단/급경사 edge별 페널티가 필요하다. |
| 팀원5 방법론 | PASS with 제한 | Monte Carlo는 사용하지 않았고 결정론적 variant sensitivity다. 이 사실을 명시하면 방어 가능하다. 다만 `hidden 632` 단독 주장은 약하고 robust-core/quadrant를 함께 제시해야 한다. |
| 팀원6 문헌/인터넷 | PASS | 접근성은 실제 통행량이 아니라 도달 잠재력으로 쓰일 수 있다는 근거가 충분하다. 한국 접근로 기준, ADA/PROWAG, OECD/JRC 복합지표 민감도 기준을 함께 사용해야 한다. |

## 의심별 방어 결과

### 1. 가중치가 임의인가?

부분적으로 맞다. `slope_alpha`, `interaction_beta`, `snow_weight` 같은 보이는 비용계수는 시나리오 기본값으로 제한하면 방어 가능하다. 하지만 실제 결과를 크게 흔드는 것은 보이는 비용계수보다 정규화, product/additive 결합, demand 축, threshold다.

실행 결과:

| variant | hidden | hidden replacement |
|---|---:|---:|
| baseline minmax product | 632 | 0.0% |
| winsorize 1/99 product | 636 | 0.6% |
| log1p product | 808 | 57.6% |
| rank product | 755 | 23.8% |
| additive minmax | 796 | 69.0% |
| threshold 10/20/30% | 252 / 632 / 1,040 | threshold 민감 |

따라서 보고서 본문은 `632개 hidden`만 말하면 약하다. `robust-core 429개`, `정규화 민감 후보 624개`, 그리고 variant별 교체율을 함께 제시해야 한다.

### 2. 수식은 프로젝트에 적절한가?

M0-M3 비용식은 네트워크 최단경로 산출에는 적절하다. 이유는 edge weight가 길이에 양수 페널티를 곱한 additive 비용이라 Dijkstra에 들어갈 수 있고, 경사 이상치 cap도 한두 edge가 전체 지도를 지배하는 문제를 줄인다.

취약도 수식 `V = normalized cost * normalized demand`도 "고비용 AND 고수요" 스크리닝에는 쓸 수 있다. 다만 product는 정규화 방식에 매우 민감하므로 단독 주지표로 쓰면 약하다. v2.2에서는 quadrant `(cost high/low) x (demand high/low)`를 병행해 이 약점을 줄이는 방향이 맞다.

고령자 M4 수식은 아직 구현 전이므로 다음 구조가 필요하다.

```text
edge_cost_m4_senior_min =
  length_m / senior_flat_speed_m_per_min
  * senior_slope_factor(edge_grade)
  * weather_time_factor(weather_profile)
  * step_factor(edge_highway)
```

속도만 낮추면 경로 순위가 그대로라 "고령자에게 더 취약한 경로"를 찾지 못한다. 계단, 급경사, 날씨처럼 edge별로 달라지는 항이 들어가야 고령자 전용 모델이 된다.

### 3. 0.9947이면 연구 실패인가?

실패라기보다 claim을 바꿔야 한다. M0-M3 Spearman 0.9947은 경사/기상 비용이 순수 거리 순위를 거의 재정렬하지 못했다는 뜻이다. 따라서 "경사·기상이 서울 접근성 순위를 크게 바꿨다"는 주장은 금지해야 한다.

대신 이렇게 말해야 한다.

- M3는 현행 400m 기준이 놓치는 후보를 찾는 보수적 스크리닝이다.
- 단일 ASOS 기상과 현재 경사 계수로는 공간 재정렬 효과가 작다.
- 고령자 전용 문제는 M4에서 계단/급경사/속도 profile을 넣어 별도 검증해야 한다.

### 4. 시나리오 효과를 주장할 수 있는가?

현재는 불가하다. `scenario_effect_registry_v2_2.csv`에서 S1/S3/S4/M4 모두 `counterfactual_effect_claim_allowed=False`로 표시했다.

- S1: 정류장 신설/이전/접근로 개선 현장검토 후보 또는 상한선 스크리닝.
- S3: 효과 확정보다 범주 진단.
- S4: 기상 대응 Top20 후보표.
- M4: 설계/후속 구현 대상.

효과 주장으로 올리려면 scenario cost hash, FrozenBaseline runner, threshold hash, path re-search, ΔV/Δrank manifest가 필요하다.

### 5. 전처리 손실이 불투명한가?

이번 ledger로 상당 부분 방어됐다. 중요한 구분은 다음이다.

- 진짜 제외: 보행망 grade 결측/비정상 930 edge, 접근성 분석 불가 168 hex.
- 집계 압축: 생활인구 원천 관측행 `7,572,988 -> 8,600 grid`, OD `1,666,759,315 -> 425 admin`.
- 행 보존: final demand `4,551 -> 4,551`, final hidden diagnostics `632 -> 632`.
- threshold: vulnerable `877`은 데이터 손실이 아니라 top 20% 정책 컷이다.

### 6. S4 산출물은 지도에 바로 쓸 수 있는가?

기존 CSV는 라벨 결측이 없지만, 기존 GPKG는 `district_name/admin_name`이 20건 모두 결측이었다. 이번에 `qgis/scenario3_weather_response_top20_admin_fixed.gpkg`를 생성했고, fixed GPKG는 `district_name/admin_name/admin_code` 결측 0건이다.

## 최종 권장 문장

> 본 연구는 관측 탑승량이나 OD 기반 실현 수요예측이 아니라, 고정된 잠재 수요압력과 보행 네트워크 접근비용을 결합해 현행 400m 기준이 놓칠 수 있는 접근성 부담 후보지를 선별한다. final 기준 분석 가능 hex 4,383개 중 M3 취약 hex는 877개이며, 그중 현행 400m 기준으로는 양호하지만 M3 기준에서 취약으로 재분류되는 hidden vulnerable hex는 632개다. 다만 정규화 방식에 따라 후보가 크게 바뀌므로, 정책 우선순위는 robust-core 429개와 quadrant 분류를 함께 검토한다.

## 금지 문장

- 정류장을 추가하면 실제 이용수요가 N% 증가/분산된다.
- 경사·기상 모델이 서울 접근성 순위를 크게 재정렬했다.
- M3는 고령자가 실제로 느끼는 보행시간을 정확히 예측한다.
- S4 Top20은 기상 대응 시설 설치 효과를 검증한 결과다.
- Monte Carlo 신뢰구간에서 강건하다.

## 검증 증거

- 산출물 생성: `uv run python scripts/build_v2_2_execution_artifacts.py`
- 출력 요약: valid `4,383`, hidden `632`, robust-core hidden `429`, S4 fixed label ready `true`
- QGIS row count: robust `1,053`, quadrant `4,383`, S4 fixed `20`
- S4 fixed label null: district `0`, admin `0`
- 테스트: `uv run pytest -q` 결과 `71 passed`
- 정적 검사: `ruff` 실행 파일이 현재 환경에 없어 실패, `python -m py_compile scripts/build_v2_2_execution_artifacts.py` 통과

## 참고 근거

- Hansen, 1959, accessibility as potential opportunities: https://www.tandfonline.com/doi/abs/10.1080/01944365908978307
- Geurs & van Wee, 2004, accessibility evaluation review: https://projectwaalbrug.pbworks.com/f/Transp%2BAccessib%2B-%2BGeurs%2Band%2BVan%2BWee%2B%282004%29.pdf
- OECD/JRC composite indicator handbook: https://www.oecd.org/en/publications/handbook-on-constructing-composite-indicators-methodology-and-user-guide_9789264043466-en.html
- JRC sensitivity analysis guide: https://knowledge4policy.ec.europa.eu/composite-indicators/toolkit_en/navigation-page/10-step-guide_en/step-8-sensitivity-analysis_en
- 한국 장애인등편의법 시행규칙 별표 접근로/경사로 기준: https://www.law.go.kr/
- ADA accessible route guidance: https://www.access-board.gov/ada/guides/chapter-4-accessible-routes/
- PROWAG technical requirements: https://www.access-board.gov/prowag/technical.html
- FHWA older road user handbook: https://highways.dot.gov/safety/other/older-road-user/handbook-designing-roadways-aging-population/chapter-7-intersections
