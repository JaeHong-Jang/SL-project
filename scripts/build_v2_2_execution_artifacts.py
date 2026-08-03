"""Build v2.2 defense artifacts from the current final hex outputs.

The script is intentionally downstream-only: it does not alter the production
pipeline or reinterpret scenario outputs as causal effects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from sl_accessibility.accessibility.scenario import FrozenBaseline, evaluate_scenario


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "outputs" / "reports" / "v2_2_execution"
QGIS_DIR = ROOT / "qgis"


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


def minmax(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce")
    lo = series.min()
    hi = series.max()
    if not np.isfinite(lo) or not np.isfinite(hi) or hi == lo:
        return pd.Series(np.nan, index=series.index)
    return (series - lo) / (hi - lo)


def qcut_labels(series: pd.Series, labels: list[str]) -> pd.Series:
    ranked = pd.to_numeric(series, errors="coerce").rank(method="first")
    return pd.qcut(ranked, q=len(labels), labels=labels)


def top_fraction_flag(score: pd.Series, fraction: float) -> pd.Series:
    score = pd.to_numeric(score, errors="coerce")
    cutoff = score.quantile(1 - fraction)
    return score >= cutoff


def jaccard(left: pd.Series, right: pd.Series) -> float:
    left = left.fillna(False).astype(bool)
    right = right.fillna(False).astype(bool)
    union = (left | right).sum()
    if union == 0:
        return 1.0
    return float((left & right).sum() / union)


def frame_hash(df: pd.DataFrame, columns: list[str]) -> str:
    """Hash the exact row/value set used in a diagnostic manifest."""
    stable = df[columns].copy().sort_values(columns[0]).reset_index(drop=True)
    row_hashes = pd.util.hash_pandas_object(stable, index=False).values.tobytes()
    import hashlib

    return hashlib.sha256(row_hashes).hexdigest()


def weighted_average(values: pd.Series, weights: pd.Series | None = None) -> float:
    """Return a NaN-safe weighted mean for compact report summaries."""
    value_arr = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    if weights is None:
        return float(np.nanmean(value_arr))
    weight_arr = pd.to_numeric(weights, errors="coerce").to_numpy(dtype=float)
    mask = ~(np.isnan(value_arr) | np.isnan(weight_arr)) & (weight_arr > 0)
    if not mask.any():
        return float("nan")
    return float(np.sum(value_arr[mask] * weight_arr[mask]) / np.sum(weight_arr[mask]))


def build_variant_table(hex_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid = hex_df["analysis_valid_final"].fillna(False).astype(bool)
    official_ok = hex_df["official_400m_ok_m0"].fillna(False).astype(bool)
    base_hidden = hex_df["hidden_vulnerable_final"].fillna(False).astype(bool)
    base_vulnerable = hex_df["vulnerable_m3_final"].fillna(False).astype(bool)

    work = hex_df.loc[valid].copy()
    demand_norm = work["demand_norm_final"]
    cost = work["access_cost_m3"]

    cost_winsor = cost.clip(cost.quantile(0.01), cost.quantile(0.99))
    variants: dict[str, pd.Series] = {
        "baseline_minmax_product": work["vulnerability_m3_final"],
        "winsorize_1_99_product": minmax(cost_winsor) * demand_norm,
        "log1p_product": minmax(np.log1p(cost)) * demand_norm,
        "rank_product": cost.rank(pct=True) * demand_norm,
        "additive_minmax": minmax(cost) + demand_norm,
    }

    rows: list[dict[str, Any]] = []
    flag_df = pd.DataFrame(index=hex_df.index)
    flag_df["baseline_minmax_product_hidden"] = base_hidden
    flag_df["baseline_minmax_product_vulnerable"] = base_vulnerable

    for name, score in variants.items():
        full_score = pd.Series(np.nan, index=hex_df.index)
        full_score.loc[work.index] = score
        vulnerable = pd.Series(False, index=hex_df.index)
        vulnerable.loc[work.index] = top_fraction_flag(score, 0.20)
        hidden = official_ok & vulnerable
        flag_df[f"{name}_score"] = full_score
        flag_df[f"{name}_vulnerable"] = vulnerable
        flag_df[f"{name}_hidden"] = hidden
        rows.append(
            {
                "variant": name,
                "transform_family": "baseline" if name == "baseline_minmax_product" else name,
                "threshold_top_fraction": 0.20,
                "vulnerable_hex_count": int(vulnerable.sum()),
                "hidden_hex_count": int(hidden.sum()),
                "vulnerable_jaccard_vs_baseline": round(jaccard(vulnerable, base_vulnerable), 6),
                "hidden_jaccard_vs_baseline": round(jaccard(hidden, base_hidden), 6),
                "vulnerable_replacement_rate": round(1 - jaccard(vulnerable, base_vulnerable), 6),
                "hidden_replacement_rate": round(1 - jaccard(hidden, base_hidden), 6),
                "shared_hidden_with_baseline": int((hidden & base_hidden).sum()),
                "new_hidden_vs_baseline": int((hidden & ~base_hidden).sum()),
                "dropped_hidden_vs_baseline": int((base_hidden & ~hidden).sum()),
                "claim_use": "robustness_check_not_monte_carlo",
            }
        )

    base_score = work["vulnerability_m3_final"]
    for fraction in [0.10, 0.20, 0.30]:
        vulnerable = pd.Series(False, index=hex_df.index)
        vulnerable.loc[work.index] = top_fraction_flag(base_score, fraction)
        hidden = official_ok & vulnerable
        rows.append(
            {
                "variant": f"threshold_top_{int(fraction * 100)}pct",
                "transform_family": "baseline_minmax_product",
                "threshold_top_fraction": fraction,
                "vulnerable_hex_count": int(vulnerable.sum()),
                "hidden_hex_count": int(hidden.sum()),
                "vulnerable_jaccard_vs_baseline": round(jaccard(vulnerable, base_vulnerable), 6),
                "hidden_jaccard_vs_baseline": round(jaccard(hidden, base_hidden), 6),
                "vulnerable_replacement_rate": round(1 - jaccard(vulnerable, base_vulnerable), 6),
                "hidden_replacement_rate": round(1 - jaccard(hidden, base_hidden), 6),
                "shared_hidden_with_baseline": int((hidden & base_hidden).sum()),
                "new_hidden_vs_baseline": int((hidden & ~base_hidden).sum()),
                "dropped_hidden_vs_baseline": int((base_hidden & ~hidden).sum()),
                "claim_use": "threshold_sensitivity_not_effect_claim",
            }
        )

    return pd.DataFrame(rows), flag_df


def build_robust_core(
    hex_df: pd.DataFrame,
    hex_gdf: gpd.GeoDataFrame,
    flag_df: pd.DataFrame,
    diagnostics: pd.DataFrame,
) -> tuple[pd.DataFrame, gpd.GeoDataFrame, dict[str, Any]]:
    flag_cols = [
        "baseline_minmax_product_hidden",
        "winsorize_1_99_product_hidden",
        "log1p_product_hidden",
        "rank_product_hidden",
    ]
    flags = flag_df[flag_cols].fillna(False).astype(bool)
    any_hidden = flags.any(axis=1)
    robust_core = flags.all(axis=1)

    admin_cols = [
        "hex_id",
        "district_name",
        "admin_name",
        "admin_code",
    ]
    admin_lookup = diagnostics[[c for c in admin_cols if c in diagnostics.columns]].drop_duplicates(
        "hex_id"
    )
    base_cols = [
        "hex_id",
        "analysis_valid_final",
        "access_cost_m0",
        "access_cost_m3",
        "cost_m3_norm_final",
        "demand_norm_final",
        "demand_index_final",
        "vulnerability_m3_final",
        "vulnerability_threshold_final",
        "official_400m_ok_m0",
        "hidden_vulnerable_final",
        "registered_population",
        "registered_senior_population",
        "registered_senior_share",
        "poi_total_count",
    ]
    out = hex_df[base_cols].copy()
    out = out.join(flag_df[[c for c in flag_df.columns if c.endswith("_hidden")]])
    out["delta_cost_m3_minus_m0"] = out["access_cost_m3"] - out["access_cost_m0"]
    out["delta_pct_m3_over_m0"] = np.where(
        out["access_cost_m0"] > 0,
        out["delta_cost_m3_minus_m0"] / out["access_cost_m0"],
        np.nan,
    )
    out["any_normalization_hidden_flag"] = any_hidden
    out["robust_core_hidden_flag"] = robust_core
    out["variant_hidden_count"] = flags.sum(axis=1).astype(int)
    out["normalization_sensitive_flag"] = any_hidden & ~robust_core
    out = out.merge(admin_lookup, on="hex_id", how="left")

    out = out.loc[out["any_normalization_hidden_flag"]].copy()
    gdf = hex_gdf[["hex_id", "geometry"]].merge(out, on="hex_id", how="inner")

    summary = {
        "source": "data/derived/hex_vulnerability_final.parquet",
        "any_normalization_hidden_rows": int(out["any_normalization_hidden_flag"].sum()),
        "robust_core_hidden_rows": int(out["robust_core_hidden_flag"].sum()),
        "baseline_hidden_rows": int(hex_df["hidden_vulnerable_final"].fillna(False).sum()),
        "normalization_sensitive_rows": int(out["normalization_sensitive_flag"].sum()),
        "definition": (
            "robust_core_hidden_flag requires hidden vulnerable under baseline minmax, "
            "winsorized cost, log1p cost, and rank cost variants."
        ),
    }
    return out, gdf, summary


def build_hidden_admin_burden_summary(robust_csv: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hidden-candidate environment burden by admin label."""
    label_cols = ["district_name", "admin_name", "admin_code"]
    labeled = robust_csv.dropna(subset=["district_name", "admin_name"]).copy()
    if labeled.empty:
        return pd.DataFrame(columns=label_cols)
    return (
        labeled.groupby(label_cols, dropna=False)
        .agg(
            candidate_hex_count=("hex_id", "count"),
            robust_core_hidden_count=("robust_core_hidden_flag", "sum"),
            normalization_sensitive_count=("normalization_sensitive_flag", "sum"),
            registered_population_sum=("registered_population", "sum"),
            registered_senior_population_sum=("registered_senior_population", "sum"),
            mean_delta_cost_m3_minus_m0=("delta_cost_m3_minus_m0", "mean"),
            p90_delta_cost_m3_minus_m0=(
                "delta_cost_m3_minus_m0",
                lambda s: float(pd.to_numeric(s, errors="coerce").quantile(0.90)),
            ),
            mean_delta_pct_m3_over_m0=("delta_pct_m3_over_m0", "mean"),
        )
        .reset_index()
        .sort_values(
            ["robust_core_hidden_count", "candidate_hex_count", "registered_senior_population_sum"],
            ascending=False,
        )
    )


