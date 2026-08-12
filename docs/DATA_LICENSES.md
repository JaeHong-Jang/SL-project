# 데이터 출처와 라이선스

이 저장소는 아래 자료의 **파생물**(격자 집계 결과, 접근비용 테이블, 지도)을 포함한다.
원자료 자체는 용량과 재배포 조건 때문에 저장소에 포함하지 않는다. 취득 방법은
[docs/setup/data_acquisition.md](setup/data_acquisition.md)를 본다.

## 출처 표시 (필수)

### OpenStreetMap — 보행 도로망

- 자료: OSMnx로 추출한 서울 보행 네트워크 (edge 466,626개)
- 라이선스: **ODbL 1.0** (Open Database License)
- 표시 의무: `© OpenStreetMap contributors`
- **Produced Work 고지:** 이 저장소의 다음 산출물은 OSM 데이터를 이용해 생성된 2차 저작물이다.
  - `data/derived/hex_accessibility_prelim_M0_M3.parquet` — `access_cost_m0` ~ `access_cost_m3`
  - `data/derived/hex_vulnerability_final.parquet` — `origin_node_id`(OSM node ID), 모든 비용 컬럼
  - `outputs/reports/**` 의 비용·경로 기반 지표 전체
  - `outputs/qgis_midterm_layers/**`, `outputs/qgis_midterm_maps/**` 의 지도

### 서울 열린데이터광장

- 자료: 250m 생활인구, 등록인구(연령별·동별), 버스/지하철 정류장별 승하차
- 조건: **출처 표시 필수**
- 표시: `출처: 서울 열린데이터광장 (data.seoul.go.kr)`
- 해당 파생물: `data/derived/hex_demand_features_final_h3res9.parquet` 의 `living_*`,
  `registered_population`, `registered_senior_population` 컬럼과 이를 이용한 모든 취약도 산출물

### Copernicus GLO-30 DEM — 고도

- 자료: `seoul_south_korea_copernicus_glo30_node_elevations.csv` (노드 165,300개)
- 표시: `© European Union, contains modified Copernicus DEM data`
- 용도: Google 고도의 교차검증(QA), 그리고 재배포가 필요한 공개 산출물(웹 프로토타입 등)의
  경사 재계산용 대체 소스
- **주의:** 현재 M0~M3 접근비용 산출물의 경사는 Copernicus가 아니라 Google Elevation
  기반(`walking_network_edges_with_slope_google.csv`, `elevation_source=google`)에서 계산되었다.

### 기상청 ASOS

- 자료: 종관기상관측 시간자료 (`OBS_ASOS_TIM_*.csv`)
- 출처: 기상청 기상자료개방포털 (data.kma.go.kr)
- 용도: 강수·적설 조건 → M2/M3 비용모형

### 소상공인시장진흥공단

- 자료: 상가(상권)정보 서울
- 출처 표시: `출처: 소상공인시장진흥공단`
- 용도: 시설밀도 수요 변수

## 재배포 제한 (저장소에 포함하지 않음)

### 서울시 빅데이터캠퍼스 — 생활이동 행정동 OD

- 파일: `data/life_mobility_admin_2025_summary.csv` (약 85GB)
- **재배포 제한.** 파생 결과물도 반출 심의 대상이다.
- 따라서 다음도 저장소에서 제외한다.
  - `data/derived/hex_mobility_aux*.parquet`
  - `outputs/reports/life_mobility_od_*.json`
  - `outputs/reports/hex_mobility_aux*_qa.json`
- 본 자료는 메인 수요지수에 포함되지 않은 **보조 변수**이므로, 제외해도
  핵심 결과(4,383 / 877 / 632 / 429)의 재현에는 영향이 없다.
- 이용을 원하면 서울시 빅데이터캠퍼스에서 직접 신청·취득해야 한다.

### Google Elevation API — 고도 (현행 비용모형의 경사 소스)

- 파일: `data/walking_network_nodes_with_elevation.csv`,
  `data/walking_network_edges_with_slope_google.csv`
- API 이용약관상 **재배포 제한**. 로컬에서 직접 재생성해야 한다.
- 현재 M0~M3 접근비용 산출물(`data/interim/walking_edge_costs.parquet` 및 이를 이용한
  발표 수치)의 경사는 이 Google 기반 파일에서 계산되었다. Copernicus GLO-30은
  교차검증용이며, 재배포가 필요한 공개 산출물은 Copernicus 기반으로 경사를
  재계산해 사용한다.

## 코드 라이선스

이 저장소의 **코드**(`src/`, `scripts/`, `tests/`)는 [LICENSE](../LICENSE)를 따른다.
데이터 파생물에 대한 위 출처 표시 의무는 코드 라이선스와 별개로 유지된다.
