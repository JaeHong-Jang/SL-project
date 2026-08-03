# v2 vs v2.2 Plan Comparison Review

검토일: 2026-05-31

## 결론

`demand-scenario-redesign-v2_2-2026-05-31.md`를 현행 controlling plan으로 채택하는 것이 타당하다.

단, 원본 v2.2를 그대로 승인하는 것은 부적절했다. v2.2는 claim scope, 정규화 robustness, 시나리오 효과/진단 분리에서 v2보다 강하지만, v2에 있던 effect manifest 조건이 약해졌고 S1 upper-bound delta 산출물을 "미산출"처럼 표현한 문제가 있었다. 본 검토에서 v2.2에 다음 보강을 반영했다.

- v2의 강한 manifest 필드 복원: `baseline_cost_hash`, `scenario_cost_hash`, `path_research_run`, `frozen_baseline_threshold_hash`, `effect_output_label`.
- S1 상태 수정: `qgis/S1_delta_vulnerability_map.gpkg`는 존재하지만 공식 counterfactual effect가 아니라 48개 후보 일괄 적용 upper-bound 진단 산출물로 라벨.
- 정규화·결합·threshold robustness를 필수 산출물로 명시.
- 문서 stale 상태는 "해결"이 아니라 "식별 완료, 문서 갱신 필요"로 수정.

## 4+1 검토 결과

| 레인 | 질문 | 판정 |
|---|---|---|
| Lane A 방법론·데이터 | 가중치·정규화·수요지수 설계가 방어 가능한가 | v2.2 우세. 결과를 좌우하는 레버가 계수보다 정규화·결합·수요축임을 명시한다. |
| Lane B 시나리오 아키텍처 | 시나리오가 counterfactual effect인지 diagnostic인지 구분되는가 | v2.2 우세. S4를 후보 진단표로 제한하고, 효과 claim 조건을 둔다. |
| Lane C 문헌·claim scope | 수요모형 없이 접근성 정책 스크리닝을 주장할 수 있는가 | v2.2 우세. 잠재 접근성/형평성 스크리닝과 실제 수요예측을 분리한다. |
| Lane D 재현성 | 산출물·문서·manifest가 검증 가능한가 | v2.2 우세이나 보강 필요. v2의 manifest 조건을 복원해야 한다. |
| Lead 통합 | 어느 계획을 써야 하는가 | v2.2 보강본 채택. v2는 역사적 초안으로 둔다. |

## 왜 v2.2가 더 설득력 있는가

### 1. "수요예측"이 아니라 "잠재 수요압력 기반 접근성 부담"이라고 정확히 말한다

v2도 수요모형과 접근성 스크리닝을 구분하지만, v2.2는 더 명확하다. 현재 데이터는 관측 탑승량·교통카드·검증된 OD가 아니므로 실제 수요 증가/분산을 예측하면 오히려 연구가 약해진다. v2.2는 이를 Track A/B/C로 분리하고, 이번 계획의 기본 주장을 다음으로 제한한다.

> 고정된 잠재 수요압력 위에서 접근비용과 취약도 부담이 어디에 집중되는지, 정책 개입 후보가 그 부담을 어떻게 줄일 수 있는지 선별한다.

이 표현은 "실제 이용수요 N% 증가"보다 보수적이고, 현재 데이터와 코드가 감당할 수 있는 주장 범위와 일치한다.

### 2. 가중치보다 더 큰 위험이 정규화·결합·threshold임을 드러낸다

검증 수치상 `alpha/beta/snow` 같은 보이는 계수 ±30%는 취약집합을 약 1.8%만 바꾼다. 반대로 log 정규화는 1−Jaccard 60.4%, additive 결합은 68.6%, 수요 4축→3축은 25.3% 교체를 만든다.

따라서 "계수는 논문에서 왔는가"보다 중요한 질문은 "정규화·결합·threshold 선택이 결론을 바꾸는가"다. v2.2는 이 지점을 정면으로 다루고, 단일 hidden list 대신 robust 교집합과 사분면 분류를 요구한다.

### 3. S4와 시나리오 효과를 과대주장하지 않는다

현재 `scripts/make_scenario3_weather_response.py`는 `scenario_cost`를 재계산하지 않고 기존 진단 컬럼을 `rank(pct=True)`로 점수화한다. 따라서 S4는 "기상 대응 후보 우선순위"이지 "β=0 반사실 효과"가 아니다.

v2.2는 이 차이를 문서 전면에 둔다. 효과를 주장하려면 `evaluate_scenario`/`FrozenBaseline` 연결, scenario cost hash, delta output, manifest가 필요하다. 이것이 심사자가 보기에 훨씬 방어 가능하다.

### 4. S1의 부정적 결과를 실패가 아니라 연구 발견으로 재해석한다

S1 Top20 검토에서 순수 신규 정류장 후보는 희소하고, 많은 후보는 이미 가까운 정류장이 있다. 이는 "정류장 신설 효과가 0"이라는 뜻이 아니라 "취약성의 원인이 정류장 부재보다 보행환경/연결성일 수 있다"는 RQ3 근거다.

다만 현재 존재하는 `qgis/S1_delta_vulnerability_map.gpkg`는 48개 후보 일괄 적용 upper-bound 산출물이다. 공식 counterfactual effect로 쓰려면 manifest와 runner provenance가 추가되어야 한다.

## Fresh Verification Evidence

- `.venv\Scripts\python.exe -m pytest -q`: 71 passed, 1 warning.
- `data/derived/hex_vulnerability_final.parquet`: valid rows 4,383; vulnerable 877; hidden 632.
- M0-M3 Spearman: 0.9947.
- `access_cost_m3` skew: 4.6143; max: 4,126.2m.
- `cost_m3_norm_final` median 0.041 vs `demand_norm_final` median 0.402.
- registered vs senior Spearman: universe-A 0.8536, universe-B 0.8517.
- `outputs/reports/hex_vulnerability_final_audit.json`: status pass; parquet/GPKG/QA comparison pass.
- `qgis/S1_delta_vulnerability_map.gpkg`: exists, 4,383 rows, resolved 49, nonzero `delta_vulnerability` 55.

## 권고

1. 현행 계획은 v2.2 보강본으로 진행한다.
2. v2는 그대로 두되, 작업 지시와 보고서에서는 v2.2를 canonical로 참조한다.
3. 다음 구현 단계의 첫 작업은 README/current_status_audit/분석_진행_정리의 stale 수치 동기화와 scenario manifest 스키마 구현이다.
4. 실제 수요 증가/분산 예측은 Track B/C로 분리하고, 이번 Track A에서는 "burden redistribution"만 주장한다.
