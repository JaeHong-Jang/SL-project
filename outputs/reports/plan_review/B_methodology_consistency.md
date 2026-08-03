# B. 방법론·수락기준 자기일관성 검토 보고서 (팀원B · architect)

**대상**: `.omx/plans/demand-scenario-redesign-2026-05-23.md` §2, §5, §7, §8-1, §8-2, §9, §11, §12
**모드**: read-only. 본문 내부 모순·누락·실행 불가능 조건 식별.

---

## M1. §5 합격기준 공식 자기일관성 — **[MINOR]**
- 사실: §5(L204-207)의 hidden recall / Jaccard / 신규 후보 비중 / top-K 공식이 §11.2(L541)에 재정의됨. 임계값(80% / 60-80% / <60%, 신규 20% / 20-40% / >40%)은 §5에만 명시.
- 누락:
  - §5 L208 "hidden 후보 overlap" vs L209 "hidden recall" → 같은 지표인데 용어 두 개.
  - 신규 후보 비중 분모가 alt이라 alt=0이면 정의 불가, zero-guard 없음.
  - §11.2가 §5 임계값을 인라인 복기하지 않음.
- 권고: §5 용어를 "hidden recall"로 통일. §11.2 끝에 "임계값은 §5 적용" 한 줄. §5에 "alt=0이면 결론보류" 추가.

## M2. §8-2 G1~G8 게이트 완성도 — **[MAJOR]**
- 사실: G1(주장수준), G2(문헌-변수), G3(universe), G4(고정기준선), G5(counterfactual), G6(민감도), G7(관측검증), G8(산출물재현). 8개 통과/탈락 기준은 정의됨.
- 누락:
  1. **G ↔ §11 단계 1:1 매핑 표 없음**. G5(counterfactual)는 §11.6-8 manifest 작성과 §11.9 리뷰 사이에 검증 단계가 빠짐.
  2. G5 ↔ G6 검증 단계가 §11에서 합쳐져 있어 게이트 분리 효과 약함.
  3. G7 "관측자료 없이 수요변화 주장 탐지" 절차가 grep/리뷰어/lint 중 어느 형태인지 불명.
  4. G2 통과 기준이 정성적("모든 변수에 문헌 근거"). 통과율 측정 형식 부재.
- 권고: §8-2 끝에 게이트↔단계 매핑 표 추가:
  ```
  G1↔§11.9 | G2↔§11.1 | G3↔§11.5 | G4↔§11.5-8 | G5↔§11.6-8 manifest+§11.9 | G6↔§11.2 | G7↔§11.4+§11.9 | G8↔§11.8
  ```
  G7 통과기준에 "`증가|감소|이용|탑승|예측` 키워드 grep + (접근성/관측검증/예측) 태그 분류" 추가.

## M3. §11 실행 단계 ↔ §12 수락 기준 매핑 — **[MAJOR]**
- 누락:
  1. **§12 보고서 영역(L624-627) 충족 단계 없음**. "모형상·잠재수요압력·우선검토 후보" 표현 강제와 §10 그림/표 11종 생성이 §11에 단계로 존재하지 않음.
  2. §12 L601 "동일가중·4분위·고령축 분리·POI 분리 중 최소 3개 비교" vs §11.2가 4종 모두 명시 → "필수" vs "최소" 충돌.
  3. §12 L609 S1 후보 필터 결과 수치가 §11.6 검증 라인에 없음.
- 권고:
  - §11.2 "4종을 모두 산출, 보고서에는 최소 3개"로 §12와 통일.
  - §11에 단계 9.5 신설: "§10의 그림/표 11종 산출 및 합격기준 자체 점검".
  - §11.6 검증에 "도로 타입/250m 필터 제외 후보 수" 추가.

## M4. §9 시나리오 manifest 필드 완전성 — **[MAJOR]**
- 사실: §11.6 manifest 필드(intervention parameter, changed/unchanged term, demand_source, demand_hash, `scenario_demand_created=false`, fixed normalization/threshold universe, row-count parity, baseline hash). §11.7 유사. §12 L615는 더 강한 "baseline/scenario row count + hex_id 집합" 명시.
- 누락:
  1. §11.6/7 ↔ §12 불일치: §11이 "row-count parity"만, §12는 "hex_id 집합 동일성".
  2. §11.6/7은 `canonical_scenario`, `legacy_name` 누락(§11.8 S4만 명시). 스키마 일관성 깨짐.
  3. 다음 필드 전체 누락: `scenario_id`, `run_timestamp`, `code_commit_sha`, `fail_reason`, `intervention_count`, `unchanged_term_hash_match`.
- 권고: §9/§11.6-8/§12를 공통 스키마로 통일:
  ```
  scenario_id, canonical_scenario, legacy_name,
  intervention_parameter, intervention_count,
  changed_cost_term, unchanged_cost_term, unchanged_term_hash_match,
  demand_source, demand_hash, scenario_demand_created,
  fixed_normalization_universe, fixed_threshold_universe,
  baseline_row_count, scenario_row_count, hex_id_set_equal,
  baseline_hash, output_path,
  code_commit_sha, run_timestamp, fail_reason
  ```

