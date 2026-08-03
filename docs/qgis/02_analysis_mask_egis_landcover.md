# EGIS 토지피복도 기반 분석영역 마스크

## 목적

서울시 행정경계 안에는 북한산, 도봉산, 관악산, 하천, 대규모 공원 등 일상 대중교통 보행접근성 분석 대상이 아닌 영역이 포함된다. 이 문서는 시가지 중심의 분석영역 마스크를 만드는 절차를 정리한다.

## 입력

- EGIS 토지피복도 원본
- 서울시 경계 또는 연구대상 경계
- EGIS 토지피복도 코드표
- 필요 시 하천, 공원, 산림 보조 레이어

## 작업 절차

1. EGIS 토지피복도를 `raw_egis_landcover`로 불러온다.
2. 서울시 경계 레이어를 `raw_seoul_boundary`로 불러온다.
3. 두 레이어의 CRS를 확인하고, 필요하면 `EPSG:5179`로 변환한다.
4. `Processing Toolbox > Vector overlay > Clip`으로 토지피복도를 서울 경계로 자른다.
5. EGIS 코드표를 확인해 분석 포함 class를 선택한다.
   - 기본 포함 후보: 주거, 상업, 공업, 교통시설, 도시 기반시설
   - 기본 제외 후보: 산림, 수역, 농지, 나지, 등산/자연 중심 영역
6. 선택 결과를 `wrk_analysis_mask_classes.gpkg`로 저장한다.
7. `Processing Toolbox > Vector geometry > Dissolve`로 선택된 polygon을 dissolve한다.
8. `Processing Toolbox > Vector geometry > Fix geometries`로 geometry를 정리한다.
9. 최종 마스크를 `qgis/out_analysis_mask_5179.gpkg`로 저장한다.
10. 제외 영역은 회색 hatch로 표시한 검토용 지도를 export한다.

## 출력

```text
qgis/wrk_egis_landcover_5179.gpkg
qgis/wrk_analysis_mask_classes.gpkg
qgis/qa/qa_analysis_mask_geometry_check.gpkg
qgis/out_analysis_mask_5179.gpkg
qgis/exports/map_analysis_mask_review.png
```

## 합격 기준

- 최종 마스크가 `EPSG:5179`이다.
- 포함/제외 토지피복 class 코드가 문서 또는 레이어 metadata에 기록되어 있다.
- 산림, 하천, 산지 등 연구 범위 밖 영역이 취약지역 후보로 들어오지 않는다.
- geometry validity 오류가 없거나, 예외가 `qa_` 레이어에 기록되어 있다.
- dissolve 전후 면적 합계가 비정상적으로 달라지지 않는다.

## 자주 생기는 문제

- 토지피복 class 이름만 보고 코드표 확인 없이 선택하는 경우
- 하천/산림 일부가 시가지로 잘못 포함되는 경우
- dissolve 후 작은 섬 polygon이 숨어서 검토되지 않는 경우
- sliver 제거 과정에서 실제 시가지 좁은 영역까지 삭제하는 경우
