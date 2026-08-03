# 팀원D 검토 보고서: 산출물 명세 · 합격기준 측정가능성

작성일: 2026-05-29  
검토자: 팀원D (산출물·QA 검토자)  
검토 대상: `.omx/plans/demand-scenario-redesign-2026-05-23.md` §9, §10, §11, §12

---

## D1. §10 그림·표 최소 세트(11종) 완전성 점검

| # | 산출물 | 합격기준 명시 여부 | 기존 파일 존재 여부 | 누락/보완 필요 사항 | 판정 |
|---|---|---|---|---|---|
| 1 | 문헌-변수 검증 매트릭스 | 구성개념·문헌·기대방향·한계·제외이유 — §6에 8개 열 정의됨 | 미존재 (파일 없음) | 합격기준에 **행 수(몇 개 변수를 커버해야 하는지)** 미명시. "모든 변수"가 몇 개인지 기준 없음 | 보완 필요 |
| 2 | 분석 universe 감사표 | 4,551/4,383/제외/null/고정 universe 기록 — §3, §11.5에 정의됨 | 미존재 (파일 없음) | 합격기준에 **테이블 형식(CSV vs. 인라인 표)**과 고정 min/max 수치를 같이 기록해야 한다는 요건이 없음 | 보완 필요 |
| 3 | 수요 구성요소 지도 4종 | 각 구성요소 percentile + Spearman 상관 같이 제시 | 미존재 (`outputs/figures/critique/*.png` 미확인) | **4종**의 범위가 registered_population / registered_senior / living_population / poi_total 4개인지 명시 없음. 고령 축 분리형(D안) 포함 여부 불명 | 보완 필요 |
| 4 | 수요 4분위별 취약성 표 | Q4 hidden 비중·고령등록인구 비중이 전체 평균보다 높은지 수치 제시 | §4에 수치 기재(hidden 325/Q4, 668,749 고령인구) — 인라인 표로 존재 | 합격기준이 "높은지"라는 비교 방향만 있고 **수치 임계값 없음**. "얼마나 높아야 합격인가" 불명확 | 측정가능 (방향 기준) / 수치 임계값 없음 |
| 5 | 수요-접근비용 4x4 행렬 | demand Q4 + cost Q4 후보가 별도 제시 | §4에 185 hex / hidden 156 / 등록인구 535,696 인라인 수치 존재 | 합격기준에 **전체 16개 셀을 모두 채워야 하는지**, Q4×Q4 한 셀만 제시하면 충분한지 불명. 계획서 §4에서는 전체 4×4를 권장하나 §10 합격기준은 "demand Q4+cost Q4 별도 제시"로만 기재 | 보완 필요 |
| 6 | 가중치 민감도 표 | hidden overlap·top-K K=20/50/100 overlap·판정 등급 제시 | 미존재 | 합격기준에 **Jaccard·신규후보비중** 포함 요건 없음(§5에는 있으나 §10 합격기준에서 누락). 일관성 결여 | 보완 필요 |
| 7 | S1/S3 전후 지도 | 개선 대상과 실제 해소 지역이 연결되어야 함 | `qgis/S1_delta_vulnerability_map.gpkg`, `qgis/S1_candidates.gpkg`, `qgis/S2_s3_effect_categories.gpkg` 존재 | §10 합격기준에 **S3 전후 지도**가 언급되나 현재 `S2_s3_effect_categories.gpkg`는 S3 재설계 전 산출물(구 S2). 재설계 후 S3 지도 파일 아직 없음. "연결되어야 함"의 측정 방법 미명시 | 보완 필요 |
| 8 | S1/S3/S4 성과 비교표 | hidden 해소 수·고령인구 가중 감소·후보당 효율 제시 | 부분 존재(S1 수치 §9에 인라인, S3/S4 미완) | **S4** 성과는 counterfactual 재계산 전까지 산출 불가. 합격기준에 S4가 "후보 진단표"인 경우의 대체 기준 없음 | 보완 필요 |
| 9 | S1/S3/S4 scenario manifest | intervention parameter·changed cost term 등 9개 필드 기록 | `outputs/reports/` 내 시나리오 전용 manifest 없음 (기존 manifest는 vulnerability build 용도) | §10 합격기준에 manifest 필드가 §12 수락기준과 다름(§10은 6개 필드 언급, §12는 10개 필드 요구 — 불일치). 자세한 내용은 D4 참조 | 누락 |
| 10 | S4 weather-response Top20 지도/표 | CSV·GPKG hex_id·CRS·점수 순위 일치 + rank-stability 전 휴리스틱 표시 | `scenario3_weather_response_top20.csv`(루트, 20행/20 unique hex_id), `qgis/scenario3_weather_response_top20.gpkg` 존재 | CSV가 **루트 경로**에 있고 `outputs/reports/`에 없음 — §10·§12에서 명시한 공식 위치와 불일치. rank-stability 표 미존재 | 부분 충족 / 경로 불일치·rank-stability 누락 |
| 11 | 수요모형 의사결정 표 | "고정 수요 접근성 시나리오"와 "실제 수요 예측" 주장을 분리 | §8-1 트랙 A/B/C 표로 인라인 존재 | §10의 독립 산출물인지, §8-1 표 재사용인지 명시 없음. 자세한 내용은 D6 참조 | 보완 필요 |

