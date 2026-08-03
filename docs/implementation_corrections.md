# 구현 중 발견한 문제와 반영 사항

이 문서는 변경 이력 기록이다. 중간 검증 결과(`19 passed`, `21 passed` 등)는 당시 상태를 보존한 것이며, 최신 상태 판단은 `README.md`와 `outputs/reports/v2_2_execution/v2_2_execution_summary.md`를 기준으로 한다.

## 1. QGIS 문서가 너무 추상적이었음

초기 문서는 영어 중심이고 “무엇을 클릭해서 어떤 파일을 만들지”가 부족했다.

반영:

- `docs/qgis/00_workflow_index.md` 추가
- QGIS 문서 6개를 한국어 작업 절차로 재작성
- 입력, 작업 절차, 출력, 합격 기준, 자주 생기는 문제를 통일

## 2. 비용함수 계수가 근거 있는 보정값처럼 보일 수 있었음

초기 `costs.py`에는 `alpha=0.03`, `weather_beta=0.03`, `interaction_beta=0.08`, `snow_weight=5.0`이 바로 들어가 있었다. 이 값들은 아직 서울 보행자료로 보정된 값이 아니다.

반영:

- `docs/methods/cost_function_parameters.md` 추가
- 계수를 “시나리오 기본값”으로 명시
- `configs/model_params.yaml`에 민감도 후보값 추가
- `CostParameters.from_mapping()` 추가로 config에서 계수를 읽을 수 있게 정리

현재 해석:

- 모형 구조는 연구 가설에 기반
- 숫자 계수는 민감도 분석용 초기값
- 최종 보고에서는 “보정계수”가 아니라 “시나리오 파라미터”라고 표현

## 3. Python 실행 환경을 잘못 진단했음

처음에는 Python이 없다고 봤지만, 실제로는 `python.exe`가 Windows Store shim이었고 `uv.exe`는 설치되어 있었다.

반영:

- `.venv` 생성
- `requirements-dev.txt` 추가
- `docs/setup/python_environment.md` 추가
- `PYTHONPATH=src` 방식으로 테스트 실행 절차 정리

검증:

```text
19 passed
```

## 4. 인코딩 설정이 틀렸음

ASOS와 250m 생활인구 파일을 처음에는 `utf-8`로 가정했지만 실제 샘플 확인 결과 `cp949` 또는 `euc-kr`로 읽어야 했다.

반영:

- `configs/data_sources.yaml`
  - `asos_weather.encoding = cp949`
  - `local_resident_250m.encoding = cp949`

검증:

- `validate-data` 통과
- `outputs/reports/data_validation.json` 생성

## 5. glob 샘플 읽기가 깨졌음

`local_resident_250m`은 `data/250_LOCAL_RESD_202511/*.csv` glob으로 등록되어 있는데, 샘플 검증에서 glob 문자열을 eager reader에 그대로 넘겼다.

반영:

- `read_csv_sample()`에서 glob 패턴이면 첫 번째 매칭 파일을 샘플로 읽도록 수정

## 6. pytest가 Windows Temp 권한 문제를 밟았음

`tmp_path` fixture가 `<system-temp>/pytest` 권한 문제로 실패했다.

반영:

- `tests/test_csv_reader.py`에서 `tmp_path` 의존 제거
- 고정 fixture 파일을 사용하도록 변경
- pytest cache provider 비활성화 명령 문서화

## 7. NumPy 2.x 호환성 문제

`np.trapz`가 NumPy 2.x에서 제거되어 Gini 계산 테스트가 실패했다.

반영:

- 직접 trapezoid 면적을 계산하도록 `metrics.py` 수정

