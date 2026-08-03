# 원자료 취득 가이드

이 저장소는 코드와 **최종 결과 테이블**만 포함한다. 원자료(약 90GB)는 용량과
재배포 조건 때문에 포함하지 않으므로, 파이프라인을 처음부터 다시 돌리려면
아래 자료를 직접 취득해야 한다.

라이선스와 출처 표시 의무는 [docs/DATA_LICENSES.md](../DATA_LICENSES.md)를 본다.

## 무엇이 없어도 되는가

먼저 확인할 것: **핵심 결과를 확인하는 데는 원자료가 필요 없다.**

| 하려는 일 | 원자료 필요 | 방법 |
|---|---|---|
| 결과 수치 확인 (4,383 / 877 / 632 / 429) | 불필요 | `outputs/reports/v2_2_execution/v2_2_execution_summary.md` |
| 결과 지도 보기 | 불필요 | `outputs/qgis_midterm_maps/*.png` |
| 격자 단위 결과 재분석 | 불필요 | `data/derived/*.parquet` 3종 (아래) |
| 그림 재생성 | 불필요 | `scripts/build_midterm_visuals.py` |
| 비용모형·수요지수부터 재계산 | **필요** | 아래 표대로 취득 |
| 테스트 실행 | 불필요 | `pytest -q` (fixture 기반, 86 passed) |

저장소에 포함된 결과 테이블:

```text
data/derived/hex_vulnerability_final.parquet          # 4,383 hex 취약도 최종
data/derived/hex_demand_features_final_h3res9.parquet # 수요 피처 최종
data/derived/hex_accessibility_prelim_M0_M3.parquet   # M0~M3 접근비용
```

> `hex_accessibility_prelim_M0_M3.parquet` 는 이름에 `prelim` 이 붙어 있지만
> `build-vulnerability-final` 이 실제로 읽는 입력이다. 이름만 구버전이다.

## 취득해야 할 원자료

`configs/data_sources.yaml` 의 각 키에 대응한다.

| config 키 | 자료 | 제공처 | 원본 파일명 (data_catalog.csv 기준) | 비고 |
|---|---|---|---|---|
| `walking_edges` / `walking_nodes` | 보행 도로망 + 고도·경사 | OpenStreetMap (OSMnx 추출) + Copernicus GLO-30 | `seoul_south_korea_copernicus_glo30_node_elevations.csv` (노드 165,300) | 아래 "보행망 재생성" 참조 |
| `bus_ridership` | 버스 정류장별 시간대별 승하차 | 서울 열린데이터광장 | `2025년_버스노선별_정류장별_시간대별_승하차_인원_정보(01~12월)` 12개 | cp949. 좌표 없음 → 정류장 좌표와 병합 필요 |
| `subway_ridership` | 지하철 역별 시간대별 승하차 | 서울 열린데이터광장 | `서울시_지하철_호선별_역별_시간대별_승하차_인원_정보` 12개 | cp949. 좌표 없음 → 역 좌표와 병합 필요 |
| `asos_weather` | 종관기상관측 시간자료 | 기상청 기상자료개방포털 | `OBS_ASOS_TIM_*.csv` | cp949. 서울 관측소, 강수·적설 |
| `local_resident_250m` | 250m 격자 생활인구 | 서울 열린데이터광장 | `250_LOCAL_RESD_*` | cp949. 격자 메타데이터 별도 필요 |
| `registered_population` | 등록인구 (연령별·동별) | 서울 열린데이터광장 | `서울시등록인구_2025_4분기.xlsx` | 시트 `2-1. 세대 및 인구상세`, 65세 이상 총인구 |
| `commercial_poi` | 상가(상권)정보 서울 | 소상공인시장진흥공단 | `소상공인시장진흥공단_상가(상권)정보_서울_202512.csv` | utf-8-sig, 534,978행 |
| `medical_poi` | 병의원 위치 | 서울 열린데이터광장 | `서울시 병의원 위치 정보.csv` | cp949, 22,239행 |
| `senior_welfare_poi` | 노인의료복지시설 | 서울 열린데이터광장 | `서울시 노인의료복지시설현황.xlsx` | 2024-12-31 기준 |
| `life_mobility_admin` | 생활이동 행정동 OD | **서울시 빅데이터캠퍼스** | `생활이동_행정동_202501` (288 파일) | **재배포 제한.** 아래 참조 |

