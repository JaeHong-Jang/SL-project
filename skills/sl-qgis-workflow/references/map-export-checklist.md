# 지도 Export 체크리스트

## 레이아웃

- 제목에 장소, 주제, 기준시점, 시나리오명이 들어 있다.
- 범례 이름이 실제 레이어와 일치한다.
- 축척, 북쪽 화살표, CRS, 자료 출처가 들어 있다.
- 지도 안쪽 라벨이나 inset이 핵심 결과를 가리지 않는다.

## 지도 표현

- 비교 지도끼리 class break가 동일하다.
- 분석 제외/NoData가 낮은 접근성 영역과 구분된다.
- 색상은 흑백 출력에서도 어느 정도 구분된다.
- 행정경계는 보이지만 주제도를 압도하지 않는다.
- 정류장/출입구 점은 결과 격자를 가리지 않는다.

## Export

- 보고서용 지도는 PDF와 PNG를 모두 만든다.
- 발표용 지도는 PNG 고해상도로 export한다.
- 한국어 글자가 export 후 깨지지 않는지 확인한다.
- 최종 파일명은 그림 번호 또는 주제명과 맞춘다.

예시:

```text
qgis/exports/map_hidden_vulnerable_areas.png
qgis/exports/map_scenario_S1_S3_S4_comparison.pdf
```
