# 검토 대상: demand-scenario-redesign-2026-05-23.md 보고서/계획 검증 브리프

## 검토 목적
다음 파일을 **이대로 실행하면 안전한 계획인지** 팀 구조로 체계적 검증.

- **대상**: `.omx/plans/demand-scenario-redesign-2026-05-23.md` (653줄, 13개 섹션)
- **상태**: 코드/데이터 반영 전 검토용 계획. 사용자 승인 게이트 5단계 명시(§2).
- **모드**: review-only. mutation 없음. 보고서 작성만.

## 검토 대상 구조 요약
| # | 섹션 | 핵심 내용 |
|---|---|---|
| 1 | 결론 요약 | demand_index_final을 "잠재 수요압력"으로 재명명. "실제 통행수요" 표현 금지. 분리 카테고리 3종(접근성/정책우선/형평성) |
| 2 | 팀 구조와 검토 게이트 | 팀장+팀원1~6, 사용자 검토 게이트 5단계 |
| 3 | 현재 수요지표 진단 | 4,551 hex 검증 수치, demand_index 평균 0.213, 기여 비중, Spearman |
| 4 | 4분위 분석 | demand×cost 4x4 행렬. demand Q4+cost Q4 = 185 hex (hidden 156, 등록인구 535K) |
| 5 | Min-Max/log/4분위 역할 | log는 기본 산식 X, 선택적 민감도. 검증 세트 A~E. 합격기준 overlap 공식 |
| 6 | 고령자 POI 선택 근거 | 문헌-변수 매트릭스 8개 열, POI 계층 7종, 가중치 처리 원칙 |
| 7 | M1/M2/M3 분리 | 본문 M0vsM3, 원인진단 분해, 시나리오 대상 선정 분리 |
| 8 | 취약지역 달라지는 이유 | 변동 원인 5개, "잠재 필요 프록시 차이"로 설명 |
| 8-1 | 수요 시나리오와 예측모형 판단 | 트랙 A/B/C 분리, A=기본, C는 범위확장 시만. 학습형 최소 조건 |
| 8-2 | 선행연구 기반 검증 프로토콜 | G1~G8 게이트 8개, 선행연구 매핑 7행, 최종 판정 규칙(통과/보류/탈락) |
| 9 | S1/S3/S4 재설계 및 시나리오3 산출물 판정 | 번호체계 재정렬, S1 A/B/C 후보, S3 shortest-path, S4 weather-response QA 결과 |
| 10 | 필요한 그림과 표 | 11종 최소 세트와 합격기준 |
| 11 | 실행 단계 | 10단계 (수요지표→민감도→POI→수요모형 범위→universe→S1→S3→S4→리뷰→승인) |
| 12 | 수락 기준 | 수요지표/시나리오/수요모형/보고서 4영역 |
| 13 | 참고 근거 | 22개 (영문 학술 16건 + 한국 정부/학술 6건) |

## 팀 분담
- **팀원A (scientist)**: §1, §3, §4 — 데이터 정의·진단 수치·4분위 표의 사실 정합성 검증
- **팀원B (architect)**: §2, §5, §7, §8-1, §8-2, §9, §11, §12 — 방법론/실행단계/G1~G8/수락기준 자기일관성
- **팀원C (document-specialist)**: §6, §8-2, §13 — 22개 참고문헌이 본문 주장에 정확히 매핑되는지
- **팀원D (executor)**: §10, §9 manifest 필드, 합격기준 — 그림/표 11종 충분성, manifest 필드 명세, 측정가능성
- **팀장 (critic, Wave B)**: 4명 결과 종합, 최종 verdict (APPROVE / REVISE / REJECT) + 사용자 결정 게이트

## 검토 산출 위치
- `outputs/reports/plan_review/A_data_definitions.md`
- `outputs/reports/plan_review/B_methodology_consistency.md`
- `outputs/reports/plan_review/C_literature_mapping.md`
- `outputs/reports/plan_review/D_figures_acceptance.md`
- `outputs/reports/plan_review/00_lead_verdict.md`

## 공통 검증 원칙
- 코드/데이터를 **수정하지 말 것**. 읽기만.
- 본 계획서가 인용한 file:line, 수치, 공식을 **실측·실파일로 교차 검증**.
- 본문 주장과 인용 출처 간의 정합성을 평가.
- 자기일관성 점검: 본문 내 다른 섹션에서 모순되는 정의나 수치가 있는지.
- 누락된 단계/필드/측정기준이 있는지 식별.
- 결과는 (사실/우려/권고) 3분류로 명확히 보고.

## 검토 대상이 사용 중인 실측 데이터(교차검증용)
- `data/derived/hex_vulnerability_final.parquet` (4,551 hex, 4,383 valid)
- `outputs/reports/hex_vulnerability_final_qa.json` (vulnerability_threshold 0.0288, vulnerable 877)
- `outputs/reports/hidden_vulnerability_reason_diagnostics.csv` (hidden 632개)
- `outputs/reports/scenario3_weather_response_top20.csv`, `qgis/scenario3_weather_response_top20.gpkg`
- `src/sl_accessibility/population/hex_features.py`, `src/sl_accessibility/accessibility/vulnerability.py`, `src/sl_accessibility/accessibility/metrics.py`
- `configs/data_sources.yaml`, `docs/SCENARIO_TASK_ASSIGNMENT.md`

각 reviewer는 위 파일 중 자신의 담당 섹션과 관련된 파일만 선택적으로 읽으면 됨.