행정동 경계와 토지피복은 별도로 받는다.

| 자료 | 제공처 | 용도 |
|---|---|---|
| 전국 행정동 경계 `BND_ADM_DONG_PG.shp` | 통계청 SGIS | 등록인구 → H3 배분 |
| 토지피복도 | 환경공간정보서비스(EGIS) | 분석영역 마스크 |

## 파일명 정합 문제

`configs/data_sources.yaml` 의 경로는 **정제 후 이름**이고,
`data/data_catalog.csv` 는 **다운로드 직후 원본 이름**이다. 둘은 1:1로 대응하지 않는다.

- `data_sources.yaml` 은 `data/250_LOCAL_RESD_202511/*.csv` 를 글롭하지만
  `data_catalog.csv` 에는 `250_LOCAL_RESD_20260425` 가 기록되어 있다.
  카탈로그의 `use_status` 가 `제외`인 이유는 **2026-04 스냅샷이 2025년 기준 분석과 시점이 맞지 않아서**다.
  현재 결과는 `202511` 스냅샷으로 산출되었다.
- `*_with_geom`, `*_clean`, `*_with_coords` 접미사가 붙은 파일은 좌표 병합·정제를 거친 산출물이다.
  원본을 받은 뒤 좌표 조인과 컬럼 정규화를 직접 수행해야 한다.

> 이 정제 단계를 수행하는 코드는 현재 저장소에 포함되어 있지 않다(탐색적 노트북에서 수행됨).
> 따라서 **"clone 후 원자료만 받으면 바로 전 과정이 돌아간다"고 말할 수 없다.**
> 재현 가능한 범위는 정제된 입력이 갖춰진 시점부터다.

## 보행망 재생성

`walking_network_*` 두 파일은 Google Elevation API 파생물이라 재배포할 수 없다.
직접 만들려면:

1. OSMnx로 서울 보행 네트워크(`network_type="walk"`)를 추출한다.
2. 노드에 Copernicus GLO-30 고도를 조인한다 (`elevation_copernicus` 자료).
3. edge별 경사를 계산한다. 경사 30~100% 구간은 **삭제하지 않고 30%로 상한 처리**한다.
   고도 결측 900개, 경사 100% 초과 30개는 제외한다 (총 467,556 → 466,626).

경사·기상 계수는 `configs/model_params.yaml` 에 있다. 이 값은 실측 보정값이 아니라
시나리오 기본값이다 — [docs/methods/cost_function_parameters.md](../methods/cost_function_parameters.md) 참조.

## 생활이동 OD (재배포 제한)

`data/life_mobility_admin_2025_summary.csv` (약 85GB)는 서울시 빅데이터캠퍼스 제공
자료로 재배포가 제한된다. 파생 결과물도 반출 심의 대상이므로 이 저장소에는
원본도 파생물도 포함하지 않는다.

이 자료는 **메인 수요지수에 포함되지 않은 보조 변수**다. 따라서 없어도
핵심 결과(4,383 / 877 / 632 / 429)는 그대로 재현된다.

취득 후 사용할 때는 절대 eager read 하지 말고 chunk 집계 CLI를 쓴다.

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m sl_accessibility.cli profile-life-mobility-od
.venv\Scripts\python.exe -m sl_accessibility.cli build-life-mobility-od-aux --max-rows 500000
```

`--max-rows` 를 빼면 전체를 처리하지만 매우 오래 걸린다.

## 취득 후 실행 순서

```powershell
$env:UV_CACHE_DIR='.uv-cache2'
uv venv --python 3.14
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
$env:PYTHONPATH='src'

.venv\Scripts\python.exe -m sl_accessibility.cli validate-data
.venv\Scripts\python.exe -m sl_accessibility.cli extract-registered-population
# 행정동 등록인구 polygon 준비 후:
.venv\Scripts\python.exe -m sl_accessibility.cli build-hex-demand-final
.venv\Scripts\python.exe -m sl_accessibility.cli build-vulnerability-final
.venv\Scripts\python.exe -m sl_accessibility.cli validate-vulnerability-final
```

QGIS 수동 작업은 [docs/qgis/00_workflow_index.md](../qgis/00_workflow_index.md)를 따른다.