## M5. §9 S1/S3/S4 재설계 실행가능성 — **[MAJOR]**
- 사실:
  - S1 A/B/C 분류 기준 (§9 L436-438): footway/steps/path/service 제외, primary/secondary/tertiary=A, residential/unclassified=B, 250m 미만 제외. raw csv `S1_candidates_review.csv`에 `nearest_road_highway`/`nearest_bus_stop_m`/`bus_stop_count_300m` 컬럼 실재. 실행 가능.
  - **S3 shortest-path edge 추적 코드 부재**: `src/sl_accessibility/accessibility/routing.py:78-101` `nearest_destination_lengths`가 `multi_source_dijkstra_path_length`만 호출. **edge 집합 반환 함수 없음**. predecessor 추적 또는 `dijkstra_path` 추가 필요.
  - S4 rank-stability: §11.8에 "variant" 명시했지만 variant set 정의 없음.
- 누락:
  1. **S3 실행 불가능**: §11.7이 "다시 잡는다"로만 적혀 routing 모듈 신규 함수 추가가 명시 안 됨.
  2. S1 실패판정 임계값(70%/200m/10%)이 §5 합격기준(80%/60%/20%/40%)과 다른 차원이지만 본문이 그 차이를 명시 안 함.
  3. S4 variant set 미정의 → 재현 불가.
  4. S1 실측 `recommended_action`(access_route_improvement_review, stop_relocation_or_pedestrian_connection_review) ↔ A/B/C 라벨 매핑 표 없음.
- 권고:
  - §11.7에 "routing.py에 hex→D 최단경로 edge 집합 반환 함수 추가(predecessor 기반)" 명문화.
  - §9 S1 실패판정 위에 "이 임계값은 §5와 별개의 정책 시나리오 적합성 검사" 한 줄.
  - §9 S4에 variant set 명시: "weight ±20%, equal weight, leave-one-out 4종 → 총 6개 variant".
  - §9 S1에 `recommended_action` ↔ A/B/C 매핑 표 추가.

## M6. §8-1 트랙 A/B/C 결정 게이트 — **[MINOR]**
- 누락:
  1. B/C 확장 시 §11에 추가 단계 4a-4d(데이터→ETL→학습→holdout) 누락.
  2. "수요가 증가한다" 탐지 절차가 §11.9 "태깅"으로만, 실행 형태 미정.
  3. §2 게이트 5(수요모형 범위 결정)이 사실상 §11.4와 동일 시점인데 §2에서 마지막에 위치 → 순서 모순.
- 권고: §11.4에 "B/C 선택 시 4a-4d 삽입" 추가. §11.9에 grep 명령 명시. §2 게이트 5를 게이트 2~3 사이로 재배치.

## M7. §2 팀 ↔ 게이트 ↔ §11 매핑 — **[MINOR]**
- 누락:
  1. 팀원1~6 ↔ §11.1~10 매핑 표 없음.
  2. 게이트 1→2→3→4→5 의존성/blocking 명시 안 됨.
  3. 게이트 4 검토자료 형태 미정(PDF/JSON/통과표).
- 권고:
  ```
  팀원1: §11.5-7 (코드/데이터)
  팀원2: §11.2 (민감도)
  팀원3: §11.1, §11.9 (문헌)
  팀원4: §11.9.5 신설 (그림/표)
  팀원5: §11.8 (QA)
  팀원6: G1-G8, §11.9 (리뷰)
  ```
  게이트 4 검토자료: "G1-G8 통과표 + manifest 묶음 + 그림/표 11종".

---

## 최종 판정: **이 계획을 그대로 실행하면 안전한가? — 아니오. MAJOR 보완 후 실행해야 한다.**

방법론 골격과 검증 게이트 설계는 견고하나, 실행 가능성에 직결되는 3개 항목이 해결되지 않으면 단계 중간에 멈춘다.

### 반드시 보완해야 할 누락 3가지
1. **S3 shortest-path edge 추적 코드 부재** — `routing.py:78-101`은 length만 반환. path edge 집합을 산출하지 못함. §11.7에 routing 모듈 확장 단계 명문화 필수.
2. **scenario manifest 스키마 불일치** — `scenario_id`, `code_commit_sha`, `run_timestamp`, `hex_id_set_equal`, `fail_reason`, `unchanged_term_hash_match` 등이 §9·§11.6-8·§12에서 분산·누락. 공통 스키마 통일 필요.
3. **G1~G8 ↔ §11 10단계 매핑 표 부재** — 특히 G5(counterfactual), G7(관측검증)이 어느 단계에서 객관적 검증되는지 명시 안 됨. 게이트가 형식적으로만 존재할 위험.

---

## 판정 요약
| 항목 | 판정 |
|---|---|
| M1 §5 공식 일관성 | MINOR |
| M2 G1-G8 완성도 | **MAJOR** |
| M3 §11 ↔ §12 매핑 | **MAJOR** |
| M4 manifest 필드 | **MAJOR** |
| M5 S1/S3/S4 실행가능성 | **MAJOR** |
| M6 트랙 결정 게이트 | MINOR |
| M7 팀↔게이트↔단계 | MINOR |

**MAJOR 4건, MINOR 3건**. MAJOR 4건은 모두 실행 단계 진입 전 본문 수정 필수.