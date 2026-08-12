"""단계 0 — 공개 안전 경사망 생성 + Copernicus 노이즈 진단.

docs/prototype_plan.md v2의 단계 0을 구현한다.

- 입력 엣지 파일에서 OSM 기원 열(u, v, key, length_m, geometry_wkt)만 읽는다.
- 노드의 elevation_copernicus_m만으로 방향·절대경사를 재계산한다.
- Google 고도·경사 열은 산출물에 복사하지 않는다(로컬 비교 보고서에만 사용).
- 엣지 길이 구간별 경사 분포로 GLO-30 해상도 노이즈를 진단한다.

산출물:
- data/processed/prototype/edges_base.parquet  (유효 엣지만, google 열 0건)
- data/processed/prototype/build_report.json   (QA·노이즈 진단·Google 대비 비교)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "prototype.yaml"

OSM_EDGE_COLS = ["u", "v", "key", "length_m", "geometry_wkt"]
# 로컬 비교 보고서에만 쓰고 산출물에는 절대 복사하지 않는다.
GOOGLE_COMPARE_COL = "grade_abs_percent"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def grade_stats(series: pd.Series) -> dict:
    s = series.dropna()
    if s.empty:
        return {}
    return {
        "count": int(s.size),
        "median": round(float(s.median()), 4),
        "mean": round(float(s.mean()), 4),
        "p90": round(float(s.quantile(0.90)), 4),
        "p99": round(float(s.quantile(0.99)), 4),
        "max": round(float(s.max()), 4),
    }


def main() -> None:
    cfg = load_config()
    out_dir = ROOT / cfg["paths"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    error_grade = float(cfg["slope"]["error_exclude_grade_abs_percent"])
    bucket_edges = list(cfg["noise_diagnostics"]["length_buckets"]) + [float("inf")]

    edges = pd.read_csv(
        ROOT / cfg["paths"]["edges_csv"],
        usecols=OSM_EDGE_COLS + [GOOGLE_COMPARE_COL],
        low_memory=False,
    )
    edges["edge_id"] = edges.index.astype("int64")
    nodes = pd.read_csv(
        ROOT / cfg["paths"]["nodes_csv"],
        usecols=["node_id", "elevation_copernicus_m"],
        low_memory=False,
    )
    elev = nodes.set_index("node_id")["elevation_copernicus_m"]

    input_rows = len(edges)
    edges["elev_u_cop"] = edges["u"].map(elev)
    edges["elev_v_cop"] = edges["v"].map(elev)

    missing_node_ref = edges["u"].isin(elev.index) & edges["v"].isin(elev.index)
    nonpositive_length = edges["length_m"] <= 0
    missing_elev = edges["elev_u_cop"].isna() | edges["elev_v_cop"].isna()

    edges["grade_percent_cop"] = (
        (edges["elev_v_cop"] - edges["elev_u_cop"]) / edges["length_m"] * 100.0
    )
    edges["grade_abs_percent_cop"] = edges["grade_percent_cop"].abs()
    over_error = edges["grade_abs_percent_cop"] > error_grade

    valid = missing_node_ref & ~nonpositive_length & ~missing_elev & ~over_error
    valid_edges = edges[valid].copy()

    # --- 노이즈 진단: 길이 구간별 경사 분포 (Copernicus vs Google) ---
    labels = [
        f"{lo:g}-{hi:g}m" if np.isfinite(hi) else f">={lo:g}m"
        for lo, hi in zip(bucket_edges[:-1], bucket_edges[1:])
    ]
    diag_pool = edges[missing_node_ref & ~nonpositive_length & ~missing_elev].copy()
    diag_pool["len_bucket"] = pd.cut(
        diag_pool["length_m"], bins=bucket_edges, labels=labels, right=False
    )
    bucket_report = []
    for b in labels:
        sub = diag_pool[diag_pool["len_bucket"] == b]
        bucket_report.append(
            {
                "bucket": b,
                "edge_count": int(len(sub)),
                "copernicus": grade_stats(sub["grade_abs_percent_cop"]),
                "google": grade_stats(sub[GOOGLE_COMPARE_COL]),
                "over_100pct_copernicus": int((sub["grade_abs_percent_cop"] > error_grade).sum()),
                "over_100pct_google": int((sub[GOOGLE_COMPARE_COL] > error_grade).sum()),
            }
        )

    # --- Google 대비 상관 (양쪽 모두 유효한 엣지) ---
    both = edges[valid & edges[GOOGLE_COMPARE_COL].notna() & (edges[GOOGLE_COMPARE_COL] <= error_grade)]
    corr_pearson = float(both["grade_abs_percent_cop"].corr(both[GOOGLE_COMPARE_COL]))
    # spearman = 순위 변환 후 pearson (scipy 의존 없이 계산)
    corr_spearman = float(
        both["grade_abs_percent_cop"].rank().corr(both[GOOGLE_COMPARE_COL].rank())
    )

    # --- 산출물: google 열 없이 저장 ---
    out_cols = [
        "edge_id", "u", "v", "key", "length_m",
        "grade_percent_cop", "grade_abs_percent_cop", "geometry_wkt",
    ]
    out = valid_edges[out_cols]
    assert not any("google" in c.lower() for c in out.columns), "google 열이 산출물에 포함됨"
    out_path = out_dir / "edges_base.parquet"
    out.to_parquet(out_path, index=False)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan": "docs/prototype_plan.md v2 단계 0",
        "sources": {
            "network": "OpenStreetMap (ODbL 1.0) — © OpenStreetMap contributors",
            "elevation": "Copernicus GLO-30 — © European Union, contains modified Copernicus DEM data",
            "google_columns_in_output": 0,
        },
        "input_rows": input_rows,
        "exclusions": {
            "missing_node_ref": int((~missing_node_ref).sum()),
            "nonpositive_length": int((nonpositive_length & missing_node_ref).sum()),
            "missing_copernicus_elevation": int(
                (missing_elev & missing_node_ref & ~nonpositive_length).sum()
            ),
            "grade_over_100pct": int(
                (over_error & missing_node_ref & ~nonpositive_length & ~missing_elev).sum()
            ),
        },
        "valid_rows": int(valid.sum()),
        "grade_overall": {
            "copernicus_valid": grade_stats(valid_edges["grade_abs_percent_cop"]),
            "google_reference": grade_stats(
                edges.loc[edges[GOOGLE_COMPARE_COL] <= error_grade, GOOGLE_COMPARE_COL]
            ),
        },
        "noise_diagnostics_by_length_bucket": bucket_report,
        "google_correlation_on_common_valid": {
            "n": int(len(both)),
            "pearson": round(corr_pearson, 4),
            "spearman": round(corr_spearman, 4),
        },
        "outputs": {"edges_base_parquet": str(out_path.relative_to(ROOT))},
    }
    report_path = out_dir / "build_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 행수 정합 검사
    total = report["valid_rows"] + sum(report["exclusions"].values())
    assert total == input_rows, f"행수 불일치: {total} != {input_rows}"
    print(json.dumps({k: report[k] for k in ["input_rows", "exclusions", "valid_rows"]}, ensure_ascii=False))
    print(f"OK -> {out_path}")
    print(f"OK -> {report_path}")


if __name__ == "__main__":
    main()
