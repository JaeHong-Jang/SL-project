# v2 재검토 브리프

## 검토 목적
v2 계획서가 v1 검토 결과(`outputs/reports/plan_review/00_lead_verdict.md`, verdict=REVISE)를 **충실히 반영**했는지, **새 갈등**을 만들지 않았는지, **자체 품질**이 실행 가능 수준인지를 평가.

- **대상**: `.omx/plans/demand-scenario-redesign-v2-2026-05-29.md`
- **v1 검토 결과 위치**: `outputs/reports/plan_review/{A,B,C,D,00_lead_verdict}.md`
- **모드**: review-only. 데이터·코드 mutation 없음.

## v2가 도입한 신규 항목 (각별 점검 필요)

| 항목 | v2 위치 | v1 대비 | 점검 포인트 |
|---|---|---|---|
| §0 변경 요약 표 | §0 | 신설 | 17개 reviewer 발견 ↔ v2 위치 매핑이 정확한가 |
| universe-A/B 명시 | §3, §4.1, §4.2 | 신설 | universe 전환 표기가 본문 전체에서 일관되는가 |
| POI 손실 표 | §3 | 신설 | 손실 수치(34,234/1,065/39)가 실측과 일치하는가 |
| §5.1 합격기준 절 | §5 | 신설 | 용어 통일·zero-guard·임계값이 §11.2/§12와 일치하는가 |
| §6.0 결합방식 비교 표 | §6 | 신설 | 차감/비율/곱셈/가중합 4행이 학술 표준과 부합하는가 |
| §8-2 게이트↔§11 매핑 | §8-2 | 신설 | G1~G8 8행이 §11.1~§11.11에 1:1 매핑되는가 |
| §9.1 recommended_action↔A/B/C | §9.1 | 신설 | 실측 csv 라벨과 매핑 표가 일치하는가 |
| §9.2 routing.py 함수 시그니처 | §9.2 | 신설 | 시그니처가 실현 가능하고 단위 테스트가 의미 있는가 |
| §9.3 variant 6종 | §9.3 | 신설 | rank-stability variant 6개가 충분히 다양한가 |
| §10 측정가능 기준 | §10 | 갱신 | 11종 산출물 각 행 합격기준이 측정 가능한가 |
| §11.10 그림표 산출 단계 | §11 | 신설 | §10과 §11.10가 1:1 정합하는가 |
| §11.7 routing 사전 작업 | §11.7 | 신설 | predecessor reconstruction 코드 변경 범위가 명확한가 |
| §12.5 OECD/JRC 한계 | §12 | 신설 | Monte Carlo 한계 인정 표현이 충분한가 |
| §13.2 추가 3건 | §13 | 신설 | EJSCREEN·CDC SVI·UK IMD URL 생존·인용 정확성 |
| §13 #19 URL 교체 | §13 | 갱신 | www.korea.kr 데스크톱 URL이 실제 유효한가 |
| 부록 A 21필드 스키마 | 부록 A | **신설** | 필드 정의·타입·필수/선택이 §11·§12와 모두 정합하는가 |
| 부록 B 빠른 참조 | 부록 B | 신설 | v1↔v2 차이 모두 누락 없이 기록됐는가 |

## 팀 분담
- **팀원A (scientist)**: §0, §3, §4.1, §4.2 — universe-A/B 명시·POI 손실·V6 회귀 확인
- **팀원B (architect)**: §0, §5.1, §8-2 매핑, §9.1/9.2/9.3, §11(10단계+신설), §12, **부록 A 21필드** 자기일관성
- **팀원C (document-specialist)**: §6.0 비교 표, §13.2 추가 3건 URL/인용, §13 #19 URL 교체, §12.5 한계 표현
- **팀원D (executor)**: §10 측정가능 기준, §11.10 산출 단계, §9.0 QA 4번째 항, **부록 A의 산출 가능성**
- **팀장 (critic, Wave B)**: 4명 결과 종합 → v2 verdict (APPROVE / REVISE / REJECT)

## 산출 위치
- `outputs/reports/plan_review_v2/A_data_definitions_v2.md`
- `outputs/reports/plan_review_v2/B_methodology_consistency_v2.md`
- `outputs/reports/plan_review_v2/C_literature_mapping_v2.md`
- `outputs/reports/plan_review_v2/D_figures_acceptance_v2.md`
- `outputs/reports/plan_review_v2/00_lead_verdict_v2.md`

## 공통 검증 원칙
- v1 검토에서 지적된 항목이 v2에서 **해결됐는가** (회귀 확인)
- v2가 도입한 신규 항목이 **자기일관성·실행가능성·재현성**을 갖추는가
- v2가 v1 대비 **새로 만든 갈등**이 있는가 (예: 부록 A 필드 ↔ §11 본문 모순)
- 정답을 회피하지 말 것. APPROVE / REVISE / REJECT 중 하나만 선택.

## v1 핵심 발견 빠른 참조 (회귀 확인용)
- A V6 MAJOR: §4 universe 4,551 vs 4,383
- B M2 MAJOR: G1~G8↔§11 매핑 부재
- B M3 MAJOR: §11↔§12 매핑·그림표 단계 부재
- B M4 MAJOR: scenario manifest 분산
- B M5 MAJOR: routing.py path edge 함수 부재
- C cherry-pick: Jiao&Dillivan 차감 모델 곱셈 변호로 인용
- C 누락: EJSCREEN·CDC SVI·UK IMD
- D D2: scenario3 weather-response 4번째 수정 항
- D 측정불가 6 + 누락 manifest 5