"""단계 0 — 공개 안전 경사망 생성 + Copernicus 노이즈 진단·완화.

docs/prototype_plan.md v2의 단계 0을 구현한다.

- 입력 엣지 파일에서 OSM 기원 열(u, v, key, length_m, geometry_wkt)만 읽는다.
- 노드의 elevation_copernicus_m만으로 방향·절대경사를 재계산한다.
- Google 고도·경사 열은 산출물에 복사하지 않는다(로컬 비교 보고서에만 사용).
- GLO-30 30m 격자 양자화 노이즈를 길이 구간별로 진단하고,
  네트워크 이웃 고도 스무딩(IDW)으로 완화한다(게이트 결정: 투트랙 분리, 웹용 데이터 전용).

산출물:
- data/processed/prototype/edges_base.parquet  (유효 엣지만, 스무딩 적용 경사, google 열 0건)
- data/processed/prototype/build_report.json   (원값/완화 후 QA·노이즈 진단·Google 대비 비교)
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


def compute_grades(edges: pd.DataFrame, elev: pd.Series) -> pd.DataFrame:
    """엣지 양끝 고도차로 방향·절대경사(%)를 계산해 새 프레임으로 반환한다."""
    out = edges[["edge_id", "u", "v", "length_m"]].copy()
    out["elev_u"] = out["u"].map(elev)
    out["elev_v"] = out["v"].map(elev)
    out["grade_percent"] = (out["elev_v"] - out["elev_u"]) / out["length_m"] * 100.0
    out["grade_abs_percent"] = out["grade_percent"].abs()
    return out


def smooth_elevations(
    edges: pd.DataFrame, elev: pd.Series, *, max_len: float, alpha: float, passes: int
) -> pd.Series:
    """네트워크 이웃 IDW로 노드 고도를 스무딩한다 (짧은 링크의 양자화 스텝 억제)."""
    adj = pd.concat(
        [
            edges[["u", "v", "length_m"]].rename(columns={"u": "a", "v": "b"}),
            edges[["v", "u", "length_m"]].rename(columns={"v": "a", "u": "b"}),
        ],
        ignore_index=True,
    )
    adj = adj[(adj["length_m"] > 0) & (adj["length_m"] <= max_len)]
    adj["w"] = 1.0 / adj["length_m"].clip(lower=5.0)

    cur = elev.copy()
    for _ in range(passes):
        e = adj["b"].map(cur)
        ok = e.notna()
        we = (adj.loc[ok, "w"] * e[ok]).groupby(adj.loc[ok, "a"]).sum()
        ws = adj.loc[ok, "w"].groupby(adj.loc[ok, "a"]).sum()
        nbr_mean = we / ws
        nxt = cur.copy()
        common = nxt.index.intersection(nbr_mean.index)
        base = nxt.loc[common]
        blended = alpha * base + (1.0 - alpha) * nbr_mean.loc[common]
        # 원 고도가 결측인 노드는 스무딩으로 채우지 않는다(결측 정책 보존).
        nxt.loc[common] = blended.where(base.notna(), np.nan)
        cur = nxt
    return cur


def bucket_diagnostics(
    g: pd.DataFrame, google: pd.Series, bucket_edges: list, error_grade: float
) -> list[dict]:
    labels = [
        f"{lo:g}-{hi:g}m" if np.isfinite(hi) else f">={lo:g}m"
        for lo, hi in zip(bucket_edges[:-1], bucket_edges[1:])
    ]
    pool = g[g["grade_abs_percent"].notna()].copy()
    pool["len_bucket"] = pd.cut(pool["length_m"], bins=bucket_edges, labels=labels, right=False)
    pool["google"] = google.reindex(pool.index)
    rows = []
    for b in labels:
        sub = pool[pool["len_bucket"] == b]
        gg = sub[sub["google"].notna() & (sub["google"] <= error_grade)]
        rows.append(
            {
                "bucket": b,
                "edge_count": int(len(sub)),
                "copernicus": grade_stats(sub["grade_abs_percent"]),
                "google": grade_stats(sub["google"]),
                "over_100pct_copernicus": int((sub["grade_abs_percent"] > error_grade).sum()),
                "pearson_vs_google": round(float(gg["grade_abs_percent"].corr(gg["google"])), 4)
                if len(gg) > 2
                else None,
                "spearman_vs_google": round(
                    float(gg["grade_abs_percent"].rank().corr(gg["google"].rank())), 4
                )
                if len(gg) > 2
                else None,
            }
        )
    return rows


def main() -> None:
    cfg = load_config()
    out_dir = ROOT / cfg["paths"]["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    error_grade = float(cfg["slope"]["error_exclude_grade_abs_percent"])
    bucket_edges = list(cfg["noise_diagnostics"]["length_buckets"]) + [float("inf")]
    mit = cfg["noise_mitigation"]

    edges = pd.read_csv(
        ROOT / cfg["paths"]["edges_csv"],
        usecols=OSM_EDGE_COLS + [GOOGLE_COMPARE_COL],
        low_memory=False,
    )
    edges["edge_id"] = edges.index.astype("int64")
    google_ref = edges[GOOGLE_COMPARE_COL]
    nodes = pd.read_csv(
        ROOT / cfg["paths"]["nodes_csv"],
        usecols=["node_id", "elevation_copernicus_m"],
        low_memory=False,
    )
    elev_raw = nodes.set_index("node_id")["elevation_copernicus_m"]
    input_rows = len(edges)

    # --- 1) 원값 진단 ---
    raw = compute_grades(edges, elev_raw)
    raw_diag = {
        "overall": grade_stats(raw.loc[raw["grade_abs_percent"] <= error_grade, "grade_abs_percent"]),
        "over_100pct": int((raw["grade_abs_percent"] > error_grade).sum()),
        "by_length_bucket": bucket_diagnostics(raw, google_ref, bucket_edges, error_grade),
    }

    # --- 2) 노이즈 완화: 네트워크 이웃 IDW 스무딩 ---
    elev_smooth = smooth_elevations(
        edges,
        elev_raw,
        max_len=float(mit["neighbor_max_length_m"]),
        alpha=float(mit["self_weight_alpha"]),
        passes=int(mit["passes"]),
    )
    sm = compute_grades(edges, elev_smooth)
    mit_diag = {
        "overall": grade_stats(sm.loc[sm["grade_abs_percent"] <= error_grade, "grade_abs_percent"]),
        "over_100pct": int((sm["grade_abs_percent"] > error_grade).sum()),
        "by_length_bucket": bucket_diagnostics(sm, google_ref, bucket_edges, error_grade),
    }

    # --- 3) 유효성 판정 (스무딩 후 기준) 및 산출물 저장 ---
    missing_node_ref = ~(edges["u"].isin(elev_raw.index) & edges["v"].isin(elev_raw.index))
    nonpositive_length = edges["length_m"] <= 0
    missing_elev = sm["elev_u"].isna() | sm["elev_v"].isna()
    over_error = sm["grade_abs_percent"] > error_grade
    valid = ~missing_node_ref & ~nonpositive_length & ~missing_elev & ~over_error

    out = edges.loc[valid, ["edge_id", "u", "v", "key", "length_m", "geometry_wkt"]].copy()
    out["grade_percent_cop"] = sm.loc[valid, "grade_percent"]
    out["grade_abs_percent_cop"] = sm.loc[valid, "grade_abs_percent"]
    assert not any("google" in c.lower() for c in out.columns), "google 열이 산출물에 포함됨"
    out_path = out_dir / "edges_base.parquet"
    out.to_parquet(out_path, index=False)

    # ≥100m 구간 불변성: 스무딩이 장거리 실제 지형을 훼손하지 않는지
    raw_long = raw_diag["by_length_bucket"][-1]["copernicus"]
    mit_long = mit_diag["by_length_bucket"][-1]["copernicus"]
    long_bucket_median_shift = (
        round(abs(mit_long["median"] - raw_long["median"]) / raw_long["median"], 4)
        if raw_long and raw_long.get("median")
        else None
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan": "docs/prototype_plan.md v2 단계 0 (게이트 결정: 투트랙 분리)",
        "sources": {
            "network": "OpenStreetMap (ODbL 1.0) — © OpenStreetMap contributors",
            "elevation": "Copernicus GLO-30 — © European Union, contains modified Copernicus DEM data",
            "google_columns_in_output": 0,
        },
        "input_rows": input_rows,
        "exclusions": {
            "missing_node_ref": int(missing_node_ref.sum()),
            "nonpositive_length": int((nonpositive_length & ~missing_node_ref).sum()),
            "missing_copernicus_elevation": int(
                (missing_elev & ~missing_node_ref & ~nonpositive_length).sum()
            ),
            "grade_over_100pct_after_mitigation": int(
                (over_error & ~missing_node_ref & ~nonpositive_length & ~missing_elev).sum()
            ),
        },
        "valid_rows": int(valid.sum()),
        "noise_mitigation": {
            "method": mit["method"],
            "params": {
                "neighbor_max_length_m": mit["neighbor_max_length_m"],
                "self_weight_alpha": mit["self_weight_alpha"],
                "passes": mit["passes"],
            },
            "long_bucket_median_shift_ratio": long_bucket_median_shift,
        },
        "diagnostics_raw": raw_diag,
        "diagnostics_mitigated": mit_diag,
        "outputs": {"edges_base_parquet": str(out_path.relative_to(ROOT))},
    }
    report_path = out_dir / "build_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    total = report["valid_rows"] + sum(report["exclusions"].values())
    assert total == input_rows, f"행수 불일치: {total} != {input_rows}"
    print(json.dumps(
        {
            "valid_rows": report["valid_rows"],
            "over_100pct_raw": raw_diag["over_100pct"],
            "over_100pct_mitigated": mit_diag["over_100pct"],
            "median_raw": raw_diag["overall"].get("median"),
            "median_mitigated": mit_diag["overall"].get("median"),
            "long_bucket_median_shift_ratio": long_bucket_median_shift,
        },
        ensure_ascii=False,
    ))
    print(f"OK -> {out_path}")
    print(f"OK -> {report_path}")

    # --- 단계 2: 라우팅·지도 산출물 (CSR 4종 + 정류장 스냅) ---
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from sl_accessibility.prototype import artifacts as proto_artifacts

    art = proto_artifacts.build_all(cfg, ROOT, out)
    print(json.dumps(
        {
            "cost_check_max_err": art["cost_verification"]["max_relative_error"],
            "nodes": art["nodes"],
            "arcs": {k: v["arcs"] for k, v in art["graphs"].items()},
            "stops_snapped": art["stops_snapped"],
            "stops_excluded": art["stops_excluded_over_snap_limit"],
        },
        ensure_ascii=False,
    ))
    print(f"OK -> {out_dir / 'artifacts_report.json'}")


if __name__ == "__main__":
    main()
