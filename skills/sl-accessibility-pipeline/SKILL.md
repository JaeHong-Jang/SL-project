---
name: sl-accessibility-pipeline
description: Build, debug, audit, and explain the Seoul slope-weather-transit walking accessibility data pipeline. Use when working on DEM/slope features, ASOS weather joins, transit stop access, walking cost models, M0/M3/S0-M3 baselines, reproducible processing, data QA, or validation for the SL project.
---

# SL Accessibility Pipeline

이 스킬은 서울 경사·기상 대중교통 보행접근성 하네스를 수정하거나 점검할 때 쓴다. 데이터 준비, 비용함수, 접근성 점수, QA 기준이 매번 흔들리지 않도록 같은 절차를 따른다.

## Workflow

1. 입력 테이블, geometry 필드, 식별자, CRS, 결측 처리 방식을 `references/data-contracts.md`와 먼저 대조한다.
2. 접근성 점수 정의와 가중 방식은 `references/scoring-method.md`에서 고른다.
3. 산출물을 분석-ready로 보기 전에 `references/qa-checks.md`의 QA를 수행한다.
4. 계약에서 벗어난 내용은 반드시 기록한다. 예: 결측값, CRS 변환, 제외 row, 파라미터 변경, unmatched geometry.

## Output Expectations

- “정류장 데이터”처럼 뭉뚱그리지 말고 실제 테이블명과 필드명을 쓴다.
- 점수 공식, 거리/시간 threshold, 정규화 방식을 명시한다.
- 입력 row, 유지 row, 제외 row, 매칭 실패 geometry 수를 함께 보고한다.
- 미해결 가정은 조용히 채우지 말고 “아직 가정” 또는 “미확정”으로 표시한다.
