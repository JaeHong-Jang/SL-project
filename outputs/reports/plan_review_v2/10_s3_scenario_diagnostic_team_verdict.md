# S3 시나리오 점검 팀 결론

작성일: 2026-05-31

## 팀장 결론

S3가 "아무 개선도 없음"이라는 뜻은 아니다. 현재 산출물의 정확한 의미는 다음이다.

- S3로 접근비용/취약도 부담이 감소한 hex는 45개 있다.
- 그중 기존 hidden 취약지역과 겹치는 hex는 12개다.
- 그러나 frozen S0-M3 threshold를 넘어 "hidden 취약 해소"로 분류된 hex는 0개다.

따라서 S3는 코드 버그라기보다, 현재 정의된 정책 레버가 hidden vulnerability를 해소할 만큼 강하지 않거나 대상이 좁다는 결과로 해석하는 것이 타당하다.

## 팀원1: 데이터 분석 점검

근거 파일:

- `outputs/reports/scenario_counterfactual/S3_delta_vulnerability.csv`
- `outputs/reports/scenario_counterfactual/S3_delta_vulnerability_summary.json`

확인 결과:

| 항목 | 값 | 해석 |
|---|---:|---|
| 전체 hex | 4,383 | 분석 대상 |
| baseline hidden | 632 | S0-M3 기준 hidden 취약지역 |
| scenario hidden | 632 | S3 이후에도 hidden 수 동일 |
| resolved hidden | 0 | threshold를 넘어 해소된 hidden 없음 |
| nonzero delta vulnerability | 45 | 취약도 점수가 감소한 hex는 있음 |
| changed hidden overlap | 12 | 기존 hidden 중 부담이 줄어든 hex |
| max delta cost | 104.26m | 일부 경로에서는 비용 감소가 큼 |
| changed hex 평균 delta cost | 17.58m | 변화가 생긴 hex만 보면 개선 존재 |
| 전체 평균 delta cost | 0.18m | 전체 서울 hex 기준으로는 효과가 매우 작음 |

핵심은 "개선 45개"와 "해소 0개"가 다른 지표라는 점이다. 해소는 단순히 조금 좋아진 것이 아니라, baseline hidden 상태에서 시나리오 후 vulnerable threshold 밖으로 이동해야만 잡힌다.

## 팀원2: 모델/코드 설계 점검

S3 runner는 다음 구조로 되어 있다.

1. `grade_abs_percent > 30`인 edge만 개입 대상으로 잡는다.
2. 해당 edge의 비용 계산용 경사를 15% cap으로 낮춘다.
3. 같은 정류장 목적지 집합으로 Dijkstra를 다시 수행한다.
4. 수요지표와 official 400m 판정은 고정한다.
5. FrozenBaseline threshold로 전후 취약도와 hidden 해소 여부를 비교한다.

이 구조 자체는 반사실 실험으로는 타당하다. 다만 정책 레버가 좁다. 특히 기존 비용 생성 단계에서 이미 경사 비용이 30% cap을 거치기 때문에, S3는 "실제 고경사를 15%로 낮춤"이 아니라 "모델상 30%로 cap된 고경사 edge를 15%로 낮춤"에 가깝다. 그래서 많은 지역에서 경로 비용 순위가 크게 바뀌지 않는다.

## 팀원3: 전처리/데이터 구조 점검

S3의 효과가 작게 나온 주요 원인은 다음과 같다.

- 개선 대상은 edge 단위이지만, 취약 판정은 hex 단위 threshold crossing이다.
- 급경사 edge가 많아도 실제 최단경로에 포함되지 않으면 hex 접근비용은 바뀌지 않는다.
- 기존 hidden 지역이 개선 edge 주변에 있더라도, threshold를 넘을 만큼 비용이 줄어야 resolved로 잡힌다.
- S3는 정류장 위치, 목적지 수, 수요, 공식 400m 판정을 바꾸지 않는다.

즉 "경사 개선 사업"이 무의미하다는 결론이 아니라, 현재 S3 정의가 hidden vulnerability 해소까지 보여주기에는 좁다는 결론이다.

## 팀원4: 시각화 점검

기존 HTML은 `해소 hidden` 중심으로 보이면 S3가 "개선 없음"처럼 오해될 수 있었다. 그래서 다음처럼 수정했다.

- `부담 감소 hex(해소 아님)`과 `hidden 해소 hex(취약 해제)`를 명확히 분리했다.
- S3에도 `S3 hidden 해소 hex(취약 해제)` 범례를 추가했다.
- S3 해소 수는 0개로 표시되도록 유지했다.
- 오른쪽 요약 카드에서 `개선 hex / 해소 hidden`을 같이 보여주도록 바꿨다.
- 해소 레이어는 공통 초록색과 두꺼운 검정 테두리로 강조했다.

이제 S3는 "45개 hex에서 부담 감소, hidden 해소 0개"로 읽히게 된다.

## 팀원5: 방법론 타당성 점검

정책 시나리오의 목적은 반드시 모든 시나리오에서 해소가 발생해야 한다는 뜻은 아니다. 오히려 어떤 정책 레버가 효과가 약한지 드러나는 것도 시나리오 분석의 결과다.

다만 보고서에서는 다음처럼 구분해야 한다.

- 부담 감소: 비용이나 취약도 점수가 낮아진 상태
- 취약 해소: frozen threshold를 넘어 vulnerable/hidden 상태에서 벗어난 상태
- 정책 후보: 실제 집행 효과가 아니라 모델상 우선 검토 대상

S3는 현재 "해소 정책"보다는 "급경사 edge 개선만으로는 hidden 취약 해소가 거의 발생하지 않음을 보여주는 반사실 진단"으로 쓰는 것이 안전하다.

## 팀원6: 최종 표현 권고

사용 가능한 문장:

> S3 경사 개선 반사실에서는 45개 hex에서 접근비용 또는 취약도 부담이 감소했으나, frozen S0-M3 threshold 기준으로 hidden vulnerability에서 해소된 hex는 없었다. 이는 경사 개선이 무의미하다는 뜻이 아니라, 현재 S3가 `grade_abs_percent > 30` edge의 모델 비용만 낮추는 좁은 개입이어서 hidden 취약 해소까지 이어지기에는 효과 범위가 제한적임을 의미한다.

피해야 할 문장:

- S3는 효과가 없다.
- 경사 개선은 의미가 없다.
- S3가 hidden 취약을 해소했다.
- 경사 개선 정책의 실제 효과가 0이다.

## 다음 액션

현재 S3를 유지한다면, 보고서에서는 "작은 부담 감소, 해소 없음"으로 정직하게 제시한다.

만약 정책 제안에서 S3도 해소 효과를 보여야 한다면, 별도 S3+ 민감도 시나리오가 필요하다. 예시는 다음과 같다.

- S3a: grade > 20 edge를 cap15로 완화
- S3b: hidden 취약지역 주변 edge만 집중 개선
- S3c: 계단/급경사/보행 단절 edge를 함께 개선
- S3d: 경사 개선 + 정류장 접근로 연결을 결합

이 경우 기존 S3와 혼동하지 않도록 `S3+ sensitivity` 또는 `S3_policy_bundle`로 별도 명명해야 한다.