def build_quadrants(
    hex_df: pd.DataFrame, hex_gdf: gpd.GeoDataFrame
) -> tuple[pd.DataFrame, gpd.GeoDataFrame, dict[str, Any]]:
    valid = hex_df["analysis_valid_final"].fillna(False).astype(bool)
    work = hex_df.loc[valid].copy()
    work["cost_quartile"] = qcut_labels(work["access_cost_m3"], ["C1_low", "C2", "C3", "C4_high"])
    work["demand_quartile"] = qcut_labels(
        work["demand_index_final"], ["D1_low", "D2", "D3", "D4_high"]
    )
    work["high_cost_flag"] = work["cost_quartile"].astype(str).eq("C4_high")
    work["high_demand_flag"] = work["demand_quartile"].astype(str).eq("D4_high")
    work["quadrant_label"] = np.select(
        [
            work["high_cost_flag"] & work["high_demand_flag"],
            work["high_cost_flag"] & ~work["high_demand_flag"],
            ~work["high_cost_flag"] & work["high_demand_flag"],
        ],
        ["high_cost_high_demand", "high_cost_lower_demand", "lower_cost_high_demand"],
        default="lower_cost_lower_demand",
    )

    matrix = (
        work.groupby(["cost_quartile", "demand_quartile"], observed=False)
        .agg(
            hex_count=("hex_id", "count"),
            vulnerable_count=("vulnerable_m3_final", "sum"),
            hidden_count=("hidden_vulnerable_final", "sum"),
            registered_population_sum=("registered_population", "sum"),
            registered_senior_population_sum=("registered_senior_population", "sum"),
            mean_access_cost_m3=("access_cost_m3", "mean"),
            mean_demand_index_final=("demand_index_final", "mean"),
        )
        .reset_index()
    )
    matrix["hidden_share"] = matrix["hidden_count"] / matrix["hex_count"]

    quadrant_cols = [
        "hex_id",
        "access_cost_m3",
        "demand_index_final",
        "vulnerability_m3_final",
        "vulnerable_m3_final",
        "hidden_vulnerable_final",
        "cost_quartile",
        "demand_quartile",
        "quadrant_label",
        "registered_population",
        "registered_senior_population",
    ]
    gdf = hex_gdf[["hex_id", "geometry"]].merge(work[quadrant_cols], on="hex_id", how="inner")
    summary = {
        "valid_hex_rows": int(len(work)),
        "high_cost_high_demand_hex_rows": int(
            (work["quadrant_label"] == "high_cost_high_demand").sum()
        ),
        "high_cost_high_demand_hidden_rows": int(
            (
                (work["quadrant_label"] == "high_cost_high_demand")
                & work["hidden_vulnerable_final"].fillna(False)
            ).sum()
        ),
        "purpose": "Expose cost and demand axes directly without relying on product-score normalization.",
    }
    return matrix, gdf, summary


