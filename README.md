# 서울 경사·기상 대중교통 보행접근성 프로젝트

서울시에서 경사와 기상 악화가 결합될 때 대중교통 보행접근성이 취약해지는 지역을 찾고, 정책 시나리오별 개선 효과를 비교하기 위한 연구 하네스다.

## 핵심 기준선

- `M0`: 거리만 반영한 현행 기준 비교용 baseline
- `M3`: 거리, 경사, 기상, 경사·기상 상호작용을 반영한 비용모형
- `S0-M3`: 현재 정류장/출입구/D 세트를 사용한 정책평가 기준선

모든 시나리오(`S1`, `S3`, `S4`)는 `S0-M3`에서 고정한 분석 hex, 정규화 파라미터, 취약 threshold를 재사용한다. 시나리오별로 Min-Max 정규화를 다시 하면 비교가 깨지므로 금지한다.

## 프로젝트 구조

자세한 구조도는 `docs/project_structure.md`를 본다.

## 시작 가이드

처음 보는 사람은 다음 순서로 본다.

1. `docs/setup/python_environment.md` — Python 환경 세팅 (uv + `.venv`)
2. `docs/setup/data_acquisition.md` — 원자료 취득. **원자료 없이 확인할 수 있는 범위**를 먼저 정리해 둔다
3. `docs/분석_진행_정리.md` — 본문 보고서 v2.0 (방법론·결과·해석)
4. `docs/methods/cost_function_parameters.md` — M0~M3 비용함수와 계수의 해석 범위
5. `docs/qgis/00_workflow_index.md` — QGIS 수동 작업 절차

## 데이터와 라이선스

이 저장소는 **코드와 최종 결과 테이블만** 포함한다. 원자료 약 90GB는 용량과
재배포 조건 때문에 포함하지 않는다.

- 코드 라이선스: `LICENSE` (MIT)
- 데이터 출처 표시 의무: `docs/DATA_LICENSES.md` — OpenStreetMap(ODbL), 서울 열린데이터광장,
  Copernicus GLO-30 등의 표시 의무가 있으니 재사용 전 반드시 확인한다
- 생활이동 OD는 서울시 빅데이터캠퍼스 재배포 제한 자료라 원본·파생물 모두 제외했다.
  메인 수요지수에 포함되지 않은 보조 변수이므로 핵심 결과 재현에는 영향이 없다

## 현재 진행 상태

2026-06-11 재확인 기준으로 테스트와 데이터 계약 검증은 통과했다.

```text
pytest: 86 passed
validate-data: outputs/reports/data_validation.json 생성, 등록 데이터셋 ok
validate-vulnerability-final: outputs/reports/hex_vulnerability_final_audit.json (pass)
```

## 2026-05-31 v2.2 실행 상태 요약

- final 기준 분석 가능 hex 4,383개, M3 취약 877개, hidden vulnerable **632개** (threshold 0.0288, 영향 등록인구 약 166만 명).
- 정규화 4종(minmax/winsorize/log1p/rank) 공통으로 잡히는 **robust-core hidden 429개**와 정규화 민감 후보 624개를 분리했다 (`outputs/reports/v2_2_execution/`). 보고서에서 632를 단독 확정값처럼 쓰지 않는다.
- M0-M3 Spearman 0.9947: 순위 재정렬 효과는 작고, 절대 부담 증가(평균 +15.4%, 고령가중 +15.8%, 400m crossing 167개)로 해석한다.
- S1/S3/S4 counterfactual runner 산출 완료 (`outputs/reports/scenario_counterfactual/`, FrozenBaseline + Dijkstra 재탐색 + manifest). claim label: S1/S4 `upper_bound`, S3 `counterfactual_effect`(hidden 해소 0).

## 2026-06-11 M4-senior·민감도 실행 상태

- **M4-senior 고령자 보행 임피던스** 구현 완료 (`scripts/build_m4_senior_runner.py`, `outputs/reports/m4_senior/`, `qgis/m4_senior_access_runner.gpkg`). 속도 4프로필 × 기상 3프로필 × 계단 3정책 = 9개 변형 Dijkstra 재탐색.
  - 임피던스 자체는 M3 순위를 거의 안 바꿈(Spearman 0.996) — "고령자 임피던스가 새 취약지를 드러냈다"고 쓰지 않는다.
  - 방어 가능한 발견: 노출축을 고령인구로 바꾸면 취약 후보 약 1/3 교체(Jaccard 0.667), **계단 차단 시 도달 불가 hex 27개**, 최단경로 계단 의존 hex 92개, robust senior core 780개(그중 hidden 543개), snow 프로필에서 취약 877→1,143.
- **민감도 E1/E3/E6** 완료 (`outputs/reports/e_sensitivity/`): cap·기상계수는 hidden 632 교체율 ≤0.16%로 robust, k근접 D(k=2/3)는 교체율 12.3%/17.7%로 정규화 다음으로 민감한 레버.
- 미완: T1 취약 유형 4분류, E2 해상도·E4 수요가중 민감도, TAAS 외부 검증(데이터 미확보).

