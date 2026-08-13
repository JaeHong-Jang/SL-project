# Codex Project Guide

이 저장소는 서울 경사·기상 대중교통 보행접근성 분석 프로젝트다. Codex/GPT 계열 도구가 이 프로젝트에서 작업할 때는 아래 기준을 우선 적용한다.

## Project Context

- 핵심 질문: 서울에서 경사와 기상 악화가 결합될 때 대중교통 보행접근성이 취약해지는 지역을 찾고, 정책 시나리오별 개선 효과를 비교한다.
- 기준선: `M0`은 거리-only baseline, `M3`는 거리·경사·기상·상호작용 비용모형, `S0-M3`는 정책평가 기준선이다.
- 시나리오 비교에서는 `S0-M3`에서 고정한 분석 hex, 정규화 파라미터, 취약 threshold를 재사용한다. 시나리오별 Min-Max 재정규화는 금지한다.
- 최종 수치와 진행 상태는 `README.md`를 먼저 확인한다.

## Local Skills

작업 성격에 따라 repo-local skill을 우선 참고한다.

- `skills/sl-accessibility-pipeline/SKILL.md`: 데이터 계약, 비용함수, 접근성 점수, QA, 재현 실행을 다룰 때 사용한다.
- `skills/sl-qgis-workflow/SKILL.md`: QGIS 레이어, EPSG:5179, 250m 생활인구 조인, 경사 QC, 지도 export를 다룰 때 사용한다.
- `skills/sl-research-writing/SKILL.md`: 보고서, 발표문, 방법론 문장, 한영 용어, 인용 정리를 다룰 때 사용한다.

## Engineering Rules

- 기존 패턴을 우선 따른다. 분석 로직은 `src/sl_accessibility/`, 실행 wrapper는 `scripts/`, 설정은 `configs/`, 검증은 `tests/`에 둔다.
- 원자료와 대용량 산출물은 임의 수정하지 않는다. 특히 `data/raw/`, `qgis/`, 대형 `outputs/` 파일은 필요한 경우에만 명시적으로 다룬다.
- 비용함수나 threshold를 바꾸면 `configs/model_params.yaml`, 관련 문서, 테스트, manifest/QA 산출물의 일관성을 함께 확인한다.
- 접근성·취약도 산출물을 보고할 때는 입력 row, 유지 row, 제외 row, 스냅 실패 수, CRS, 정규화 방식을 함께 기록한다.
- 최종 주장에서는 robust-core, sensitivity, upper-bound/counterfactual label을 구분한다.

## Verification

- Python 변경 후에는 가능한 범위에서 `pytest`를 실행한다.
- 데이터 계약이나 QA 로직 변경 후에는 관련 CLI 또는 산출 JSON을 재생성하고 변경 이유를 기록한다.
- 프론트엔드 변경은 `prototype/frontend`에서 `npm` 스크립트와 브라우저 확인을 수행한다.

## Communication

- 한국어 자료는 프로젝트의 기존 표현을 따른다.
- 결과 수치는 날짜와 산출물 경로를 함께 제시한다.
- 근거보다 큰 정책 효과를 주장하지 않는다. 미확정 가정은 명시한다.
