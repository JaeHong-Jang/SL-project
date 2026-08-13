"""슬라이드 5 좌측 패널용 고도 래스터 생성.

보행 네트워크 노드의 Copernicus GLO-30 고도값을 규칙 격자로 평균 집계하고,
빈 셀은 이웃 평균으로 채운 뒤 서울 경계로 자른다.
출력은 QGIS가 바로 읽는 ESRI ASCII grid.

주의: 이것은 원본 DEM이 아니라 보행망 노드 고도의 격자 요약이다.
"""

import warnings

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely

CELL = 200.0  # m
NODATA = -9999.0
NODES = "data/walking_network_nodes_with_elevation.csv"
BOUNDARY = "qgis/wrk_district_seoul_5179.gpkg"
OUT = "qgis/wrk_elevation_copernicus_200m_5179.asc"


def main():
    df = pd.read_csv(NODES, usecols=["x", "y", "elevation_copernicus_m"]).dropna()
    print(f"노드 {len(df):,}개, 고도 {df.elevation_copernicus_m.min():.1f}~{df.elevation_copernicus_m.max():.1f}m")

    seoul = gpd.read_file(BOUNDARY).union_all()
    minx, miny, maxx, maxy = seoul.bounds
    ncols = int(np.ceil((maxx - minx) / CELL))
    nrows = int(np.ceil((maxy - miny) / CELL))

    col = ((df.x - minx) // CELL).astype(int)
    row = ((df.y - miny) // CELL).astype(int)
    keep = (col >= 0) & (col < ncols) & (row >= 0) & (row < nrows)
    idx = (row[keep] * ncols + col[keep]).to_numpy()

    total = np.bincount(idx, weights=df.elevation_copernicus_m[keep].to_numpy(), minlength=nrows * ncols)
    count = np.bincount(idx, minlength=nrows * ncols)
    grid = np.where(count > 0, total / np.maximum(count, 1), np.nan).reshape(nrows, ncols)
    print(f"격자 {nrows}x{ncols}, 노드 채워진 셀 {np.isfinite(grid).sum():,} ({np.isfinite(grid).mean():.1%})")

    # 빈 셀을 이웃 평균으로 반복 확산
    for _ in range(40):
        holes = ~np.isfinite(grid)
        if not holes.any():
            break
        padded = np.pad(grid, 1, constant_values=np.nan)
        stack = np.stack([padded[i:i + nrows, j:j + ncols]
                          for i in range(3) for j in range(3)])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # 이웃이 전부 빈 셀인 경우
            neigh = np.nanmean(stack, axis=0)
        grid = np.where(holes & np.isfinite(neigh), neigh, grid)
    print(f"확산 후 채워진 셀 {np.isfinite(grid).mean():.1%}")

    # 서울 경계 밖은 NoData
    cx = minx + (np.arange(ncols) + 0.5) * CELL
    cy = miny + (np.arange(nrows) + 0.5) * CELL
    gx, gy = np.meshgrid(cx, cy)
    inside = shapely.contains_xy(seoul, gx.ravel(), gy.ravel()).reshape(nrows, ncols)
    grid = np.where(inside & np.isfinite(grid), grid, NODATA)
    print(f"서울 내부 유효 셀 {(grid != NODATA).sum():,}")

    header = (f"ncols {ncols}\nnrows {nrows}\n"
              f"xllcorner {minx}\nyllcorner {miny}\n"
              f"cellsize {CELL}\nNODATA_value {NODATA:.0f}\n")
    with open(OUT, "w") as f:
        f.write(header)
        for r in range(nrows - 1, -1, -1):  # ASCII grid는 북쪽 행부터
            f.write(" ".join(f"{v:.1f}" for v in grid[r]) + "\n")
    with open(OUT.replace(".asc", ".prj"), "w") as f:
        f.write(gpd.read_file(BOUNDARY).crs.to_wkt())

    valid = grid[grid != NODATA]
    print(f"저장 {OUT} | 고도 {valid.min():.0f}~{valid.max():.0f}m, 중앙값 {np.median(valid):.0f}m")


if __name__ == "__main__":
    main()