def build_m0_m3_environment_burden(
    hex_df: pd.DataFrame,
    hex_gdf: gpd.GeoDataFrame,
) -> tuple[pd.DataFrame, gpd.GeoDataFrame, dict[str, Any], dict[str, Any]]:
    """Compare pure distance (M0) with slope-weather cost (M3).

    This is the repair for the 0.9947 concern.  A high rank correlation means
    M3 does not reorder Seoul-wide accessibility very much, but it can still
    increase generalized walking cost, push some hexes past a fixed burden
    threshold, and expose where the 400m rule is optimistic.
    """
    valid = hex_df["analysis_valid_final"].fillna(False).astype(bool)
    work = hex_df.loc[valid].copy()

    m0 = work["access_cost_m0"]
    m3 = work["access_cost_m3"]
    demand = work["demand_index_final"]
    population = work["registered_population"]
    senior_population = work["registered_senior_population"]

    frozen = FrozenBaseline.fit(m0, demand)
    base_vulnerability = pd.Series(frozen.vulnerability(m0, demand), index=work.index)
    scenario_vulnerability = pd.Series(frozen.vulnerability(m3, demand), index=work.index)
    base_mask = pd.Series(frozen.vulnerable_mask(m0, demand), index=work.index)
    scenario_mask = pd.Series(frozen.vulnerable_mask(m3, demand), index=work.index)

    # M0 and M3 were produced as separate Dijkstra runs upstream.  Rank shift is
    # therefore a route-cost comparison, not just a post-hoc multiplier check.
    m0_rank = m0.rank(method="average")
    m3_rank = m3.rank(method="average")

    out = work[
        [
            "hex_id",
            "access_cost_m0",
            "access_cost_m3",
            "cost_gap_m3_minus_m0",
            "cost_gap_ratio_m3_over_m0",
            "official_400m_ok_m0",
            "hidden_vulnerable_final",
            "registered_population",
            "registered_senior_population",
            "demand_index_final",
        ]
    ].copy()
    out["m0_rank"] = m0_rank
    out["m3_rank"] = m3_rank
    out["rank_shift_m3_minus_m0"] = m3_rank - m0_rank
    out["abs_rank_shift_m0_m3"] = out["rank_shift_m3_minus_m0"].abs()
    out["m0_frozen_vulnerability"] = base_vulnerability
    out["m3_under_m0_frozen_vulnerability"] = scenario_vulnerability
    out["delta_vulnerability_m3_minus_m0"] = scenario_vulnerability - base_vulnerability
    out["m0_frozen_vulnerable"] = base_mask
    out["m3_under_m0_frozen_vulnerable"] = scenario_mask
    out["new_environment_burden_vulnerable"] = ~base_mask & scenario_mask
    out["resolved_environment_burden_vulnerable"] = base_mask & ~scenario_mask
    out["m0_400_to_m3_over_400"] = (m0 <= 400) & (m3 > 400)
    out["diagnostic_label"] = np.select(
        [
            out["new_environment_burden_vulnerable"],
            out["m0_400_to_m3_over_400"],
            out["hidden_vulnerable_final"],
        ],
        [
            "threshold_crossing_under_environment_cost",
            "distance_standard_crossing",
            "hidden_vulnerable_under_m3_threshold",
        ],
        default="no_crossing",
    )

    gdf = hex_gdf[["hex_id", "geometry"]].merge(out, on="hex_id", how="inner")

    evaluation = evaluate_scenario(
        baseline_cost=m0,
        scenario_cost=m3,
        demand=demand,
        population=population,
        senior_population=senior_population,
        frozen_baseline=frozen,
        scenario_name="M0_to_M3_environment_burden",
    )
    summary = {
        "diagnostic_id": "E0_m0_to_m3_environment_burden",
        "interpretation": (
            "M3 does not strongly reorder M0 ranks, but it increases generalized "
            "walking cost and identifies threshold-crossing burden candidates."
        ),
        "rank_spearman_m0_m3": round(float(m0_rank.corr(m3_rank, method="pearson")), 6),
        "rank_pearson_m0_m3": round(float(m0.corr(m3, method="pearson")), 6),
        "valid_hex_rows": int(len(work)),
        "mean_delta_cost_m": round(float((m3 - m0).mean()), 6),
        "median_delta_cost_m": round(float((m3 - m0).median()), 6),
        "p90_delta_cost_m": round(float((m3 - m0).quantile(0.90)), 6),
        "mean_cost_increase_rate": round(float((m3.mean() - m0.mean()) / m0.mean()), 6),
        "population_weighted_cost_increase_rate": round(
            (weighted_average(m3, population) - weighted_average(m0, population))
            / weighted_average(m0, population),
            6,
        ),
        "senior_weighted_cost_increase_rate": round(
            (weighted_average(m3, senior_population) - weighted_average(m0, senior_population))
            / weighted_average(m0, senior_population),
            6,
        ),
        "abs_rank_shift_p90": round(float(out["abs_rank_shift_m0_m3"].quantile(0.90)), 6),
        "abs_rank_shift_p95": round(float(out["abs_rank_shift_m0_m3"].quantile(0.95)), 6),
        "abs_rank_shift_ge_100_count": int((out["abs_rank_shift_m0_m3"] >= 100).sum()),
        "m0_400_to_m3_over_400_count": int(out["m0_400_to_m3_over_400"].sum()),
        "m0_400_to_m3_over_400_hidden_count": int(
            (out["m0_400_to_m3_over_400"] & out["hidden_vulnerable_final"]).sum()
        ),
        "m0_frozen_vulnerable_count": int(base_mask.sum()),
        "m3_under_m0_frozen_vulnerable_count": int(scenario_mask.sum()),
        "new_environment_burden_vulnerable_count": int(
            out["new_environment_burden_vulnerable"].sum()
        ),
        "new_environment_burden_registered_population_sum": round(
            float(out.loc[out["new_environment_burden_vulnerable"], "registered_population"].sum()),
            6,
        ),
        "new_environment_burden_registered_senior_population_sum": round(
            float(
                out.loc[
                    out["new_environment_burden_vulnerable"],
                    "registered_senior_population",
                ].sum()
            ),
            6,
        ),
        "evaluation": evaluation.to_dict(),
        "claim_boundary": (
            "Allowed: environment-cost burden diagnostic / accessibility burden forecast. "
            "Not allowed: ridership demand forecast or policy intervention effect."
        ),
    }
    manifest = {
        "scenario_id": "E0_m0_to_m3_environment_burden_20260531",
        "canonical_scenario": "environment_cost_added_to_pure_distance",
        "legacy_name": None,
        "run_timestamp": "2026-05-31",
        "code_version_id": "workspace",
        "changed_cost_term": ["slope_penalty", "weather_factor", "slope_weather_interaction"],
        "unchanged_cost_term": ["demand_index_final", "registered_population"],
        "baseline_cost_column": "access_cost_m0",
        "scenario_cost_column": "access_cost_m3",
        "baseline_demand_column": "demand_index_final",
        "scenario_demand_created": False,
        "fixed_normalization_universe": "analysis_valid_final",
        "fixed_threshold_universe": "M0 frozen baseline over analysis_valid_final",
        "baseline_row_count": int(len(work)),
        "scenario_row_count": int(len(work)),
        "hex_id_set_equal": True,
        "path_research_run": True,
        "effect_output_label": "environment_burden_diagnostic",
        "baseline_cost_hash": frame_hash(out, ["hex_id", "access_cost_m0"]),
        "scenario_cost_hash": frame_hash(out, ["hex_id", "access_cost_m3"]),
        "baseline_demand_hash": frame_hash(out, ["hex_id", "demand_index_final"]),
        "scenario_demand_hash": frame_hash(out, ["hex_id", "demand_index_final"]),
        "output_path": "outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.csv",
        "notes": (
            "This manifest supports an accessibility-burden diagnostic comparing M0 and M3. "
            "It is not a policy intervention effect and not a ridership demand forecast."
        ),
    }
    return out, gdf, summary, manifest