## 현재 검증 상태

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe -m sl_accessibility.cli validate-data
```

결과:

```text
21 passed
outputs/reports/data_validation.json 생성
```

## 8. 시나리오별 정규화를 다시 할 위험

정책 시나리오를 비교할 때 각 시나리오에서 Min-Max 정규화를 새로 fit하면, 취약지역 감소가 실제 개선 때문인지 척도 재조정 때문인지 구분하기 어렵다.

반영:

- `src/sl_accessibility/accessibility/scenario.py` 추가
- `FrozenBaseline`이 `S0-M3`의 cost/demand normalizer와 vulnerability threshold를 고정 저장
- `evaluate_scenario()`가 같은 기준으로 시나리오 비용을 평가
- 전체인구/고령인구 가중 평균 및 90p 감소율, 취약 hex/인구 감소율, Gini/Theil 변화를 한 번에 산출

현재 검증:

```text
29 passed
```

## 9. 실제 edge 비용 산출 진입점이 없었음

비용함수 단위 테스트는 있었지만, 보행망 edge 레코드에 `M0`~`M3` 비용 컬럼을 붙이는 실행 단위가 없었다. Dijkstra로 넘어가려면 edge별 weight 테이블이 먼저 필요하다.

반영:

- `src/sl_accessibility/accessibility/edge_cost_table.py` 추가
- `build_edge_cost_table()`이 원본 edge dict를 직접 바꾸지 않고 `cost_m0`~`cost_m3`를 붙인 새 row를 반환
- 경사 이상치(`sanitize_grade_abs(...) is None`)는 비용 테이블에서 제외
- `sl_accessibility.cli build-edge-cost-sample` 명령 추가
- 샘플 산출물 `data/interim/walking_edge_costs_sample.parquet` 생성 확인

현재 검증:

```text
25 passed
```

## 11. H3와 D 후보 생성 진입점 추가

Dijkstra로 넘어가기 위해서는 O 후보인 분석 hex 중심점과 D 후보인 대중교통 정류장/역 좌표가 필요하다. 기존에는 이 두 산출물을 만드는 명령이 없었다.

반영:

- `h3==4.4.2` 의존성 추가
- `src/sl_accessibility/geo/hex_grid.py` 추가
- `src/sl_accessibility/transit/d_candidates.py` 추가
- `sl_accessibility.cli build-analysis-hexes` 명령 추가
- `sl_accessibility.cli build-transit-d-candidates` 명령 추가
- QGIS 검수용 산출물 생성

검증:

```text
qgis/out_analysis_hex_h3res9.gpkg: hex 4,551개, centroid 4,551개
qgis/out_transit_d_candidates.gpkg:
  - 서울 경계 내부 D 후보 10,967개 (bus 10,664개, subway 303개)
  - 서울 경계 밖 QA 후보 84개 (bus 12개, subway 72개)
29 passed
```

## 12. D 후보가 서울 밖으로 튀는 문제

초기 D 후보 필터는 lon/lat bounding box와 좌표 품질 플래그만 사용했다. 이 방식은 서울 주변 수도권 정류장/역 일부를 통과시킨다.

반영:

- `split_candidates_by_boundary()` 추가
- `build-transit-d-candidates` 명령에서 `qgis/wrk_seoul_boundary_5179.gpkg` 기준으로 메인 D 후보를 서울 경계 내부로 제한
- 서울 경계 밖 후보는 삭제하지 않고 `qa_transit_d_candidates_outside_boundary` 레이어로 저장

검증:

```text
out_transit_d_candidates: 10,967개
qa_transit_d_candidates_outside_boundary: 84개
30 passed
```

## 10. 전체 edge 비용 테이블 생성

샘플 비용 테이블은 있었지만 전체 보행망을 Dijkstra 입력으로 넘길 Parquet 산출물이 없었다. 원본 `walking_network_edges_with_slope_google.csv`는 약 131MB이므로 샘플 reader나 eager read를 전체 변환에 쓰면 안 된다.

반영:

- `add_edge_cost_columns_lazy()` 추가
- `sl_accessibility.cli build-edge-costs` 명령 추가
- `configs/model_params.yaml`에서 읽은 `CostParameters`를 전체 변환에도 적용
- 전체 변환은 Polars lazy frame과 Parquet sink를 사용
- `data/interim/walking_edge_costs.parquet` 생성 확인

검증:

```text
원본 edge: 467,556행
grade_abs_percent > 100 제외: 30행
grade_abs_percent 결측 제외: 900행
최종 비용 테이블: 466,626행
25 passed
```