## 2026-05-13 추가 진행 상태

- 전국 행정동 경계 `qgis/BND_ADM_DONG_PG/BND_ADM_DONG_PG.shp`에서 서울만 추출해 `qgis/wrk_admin_dong_seoul_5179.gpkg`를 만들었다.
- 등록인구 CSV와 행정동 경계를 조인해 `qgis/wrk_registered_population_admin_5179.gpkg`를 만들었다. 입력 등록인구 9,579,177명과 65세 이상 1,912,751명은 조인 후에도 보존된다.
- 동대문구 `용두동`, `신설동`은 현재 행정동 경계의 `용신동` polygon에 합산한다. `가양제1동`처럼 `제`가 붙은 표기는 경계명과 맞게 자동 보정한다.
- H3 final demand와 final vulnerability 산출물을 생성했다: `qgis/out_hex_demand_features_final_h3res9.gpkg`, `qgis/out_hex_vulnerability_final.gpkg`.
- 등록인구 H3 배분은 분석 마스크 안에서 행정동별 총량이 보존되도록 재정규화한다.

## 2026-05-14 OD 보조 분석 진행 상태

- 생활이동 OD 원본 `data/life_mobility_admin_2025_summary.csv`는 약 89GB라서 전체 eager read를 금지하고 chunk 집계 하네스로 처리한다.
- `profile-life-mobility-od`, `build-life-mobility-od-aux`, `build-hex-mobility-aux` CLI를 추가했다.
- OD는 final demand에 자동 혼합하지 않고, 행정동 이동압력과 H3 `mobility_` 보조 레이어로 분리한다.
- 샘플 50만 행 기준 산출물을 생성했다: `qgis/out_life_mobility_admin_aux_sample_5179.gpkg`, `qgis/out_hex_mobility_aux_sample_h3res9.gpkg`.
- 전체 OD를 돌릴 때는 `build-life-mobility-od-aux`에서 `--max-rows`를 빼면 된다. 다만 오래 걸릴 수 있으므로 별도 긴 실행으로 처리하는 것을 권장한다.

| 영역 | 상태 | 현재 산출물 |
|---|---|---|
| 원천 데이터/검증 | 완료 | `data/*.csv`, `outputs/reports/data_validation.json` |
| 분석영역 마스크 | 완료, CRS 메타데이터 재저장 권장 | `qgis/out_analysis_mask_5179_fixed.gpkg` |
| H3 분석 hex | 완료 | `qgis/out_analysis_hex_h3res9.gpkg` |
| 버스/지하철 D 후보 | 완료 | `qgis/out_transit_d_candidates.gpkg` |
| edge 비용 M0-M3 | 완료 | `data/interim/walking_edge_costs.parquet` |
| 250m 생활인구 공간 조인 | 완료, QA 필요 | `qgis/out_livingpop_250m_join_5179.gpkg` |
| 등록인구 정규화 | 완료, 공간분배 전 | `data/interim/registered_population_admin_2025q4.parquet` |
| 등록인구 H3 분배 구조 | 구현 완료, 입력 대기 | `build-hex-demand-final` |
| H3 수요 피처 초안 | 완료, preliminary | `qgis/out_hex_demand_features_prelim_h3res9.gpkg` |
| 접근비용 M0-M3 초안 | 완료, preliminary | `qgis/out_hex_accessibility_prelim_M0_M3.gpkg` |
| 취약도/hidden vulnerability 초안 | 완료, preliminary | `qgis/out_hex_vulnerability_prelim.gpkg` |
| O/D 스냅과 Dijkstra | 완료, preliminary | `data/derived/hex_accessibility_prelim_M0_M3.parquet` |
| 취약도/hidden vulnerability final | 완료, audit pass | `qgis/out_hex_vulnerability_final.gpkg`, hidden 632 (robust-core 429) |
| 정책 시나리오 | runner 산출 완료 (효과 claim은 label 제한) | `outputs/reports/scenario_counterfactual/`, `qgis/S1·S3·S4_*_runner.gpkg` |

## H3 수요 피처 초안

생활인구 250m 격자와 POI를 H3 res9로 재집계한 초안 산출물을 만들었다. 아직 행정동 등록인구/고령인구 dasymetric 분배는 붙지 않았으므로 최종 `demand_index`가 아니라 `prelim`으로 구분한다.

```text
qgis/out_hex_demand_features_prelim_h3res9.gpkg
data/derived/hex_demand_features_prelim_h3res9.parquet
outputs/reports/hex_demand_features_prelim_qa.json
```

QA 요약:

```text
hex_count: 4,551
nonzero_living_hex_count: 4,548
nonzero_poi_hex_count: 4,285
poi_total_sum: 522,361
coverage_ratio_mean: 0.9937
status: preliminary, living population + POI only
```

## 접근비용·취약도 초안

H3 centroid를 보행망 node에 스냅하고, 버스/지하철 D 후보를 multi-source Dijkstra 목적지로 사용해 M0-M3 접근비용 초안을 만들었다.

