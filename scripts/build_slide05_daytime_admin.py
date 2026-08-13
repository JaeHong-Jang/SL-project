"""슬라이드 5 (b) 패널용 행정동 주간 생활인구 밀도 레이어 생성.

250m 생활인구 격자의 daytime_mean_population(09-17시 평균)을
면적 가중으로 행정동에 배분하고 밀도(명/km2)로 환산한다.
"""

import geopandas as gpd

GRID = "qgis/out_livingpop_250m_join_5179.gpkg"
ADMIN = "qgis/wrk_registered_population_admin_5179.gpkg"
OUT = "qgis/wrk_daytime_pop_admin_5179.gpkg"
LAYER = "wrk_daytime_pop_admin_5179"


def main():
    grid = gpd.read_file(GRID)[["daytime_mean_population", "geometry"]].dropna()
    admin = gpd.read_file(ADMIN)[["district_name", "admin_name", "geometry"]]
    print(f"격자 {len(grid):,}개, 행정동 {len(admin)}개")

    grid["cell_area"] = grid.geometry.area
    parts = gpd.overlay(grid, admin, how="intersection", keep_geom_type=True)
    parts["share"] = parts.geometry.area / parts["cell_area"]
    parts["daytime_pop"] = parts["daytime_mean_population"] * parts["share"]
    print(f"교차 조각 {len(parts):,}개, 배분 후 합계 보존율 "
          f"{parts['daytime_pop'].sum() / grid['daytime_mean_population'].sum():.1%}")

    agg = parts.groupby(["district_name", "admin_name"], as_index=False)["daytime_pop"].sum()
    out = admin.merge(agg, on=["district_name", "admin_name"], how="left")
    out["daytime_pop"] = out["daytime_pop"].fillna(0)
    out["area_km2"] = out.geometry.area / 1e6
    out["daytime_density"] = out["daytime_pop"] / out["area_km2"]
    out.to_file(OUT, layer=LAYER, driver="GPKG")

    q = out["daytime_density"].quantile([0, .2, .4, .6, .8, 1]).round(0)
    print("\n주간 생활인구 밀도(명/km2) 5분위:")
    print(q.to_string())
    print("\n최고 5개동:")
    print(out.nlargest(5, "daytime_density")[
        ["district_name", "admin_name", "daytime_density"]].round(0).to_string(index=False))
    print(f"\n저장 {OUT}")


if __name__ == "__main__":
    main()
