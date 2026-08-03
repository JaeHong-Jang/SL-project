# 00. 팀장 최종 verdict v2

작성일: 2026-05-29
검토 대상: `.omx/plans/demand-scenario-redesign-v2-2026-05-29.md`
모드: 4개 독립 lane(A 데이터, B 방법론, C 문헌, D 산출물/QA) + 팀장 통합

---

## 1. 단일 결론

# **REVISE-LIGHT / v2 채택**

v2가 v1보다 맞다. v1로 돌아가지 않는다.

다만 v2를 그대로 실행 승인하기보다는, 아래 보정 항목을 반영한 **v2.1**을 만든 뒤 게이트 2로 넘어가는 것이 안전하다. 이유는 v2가 v1의 P0 문제(universe, manifest, S3 실행 전제, 문헌 cherry-pick)를 대부분 해결했지만, 일부 문장이 실행자에게 여전히 다르게 해석될 수 있기 때문이다.

요약 판정:
- 계획 방향: **APPROVE**
- 실행 전 문서 완성도: **REVISE-LIGHT**
- 산출물 QA 완성도: **아직 PARTIAL**. S4 QA JSON/manifest는 계획에만 있고 실제 파일은 없다.

---

## 2. 팀별 판정

| lane | 결론 | 핵심 판정 |
|---|---|---|
| A 데이터/universe | PASS with minor edits | 4,551 vs 4,383 universe 문제는 해결. 단 `demand_index_final` 산식이 `v1 동일`로 생략되어 4항 평균인지 6항 평균인지 혼동 가능 |
| B 방법론/시나리오 | REVISE-LIGHT | v2가 v1보다 강함. 단 G5의 "changed term 정확히 1개"는 너무 엄격함. 하나의 정책 lever 안에서 여러 cost term이 바뀔 수 있음 |
| C 문헌 | PASS with minor edit | 잠재수요/accessibility/service-gap framing은 문헌상 방어 가능. 단 EJSCREEN은 정확히 같은 공식이 아니라 product-structure screening analogy로 낮춰 표현 필요 |
| D 산출물/QA | PARTIAL | 11개 산출물 기준과 rank-stability는 좋아졌지만 S4 QA JSON/manifest는 아직 없음. 일부 acceptance가 여전히 덜 구체적 |

---

## 3. v2가 v1보다 나은 이유

1. universe-A 4,551과 universe-B 4,383을 분리해 v1의 핵심 재현성 문제를 해결했다.
2. G1-G8 검증 게이트를 §11 실행 단계와 연결했다.
3. scenario manifest를 부록 A 단일 스키마로 모았다.
4. S3가 최단경로 edge 기반이 되려면 `nearest_destination_paths`가 필요하다는 실행 전제를 명시했다.
5. Jiao & Dillivan 계열 transit desert의 차감/비율 모델과 본 연구의 곱셈 모델 차이를 인정했다.
6. S4 weather-response는 효과 분석이 아니라 후보 진단표라고 제한했다.
7. rank-stability variant와 PASS 기준을 추가했다.

따라서 "어떤 것이 맞는가"에 대한 답은 **v2가 맞다**이다.

---

## 4. 실행 전 반드시 고칠 항목

### P0.5-1. `demand_index_final` 산식을 v2에 다시 적기

현재 v2 §3은 `산식: v1 동일`이라고만 한다. 그런데 바로 뒤에서 yaml 입력이 6개라고 설명해, 실행자가 6개 raw input을 각각 평균내는 실수를 할 수 있다.

권장 문장:

```text
demand_index_final =
  (
    registered_population_norm
  + registered_senior_population_norm
  + living_population_norm
  + poi_total_norm
  ) / 4

단, poi_total_norm은 commercial, medical, senior_welfare POI를 hex 단위로 집계한 뒤 만든 단일 POI 축이다. 즉 raw POI 입력은 3종이지만 최종 demand_index 항은 4개다.
```

### P0.5-2. G5 counterfactual 기준 수정

현재 v2는 G5 통과 조건을 "changed term 정확히 1개"처럼 읽히게 한다. 하지만 S3/S4에서는 하나의 정책 lever가 여러 cost term을 바꿀 수 있다.

권장 변경:

```text
changed cost term은 정확히 1개일 필요는 없다. 단, 모든 changed_cost_term은 하나의 선언된 intervention lever에 의해 바뀌어야 하며, 각 항의 변경 이유와 파라미터가 manifest에 기록되어야 한다. unchanged term은 baseline과 hash가 일치해야 한다.
```

### P0.5-3. frozen demand hash를 직접 증명하기

현재 manifest에는 `demand_hash`가 있지만, baseline과 scenario demand가 같은지 직접 비교하는 필드는 약하다.