```text
qgis/out_hex_accessibility_prelim_M0_M3.gpkg
data/derived/hex_accessibility_prelim_M0_M3.parquet
outputs/reports/hex_accessibility_prelim_qa.json
qgis/out_hex_vulnerability_prelim.gpkg
data/derived/hex_vulnerability_prelim.parquet
outputs/reports/hex_vulnerability_prelim_qa.json
```

QA 요약:

```text
origin snap valid: 4,384 / 4,551
D snap valid: 10,887 / 10,967
M0 reachable: 4,383
M3 mean cost: 212.28m distance-equivalent
prelim vulnerable hex: 877
prelim hidden vulnerable hex: 732  (등록인구 dasymetric 분배 전 수치; final은 632)
```

주의: 접근비용과 취약도는 아직 `prelim`이다. 수요지수에 행정동 등록인구/고령인구 분배가 빠져 있으므로 보고서의 최종 수치로 쓰기 전 보강이 필요하다.

## 등록인구 정규화

서울시 2025년 4/4분기 등록인구 원본 XLSX를 확보해 행정동 단위 정규화 테이블로 변환했다. 원본의 `2-1. 세대 및 인구상세` 시트에서 총등록인구와 65세 이상 총인구를 추출한다.

```text
data/raw/서울시등록인구_2025_4분기.xlsx
data/interim/registered_population_admin_2025q4.parquet
data/interim/registered_population_admin_2025q4.csv
outputs/reports/registered_population_admin_qa.json
```

QA 요약:

```text
admin dong records: 428
districts: 25
registered population total: 9,579,177
registered senior population total: 1,912,751
duplicated admin name: 신사동(관악구/강남구)
```

다음 단계는 행정동 경계 또는 `구+행정동명`을 안정적으로 붙일 수 있는 공간 기준을 확보해 H3로 면적가중 분배하는 것이다. QGIS 확인은 지금 당장 필수는 아니며, `qgis/wrk_registered_population_admin_5179.gpkg`처럼 행정동 polygon에 `registered_population`, `registered_senior_population`이 붙은 레이어를 준비한 뒤 final 산출물을 만들고 확인하면 된다.

```text
configs/                 경로, 데이터 소스, 모형 파라미터
src/sl_accessibility/    Python 하네스
scripts/                 실행용 wrapper
tests/                   단위 테스트
docs/qgis/               QGIS 수동 작업 매뉴얼
docs/methods/            방법론과 비용함수 해석
docs/setup/              Python 환경 설정
skills/                  repo-local Codex 스킬
data/                    기존 원본 데이터, 직접 수정 금지
data/interim/            중간 산출물
data/processed/          정제 산출물
outputs/                 보고서, 표, 지도 산출물
qgis/                    QGIS 프로젝트, export, QA 레이어
```

## 대용량 데이터 안전 규칙

다음 파일은 절대 eager read 하지 않는다.

- `data/life_mobility_admin_2025_summary.csv`
- `data/bus_stop_ridership_2025_with_geom.csv`
- 전체 `data/250_LOCAL_RESD_202511/*.csv` glob

대신 lazy scan, column projection, 샘플링, chunk 처리, Parquet 변환을 사용한다. 파일 경로의 최종 기준은 `data_catalog.csv`가 아니라 `configs/data_sources.yaml`이다.

## 빠른 실행

현재 PC에서는 `python.exe`가 Windows Store shim으로 잡히므로 `uv`와 `.venv`를 사용한다.

```powershell
$env:UV_CACHE_DIR='.uv-cache2'
uv venv --python 3.14
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m sl_accessibility.cli validate-data
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.venv\Scripts\python.exe -m sl_accessibility.cli extract-registered-population
# 행정동 등록인구 polygon 준비 후:
.venv\Scripts\python.exe -m sl_accessibility.cli build-hex-demand-final
.venv\Scripts\python.exe -m sl_accessibility.cli build-vulnerability-final
```

자세한 환경 설명은 `docs/setup/python_environment.md`에 있다.

## QGIS 작업

QGIS 수동 작업은 `docs/qgis/`에 정리되어 있다. 시작 파일은 다음이다.

```text
docs/qgis/00_workflow_index.md
```

모든 QGIS 분석 레이어는 `EPSG:5179`를 사용하고, 파생 레이어는 가능하면 GeoPackage로 저장한다. 레이어 이름은 `raw_`, `wrk_`, `qa_`, `out_`, `map_` 접두어를 따른다.

## 비용함수 계수

현재 비용함수 계수는 최종 보정값이 아니라 시나리오 기본값이다. 결과를 해석하거나 보고서에 쓸 때는 반드시 다음 문서를 먼저 확인한다.

```text
docs/methods/cost_function_parameters.md
```

## 구현 중 수정 반영 사항

잘못 가정했던 부분과 수정 내역은 다음 문서에 정리했다.

```text
docs/implementation_corrections.md
```