**소결**: 11종 중 실측 파일로 충분히 충족된 항목 0개, 부분 충족 2개(#4, #10), 보완 필요 7개, 누락 1개(#9 시나리오 manifest 파일).

---

## D2. §9 시나리오3/weather-response QA 결과 실측 교차검증

§9 QA 표의 7개 항목을 실제 파일로 검증한 결과:

| 항목 | §9 본문 판정 | 실측 결과 | 일치 여부 |
|---|---|---|---|
| 루트 CSV 20행, hex_id 유일 | 통과 | `scenario3_weather_response_top20.csv` — 데이터 행 20개, unique hex_id 20개, scenario3_rank 1–20 연속 | **일치** |
| 원자료 연결 632개 | 통과 | `hidden_vulnerability_reason_diagnostics.csv` 632행 확인. top20 hex_id 20개 전원 해당 파일에 포함 | **일치** |
| 점수 재현 | 통과 | 스크립트 산식 확인 가능 (검토 범위 내 — 실행 재현은 별도) | 조건부 일치 |
| QGIS GPKG CRS 5179 | 통과 | `qgis/scenario3_weather_response_top20.gpkg` 존재 확인. CRS 직접 열기는 QGIS 필요 | 존재 확인 / CRS 미검증 |
| CSV-GPKG 일치 | (§9 본문에 "통과"로 기재) | 실측 미검증 (GPKG 속성 조회 도구 미사용) | 미검증 |
| 입력 경로 `SL_outputs/...` 불일치 | 수정 필요 | `scripts/make_scenario3_weather_response.py` line 12: `BASE / "SL_outputs/outputs/reports/hidden_vulnerability_reason_diagnostics.csv"` — 현재 repo 실제 경로는 `outputs/reports/hidden_vulnerability_reason_diagnostics.csv` | **일치 (수정 필요 확인됨)** |
| 산출 폴더 `scenario3_weather_response/` 미존재 | 수정 필요 | 해당 폴더 미존재 확인. CSV는 루트(`scenario3_weather_response_top20.csv`)에만 있고, `outputs/reports/`에는 없음 | **일치 (수정 필요 확인됨)** |
| 전용 QA JSON 부재 | 수정 필요 | `outputs/reports/` 내 `scenario3*` 또는 `s4*` 접두사 QA JSON 없음. 기존 QA는 `hidden_vulnerability_reason_diagnostics_qa.json`, `hex_vulnerability_final_qa.json` 등 vulnerability build 용도 | **일치 (수정 필요 확인됨)** |

**추가 발견사항**: 스크립트 출력 경로(`OUT_DIR = BASE / "scenario3_weather_response"`)와 실제로 커밋된 파일 위치(`scenario3_weather_response_top20.csv` at repo root, `qgis/scenario3_weather_response_top20.gpkg`)가 상이하다. 스크립트를 그대로 재실행하면 루트에 `scenario3_weather_response/` 폴더가 생성되며, 기존 루트 CSV 및 QGIS GPKG와 경로가 충돌한다. §9가 "수정 필요 3건"으로 명시한 것은 현재 repo 상태와 정확히 일치하나, 스크립트·파일 위치 불일치 규모는 3건보다 크다(출력 경로 불일치도 별도 수정 필요).

---

## D3. §12 수락기준의 측정가능성·중복 점검

### 수요지표 영역 (§12 수요지표 8개 항목)

| 항목 | 측정가능성 | 판정 |
|---|---|---|
| 모든 변수에 원천·공간단위·기대방향·한계 기재 | "기재됨"의 완성도 기준 없음. 담당자 판단에 의존 | 모호 |
| 문헌-변수 검증 매트릭스에 각 변수의 6개 속성 보유 | 항목 수(변수 몇 개인지) 미명시. 완성도 % 기준 없음 | 모호 |
| 4,551↔4,383 join 감사표 + 제외/null 사유 설명 | 항목 존재 여부로 합격/불합격 판정 가능. 구체적 | 측정가능 |
| 버스/지하철이 접근성 D 또는 보조 검증 변수로 분리 | 산식 확인으로 판정 가능 | 측정가능 |
| 최소 3개 이상 민감도 비교 | 숫자 기준 명확 | 측정가능 |
| log형은 선택적으로만 비교 | 조건("왜도/극단값 진단 후")이 주관적 — "얼마나 왜도가 크면 적용하는지" 수치 임계값 없음 | 보완 필요 |
| hidden recall·Jaccard·신규후보비중·top-K overlap 산출 | 산출 여부로 판정 가능 | 측정가능 |
| overlap 공식과 판정 등급 보고서/QA에 명시 | 명시 여부로 판정 가능 | 측정가능 |

### 시나리오 영역 (§12 시나리오 10개 항목)

| 항목 | 측정가능성 | 판정 |
|---|---|---|
| S1 신규정류장/조건부/대체안 구분 | 카테고리 레이블 존재 여부 확인 가능 | 측정가능 |
| 전체 48개 upper bound 명시 | 보고서 문구 확인 가능 | 측정가능 |
| snap 성공 ≠ 설치 가능성; 도로타입/정류장 밀도 필터 통과 후보만 계산 | 필터 적용 여부 코드 확인 가능 | 측정가능 |
| S3 실제 shortest-path edge에 닿는 후보만 대상 | 코드/데이터 확인 가능 | 측정가능 |
| S4는 "후보 진단표"와 "counterfactual 시설 효과"를 구분 | 보고서 문구 확인 가능 | 측정가능 |
| 시나리오3 CSV·GPKG·QA JSON·재현 스크립트가 같은 top20 가리켜야 함 | 실측 가능. 현재 미충족 상태 | 측정가능 (미충족) |
| S4 점수는 rank-stability 통과 전 휴리스틱으로만 표현 | 표현 확인 가능 | 측정가능 |
| S0-M3 정규화·threshold 고정 | FrozenBaseline 코드 확인 가능 | 측정가능 |
| S1/S3/S4 manifest 10개 필드 보유 | 필드 존재 여부 확인 가능. 단 §10(6개)·§11(9개)·§12(10개)에서 필드 목록이 서로 다름 (D4 참조) | 보완 필요 (불일치) |
| baseline·scenario row count·hex_id 집합 일치 확인 후 hidden 해소 수 사용 | 수치 비교로 판정 가능 | 측정가능 |

### 수요모형 영역 (2개 항목)

| 항목 | 측정가능성 | 판정 |
|---|---|---|
| 학습형 미작성 시 "수요 변화" 표현 금지 | 보고서 텍스트 검색으로 확인 가능 | 측정가능 |
| 탑승량/방문량/OD 주장 시 관측자료·학습/검증·오차지표 별도 산출 | 조건 트리거 명확 | 측정가능 |

### 보고서 영역 (4개 항목)

| 항목 | 측정가능성 | 판정 |
|---|---|---|
| 금지 문구 사용 안 함 | 텍스트 검색으로 판정 가능 | 측정가능 |
| 권장 표현 사용 | 텍스트 검색 가능 | 측정가능 |
| 그림/표 최소 세트 포함 | 체크리스트 확인 가능 | 측정가능 |
| 핵심 결론 문장이 매트릭스·감사표·민감도·manifest 중 하나에 연결 | **"연결되어야 한다"의 검증 방법 미명시**. 인용 링크 형식? 담당자 판단? | 모호 |

**중복 기준**: §11.9(리뷰 단계)의 "각 결론 문장을 태깅"과 §12 보고서 영역 "핵심 결론 문장 연결"은 동일한 검증을 두 곳에서 요구한다. 실행 단계에서 통과하면 수락기준도 자동 충족되므로 중복이나, 이 중복 자체가 오류는 아니다.

---

## D4. Scenario Manifest 필드 명세 완전성

§10, §11.6~11.8, §12에서 manifest 필드가 세 곳에서 각각 다르게 기재됨:

| 필드 | §10 합격기준 언급 | §11.6(S1) 언급 | §11.7(S3) 언급 | §11.8(S4) 언급 | §12 수락기준 언급 | 데이터 타입·형식 명시 |
|---|---|---|---|---|---|---|
| intervention parameter | O | O | — | — | O | 미명시 |
| changed cost term | O | O | O | — | O | 미명시 |
| unchanged term | O | O | O | — | O | 미명시 |
| demand_source | — | O | O | O | O | 미명시 |
| demand_hash | — | O | O | O | O | 미명시 (SHA256 여부 불명) |
| `scenario_demand_created=false` | — | O | O | O | O | boolean — 형식 명시됨 |
| fixed normalization/threshold universe | O | O | O | — | O | 미명시 |
| row-count parity | O | O | O | — | O | 미명시 (어떤 형식으로 기록?) |
| baseline hash | O | O | — | — | O | 미명시 (어떤 대상의 hash?) |
| output path | — | — | — | — | O | 미명시 |
| canonical_scenario | — | — | — | O | O | 미명시 (S4_weather_response 예시만) |
| legacy_name | — | — | — | O | O | 미명시 |

**누락 필드 (계획서 어디에도 명시 없음)**:

| 누락 필드 | 권고 이유 |
|---|---|
| `scenario_id` | 동일 시나리오의 여러 파라미터 run을 구분하기 위해 필요 |
| `run_timestamp` | 재현 시점 추적. 기존 manifest(hex_vulnerability_final_qa.manifest.json)에는 `created_at_utc` 있으나 시나리오 manifest 정의에 없음 |
| `code_commit_sha` | 스크립트 버전과 산출물을 연결하는 핵심 필드. 계획서 전체에서 언급 없음 |
| `fail_reason` | QA 실패 시 이유를 기록하는 필드. 없으면 manifest만 보고 왜 실패했는지 알 수 없음 |
| `score_weights` (S4 전용) | weather-response 점수 가중치 0.34/0.18/0.16/0.12/0.10/0.10이 스크립트에만 있고 manifest 필드로 정의되지 않음. rank-stability 검증 전 휴리스틱임을 manifest에 기록해야 함 |

§11 각 단계의 manifest 정의가 서로 달라, 실행 담당자가 세 곳을 교차 참조해야 한다. 단일 정규 필드 목록이 없다는 것이 핵심 결함이다.

---

## D5. §11 실행단계 검증 라인 검증가능성

| 단계 | 검증 라인 요약 | 구체적 측정 명령 유무 | 자동화/수동 구분 명시 | 판정 |
|---|---|---|---|---|
| 1. 수요지표 문서화 | 현재 결과 재현, 변수 dictionary, 문헌-변수 매트릭스 생성 | 없음 — "생성"이라는 행위 기술만 있음 | 없음 | 모호 |
| 2. 수요 민감도 구현 | hidden 후보 수, hidden recall, Jaccard, 신규후보비중, top-K, 4x4 행렬 | overlap 공식은 §5에 정의됨. 명령은 없음 | 없음 | 조건부 측정가능 |
| 3. POI 재분류 | 유형별 좌표 유효성, 중복 제거, hex/buffer 집계 수 | 없음 | 없음 | 모호 |
| 4. 수요모형 범위 결정 | 보고서 문장에 "수요가 증가한다"가 남아 있으면 모형 근거 연결 | 텍스트 검색(grep)으로 자동화 가능 — 명시 없음 | 없음 | 조건부 측정가능 |
| 5. 분석 universe 감사 | baseline·scenario·joined row count가 manifest와 일치 | row count 수치 비교로 자동화 가능 — 명시 없음 | 없음 | 측정가능 |
| 6. S1 재설계 | hidden 해소 수, 고령인구 가중 비용 감소, 후보당 효율 | 수치 출력 가능 — 명령 미명시 | 없음 | 측정가능 |
| 7. S3 재설계 | `target_touched_no_route_effect` 비율 감소, `delta_access_cost_m3` 증가, hidden 해소 여부 | 수치 확인 가능 — 명령 미명시 | 없음 | 측정가능 |
| 8. S4 정리 | 스크립트 재실행 후 CSV/GPKG/QA가 동일 top20 | row count·hash 비교로 자동화 가능 — 명시 없음 | 없음 | 측정가능 |
| 9. 선행연구 리뷰 | 실제 수요예측 문장은 관측자료 없으면 삭제/보류 | 주관적 판단 필요 — 자동화 불가 | 없음 | 모호 |
| 10. 팀장 검토·사용자 승인 | 가능/불가능 주장 표 작성 후 사용자 결정 | 주관적 — 자동화 불가 | 없음 | 수동 |

**전체 10단계 중 어느 단계도 pytest fixture, assertion, 자동화 여부를 명시하지 않는다.** 측정 명령(예: `assert len(df) == 20`, `assert df['hex_id'].nunique() == 20`)이 하나도 없어, 검증이 담당자 재량에 전적으로 의존한다.

---

## D6. §10 산출물 11번 "수요모형 의사결정 표"의 정의 명확성

§10 합격기준: `"고정 수요 접근성 시나리오"와 "실제 수요 예측" 주장을 분리`

§8-1에는 이미 트랙 A/B/C 3행×4열 표(필요 데이터·할 수 있는 주장·권장 여부)가 존재한다. §10이 이 표를 그대로 재사용하는 것인지, 별도 새 표를 만드는 것인지 명시가 없다.

**중복 여부 판단**: §8-1 표는 방법론 판단표이고, §10이 요구하는 산출물은 "보고서용 그림/표 최소 세트"의 일부다. 용도는 다를 수 있으나, 내용이 동일하면 두 개의 표를 별도로 관리하는 것은 비효율적이며 불일치 위험이 있다. 계획서는 이 관계를 명시하지 않는다.

**권고**: §10 산출물 11번에 "(§8-1 트랙 A/B/C 표를 그대로 보고서에 삽입하거나, 해당 표를 기반으로 확장)"이라는 한 줄을 추가하면 혼선이 제거된다.

---

## 권고: 명세 보강이 필요한 항목 리스트

1. **§10 합격기준 — 가중치 민감도 표 (#6)**: Jaccard overlap·신규후보비중 항목을 합격기준에 추가 (현재 §5에만 있음).

2. **§10 합격기준 — 4x4 행렬 (#5)**: 전체 16개 셀 필수인지, Q4×Q4 단독 제시로 충분한지 명시.

3. **§10 합격기준 — 수요 구성요소 지도 (#3)**: 4종의 정확한 목록(registered_population, registered_senior_population, living_population, poi_total)과 고령 축 분리형 포함 여부 명시.

4. **§10 합격기준 — S1/S3/S4 scenario manifest (#9)**: §10·§11·§12에서 분산된 필드 목록을 단일 정규 목록으로 통합. 누락 필드(scenario_id, run_timestamp, code_commit_sha, fail_reason, score_weights) 추가 검토.

5. **§11 전 단계**: 적어도 자동화 가능한 단계(5·6·7·8)에 구체적 검증 명령 또는 pytest fixture 포인터를 추가.

6. **§9 S4 추가 수정 사항**: 계획서가 "수정 필요 3건"으로 기재한 것 외에, 스크립트 출력 경로(`scenario3_weather_response/`)와 실제 파일 위치(루트 CSV + `qgis/`) 간의 불일치도 수정 필요로 명시해야 함.

7. **§10 합격기준 — 문헌-변수 매트릭스 (#1)**: 커버해야 할 변수 수(최소 몇 개인지) 명시.

8. **§12 보고서 영역**: "핵심 결론 문장이 연결되어야 한다"의 검증 방법(인용 각주, 표 번호 참조 등) 명시.

---

## 최종 판정

> **이 계획대로 실행할 경우, 합격 판정이 가능한 항목은 11종 중 약 5개 수준이다.** 수치 기반 판정이 명확한 항목(universe 감사표, 민감도 overlap 수식, row-count parity, 금지 문구 여부)은 합격 여부 판정이 가능하다. 그러나 "모든 변수에 기재", "핵심 결론이 연결", "개선 대상과 해소 지역이 연결" 같은 주관적 기술어가 포함된 항목은 담당자마다 판정이 달라질 수 있어 측정 불가 상태다. Manifest 필드는 세 곳에서 분산 정의되고 데이터 타입·형식이 없어 구현 시 불일치가 발생할 가능성이 높다.

---

## 요약 수치 (종료 보고)

- **합격기준이 측정 불가능한 항목 수**: **6개** (D1 #1 행수 미명시, #3 지도 목록 불명, #7 "연결" 방법 미명시, #8 S4 대체기준 없음, §12 보고서 "연결" 미명시, §11 검증 명령 전무)
- **누락 manifest 필드 수**: **5개** (scenario_id, run_timestamp, code_commit_sha, fail_reason, score_weights)
