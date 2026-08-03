"""E1/E3/E6 민감도 runner — Dijkstra 재탐색을 포함한 baseline 정의 민감도.

v2.2 부록 C.2에서 미완으로 남아 있던 항목을 산출한다.

- E1: 경사 cap 25/30/40%로 edge cost_m3를 재계산하고 Dijkstra를 다시 돌린다.
- E3: beta_weather {0.01, 0.03, 0.05}, interaction_beta {0.04, 0.08, 0.12}를
  한 번에 하나씩 바꿔 재계산한다 (configs/model_params.yaml sensitivity 목록).
- E6: 각 hex에서 k=1(기준)/2/3번째로 가까운 D까지 평균 비용으로 접근비용을
  재정의한다. origin별 forward Dijkstra(cutoff 확장)로 k근접 D를 찾는다.

여기서의 민감도는 정책 시나리오 효과가 아니라 "기준선 정의를 바꾸면
취약/hidden 집합이 얼마나 흔들리는가"이므로, 각 변형은 자기 universe에서
Min-Max와 상위 20% threshold를 다시 fit하고, baseline(877/632) 집합과의
Jaccard·교체율로 보고한다.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd

from sl_accessibility.accessibility.routing import read_network_nodes, snap_points_to_nodes

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "reports" / "e_sensitivity"
QGIS_DIR = ROOT / "qgis"
CRS_METRIC = "EPSG:5179"
VULNERABLE_QUANTILE = 0.8

# M3 기준선 계수 (configs/model_params.yaml과 정렬)
ALPHA = 0.03
BETA_WEATHER = 0.03
INTERACTION_BETA = 0.08
WEATHER_INTENSITY = 2.0  # rain_mm=2 기준선과 정렬 (runner에서 추정 검증 완료)
BASE_CAP = 30.0


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def spearman(left: pd.Series, right: pd.Series) -> float:
    lr = pd.to_numeric(left, errors="coerce").rank(method="average")
    rr = pd.to_numeric(right, errors="coerce").rank(method="average")
    return float(lr.corr(rr, method="pearson"))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return float("nan")
    return len(a & b) / len(a | b)


def replacement_rate(baseline: set, variant: set) -> float:
    """baseline 집합 중 variant에서 빠진 비율 (hidden 교체율 정의와 동일)."""
    if not baseline:
        return float("nan")
    return len(baseline - variant) / len(baseline)


def load_hex_frame() -> pd.DataFrame:
    hex_df = pd.read_parquet(ROOT / "data" / "derived" / "hex_vulnerability_final.parquet")
    valid = hex_df["analysis_valid_final"].fillna(False).astype(bool)
    hex_df = hex_df.loc[valid].copy()
    hex_df["origin_node_id"] = pd.to_numeric(hex_df["origin_node_id"], errors="coerce")
    hex_df = hex_df.loc[
        hex_df["origin_node_id"].notna()
        & hex_df["access_cost_m3"].notna()
        & hex_df["demand_index_final"].notna()
    ].copy()
    hex_df["origin_node_id"] = hex_df["origin_node_id"].astype(np.int64)
    return hex_df.reset_index(drop=True)


def load_destination_nodes() -> list[int]:
    nodes = read_network_nodes(ROOT / "data" / "walking_network_nodes_with_elevation.csv", crs=CRS_METRIC)
    d_candidates = gpd.read_file(
        QGIS_DIR / "out_transit_d_candidates.gpkg",
        layer="out_transit_d_candidates",
    )
    d_snaps = snap_points_to_nodes(
        d_candidates,
        nodes,
        id_columns=["mode", "stop_id", "stop_name"],
        max_distance_m=100.0,
    )
    valid = d_snaps.loc[d_snaps["node_id"].notna() & (d_snaps["snap_distance_m"] <= 100.0)]
    return sorted({int(node) for node in valid["node_id"]})


def load_edges() -> pd.DataFrame:
    edges = pd.read_parquet(
        ROOT / "data" / "interim" / "walking_edge_costs.parquet",
        columns=["u", "v", "length_m", "grade_abs_percent", "cost_m3"],
    )
    edges["u"] = pd.to_numeric(edges["u"], errors="coerce").astype(np.int64)
    edges["v"] = pd.to_numeric(edges["v"], errors="coerce").astype(np.int64)
    return edges


def m3_edge_cost(
    edges: pd.DataFrame,
    *,
    cap: float,
    beta_weather: float,
    interaction_beta: float,
    intensity: float = WEATHER_INTENSITY,
    alpha: float = ALPHA,
) -> pd.Series:
    grade = pd.to_numeric(edges["grade_abs_percent"], errors="coerce").abs().clip(upper=cap)
    length = pd.to_numeric(edges["length_m"], errors="coerce")
    slope_factor = 1.0 + alpha * grade
    interaction_factor = 1.0 + beta_weather * intensity + interaction_beta * intensity * grade / 100.0
    return length * slope_factor * interaction_factor


def nearest_destination_costs(
    edges: pd.DataFrame,
    weight: pd.Series,
    destination_nodes: list[int],
) -> dict[int, float]:
    frame = pd.DataFrame({"v": edges["v"], "u": edges["u"], "weight": weight}).dropna(subset=["weight"])
    dedup = frame.groupby(["v", "u"], sort=False)["weight"].min().reset_index()
    graph = nx.DiGraph()
    graph.add_weighted_edges_from(dedup.itertuples(index=False, name=None))
    sources = [node for node in destination_nodes if node in graph]
    return nx.multi_source_dijkstra_path_length(graph, sources, weight="weight")


def evaluate_variant(
    hex_df: pd.DataFrame,
    cost: pd.Series,
    *,
    experiment: str,
    variant_name: str,
    baseline_vulnerable: set,
    baseline_hidden: set,
    parameter: dict[str, Any],
) -> dict[str, Any]:
    """변형별 자기 universe 재정규화 후 취약/hidden 집합 안정성을 평가한다."""
    valid = cost.notna() & hex_df["demand_index_final"].notna()
    cost_v = cost[valid]
    demand_v = hex_df.loc[valid, "demand_index_final"]
    cost_norm = (cost_v - cost_v.min()) / (cost_v.max() - cost_v.min())
    demand_norm = (demand_v - demand_v.min()) / (demand_v.max() - demand_v.min())
    vulnerability = cost_norm * demand_norm
    threshold = float(np.nanquantile(vulnerability, VULNERABLE_QUANTILE))
    vulnerable_mask = vulnerability >= threshold
    official_ok = hex_df.loc[valid, "official_400m_ok_m0"].fillna(False).astype(bool)
    hidden_mask = official_ok & vulnerable_mask

    vulnerable_set = set(hex_df.loc[valid, "hex_id"][vulnerable_mask])
    hidden_set = set(hex_df.loc[valid, "hex_id"][hidden_mask])

    return {
        "experiment": experiment,
        "variant": variant_name,
        **parameter,
        "valid_hex_count": int(valid.sum()),
        "mean_access_cost": float(cost_v.mean()),
        "p90_access_cost": float(cost_v.quantile(0.90)),
        "spearman_vs_baseline_m3": spearman(cost, hex_df["access_cost_m3"]),
        "threshold": threshold,
        "vulnerable_count": int(vulnerable_mask.sum()),
        "hidden_count": int(hidden_mask.sum()),
        "vulnerable_jaccard_vs_baseline": jaccard(vulnerable_set, baseline_vulnerable),
        "hidden_jaccard_vs_baseline": jaccard(hidden_set, baseline_hidden),
        "hidden_replacement_rate_vs_baseline": replacement_rate(baseline_hidden, hidden_set),
        "claim_use": "baseline_definition_sensitivity_not_effect_claim",
    }


def k_nearest_destination_costs(
    edges: pd.DataFrame,
    weight: pd.Series,
    origin_nodes: Iterable[int],
    destination_nodes: list[int],
    *,
    k_max: int,
    k1_cost_by_origin: dict[int, float],
) -> dict[int, list[float]]:
    """origin별 forward Dijkstra(cutoff 확장)로 k근접 D까지 비용 목록을 만든다."""
    frame = pd.DataFrame({"u": edges["u"], "v": edges["v"], "weight": weight}).dropna(subset=["weight"])
    dedup = frame.groupby(["u", "v"], sort=False)["weight"].min().reset_index()
    graph = nx.DiGraph()
    graph.add_weighted_edges_from(dedup.itertuples(index=False, name=None))
    dest_set = set(destination_nodes)

    results: dict[int, list[float]] = {}
    origins = list(dict.fromkeys(int(o) for o in origin_nodes))
    for idx, origin in enumerate(origins):
        if origin not in graph:
            results[origin] = []
            continue
        k1 = k1_cost_by_origin.get(origin, float("nan"))
        base_cutoff = 4.0 * k1 if np.isfinite(k1) and k1 > 0 else 1200.0
        found: list[float] = []
        for cutoff in (max(base_cutoff, 600.0), max(base_cutoff, 600.0) * 2, 6000.0):
            lengths = nx.single_source_dijkstra_path_length(graph, origin, cutoff=cutoff, weight="weight")
            found = sorted(dist for node, dist in lengths.items() if node in dest_set)[:k_max]
            if len(found) >= k_max:
                break
        results[origin] = found
        if (idx + 1) % 500 == 0:
            print(f"[e6] {idx + 1}/{len(origins)} origins")
    return results


def main() -> None:
    run_started = datetime.now(UTC)
    hex_df = load_hex_frame()
    destination_nodes = load_destination_nodes()
    edges = load_edges()

    baseline_vulnerable = set(hex_df.loc[hex_df["vulnerable_m3_final"].fillna(False).astype(bool), "hex_id"])
    baseline_hidden = set(hex_df.loc[hex_df["hidden_vulnerable_final"].fillna(False).astype(bool), "hex_id"])

    rows: list[dict[str, Any]] = []

    # --- E1: 경사 cap 민감도 (Dijkstra 재탐색) ---
    sanity_max_abs_diff = float("nan")
    for cap in (25.0, 30.0, 40.0):
        weight = m3_edge_cost(edges, cap=cap, beta_weather=BETA_WEATHER, interaction_beta=INTERACTION_BETA)
        if cap == BASE_CAP:
            # 재계산 sanity check: 저장된 cost_m3와 일치해야 한다.
            sanity_max_abs_diff = float((weight - pd.to_numeric(edges["cost_m3"], errors="coerce")).abs().max())
        lengths = nearest_destination_costs(edges, weight, destination_nodes)
        cost = hex_df["origin_node_id"].map(lengths).astype(float)
        rows.append(
            evaluate_variant(
                hex_df,
                cost,
                experiment="E1_slope_cap",
                variant_name=f"cap_{int(cap)}",
                baseline_vulnerable=baseline_vulnerable,
                baseline_hidden=baseline_hidden,
                parameter={"slope_cap_percent": cap, "beta_weather": BETA_WEATHER, "interaction_beta": INTERACTION_BETA},
            )
        )
        print(f"[e1] cap={cap} done")

    # --- E3: 기상/상호작용 계수 민감도 (one-at-a-time, Dijkstra 재탐색) ---
    e3_variants = [
        {"beta_weather": 0.01, "interaction_beta": INTERACTION_BETA},
        {"beta_weather": 0.05, "interaction_beta": INTERACTION_BETA},
        {"beta_weather": BETA_WEATHER, "interaction_beta": 0.04},
        {"beta_weather": BETA_WEATHER, "interaction_beta": 0.12},
    ]
    for variant in e3_variants:
        weight = m3_edge_cost(
            edges,
            cap=BASE_CAP,
            beta_weather=variant["beta_weather"],
            interaction_beta=variant["interaction_beta"],
        )
        lengths = nearest_destination_costs(edges, weight, destination_nodes)
        cost = hex_df["origin_node_id"].map(lengths).astype(float)
        name = f"beta_{variant['beta_weather']}_gamma_{variant['interaction_beta']}"
        rows.append(
            evaluate_variant(
                hex_df,
                cost,
                experiment="E3_weather_coefficients",
                variant_name=name,
                baseline_vulnerable=baseline_vulnerable,
                baseline_hidden=baseline_hidden,
                parameter={"slope_cap_percent": BASE_CAP, **variant},
            )
        )
        print(f"[e3] {name} done")

    # --- E6: k근접 D 민감도 (origin별 forward Dijkstra) ---
    base_weight = m3_edge_cost(edges, cap=BASE_CAP, beta_weather=BETA_WEATHER, interaction_beta=INTERACTION_BETA)
    k1_by_origin = dict(zip(hex_df["origin_node_id"], hex_df["access_cost_m3"]))
    k_costs = k_nearest_destination_costs(
        edges,
        base_weight,
        hex_df["origin_node_id"],
        destination_nodes,
        k_max=3,
        k1_cost_by_origin=k1_by_origin,
    )
    e6_detail = pd.DataFrame(
        {
            "hex_id": hex_df["hex_id"],
            "origin_node_id": hex_df["origin_node_id"],
            "access_cost_m3_k1_stored": hex_df["access_cost_m3"],
        }
    )
    for k in (1, 2, 3):
        e6_detail[f"mean_cost_k{k}"] = [
            float(np.mean(k_costs.get(int(o), [])[:k])) if len(k_costs.get(int(o), [])) >= k else np.nan
            for o in hex_df["origin_node_id"]
        ]
    e6_k1_sanity = float((e6_detail["mean_cost_k1"] - e6_detail["access_cost_m3_k1_stored"]).abs().max())
    for k in (2, 3):
        cost = e6_detail[f"mean_cost_k{k}"]
        rows.append(
            evaluate_variant(
                hex_df,
                cost,
                experiment="E6_k_nearest_destinations",
                variant_name=f"k_{k}_mean",
                baseline_vulnerable=baseline_vulnerable,
                baseline_hidden=baseline_hidden,
                parameter={"k": k, "slope_cap_percent": BASE_CAP, "beta_weather": BETA_WEATHER, "interaction_beta": INTERACTION_BETA},
            )
        )
        print(f"[e6] k={k} done")

    metrics = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = OUT_DIR / "e_sensitivity_metrics.csv"
    e6_path = OUT_DIR / "e6_k_nearest_costs.csv"
    summary_path = OUT_DIR / "e_sensitivity_summary.json"
    manifest_path = OUT_DIR / "e_sensitivity.manifest.json"
    write_csv(metrics_path, metrics)
    write_csv(e6_path, e6_detail)

    summary = {
        "run_date": run_started.date().isoformat(),
        "run_timestamp": run_started.isoformat(),
        "valid_hex_rows": int(len(hex_df)),
        "baseline_vulnerable_count": len(baseline_vulnerable),
        "baseline_hidden_count": len(baseline_hidden),
        "e1_cap30_recompute_max_abs_diff_vs_stored_cost_m3": sanity_max_abs_diff,
        "e6_k1_max_abs_diff_vs_stored_access_cost_m3": e6_k1_sanity,
        "hidden_count_range": [int(metrics["hidden_count"].min()), int(metrics["hidden_count"].max())],
        "hidden_replacement_rate_max": float(metrics["hidden_replacement_rate_vs_baseline"].max()),
        "spearman_vs_baseline_min": float(metrics["spearman_vs_baseline_m3"].min()),
        "claim_boundary": (
            "이 결과는 기준선 정의(cap, 계수, k근접 D)에 대한 민감도이며 "
            "정책 효과 추정이 아니다. 각 변형은 자기 universe에서 재정규화했다."
        ),
    }
    write_json(summary_path, summary)
    manifest = {
        "experiment_set": ["E1_slope_cap", "E3_weather_coefficients", "E6_k_nearest_destinations"],
        "run_timestamp": run_started.isoformat(),
        "code_version_id": "workspace",
        "effect_output_label": "baseline_definition_sensitivity",
        "counterfactual_effect_claim_allowed": False,
        "path_research_run": True,
        "path_research_method": (
            "multi_source_dijkstra_path_length per variant; E6 uses per-origin "
            "single_source_dijkstra_path_length with expanding cutoff"
        ),
        "weather_intensity": WEATHER_INTENSITY,
        "renormalization": "per-variant Min-Max + top 20% threshold (baseline definition sensitivity)",
        "config_hash": stable_hash(
            {
                "alpha": ALPHA,
                "beta_weather": BETA_WEATHER,
                "interaction_beta": INTERACTION_BETA,
                "intensity": WEATHER_INTENSITY,
                "caps": [25, 30, 40],
                "e3": e3_variants,
                "k": [1, 2, 3],
            }
        ),
        "input_paths": [
            "data/derived/hex_vulnerability_final.parquet",
            "data/interim/walking_edge_costs.parquet",
            "data/walking_network_nodes_with_elevation.csv",
            "qgis/out_transit_d_candidates.gpkg",
        ],
        "output_paths": [
            str(metrics_path.relative_to(ROOT)),
            str(e6_path.relative_to(ROOT)),
            str(summary_path.relative_to(ROOT)),
        ],
    }
    write_json(manifest_path, manifest)

    print(metrics.to_string(index=False))
    print(f"sanity cap30 max abs diff: {sanity_max_abs_diff:.6f}")
    print(f"sanity e6 k1 max abs diff: {e6_k1_sanity:.6f}")


if __name__ == "__main__":
    main()
