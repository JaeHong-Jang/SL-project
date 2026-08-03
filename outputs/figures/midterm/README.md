# Midterm Visualization Set

논문/분석 보고서/중간발표에 쓸 수 있도록 같은 입력 데이터에서 생성한 시각화 세트입니다.

## 사용 원칙

- `hidden`은 확정 취약지역이 아니라 모형 기준 현장검토 후보입니다.
- 정책 시나리오는 효과 입증이 아니라 상한·진단으로만 해석합니다.
- `632 baseline`과 `429 robust-core`를 함께 보여 기준 민감도 질문을 방어합니다.
- 지도에는 가능하면 후보 정의 주석을 함께 넣습니다.

## Figures

### fig01_problem_walkshed
- Title: 400m 직선거리 기준과 실제 보행권의 차이
- Claim: 정류장 반경 400m 안에서도 실제 보행망과 경사 때문에 도달 가능 영역이 달라질 수 있음을 도입부에서 설명한다.
- PNG: `outputs/figures/midterm/fig01_problem_walkshed.png`
- PDF: copied source only
- Sources: outputs/figures/s3_walkshed_comparison.png

### fig02_data_qa_dashboard
- Title: 데이터 정합 및 품질관리 대시보드
- Claim: 분석 결과가 단순 지도 색칠이 아니라 정제·유효성 검사를 통과한 분석셋에서 산출됐음을 보여준다.
- PNG: `outputs/figures/midterm/fig02_data_qa_dashboard.png`
- PDF: `outputs/figures/midterm/fig02_data_qa_dashboard.pdf`
- Sources: outputs/reports/v2_2_execution/data_loss_ledger_v2_2.csv, outputs/reports/hex_vulnerability_final_audit.json

### fig03_model_cost_demand_framework
- Title: 보행비용과 수요지수 분석 프레임
- Claim: M0~M3 단계적 비용 증가와 수요지수 구성요소를 함께 보여 분석 프레임을 설명한다.
- PNG: `outputs/figures/midterm/fig03_model_cost_demand_framework.png`
- PDF: `outputs/figures/midterm/fig03_model_cost_demand_framework.pdf`
- Sources: data/derived/hex_vulnerability_final.parquet, outputs/reports/hex_vulnerability_summary_stats_v3.csv

### fig04_environment_burden_map
- Title: M0-M3 환경부담 증가 지도
- Claim: 경사·기상 반영이 서울 전역에서 접근비용을 얼마나 늘렸는지 공간적으로 보여준다.
- PNG: `outputs/figures/midterm/fig04_environment_burden_map.png`
- PDF: `outputs/figures/midterm/fig04_environment_burden_map.pdf`
- Sources: qgis/m0_m3_environment_burden_shift.gpkg, outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.json

### fig05_hidden_candidates_before_after_map
- Title: 현행 400m 기준과 hidden 후보 비교 지도
- Claim: 현행 거리 기준으로는 양호해 보이는 영역 안에서 M3+수요 기준 hidden 후보가 어떻게 나타나는지 보여준다.
- PNG: `outputs/figures/midterm/fig05_hidden_candidates_before_after_map.png`
- PDF: `outputs/figures/midterm/fig05_hidden_candidates_before_after_map.pdf`
- Sources: qgis/out_hex_vulnerability_final.gpkg, qgis/hidden_vulnerable_robust_core.gpkg

### fig06_robustness_and_quadrant
- Title: 강건성 및 비용×수요 교차검증
- Claim: baseline 632개와 robust-core 429개를 분리하고, 곱셈 점수 외 비용·수요 직접 교차검증 결과를 보여준다.
- PNG: `outputs/figures/midterm/fig06_robustness_and_quadrant.png`
- PDF: `outputs/figures/midterm/fig06_robustness_and_quadrant.pdf`
- Sources: outputs/reports/v2_2_execution/normalization_combination_threshold_robustness.csv, outputs/reports/v2_2_execution/quadrant_4x4_matrix.csv

### fig07_reason_diagnostics
- Title: hidden 후보 원인 진단 및 자치구 분포
- Claim: hidden 후보가 경사·기상 부담형, 수요집중형, 복합형 등으로 나뉘며 정책 후보도 유형별로 달라져야 함을 보여준다.
- PNG: `outputs/figures/midterm/fig07_reason_diagnostics.png`
- PDF: `outputs/figures/midterm/fig07_reason_diagnostics.pdf`
- Sources: outputs/reports/hidden_vulnerability_reason_diagnostics_qa.json, outputs/reports/hidden_vulnerability_reason_diagnostics.csv

### fig08_policy_scenario_diagnostics
- Title: 정책 시나리오 상한·진단 결과
- Claim: 후보 정류장, 경사 cap, 기상항 제거 시나리오가 실제 정책효과가 아니라 우선순위 검토용 상한·진단임을 보여준다.
- PNG: `outputs/figures/midterm/fig08_policy_scenario_diagnostics.png`
- PDF: `outputs/figures/midterm/fig08_policy_scenario_diagnostics.pdf`
- Sources: outputs/reports/scenario_counterfactual/S1_delta_vulnerability_summary.json, outputs/reports/scenario_counterfactual/S3_delta_vulnerability_summary.json, outputs/reports/scenario_counterfactual/S4_weather_off_delta_vulnerability_summary.json

### fig09_key_numbers_summary
- Title: 핵심 숫자 요약 패널
- Claim: 발표나 부록 첫 장에서 전체 분석 규모, hidden 후보, 강건성, 한계를 한눈에 정리한다.
- PNG: `outputs/figures/midterm/fig09_key_numbers_summary.png`
- PDF: `outputs/figures/midterm/fig09_key_numbers_summary.pdf`
- Sources: outputs/reports/hex_vulnerability_final_qa.json, outputs/reports/v2_2_execution/v2_2_execution_summary.md, outputs/reports/m4_senior/m4_senior_summary.json
