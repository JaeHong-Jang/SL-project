# Worker 1 민감도 분석: alpha, beta_weather, beta_interaction, threshold

## 범위와 재현 명령

- 입력: `data/derived/hex_vulnerability_final.parquet`
- 기준 설정: `configs/model_params.yaml`
- 실행 명령: `./.venv/Scripts/python.exe scripts/worker1_sensitivity_analysis.py`
- 검증 명령: `./.venv/Scripts/python.exe -m pytest tests/test_cost_parameters.py tests/test_vulnerability.py`
- 산출물: `docs/reports/worker1_sensitivity_parameter_table.csv`, `docs/reports/worker1_sensitivity_threshold_table.csv`, `docs/reports/worker1_sensitivity_summary.json`

## 이번 실행과 검증 결과

- 생성 시각: 2026-05-16T18:32:58+09:00
- 실제 분석 실행: `.venv-linux/bin/python scripts/worker1_sensitivity_analysis.py`
- 실제 검증 실행: `.venv-linux/bin/python -m pytest tests/test_cost_parameters.py tests/test_vulnerability.py -q -p no:cacheprovider; PYTHONPATH=src .venv-linux/bin/python -m sl_accessibility.cli validate-data --output .omx/logs/worker1_data_validation.json`
- 검증 결과: pass: pytest 7 passed in 3.74s; validate-data 35/35 contract samples ok
- 실행 환경 메모: Windows .venv/Scripts/python.exe and powershell.exe bridge attempts failed with WSL UtilBindVsockAnyPort; analysis was reproduced in WSL .venv-linux.

## 기준선

- 유효 hex: 4,383 / 4,551
- 기본 계수: alpha=0.03, beta_weather=0.03, beta_interaction=0.08
- 기존 final 기준 top 20% 취약 hex: 877
- 기존 final hidden vulnerable hex: 632
- 추정 weather intensity: 2.0000
- M3 비용 재구성 평균 절대오차: 0.0649 m-equivalent

## 결론

결론은 유지된다. alpha, beta_weather, beta_interaction을 각각 기준값의 -30%부터 +30%까지
단독 변경해도 top 20% 취약지역의 최저 유지율은 98.2%, hidden vulnerable의
최저 유지율은 97.5%였다. 취약도 순위 Spearman 상관의 최저값도
0.9997로 높아, 계수 절대값보다 공간적 우선순위가 더 안정적이라는 기존 해석을 유지할 수 있다.

단, 이 분석은 기존 접근성 산출물의 M0/M1/M2/M3 비용에서 유효 경사부담을 역산해 비용을 재구성했다.
계수 변경 시 최단경로 자체가 바뀌는 효과는 재탐색하지 않았으므로, 최종 제출 전에는 주요 조합에 대해
`build-edge-costs`와 `build-accessibility-prelim`을 별도 산출명으로 재실행하는 보강이 필요하다.

## 파라미터 민감도 표

| parameter | multiplier | value | vulnerable | hidden | vulnerable retention | hidden retention | Spearman rho |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alpha | 70% | 0.0210 | 877 | 632 | 98.2% | 97.5% | 0.9997 |
| alpha | 80% | 0.0240 | 877 | 632 | 98.7% | 98.3% | 0.9999 |
| alpha | 90% | 0.0270 | 877 | 632 | 99.3% | 99.1% | 1.0000 |
| alpha | 100% | 0.0300 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| alpha | 110% | 0.0330 | 877 | 633 | 99.5% | 99.5% | 1.0000 |
| alpha | 120% | 0.0360 | 877 | 633 | 99.1% | 98.9% | 0.9999 |
| alpha | 130% | 0.0390 | 877 | 633 | 98.6% | 98.3% | 0.9997 |
| beta_weather | 70% | 0.0210 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_weather | 80% | 0.0240 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_weather | 90% | 0.0270 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_weather | 100% | 0.0300 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_weather | 110% | 0.0330 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_weather | 120% | 0.0360 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_weather | 130% | 0.0390 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_interaction | 70% | 0.0560 | 877 | 632 | 99.9% | 99.8% | 1.0000 |
| beta_interaction | 80% | 0.0640 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_interaction | 90% | 0.0720 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_interaction | 100% | 0.0800 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_interaction | 110% | 0.0880 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_interaction | 120% | 0.0960 | 877 | 632 | 100.0% | 100.0% | 1.0000 |
| beta_interaction | 130% | 0.1040 | 877 | 632 | 100.0% | 100.0% | 1.0000 |

## Threshold 민감도 표

| top share | vulnerable | hidden | hidden registered pop | retention vs top20 | Jaccard vs top20 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10% | 439 | 252 | 709,044 | 50.1% | 0.501 |
| 20% | 877 | 632 | 1,660,654 | 100.0% | 1.000 |
| 30% | 1315 | 1040 | 2,621,234 | 100.0% | 0.667 |

## 파라미터별 관찰

- alpha: hidden count 범위 632~633; 경사 부담을 키워도 top 20% 취약지역의 골격은 유지된다.
- beta_weather: hidden count 범위 632~632; 공간적으로 균일한 기상 가산항 성격이 강해 순위 변화가 제한적이다.
- beta_interaction: hidden count 범위 632~632; 경사와 기상이 결합된 hex에서 일부 순위 이동이 있으나 결론을 뒤집지는 않는다.
- 전체 파라미터 변형의 vulnerable count 범위는 877~877, hidden count 범위는 632~633이다.

## 남은 리스크

- 계수는 보행속도 관측자료로 보정된 값이 아니라 시나리오 기본값이다.
- 본 Worker 1 분석은 최단경로 재탐색 없이 기존 산출물 기반으로 수행한 국소 민감도 분석이다.
- ASOS 서울 단일 관측소 기반 weather intensity를 공간적으로 동일하게 적용한 한계는 그대로 남는다.