def build_s4_admin_qa() -> dict[str, Any]:
    s4_csv_path = ROOT / "scenario3_weather_response_top20.csv"
    s4_gpkg_path = QGIS_DIR / "scenario3_weather_response_top20.gpkg"
    fixed_path = QGIS_DIR / "scenario3_weather_response_top20_admin_fixed.gpkg"

    s4_csv = pd.read_csv(s4_csv_path)
    s4_gdf = gpd.read_file(s4_gpkg_path, layer="scenario3_weather_response_top20")

    label_cols = ["district_name", "admin_name", "admin_code"]
    label_lookup = s4_csv[["hex_id", *label_cols]].drop_duplicates("hex_id")
    fixed = s4_gdf.drop(columns=[c for c in label_cols if c in s4_gdf.columns]).merge(
        label_lookup, on="hex_id", how="left"
    )
    fixed = gpd.GeoDataFrame(fixed, geometry="geometry", crs=s4_gdf.crs)
    overwrite_gpkg(fixed, fixed_path, "scenario3_weather_response_top20_admin_fixed")

    before = {f"gpkg_before_{c}_nulls": int(s4_gdf[c].isna().sum()) for c in label_cols}
    after = {f"fixed_{c}_nulls": int(fixed[c].isna().sum()) for c in label_cols}
    csv_nulls = {f"csv_{c}_nulls": int(s4_csv[c].isna().sum()) for c in label_cols}
    qa = {
        "csv_path": str(s4_csv_path.relative_to(ROOT)),
        "gpkg_path": str(s4_gpkg_path.relative_to(ROOT)),
        "fixed_gpkg_path": str(fixed_path.relative_to(ROOT)),
        "csv_rows": int(len(s4_csv)),
        "gpkg_rows": int(len(s4_gdf)),
        "fixed_rows": int(len(fixed)),
        **csv_nulls,
        **before,
        **after,
        "csv_label_ready": all(value == 0 for value in csv_nulls.values()),
        "original_gpkg_label_ready": all(value == 0 for value in before.values()),
        "fixed_gpkg_label_ready": all(value == 0 for value in after.values()),
        "interpretation": (
            "CSV already carries admin labels; original GPKG label columns are repaired "
            "into the fixed QGIS layer for map labeling."
        ),
    }
    return qa


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_data_loss_ledger(
    hex_df: pd.DataFrame,
    diagnostics: pd.DataFrame,
    s4_qa: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    demand_qa = load_json(ROOT / "outputs" / "reports" / "hex_demand_features_final_qa.json")
    vuln_qa = load_json(ROOT / "outputs" / "reports" / "hex_vulnerability_final_audit.json")
    admin_qa = load_json(ROOT / "outputs" / "reports" / "admin_dong_seoul_qa.json")
    registered_layer_qa = load_json(
        ROOT / "outputs" / "reports" / "registered_population_admin_layer_qa.json"
    )
    living_join_qa = load_json(ROOT / "outputs" / "reports" / "livingpop_250m_join_qa.json")
    accessibility_qa = load_json(ROOT / "outputs" / "reports" / "hex_accessibility_prelim_qa.json")
    mobility_qa = load_json(ROOT / "outputs" / "reports" / "life_mobility_od_aux_qa.json")
    hidden_qa = load_json(
        ROOT / "outputs" / "reports" / "hidden_vulnerability_reason_diagnostics_qa.json"
    )

    edge_input_rows = edge_output_rows = edge_drop_rows = None
    edge_drop_reason = "not recomputed"
    edge_source = ROOT / "data" / "walking_network_edges_with_slope_google.csv"
    edge_costs = ROOT / "data" / "interim" / "walking_edge_costs.parquet"
    if edge_source.exists() and edge_costs.exists():
        edge_grades = pd.read_csv(edge_source, usecols=["grade_abs_percent"])
        edge_input_rows = int(len(edge_grades))
        edge_output_rows = int(len(pd.read_parquet(edge_costs, columns=["u"])))
        missing_grade = int(edge_grades["grade_abs_percent"].isna().sum())
        over_100 = int((edge_grades["grade_abs_percent"] > 100).sum())
        edge_drop_rows = edge_input_rows - edge_output_rows
        edge_drop_reason = (
            f"missing grade_abs_percent={missing_grade}; grade_abs_percent>100={over_100}; "
            "30-100% grades are capped, not dropped"
        )

    local_resident_summary = ROOT / "data" / "interim" / "local_resident_250m_grid_summary.parquet"
    living_observed_rows = living_summary_rows = None
    if local_resident_summary.exists():
        local_resident = pd.read_parquet(local_resident_summary, columns=["observed_rows"])
        living_observed_rows = int(local_resident["observed_rows"].sum())
        living_summary_rows = int(len(local_resident))

    def row(
        stage: str,
        input_rows: Any,
        output_rows: Any,
        loss_rows: Any,
        row_change_type: str,
        qa_status: str,
        reason: str,
        evidence: str,
    ) -> dict[str, Any]:
        return {
            "stage": stage,
            "input_rows": input_rows,
            "output_rows": output_rows,
            "loss_rows": loss_rows,
            "row_change_type": row_change_type,
            "qa_status": qa_status,
            "reason": reason,
            "evidence": evidence,
        }

    rows = [
        row(
            "walking_network_edge_costs",
            edge_input_rows,
            edge_output_rows,
            edge_drop_rows,
            "filter_then_cost_cap",
            "documented",
            edge_drop_reason,
            "data/walking_network_edges_with_slope_google.csv; data/interim/walking_edge_costs.parquet",
        ),
        row(
            "admin_boundary_seoul_subset",
            admin_qa.get("national_feature_count"),
            admin_qa.get("seoul_feature_count"),
            None,
            "spatial_subset_not_loss",
            "documented",
            "National admin boundary is subset to Seoul for project scope.",
            "outputs/reports/admin_dong_seoul_qa.json",
        ),
        row(
            "registered_population_admin_alias_join",
            registered_layer_qa.get("registered_population_input_rows"),
            registered_layer_qa.get("registered_population_join_rows"),
            0,
            "alias_merge_population_preserved",
            registered_layer_qa.get("status", "unknown"),
            (
                "Population rows are merged to boundary keys; registered and senior population sums "
                "are preserved."
            ),
            "outputs/reports/registered_population_admin_layer_qa.json",
        ),
        row(
            "living_population_250m_summary",
            living_observed_rows,
            living_summary_rows,
            None,
            "temporal_rows_aggregated_to_grid",
            "documented",
            "Raw monthly/hourly observations are summarized by 250m grid.",
            "data/interim/local_resident_250m_grid_summary.parquet",
        ),
        row(
            "living_population_250m_polygon_join",
            living_join_qa.get("summary_grid_count"),
            living_join_qa.get("joined_grid_count"),
            living_join_qa.get("summary_not_in_grid_count"),
            "join_gap_plus_zero_population_polygons",
            "documented",
            (
                f"grid_without_population={living_join_qa.get('grid_without_population_count')}; "
                f"summary_not_in_grid={living_join_qa.get('summary_not_in_grid_count')}"
            ),
            "outputs/reports/livingpop_250m_join_qa.json",
        ),
        row(
            "final_demand_h3",
            demand_qa.get("hex_count"),
            len(hex_df),
            0,
            "hex_rows_preserved",
            demand_qa.get("status", "unknown"),
            (
                f"nonzero_living={demand_qa.get('nonzero_living_hex_count')}; "
                f"nonzero_registered={demand_qa.get('nonzero_registered_hex_count')}; "
                f"nonzero_poi={demand_qa.get('nonzero_poi_hex_count')}"
            ),
            "outputs/reports/hex_demand_features_final_qa.json",
        ),
        row(
            "life_mobility_od_aux",
            mobility_qa.get("input_row_count"),
            mobility_qa.get("admin_code_count"),
            0,
            "auxiliary_aggregation_not_final_demand",
            mobility_qa.get("status", "unknown"),
            (
                "OD is kept as auxiliary, not mixed into final demand. "
                f"used_rows={mobility_qa.get('used_row_count')}; "
                f"unmatched_origin={mobility_qa.get('unmatched_origin_seoul_code_count')}; "
                f"unmatched_destination={mobility_qa.get('unmatched_destination_seoul_code_count')}"
            ),
            "outputs/reports/life_mobility_od_aux_qa.json",
        ),
        row(
            "accessibility_m0_m3",
            accessibility_qa.get("hex_count"),
            accessibility_qa.get("access_cost_m3_reachable_count"),
            (
                accessibility_qa.get("hex_count")
                - accessibility_qa.get("access_cost_m3_reachable_count")
                if accessibility_qa.get("hex_count") is not None
                and accessibility_qa.get("access_cost_m3_reachable_count") is not None
                else None
            ),
            "snap_invalid_or_unreachable",
            "documented",
            (
                f"origin_snap_valid={accessibility_qa.get('origin_snap_valid_count')}; "
                f"origin_snap_invalid={accessibility_qa.get('origin_snap_invalid_count')}; "
                f"unreachable_after_snap="
                f"{accessibility_qa.get('origin_snap_valid_count') - accessibility_qa.get('access_cost_m3_reachable_count')}"
                if accessibility_qa.get("origin_snap_valid_count") is not None
                and accessibility_qa.get("access_cost_m3_reachable_count") is not None
                else f"d_snap_invalid={accessibility_qa.get('d_snap_invalid_count')}"
            ),
            "outputs/reports/hex_accessibility_prelim_qa.json",
        ),
        row(
            "analysis_valid_final",
            len(hex_df),
            int(hex_df["analysis_valid_final"].fillna(False).sum()),
            int((~hex_df["analysis_valid_final"].fillna(False).astype(bool)).sum()),
            "analysis_universe_filter",
            vuln_qa.get("status", "unknown"),
            "Rows outside analysis-valid universe are retained in table but excluded from final score.",
            "outputs/reports/hex_vulnerability_final_audit.json",
        ),
        row(
            "vulnerable_m3_final",
            int(hex_df["analysis_valid_final"].fillna(False).sum()),
            int(hex_df["vulnerable_m3_final"].fillna(False).sum()),
            None,
            "top_fraction_threshold_not_loss",
            "top_20_percent_threshold",
            "Policy screening threshold; not row loss.",
            "data/derived/hex_vulnerability_final.parquet",
        ),
        row(
            "hidden_vulnerability_diagnostics",
            hidden_qa.get("hidden_vulnerable_count"),
            len(diagnostics),
            int(hex_df["hidden_vulnerable_final"].fillna(False).sum()) - len(diagnostics),
            "filtered_diagnostic_subset",
            "admin_labels_present"
            if diagnostics[["district_name", "admin_name"]].notna().all().all()
            else "admin_label_gap",
            "Hidden vulnerable detail table used for reason diagnostics.",
            "outputs/reports/hidden_vulnerability_reason_diagnostics_qa.json",
        ),
        row(
            "s4_weather_response_top20_fixed_gpkg",
            s4_qa["csv_rows"],
            s4_qa["fixed_rows"],
            s4_qa["csv_rows"] - s4_qa["fixed_rows"],
            "label_repair_no_row_loss",
            "map_label_ready" if s4_qa["fixed_gpkg_label_ready"] else "label_gap",
            "QGIS layer repaired from CSV admin labels.",
            "outputs/reports/v2_2_execution/s4_top20_admin_label_qa.json",
        ),
    ]
    ledger = pd.DataFrame(rows)
    summary = {
        "hex_rows": int(len(hex_df)),
        "analysis_valid_rows": int(hex_df["analysis_valid_final"].fillna(False).sum()),
        "vulnerable_rows": int(hex_df["vulnerable_m3_final"].fillna(False).sum()),
        "hidden_rows": int(hex_df["hidden_vulnerable_final"].fillna(False).sum()),
        "diagnostics_rows": int(len(diagnostics)),
        "ledger_rows": int(len(ledger)),
        "s4_fixed_gpkg_label_ready": bool(s4_qa["fixed_gpkg_label_ready"]),
        "notes": "Threshold stages are marked separately from true data loss.",
    }
    return ledger, summary


def build_scenario_registry(s4_qa: dict[str, Any]) -> pd.DataFrame:
    paths = {
        "E0": REPORT_DIR / "m0_m3_environment_burden_effect.csv",
        "S1": QGIS_DIR / "S1_delta_vulnerability_map.gpkg",
        "S3": QGIS_DIR / "S2_s3_effect_categories.gpkg",
        "S4": QGIS_DIR / "scenario3_weather_response_top20_admin_fixed.gpkg",
    }
    rows = [
        {
            "scenario_id": "E0",
            "scenario_name": "m0_to_m3_environment_burden",
            "primary_output": str(paths["E0"].relative_to(ROOT)),
            "output_exists": paths["E0"].exists(),
            "diagnostic_or_effect": "environment_burden_diagnostic",
            "counterfactual_effect_claim_allowed": True,
            "requires_before_effect_claim": (
                "Use only as accessibility-burden effect, not policy intervention or ridership demand effect"
            ),
            "allowed_wording": (
                "경사·기상 반영 시 접근비용/취약도 부담이 증가하는 후보를 진단"
            ),
        },
        {
            "scenario_id": "S1",
            "scenario_name": "candidate_stop_upper_bound",
            "primary_output": str(paths["S1"].relative_to(ROOT)),
            "output_exists": paths["S1"].exists(),
            "diagnostic_or_effect": "diagnostic_upper_bound",
            "counterfactual_effect_claim_allowed": False,
            "requires_before_effect_claim": (
                "runner manifest, scenario cost hash, threshold hash, and path re-search evidence"
            ),
            "allowed_wording": "정류장 신설/이전/접근로 개선 현장검토 후보 또는 상한선 스크리닝",
        },
        {
            "scenario_id": "S3",
            "scenario_name": "effect_category_diagnosis",
            "primary_output": str(paths["S3"].relative_to(ROOT)),
            "output_exists": paths["S3"].exists(),
            "diagnostic_or_effect": "diagnostic_category_table",
            "counterfactual_effect_claim_allowed": False,
            "requires_before_effect_claim": "FrozenBaseline-linked delta output and scenario manifest",
            "allowed_wording": "개입 효과 확정보다 원인/범주 진단",
        },
        {
            "scenario_id": "S4",
            "scenario_name": "weather_response_top20",
            "primary_output": str(paths["S4"].relative_to(ROOT)),
            "output_exists": paths["S4"].exists(),
            "diagnostic_or_effect": "candidate_priority_table",
            "counterfactual_effect_claim_allowed": False,
            "requires_before_effect_claim": "evaluate_scenario runner, delta vulnerability, and map-label QA",
            "allowed_wording": "기상 대응 현장검토 Top20 우선순위",
            "admin_label_ready": s4_qa["fixed_gpkg_label_ready"],
        },
        {
            "scenario_id": "M4",
            "scenario_name": "senior_impedance",
            "primary_output": "",
            "output_exists": False,
            "diagnostic_or_effect": "method_design_only",
            "counterfactual_effect_claim_allowed": False,
            "requires_before_effect_claim": (
                "cost_m4_senior edge table, Dijkstra re-search, profile sensitivity, and M4 vulnerability table"
            ),
            "allowed_wording": "고령자 전용 접근비용은 설계/후속 구현 대상으로만 표현",
            "admin_label_ready": None,
        },
    ]
    return pd.DataFrame(rows)


def write_summary(
    robustness: pd.DataFrame,
    robust_summary: dict[str, Any],
    environment_summary: dict[str, Any],
    quadrant_summary: dict[str, Any],
    ledger_summary: dict[str, Any],
    s4_qa: dict[str, Any],
) -> None:
    summary_path = REPORT_DIR / "v2_2_execution_summary.md"
    top_rows = "\n".join(
        [
            "| variant | hidden_hex_count | hidden_replacement_rate | claim_use |",
            "|---|---:|---:|---|",
            *[
                (
                    f"| {row.variant} | {int(row.hidden_hex_count):,} | "
                    f"{row.hidden_replacement_rate:.3f} | {row.claim_use} |"
                )
                for row in robustness[
                    [
                        "variant",
                        "hidden_hex_count",
                        "hidden_replacement_rate",
                        "claim_use",
                    ]
                ].itertuples(index=False)
            ],
        ]
    )
    text = f"""# v2.2 Execution Summary

Date: 2026-05-31

## Claim Boundary

These artifacts support potential-accessibility burden screening and field-review prioritization.
They do not support realized ridership demand prediction or policy-intervention effect claims.

## Core Counts

- Valid hex: {ledger_summary['analysis_valid_rows']:,}
- M3 vulnerable hex: {ledger_summary['vulnerable_rows']:,}
- Hidden vulnerable hex: {ledger_summary['hidden_rows']:,}
- Robust-core hidden hex: {robust_summary['robust_core_hidden_rows']:,}
- Normalization-sensitive hidden candidates: {robust_summary['normalization_sensitive_rows']:,}

## M0 to M3 Environment Burden

- M0-M3 Spearman: {environment_summary['rank_spearman_m0_m3']:.6f}
- Mean cost increase: {environment_summary['mean_cost_increase_rate']:.1%}
- Senior-weighted cost increase: {environment_summary['senior_weighted_cost_increase_rate']:.1%}
- M0 <= 400m but M3 > 400m: {environment_summary['m0_400_to_m3_over_400_count']:,}
- New vulnerable under frozen M0 threshold: {environment_summary['new_environment_burden_vulnerable_count']:,}

## Robustness Table

{top_rows}

## Quadrant

- Valid rows: {quadrant_summary['valid_hex_rows']:,}
- High-cost and high-demand rows: {quadrant_summary['high_cost_high_demand_hex_rows']:,}
- High-cost and high-demand hidden rows: {quadrant_summary['high_cost_high_demand_hidden_rows']:,}

## S4 Admin Label QA

- CSV label ready: {s4_qa['csv_label_ready']}
- Original GPKG label ready: {s4_qa['original_gpkg_label_ready']}
- Fixed GPKG label ready: {s4_qa['fixed_gpkg_label_ready']}
- Fixed GPKG: `{s4_qa['fixed_gpkg_path']}`

## Files

- `outputs/reports/v2_2_execution/normalization_combination_threshold_robustness.csv`
- `outputs/reports/v2_2_execution/hidden_vulnerable_robust_core.csv`
- `qgis/hidden_vulnerable_robust_core.gpkg`
- `outputs/reports/v2_2_execution/quadrant_4x4_matrix.csv`
- `qgis/quadrant_primary_output.gpkg`
- `outputs/reports/v2_2_execution/data_loss_ledger_v2_2.csv`
- `outputs/reports/v2_2_execution/scenario_effect_registry_v2_2.csv`
- `outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.csv`
- `qgis/m0_m3_environment_burden_shift.gpkg`
- `outputs/reports/v2_2_execution/s4_top20_admin_label_qa.json`
"""
    summary_path.write_text(text, encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    hex_df = pd.read_parquet(ROOT / "data" / "derived" / "hex_vulnerability_final.parquet")
    hex_gdf = gpd.read_file(QGIS_DIR / "out_hex_vulnerability_final.gpkg")
    diagnostics = pd.read_csv(ROOT / "outputs" / "reports" / "hidden_vulnerability_reason_diagnostics.csv")

    robustness, flags = build_variant_table(hex_df)
    write_csv(REPORT_DIR / "normalization_combination_threshold_robustness.csv", robustness)
    write_json(
        REPORT_DIR / "normalization_combination_threshold_robustness.json",
        {
            "rows": robustness.to_dict(orient="records"),
            "note": "Deterministic variant sensitivity; Monte Carlo was not used.",
        },
    )

    robust_csv, robust_gdf, robust_summary = build_robust_core(
        hex_df, hex_gdf, flags, diagnostics
    )
    write_csv(REPORT_DIR / "hidden_vulnerable_robust_core.csv", robust_csv)
    write_csv(
        REPORT_DIR / "hidden_environment_burden_admin_summary.csv",
        build_hidden_admin_burden_summary(robust_csv),
    )
    overwrite_gpkg(
        robust_gdf,
        QGIS_DIR / "hidden_vulnerable_robust_core.gpkg",
        "hidden_vulnerable_robust_core",
    )
    write_json(REPORT_DIR / "hidden_vulnerable_robust_core_summary.json", robust_summary)

    environment_csv, environment_gdf, environment_summary, environment_manifest = (
        build_m0_m3_environment_burden(hex_df, hex_gdf)
    )
    write_csv(REPORT_DIR / "m0_m3_environment_burden_effect.csv", environment_csv)
    overwrite_gpkg(
        environment_gdf,
        QGIS_DIR / "m0_m3_environment_burden_shift.gpkg",
        "m0_m3_environment_burden_shift",
    )
    write_json(REPORT_DIR / "m0_m3_environment_burden_effect.json", environment_summary)
    write_json(
        REPORT_DIR / "m0_m3_environment_burden_effect.manifest.json",
        environment_manifest,
    )

    quadrant_matrix, quadrant_gdf, quadrant_summary = build_quadrants(hex_df, hex_gdf)
    write_csv(REPORT_DIR / "quadrant_4x4_matrix.csv", quadrant_matrix)
    overwrite_gpkg(quadrant_gdf, QGIS_DIR / "quadrant_primary_output.gpkg", "quadrant_primary")
    write_json(REPORT_DIR / "quadrant_primary_summary.json", quadrant_summary)

    s4_qa = build_s4_admin_qa()
    write_json(REPORT_DIR / "s4_top20_admin_label_qa.json", s4_qa)
    write_csv(
        REPORT_DIR / "s4_top20_admin_label_qa.csv",
        pd.DataFrame([s4_qa]),
    )

    ledger, ledger_summary = build_data_loss_ledger(hex_df, diagnostics, s4_qa)
    write_csv(REPORT_DIR / "data_loss_ledger_v2_2.csv", ledger)
    write_json(REPORT_DIR / "data_loss_ledger_v2_2.json", ledger_summary)

    registry = build_scenario_registry(s4_qa)
    write_csv(REPORT_DIR / "scenario_effect_registry_v2_2.csv", registry)
    write_json(
        REPORT_DIR / "scenario_effect_registry_v2_2.json",
        {"rows": registry.to_dict(orient="records")},
    )

    write_summary(
        robustness,
        robust_summary,
        environment_summary,
        quadrant_summary,
        ledger_summary,
        s4_qa,
    )

    print(
        json.dumps(
            {
                "report_dir": str(REPORT_DIR.relative_to(ROOT)),
                "valid_hex": ledger_summary["analysis_valid_rows"],
                "hidden_hex": ledger_summary["hidden_rows"],
                "robust_core_hidden": robust_summary["robust_core_hidden_rows"],
                "m0_m3_spearman": environment_summary["rank_spearman_m0_m3"],
                "new_environment_burden_vulnerable": environment_summary[
                    "new_environment_burden_vulnerable_count"
                ],
                "s4_fixed_gpkg_label_ready": s4_qa["fixed_gpkg_label_ready"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
