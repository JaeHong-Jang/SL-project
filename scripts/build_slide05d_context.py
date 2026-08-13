"""슬라이드 5 (d) 패널용 녹지·수계 맥락 레이어 생성.

논문 (d) Bus Lines의 `Green Area and Parks`, `Lake`에 대응하는 배경 면을
환경부 토지피복지도(서울 클립)에서 추출해 클래스별로 디졸브한다.
"""

import geopandas as gpd

SRC = "qgis/wrk_egis_landcover_seoul_clip_5179.gpkg"
OUT = "qgis/wrk_slide05d_context_5179.gpkg"

# 310 활엽수림 320 침엽수림 330 혼효림 410 자연초지 140 문화·체육·휴양지역
GREEN = ["310", "320", "330", "410", "140"]
# 710 내륙수 510 내륙습지(한강 둔치)
WATER = ["710", "510"]


CRS = "EPSG:5179"  # 원본 gpkg에 CRS 선언이 없으나 좌표는 5179


def dissolve(gdf, codes, name):
    sel = gdf[gdf["L2_CODE"].astype(str).isin(codes)]
    merged = gpd.GeoDataFrame(
        {"category": [name]}, geometry=[sel.geometry.union_all()], crs=CRS)
    print(f"{name}: {len(sel):,}개 → 디졸브 1개, 면적 {sel.geometry.area.sum()/1e6:.1f}km²")
    return merged


def main():
    lc = gpd.read_file(SRC)[["L2_CODE", "L2_NAME", "geometry"]]
    print(f"토지피복 {len(lc):,}개, CRS {lc.crs}")
    dissolve(lc, GREEN, "녹지·공원").to_file(OUT, layer="green", driver="GPKG")
    dissolve(lc, WATER, "수계").to_file(OUT, layer="water", driver="GPKG")
    print(f"저장 {OUT} (레이어: green, water)")


if __name__ == "__main__":
    main()
