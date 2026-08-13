"""슬라이드 5 (c) 패널용 보행망 구간 경사 선 레이어 생성.

M1 이후 분석에 사용한 walking_edge_costs.parquet의 grade_abs_percent를 그대로 쓴다.
시각화를 위해 경사를 다시 계산하지 않는다.
구간은 논문시각화 레퍼런스 4.3-C의 0-2 / 2-5 / 5-8 / 8-10 / 10% 초과.
"""

import geopandas as gpd
import pandas as pd
import shapely

EDGES = "data/interim/walking_edge_costs.parquet"
OUT = "qgis/wrk_walking_slope_classes_5179.gpkg"
LAYER = "wrk_walking_slope_classes_5179"
BINS = [0, 2, 5, 8, 10, float("inf")]
LABELS = ["0-2%", "2-5%", "5-8%", "8-10%", "10% 초과"]


def main():
    df = pd.read_parquet(EDGES, columns=["length_m", "grade_abs_percent",
                                         "slope_available", "geometry_wkt"])
    print(f"입력 구간 {len(df):,}개")

    df = df[df["slope_available"] & df["grade_abs_percent"].notna()]
    df["slope_class"] = pd.cut(df["grade_abs_percent"], bins=BINS,
                               labels=LABELS, right=False)
    df["class_order"] = df["slope_class"].cat.codes + 1

    gdf = gpd.GeoDataFrame(
        df[["grade_abs_percent", "slope_class", "class_order", "length_m"]].assign(
            slope_class=df["slope_class"].astype(str)),
        geometry=shapely.from_wkt(df["geometry_wkt"]),
        crs="EPSG:5179",
    )
    gdf.to_file(OUT, layer=LAYER, driver="GPKG")

    summary = gdf.groupby("slope_class", observed=True).agg(
        구간수=("length_m", "size"), 연장km=("length_m", lambda s: s.sum() / 1000))
    summary["연장비중"] = (summary["연장km"] / summary["연장km"].sum() * 100).round(1)
    print(summary.round(0).to_string())
    print(f"\n저장 {OUT} ({len(gdf):,} 구간)")


if __name__ == "__main__":
    main()