부록 A에 추가:
- `baseline_demand_hash`
- `scenario_demand_hash`
- `demand_hash_algorithm`
- `demand_hash_scope`

수락 기준:

```text
Track A에서는 scenario_demand_created=false 이고 baseline_demand_hash == scenario_demand_hash 여야 한다.
```

### P0.5-4. S4 manifest에서 `score_weights`를 조건부 필수로 올리기

`score_weights`가 선택 필드이면 S4 rank-stability를 추적할 수 없다.

권장:
- S4/weather-response에서는 `score_weights` 필수
- rank-stability 실패 시 `fail_reason` 필수

### P1-1. EJSCREEN 표현 낮추기

현재 v2의 "percentile × demographics" 표현은 조금 강하다. EPA EJSCREEN은 product 구조의 유사 사례로 쓰는 것이 맞고, 정확히 같은 공식 선례처럼 쓰면 안 된다.

권장 표현:

```text
EJSCREEN은 Demographic Index와 Normalized Environmental Indicator를 곱해 screening index를 만드는 product-structure 선례다. 본 연구의 min-max demand × min-max cost와 동일한 공식은 아니며, "두 조건이 동시에 높을 때 우선검토 점수가 커진다"는 구조적 유사성의 근거로만 사용한다.
```

### P1-2. §10 산출물 #3의 "4개 구성요소"를 정확히 쓰기

권장:

```text
수요 구성요소 지도 4종 =
registered_population_norm,
registered_senior_population_norm,
living_population_norm,
poi_total_norm
```

의료/상업/노인복지 POI 3종은 `poi_total_norm`의 하위 진단표 또는 부록으로 분리한다.

### P1-3. "결측 0건" 표현 수정

§10 universe 감사표의 "결측 0건"은 access null이 없다는 뜻으로 오해될 수 있다. 168개 제외 hex는 access cost 결측 때문에 제외되는 것이므로 다음처럼 고친다.

```text
168개 제외 hex 각각의 제외 사유를 분류하고, 제외 사유 미분류 0건이어야 한다.
```

### P1-4. B/C 트랙은 이번 실행 범위 밖임을 명시

v2는 B/C 트랙 절차를 적었지만 pass/fail threshold는 얇다. 이번 연구가 Track A라면 문장 하나로 닫는 게 안전하다.

권장:

```text
본 v2 실행 범위는 Track A다. Track B/C는 관측 수요자료 확보 이후 별도 계획서에서 성능 기준(MAE/RMSE, spatial holdout, rank stability)을 정의한다.
```

---

## 5. 산출물 상태 판정

현 상태에서 확인된 사실:
- `scenario3_weather_response_top20.csv`: 존재, 20행/20 unique `hex_id`.
- `qgis/scenario3_weather_response_top20.gpkg`: 존재.
- `outputs/reports/scenario3_weather_response/`: 없음.
- `outputs/reports/s4_weather_response/`: 없음.
- S4 전용 QA JSON/manifest: 없음.
- `scripts/make_scenario3_weather_response.py`: 여전히 `SL_outputs/outputs/reports/...` 구 경로와 `scenario3_weather_response/` 출력 폴더를 사용.

따라서 v2의 S4 관련 문장은 **계획으로는 맞지만**, 산출물은 아직 acceptance 통과 상태가 아니다.

---

## 6. 최종 권고

v2를 기준안으로 채택한다. 다만 바로 코드/데이터 실행으로 가지 말고, 위 7개 보정만 반영한 `v2.1`을 만든다.

진행 순서:
1. v2.1 문서 보정: 산식, G5, frozen-demand hash, EJSCREEN, score_weights, output #3, Track A 범위 문장.
2. 사용자 게이트 1 승인.
3. 게이트 2에서 Track A 확정.
4. 그 다음 S4 QA JSON/manifest와 S3 routing function을 실제 코드/산출물 작업으로 진행.

짧게 말하면: **v2가 맞고, v1은 폐기해도 된다. 단 v2는 "최종 실행안"이 아니라 "거의 승인 가능한 보완안"이다.**

---

## 7. 근거 출처

- EPA EJSCREEN Technical Documentation v2.3. https://www.epa.gov/system/files/documents/2024-07/ejscreen-tech-doc-version-2-3.pdf
- CDC/ATSDR SVI 2022 Documentation. https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf
- UK IMD 2019 Technical Report. https://assets.publishing.service.gov.uk/media/5d8b387740f0b609909b5908/IoD2019_Technical_Report.pdf
- Jiao & Dillivan 2013, Transit Deserts. https://digitalcommons.usf.edu/jpt/vol16/iss3/2/
- Geurs & van Wee 2004, Accessibility evaluation. https://research.utwente.nl/en/publications/accessibility-evaluation-of-land-use-and-transport-strategies-rev/
