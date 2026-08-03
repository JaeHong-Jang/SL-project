# QGIS 프로젝트 설정

## 목적

모든 수동 GIS 작업의 좌표계, 레이어 그룹, 저장 위치를 통일한다. 이 단계를 잘못 잡으면 거리, 면적, buffer, overlay 결과가 전부 흔들린다.

## 입력

- 서울시 행정경계 또는 연구대상 경계
- EGIS 토지피복도
- 250m 생활인구 격자 메타데이터
- 보행 네트워크 edge/node
- 정류장, 지하철역, 출입구, 엘리베이터 등 대중교통 D 후보
- Python에서 생성한 접근성/취약성 결과

## 작업 절차

1. QGIS 새 프로젝트를 만든다.
2. `Project > Properties > CRS`에서 프로젝트 CRS를 `EPSG:5179`로 설정한다.
3. 레이어 패널에 다음 그룹을 만든다.
   - `00_raw`
   - `01_reference`
   - `02_working`
   - `03_QA`
   - `04_outputs`
   - `05_maps`
4. 원본 파일은 `00_raw`에 불러오고 직접 편집하지 않는다.
5. `EPSG:5179`가 아닌 레이어는 `Processing Toolbox > Vector general > Reproject layer`로 변환한다.
6. 변환 결과는 `qgis/` 아래 GeoPackage로 저장하고, 이름은 `wrk_[주제]_5179`로 둔다.
7. 프로젝트 파일은 `qgis/projects/seoul_slope_weather_accessibility.qgz`로 저장한다.
8. 주요 레이어에는 source, CRS, 작성일, 처리 내용을 layer metadata 또는 별도 notes에 남긴다.

## 출력

```text
qgis/projects/seoul_slope_weather_accessibility.qgz
qgis/wrk_*_5179.gpkg
```

## 합격 기준

- 프로젝트 CRS가 `EPSG:5179`이다.
- 거리/면적 계산에 쓰는 레이어가 모두 `EPSG:5179`이다.
- 원본 레이어가 수정되지 않았다.
- 임시 레이어가 후속 분석의 입력으로 남아 있지 않다.
- 레이어 이름이 `raw_`, `wrk_`, `qa_`, `out_`, `map_` 규칙을 따른다.

## 자주 생기는 문제

- QGIS 화면에서는 맞아 보이지만 실제 CRS가 섞여 있는 경우
- 임시 레이어로 처리한 뒤 저장하지 않아 다음 세션에서 사라지는 경우
- 원본 shp/csv를 직접 편집하는 경우
- `layer`, `clip result`, `joined layer`처럼 의미 없는 이름으로 저장하는 경우
