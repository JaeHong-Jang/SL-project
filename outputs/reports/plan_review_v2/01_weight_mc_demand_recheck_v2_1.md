# v2.1 가중치·Monte Carlo·수요변화 재검토

작성일: 2026-05-31

검토 대상: `.omx/plans/demand-scenario-redesign-v2-2026-05-29.md`

## Lead Verdict

판정: **REVISE → v2.1 보정 반영**

이번 검토에서는 코드가 아직 v2를 구현하지 않은 점을 실패로 보지 않았다. v2는 계획 문서이므로 핵심 검토 기준은 "가중치 근거, Monte Carlo 사용 여부, 실제 수요 변화 주장 범위가 문서 안에서 방어 가능하게 구분되는가"였다.

## 4+1 검토 결과

| 레인 | 결론 | 핵심 근거 |
|---|---|---|
| A. 로컬 산식/가중치 | REVISE | `demand_index_final`은 4축 동일가중 평균이다. raw source는 6개처럼 보이지만 POI 3종은 `poi_total_norm` 1축으로 합쳐진다. |
| B. 시나리오 설계 | REVISE | Track A는 접근비용·취약도 부담 재분배를 볼 수 있지만, 실제 탑승량·OD·이용자 이동을 말하려면 Track B/C가 필요하다. |
| C. 문헌 | REVISE | 동일가중은 허용 가능하지만 "객관 가중치"가 아니라 명시적 연구 설계 가정이다. 결정론적 민감도는 Monte Carlo 불확실성 분석이 아니다. |
| D. 산출물/QA | REVISE | 현재 S4 CSV/GPKG는 후보 진단으로는 일관되지만, S4 QA JSON·manifest·rank-stability artifact는 아직 없다. |

## 해결한 의문

1. **가중치는 논문에서 숫자를 가져온 것인가?**

아니다. 현재 가중치 숫자는 크게 세 부류다.

- `demand_index_final`의 4축 동일가중: 문헌 숫자 차용이 아니라 투명한 baseline 가정.
- `linear_alpha`, `additive_beta`, `interaction_beta`, `snow_weight`: 보정된 관측계수가 아니라 시나리오 기본값.
- S4 `score_weights`: 기상 대응 후보를 재현 가능하게 정렬하기 위한 휴리스틱.

따라서 문헌은 변수 포함과 지표 구성의 방향을 뒷받침하고, 숫자 가중치 자체는 민감도와 한계로 방어해야 한다.

2. **Monte Carlo를 사용했는가?**

현재는 사용하지 않았다. 현재 산출물은 결정론적 variant / one-at-a-time 민감도 점검이다. 따라서 "확률적 강건성", "신뢰구간", "95% 불확실성 범위"는 쓰면 안 된다.

3. **실제 수요 증가·감소를 말해야 하는가?**

Track A에서는 말하지 않는다. 지금 프로젝트가 바로 볼 수 있는 것은 고정된 잠재 수요압력 위에서 접근비용과 취약도 부담이 줄거나 재배치되는지다. 실제 수요 증가·감소, 이용자 이동, 탑승수요 분산은 관측 수요자료와 학습/검증된 수요모형이 있을 때만 말한다.

## v2.1 반영 사항

- `demand_index_final` 산식을 4축 동일가중 평균으로 직접 기재.
- raw source 6개와 최종 가중 축 4개의 차이를 명시.
- EJSCREEN을 "직접 선례"가 아니라 product-structure screening analogy로 낮춤.
- 가중치 처리 원칙을 본문에 직접 추가.
- Track A/B/C 수요모형 판단표 추가.
- "분산"을 실제 수요 분산이 아니라 접근성/취약도 부담 재분배로 제한.
- S4 baseline `score_weights`를 휴리스틱으로 명시하고 manifest 필수로 변경.
- Monte Carlo 미사용과 결정론적 민감도 분석 범위를 명시.
- non-git 작업공간을 고려해 `code_commit_sha`를 `code_version_id`로 변경.

## 사용 근거

- OECD/JRC Composite Indicators Handbook: equal weighting도 가중치이며, 가중치는 가치판단이고 민감도/불확실성 분석이 필요하다는 복합지표 기준.
- JRC composite-indicator toolkit: 가중치, 정규화, 지표 포함/제외 등 가정의 민감도 검토 필요.
- Geurs & van Wee 2004, Hansen 1959: 접근성은 실제 통행량이 아니라 기회 도달 가능성 및 잠재 상호작용을 설명하는 지표.
- ATAP travel demand modelling: 실제 수요모형은 관측자료, 보정, 검증 자료가 필요.
- EPA EJSCREEN: 두 조건을 결합하는 product-structure screening analogy로만 사용.
