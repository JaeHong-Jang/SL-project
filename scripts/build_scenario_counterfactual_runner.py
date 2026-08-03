"""Build runner-backed S1/S3/S4 scenario delta artifacts.

This is a downstream audit runner. It reuses the existing walking network,
multi-source Dijkstra, and FrozenBaseline comparison so scenario maps can show
whether they are formal counterfactuals, upper bounds, or diagnostics.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkt

from sl_accessibility.accessibility.routing import (
    nearest_destination_lengths,
    read_network_nodes,
    snap_points_to_nodes,
)
from sl_accessibility.accessibility.scenario import (
    FrozenBaseline,
    evaluate_scenario,
    evaluate_scenario_rows,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "reports" / "scenario_counterfactual"
QGIS_DIR = ROOT / "qgis"
RUN_DATE = "2026-05-31"
CRS_METRIC = "EPSG:5179"
VULNERABLE_QUANTILE = 0.8


@dataclass(frozen=True)
class RunnerContext:
    hex_df: pd.DataFrame
    hex_geometry: gpd.GeoDataFrame
    diagnostics: pd.DataFrame
    edges: pd.DataFrame
    destination_nodes: list[int]
    frozen: FrozenBaseline


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def overwrite_gpkg(gdf: gpd.GeoDataFrame, path: Path, layer: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    gdf.to_file(path, layer=layer, driver="GPKG")


def frame_hash(df: pd.DataFrame, columns: list[str]) -> str:
    stable = df[columns].copy().sort_values(columns[0]).reset_index(drop=True)
    payload = pd.util.hash_pandas_object(stable, index=False).values.tobytes()
    return hashlib.sha256(payload).hexdigest()


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def weighted_average(values: pd.Series, weights: pd.Series) -> float:
    arr = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    w = pd.to_numeric(weights, errors="coerce").to_numpy(dtype=float)
    mask = ~(np.isnan(arr) | np.isnan(w)) & (w > 0)
    if not mask.any():
        return float("nan")
    return float(np.sum(arr[mask] * w[mask]) / np.sum(w[mask]))


def spearman_without_scipy(left: pd.Series, right: pd.Series) -> float:
    """Compute Spearman correlation without adding scipy as a dependency."""
    left_rank = pd.to_numeric(left, errors="coerce").rank(method="average")
    right_rank = pd.to_numeric(right, errors="coerce").rank(method="average")
    return float(left_rank.corr(right_rank, method="pearson"))


def load_context() -> RunnerContext:
    hex_df = pd.read_parquet(ROOT / "data" / "derived" / "hex_vulnerability_final.parquet")
    valid = hex_df["analysis_valid_final"].fillna(False).astype(bool)
    hex_df = hex_df.loc[valid].copy()
    hex_df["origin_node_id"] = pd.to_numeric(hex_df["origin_node_id"], errors="coerce")
    hex_df = hex_df.loc[
        hex_df["origin_node_id"].notna()
        & hex_df["access_cost_m3"].notna()
        & hex_df["demand_index_final"].notna()
    ].copy()

    hex_geometry = gpd.read_file(
        QGIS_DIR / "out_hex_vulnerability_final.gpkg",
        layer="out_hex_vulnerability_final",
    )[["hex_id", "geometry"]]
    diagnostics = pd.read_csv(ROOT / "outputs" / "reports" / "hidden_vulnerability_reason_diagnostics.csv")

    edge_columns = [
        "u",
        "v",
        "key",
        "osmid",
        "name",
        "highway",
        "length_m",
        "grade_abs_percent",
        "geometry_wkt",
        "cost_m0",
        "cost_m1",
        "cost_m2",
        "cost_m3",
    ]
    edges = pd.read_parquet(ROOT / "data" / "interim" / "walking_edge_costs.parquet", columns=edge_columns)
    destination_nodes = load_destination_nodes()
    frozen = FrozenBaseline.fit(
        hex_df["access_cost_m3"],
        hex_df["demand_index_final"],
        vulnerable_quantile=VULNERABLE_QUANTILE,
    )
    return RunnerContext(hex_df, hex_geometry, diagnostics, edges, destination_nodes, frozen)


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


def map_lengths_to_hex(
    hex_df: pd.DataFrame,
    edges: pd.DataFrame,
    destination_nodes: list[int],
    *,
    cost_column: str,
) -> pd.Series:
    lengths = nearest_destination_lengths(edges, destination_nodes, cost_columns=[cost_column])[cost_column]
    origin_nodes = pd.to_numeric(hex_df["origin_node_id"], errors="coerce").astype("Int64")
    return origin_nodes.map(lengths).astype(float)


def build_row_output(
    ctx: RunnerContext,
    scenario_cost: pd.Series,
    *,
    scenario_id: str,
    scenario_name: str,
) -> tuple[pd.DataFrame, gpd.GeoDataFrame, dict[str, Any]]:
    base = ctx.hex_df.copy()
    work = base.loc[scenario_cost.notna()].copy()
    cost = scenario_cost.loc[work.index]
    rows = evaluate_scenario_rows(
        hex_id=work["hex_id"],
        baseline_cost=work["access_cost_m3"],
        scenario_cost=cost,
        demand=work["demand_index_final"],
        official_400m_ok=work["official_400m_ok_m0"],
        frozen_baseline=ctx.frozen,
    )
    rows.insert(1, "scenario_id", scenario_id)
    rows.insert(2, "scenario_name", scenario_name)
    rows["registered_population"] = work["registered_population"].to_numpy()
    rows["registered_senior_population"] = work["registered_senior_population"].to_numpy()
    rows["demand_index_final"] = work["demand_index_final"].to_numpy()
    admin_cols = ["hex_id", "district_name", "admin_name", "admin_code", "primary_reason"]
    rows = rows.merge(ctx.diagnostics[admin_cols].drop_duplicates("hex_id"), on="hex_id", how="left")
    no_op_rows = evaluate_scenario_rows(
        hex_id=work["hex_id"],
        baseline_cost=work["access_cost_m3"],
        scenario_cost=work["access_cost_m3"],
        demand=work["demand_index_final"],
        official_400m_ok=work["official_400m_ok_m0"],
        frozen_baseline=ctx.frozen,
    )

    gdf = ctx.hex_geometry.merge(rows, on="hex_id", how="inner")
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=CRS_METRIC)

    evaluation = evaluate_scenario(
        baseline_cost=work["access_cost_m3"],
        scenario_cost=cost,
        demand=work["demand_index_final"],
        population=work["registered_population"],
        senior_population=work["registered_senior_population"],
        frozen_baseline=ctx.frozen,
        scenario_name=scenario_name,
    )
    summary = {
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "row_count": int(len(rows)),
        "baseline_vulnerable_count": int(rows["baseline_vulnerable"].sum()),
        "scenario_vulnerable_count": int(rows["scenario_vulnerable"].sum()),
        "resolved_vulnerable_count": int(rows["resolved_vulnerable"].sum()),
        "new_vulnerable_count": int(rows["new_vulnerable"].sum()),
        "baseline_hidden_count": int(rows["baseline_hidden"].sum()),
        "scenario_hidden_count": int(rows["scenario_hidden"].sum()),
        "resolved_hidden_count": int(rows["resolved_hidden"].sum()),
        "new_hidden_count": int(rows["new_hidden"].sum()),
        "mean_delta_cost_m": float(rows["delta_cost"].mean()),
        "median_delta_cost_m": float(rows["delta_cost"].median()),
        "p90_delta_cost_m": float(rows["delta_cost"].quantile(0.90)),
        "population_weighted_mean_delta_cost_m": weighted_average(
            rows["delta_cost"],
            rows["registered_population"],
        ),
        "senior_weighted_mean_delta_cost_m": weighted_average(
            rows["delta_cost"],
            rows["registered_senior_population"],
        ),
        "mean_delta_vulnerability": float(rows["delta_vulnerability"].mean()),
        "changed_cost_hex_count": int((rows["delta_cost"].abs() > 1e-9).sum()),
        "nonzero_delta_vulnerability_count": int((rows["delta_vulnerability"].abs() > 1e-12).sum()),
        "resolved_hidden_senior_population_sum": float(
            rows.loc[rows["resolved_hidden"], "registered_senior_population"].sum()
        ),
        "p90_delta_rank_improvement": float(rows["delta_rank_improvement"].quantile(0.90)),
        "spearman_vulnerability_before_after": spearman_without_scipy(
            rows["baseline_vulnerability"],
            rows["scenario_vulnerability"],
        ),
        "no_op_delta_cost_abs_max": float(no_op_rows["delta_cost"].abs().max()),
        "no_op_delta_vulnerability_abs_max": float(no_op_rows["delta_vulnerability"].abs().max()),
        "no_op_resolved_hidden_count": int(no_op_rows["resolved_hidden"].sum()),
        "aggregate_evaluation": evaluation.to_dict(),
    }
    return rows, gdf, summary


def build_manifest(
    *,
    scenario_id: str,
    canonical_scenario: str,
    intervention_parameter: dict[str, Any],
    input_paths: list[str],
    output_paths: list[str],
    rows: pd.DataFrame | None,
    baseline_cost_column: str,
    scenario_cost_column: str,
    changed_cost_term: list[str],
    unchanged_cost_term: list[str],
    path_research_run: bool,
    effect_output_label: str,
    frozen_threshold: float,
    notes: str,
) -> dict[str, Any]:
    manifest = {
        "scenario_id": f"{scenario_id}_{RUN_DATE.replace('-', '')}",
        "canonical_scenario": canonical_scenario,
        "legacy_name": None,
        "intervention_parameter": intervention_parameter,
        "run_timestamp": datetime.now(UTC).isoformat(),
        "code_version_id": "workspace",
        "changed_cost_term": changed_cost_term,
        "unchanged_cost_term": unchanged_cost_term,
        "baseline_cost_column": baseline_cost_column,
        "scenario_cost_column": scenario_cost_column,
        "baseline_demand_column": "demand_index_final",
        "scenario_demand_created": False,
        "fixed_normalization_universe": "analysis_valid_final with reachable M3",
        "fixed_threshold_universe": "S0-M3 FrozenBaseline over reachable final hexes",
        "baseline_row_count": int(len(rows)) if rows is not None else None,
        "scenario_row_count": int(len(rows)) if rows is not None else None,
        "hex_id_set_equal": True if rows is not None else None,
        "path_research_run": path_research_run,
        "path_research_method": "networkx multi_source_dijkstra_path_length",
        "path_geometry_reconstructed": False,
        "effect_output_label": effect_output_label,
        "frozen_baseline_threshold_hash": stable_hash(
            {
                "threshold": frozen_threshold,
                "quantile": VULNERABLE_QUANTILE,
                "universe": "S0-M3 reachable final hexes",
            }
        ),
        "baseline_cost_hash": frame_hash(rows, ["hex_id", "baseline_cost"]) if rows is not None else None,
        "scenario_cost_hash": frame_hash(rows, ["hex_id", "scenario_cost"]) if rows is not None else None,
        "baseline_demand_hash": frame_hash(rows, ["hex_id", "demand_index_final"]) if rows is not None else None,
        "scenario_demand_hash": frame_hash(rows, ["hex_id", "demand_index_final"]) if rows is not None else None,
        "input_paths": input_paths,
        "output_paths": output_paths,
        "notes": notes,
    }
    return manifest


def run_s1(ctx: RunnerContext) -> dict[str, Any]:
    candidates = gpd.read_file(QGIS_DIR / "S1_candidates.gpkg", layer="out_s1_candidate_stops")
    candidate_nodes = sorted(
        {
            int(node)
            for node in candidates.loc[
                candidates["candidate_node_id"].notna()
                & (candidates["candidate_snap_distance_m"] <= 100.0),
                "candidate_node_id",
            ]
        }
    )
    candidate_cost = map_lengths_to_hex(ctx.hex_df, ctx.edges, candidate_nodes, cost_column="cost_m3")
    scenario_cost = pd.concat([ctx.hex_df["access_cost_m3"], candidate_cost], axis=1).min(axis=1)
    rows, gdf, summary = build_row_output(
        ctx,
        scenario_cost,
        scenario_id="S1",
        scenario_name="S1_all_48_candidate_stops_dijkstra_upper_bound",
    )
    rows["candidate_only_access_cost_m3"] = candidate_cost.loc[ctx.hex_df.index].to_numpy()
    csv_path = OUT_DIR / "S1_delta_vulnerability.csv"
    gpkg_path = QGIS_DIR / "S1_delta_vulnerability_runner.gpkg"
    summary_path = OUT_DIR / "S1_delta_vulnerability_summary.json"
    manifest_path = OUT_DIR / "S1_delta_vulnerability.manifest.json"
    write_csv(csv_path, rows)
    overwrite_gpkg(gdf, gpkg_path, "S1_delta_vulnerability_runner")
    write_json(summary_path, summary)
    manifest = build_manifest(
        scenario_id="S1",
        canonical_scenario="S1_transit_access_candidate_destinations",
        intervention_parameter={
            "candidate_stop_count": int(len(candidates)),
            "valid_candidate_node_count": int(len(candidate_nodes)),
            "destination_rule": "existing D cost min Dijkstra distance to 48 candidate nodes",
        },
        input_paths=[
            "data/derived/hex_vulnerability_final.parquet",
            "data/interim/walking_edge_costs.parquet",
            "qgis/S1_candidates.gpkg",
        ],
        output_paths=[str(csv_path.relative_to(ROOT)), str(gpkg_path.relative_to(ROOT))],
        rows=rows,
        baseline_cost_column="access_cost_m3",
        scenario_cost_column="min(access_cost_m3, candidate_access_cost_m3)",
        changed_cost_term=["destination_node_set"],
        unchanged_cost_term=["edge_cost_m3", "demand_index_final"],
        path_research_run=True,
        effect_output_label="upper_bound",
        frozen_threshold=ctx.frozen.vulnerability_threshold,
        notes=(
            "All 48 candidate stops are treated as available destination nodes. "
            "This is a Dijkstra re-search upper bound, not a feasible stop program."
        ),
    )
    write_json(manifest_path, manifest)
    summary["manifest_path"] = str(manifest_path.relative_to(ROOT))
    summary["output_gpkg"] = str(gpkg_path.relative_to(ROOT))
    return summary


def infer_weather_intensity(edges: pd.DataFrame, weather_beta: float = 0.03) -> float:
    valid = edges["cost_m1"].gt(0) & edges["cost_m2"].notna() & edges["cost_m1"].notna()
    additive_factor = (edges.loc[valid, "cost_m2"] / edges.loc[valid, "cost_m1"]).replace([np.inf, -np.inf], np.nan)
    return float(((additive_factor.dropna().median() - 1.0) / weather_beta))


def run_s3(ctx: RunnerContext) -> dict[str, Any]:
    edges = ctx.edges.copy()
    alpha = 0.03
    weather_beta = 0.03
    interaction_beta = 0.08
    weather_intensity = infer_weather_intensity(edges, weather_beta=weather_beta)
    grade = pd.to_numeric(edges["grade_abs_percent"], errors="coerce").abs()
    current_grade_for_cost = grade.clip(upper=30.0)
    scenario_grade_for_cost = current_grade_for_cost.where(grade <= 30.0, 15.0)
    slope_factor = 1.0 + alpha * scenario_grade_for_cost
    interaction_factor = 1.0 + weather_beta * weather_intensity + (
        interaction_beta * weather_intensity * scenario_grade_for_cost / 100.0
    )
    improved_mask = grade > 30.0
    edges["cost_m3"] = np.where(
        improved_mask,
        pd.to_numeric(edges["length_m"], errors="coerce") * slope_factor * interaction_factor,
        edges["cost_m3"],
    )
    scenario_cost = map_lengths_to_hex(ctx.hex_df, edges, ctx.destination_nodes, cost_column="cost_m3")
    rows, gdf, summary = build_row_output(
        ctx,
        scenario_cost,
        scenario_id="S3",
        scenario_name="S3_global_grade_gt30_cap15_dijkstra",
    )
    csv_path = OUT_DIR / "S3_delta_vulnerability.csv"
    gpkg_path = QGIS_DIR / "S3_delta_vulnerability_runner.gpkg"
    summary_path = OUT_DIR / "S3_delta_vulnerability_summary.json"
    manifest_path = OUT_DIR / "S3_delta_vulnerability.manifest.json"
    improved_edges_path = QGIS_DIR / "S3_improved_edges_cap15.gpkg"
    write_csv(csv_path, rows)
    overwrite_gpkg(gdf, gpkg_path, "S3_delta_vulnerability_runner")
    write_json(summary_path, summary)
    improved = edges.loc[improved_mask].copy()
    improved["scenario_grade_cap_percent"] = 15.0
    improved["baseline_cost_m3"] = ctx.edges.loc[improved.index, "cost_m3"]
    improved["scenario_cost_m3"] = improved["cost_m3"]
    improved["delta_edge_cost_m3"] = improved["baseline_cost_m3"] - improved["scenario_cost_m3"]
    improved["geometry"] = improved["geometry_wkt"].map(wkt.loads)
    improved_gdf = gpd.GeoDataFrame(improved.drop(columns=["geometry_wkt"]), geometry="geometry", crs=CRS_METRIC)
    overwrite_gpkg(improved_gdf, improved_edges_path, "S3_improved_edges_cap15")
    manifest = build_manifest(
        scenario_id="S3",
        canonical_scenario="S3_pedestrian_env_global_steep_edge_cap15",
        intervention_parameter={
            "improved_edge_rule": "grade_abs_percent > 30",
            "scenario_grade_cap_percent": 15.0,
            "improved_edge_count": int(improved_mask.sum()),
            "inferred_weather_intensity": round(weather_intensity, 6),
        },
        input_paths=[
            "data/derived/hex_vulnerability_final.parquet",
            "data/interim/walking_edge_costs.parquet",
            "qgis/out_transit_d_candidates.gpkg",
        ],
        output_paths=[
            str(csv_path.relative_to(ROOT)),
            str(gpkg_path.relative_to(ROOT)),
            str(improved_edges_path.relative_to(ROOT)),
        ],
        rows=rows,
        baseline_cost_column="access_cost_m3",
        scenario_cost_column="scenario_access_cost_m3_from_grade_cap15",
        changed_cost_term=["edge_slope_cost_m3_for_grade_gt30"],
        unchanged_cost_term=["destination_node_set", "demand_index_final"],
        path_research_run=True,
        effect_output_label="counterfactual_effect",
        frozen_threshold=ctx.frozen.vulnerability_threshold,
        notes=(
            "Formal counterfactual for a citywide steep-edge program: every edge with "
            "grade_abs_percent > 30 is recalculated with a 15 percent grade cap and "
            "Dijkstra is re-run. Budget, constructability, and exact path geometries "
            "are not validated here."
        ),
    )
    write_json(manifest_path, manifest)
    summary["manifest_path"] = str(manifest_path.relative_to(ROOT))
    summary["output_gpkg"] = str(gpkg_path.relative_to(ROOT))
    summary["improved_edges_gpkg"] = str(improved_edges_path.relative_to(ROOT))
    return summary


def run_s4(ctx: RunnerContext) -> dict[str, Any]:
    scenario_cost = map_lengths_to_hex(ctx.hex_df, ctx.edges, ctx.destination_nodes, cost_column="cost_m1")
    rows, gdf, summary = build_row_output(
        ctx,
        scenario_cost,
        scenario_id="S4",
        scenario_name="S4_weather_terms_removed_dijkstra_upper_bound",
    )
    csv_path = OUT_DIR / "S4_weather_off_delta_vulnerability.csv"
    gpkg_path = QGIS_DIR / "S4_weather_off_delta_vulnerability_runner.gpkg"
    summary_path = OUT_DIR / "S4_weather_off_delta_vulnerability_summary.json"
    manifest_path = OUT_DIR / "S4_weather_off_delta_vulnerability.manifest.json"
    write_csv(csv_path, rows)
    overwrite_gpkg(gdf, gpkg_path, "S4_weather_off_delta_vulnerability_runner")
    write_json(summary_path, summary)
    manifest = build_manifest(
        scenario_id="S4",
        canonical_scenario="S4_weather_response_weather_terms_removed",
        intervention_parameter={
            "scenario_cost": "cost_m1",
            "removed_terms": ["weather_additive_factor", "slope_weather_interaction"],
            "scope": "citywide component upper bound",
        },
        input_paths=[
            "data/derived/hex_vulnerability_final.parquet",
            "data/interim/walking_edge_costs.parquet",
            "qgis/out_transit_d_candidates.gpkg",
        ],
        output_paths=[str(csv_path.relative_to(ROOT)), str(gpkg_path.relative_to(ROOT))],
        rows=rows,
        baseline_cost_column="access_cost_m3",
        scenario_cost_column="access_cost_m1_researched",
        changed_cost_term=["weather_additive_factor", "slope_weather_interaction"],
        unchanged_cost_term=["slope_cost_m1", "destination_node_set", "demand_index_final"],
        path_research_run=True,
        effect_output_label="upper_bound",
        frozen_threshold=ctx.frozen.vulnerability_threshold,
        notes=(
            "This is a weather-component upper bound: it removes weather terms citywide "
            "and re-runs Dijkstra. It is not evidence that local shelters or snow "
            "operations will produce the same effect."
        ),
    )
    write_json(manifest_path, manifest)
    summary["manifest_path"] = str(manifest_path.relative_to(ROOT))
    summary["output_gpkg"] = str(gpkg_path.relative_to(ROOT))
    return summary


def build_registry(summaries: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for summary in summaries:
        scenario_id = summary["scenario_id"]
        manifest = json.loads((ROOT / summary["manifest_path"]).read_text(encoding="utf-8"))
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": summary["scenario_name"],
                "primary_output": summary["output_gpkg"],
                "manifest_path": summary["manifest_path"],
                "row_count": summary["row_count"],
                "path_research_run": manifest["path_research_run"],
                "effect_output_label": manifest["effect_output_label"],
                "counterfactual_effect_claim_allowed": (
                    manifest["effect_output_label"] == "counterfactual_effect"
                    and bool(manifest["path_research_run"])
                    and bool(manifest["scenario_cost_hash"])
                ),
                "baseline_hidden_count": summary["baseline_hidden_count"],
                "scenario_hidden_count": summary["scenario_hidden_count"],
                "resolved_hidden_count": summary["resolved_hidden_count"],
                "new_hidden_count": summary["new_hidden_count"],
                "senior_weighted_mean_delta_cost_m": summary["senior_weighted_mean_delta_cost_m"],
                "spearman_vulnerability_before_after": summary["spearman_vulnerability_before_after"],
                "notes": manifest["notes"],
            }
        )
    return pd.DataFrame(rows)


def write_qgis_checklist(registry: pd.DataFrame) -> None:
    table_rows = [
        "| scenario_id | effect_output_label | path_research_run | resolved_hidden_count | counterfactual_effect_claim_allowed |",
        "|---|---|---:|---:|---|",
    ]
    for row in registry[
        [
            "scenario_id",
            "effect_output_label",
            "path_research_run",
            "resolved_hidden_count",
            "counterfactual_effect_claim_allowed",
        ]
    ].itertuples(index=False):
        table_rows.append(
            f"| {row.scenario_id} | {row.effect_output_label} | {row.path_research_run} | "
            f"{int(row.resolved_hidden_count)} | {row.counterfactual_effect_claim_allowed} |"
        )
    lines = [
        "# Scenario Counterfactual QGIS Checklist",
        "",
        "## Layer Sources",
        "- S1: `qgis/S1_delta_vulnerability_runner.gpkg` + `qgis/S1_candidates.gpkg`.",
        "- S3: `qgis/S3_delta_vulnerability_runner.gpkg` + `qgis/S3_improved_edges_cap15.gpkg`.",
        "- S4: `qgis/S4_weather_off_delta_vulnerability_runner.gpkg` + `qgis/scenario3_weather_response_top20_admin_fixed.gpkg`.",
        "",
        "## Claim Labels",
        "- `upper_bound`: show as scenario screening or component upper bound.",
        "- `counterfactual_effect`: may report accessibility-burden effect under the exact manifest assumption.",
        "- Never label these as ridership demand increase, passenger redistribution, or observed behavior.",
        "",
        "## Renderer Checks",
        "- Use the same CRS (`EPSG:5179`) and the same color scale for all delta maps.",
        "- Map `delta_vulnerability` with sequential positive-improvement colors.",
        "- Label only `resolved_hidden=True` or top-20 `delta_vulnerability` if the map is crowded.",
        "- Put manifest path and `effect_output_label` in the layout note.",
        "",
        "## Registry Snapshot",
        "\n".join(table_rows),
    ]
    (OUT_DIR / "scenario_counterfactual_qgis_checklist.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ctx = load_context()
    summaries = [run_s1(ctx), run_s3(ctx), run_s4(ctx)]
    registry = build_registry(summaries)
    write_csv(OUT_DIR / "scenario_counterfactual_registry.csv", registry)
    write_json(OUT_DIR / "scenario_counterfactual_registry.json", {"rows": registry.to_dict("records")})
    write_qgis_checklist(registry)
    write_json(
        OUT_DIR / "scenario_counterfactual_runner_summary.json",
        {
            "run_date": RUN_DATE,
            "valid_hex_rows": int(len(ctx.hex_df)),
            "destination_node_count": int(len(ctx.destination_nodes)),
            "scenarios": summaries,
        },
    )
    print(registry.to_string(index=False))


if __name__ == "__main__":
    main()
