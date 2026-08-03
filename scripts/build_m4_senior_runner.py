"""M4-senior 고령자 보행 임피던스 runner.

v2.2 §0-quater 설계대로 기상 3프로필 × 계단 3정책 = 9개 변형에 대해
edge 통과시간(minutes) 기반 multi-source Dijkstra를 다시 돌리고,
속도 4프로필은 경로 불변 성질을 이용해 시간만 비례 환산한다.

이 runner는 downstream 산출물 생성기다. M0-M3 production 컬럼은 건드리지 않는다.
M4 계수들은 보정계수가 아니라 profile scenario parameter이며, 결과는
"고령자 실측 보행시간"이 아니라 profile 민감도 묶음으로 보고해야 한다.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd

from sl_accessibility.accessibility.routing import read_network_nodes, snap_points_to_nodes
from sl_accessibility.accessibility.scenario import FrozenBaseline
from sl_accessibility.accessibility.senior_cost import (
    SENIOR_SPEED_PROFILES_M_PER_S,
    STEP_PENALTY_FACTOR,
    STEP_POLICIES,
    WEATHER_PROFILES,
    SeniorCostParameters,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "reports" / "m4_senior"
QGIS_DIR = ROOT / "qgis"
CRS_METRIC = "EPSG:5179"
VULNERABLE_QUANTILE = 0.8
REFERENCE_SPEED = "base"  # 0.90 m/s
REFERENCE_WEATHER = "rain"  # M3 기준선(rain_mm=2)과 정렬
REFERENCE_STEP_POLICY = "steps_penalty"
EPS_MIN = 1e-9


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


def spearman(left: pd.Series, right: pd.Series) -> float:
    lr = pd.to_numeric(left, errors="coerce").rank(method="average")
    rr = pd.to_numeric(right, errors="coerce").rank(method="average")
    return float(lr.corr(rr, method="pearson"))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return float("nan")
    return len(a & b) / len(a | b)


def load_hex_frame() -> pd.DataFrame:
    hex_df = pd.read_parquet(ROOT / "data" / "derived" / "hex_vulnerability_final.parquet")
    valid = hex_df["analysis_valid_final"].fillna(False).astype(bool)
    hex_df = hex_df.loc[valid].copy()
    hex_df["origin_node_id"] = pd.to_numeric(hex_df["origin_node_id"], errors="coerce")
    hex_df = hex_df.loc[
        hex_df["origin_node_id"].notna()
        & hex_df["access_cost_m0"].notna()
        & hex_df["access_cost_m3"].notna()
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


def build_edge_components(params: SeniorCostParameters) -> pd.DataFrame:
    """edge별 M4 구성요소(base time, slope factor, steps 여부)를 벡터화로 만든다."""
    edges = pd.read_parquet(
        ROOT / "data" / "interim" / "walking_edge_costs.parquet",
        columns=["u", "v", "length_m", "grade_percent", "grade_abs_percent", "highway"],
    )
    edges["u"] = pd.to_numeric(edges["u"], errors="coerce").astype(np.int64)
    edges["v"] = pd.to_numeric(edges["v"], errors="coerce").astype(np.int64)
    length = pd.to_numeric(edges["length_m"], errors="coerce").to_numpy(dtype=float)
    grade_signed = pd.to_numeric(edges["grade_percent"], errors="coerce").to_numpy(dtype=float)
    grade_abs = pd.to_numeric(edges["grade_abs_percent"], errors="coerce").to_numpy(dtype=float)

    # 부호 있는 경사를 우선 사용하고, 결측이면 절대경사로 보수적 fallback한다.
    signed_missing = np.isnan(grade_signed)
    grade_used = np.where(signed_missing, grade_abs, grade_signed)

    cap = params.slope_cap_percent
    s = np.clip(grade_used, -cap, cap) / 100.0
    tobler_time = np.exp(params.tobler_scale * (np.abs(s + params.tobler_offset) - params.tobler_offset))
    slope_factor = np.maximum(1.0, tobler_time)

    edges["senior_base_time_min"] = length / (params.flat_speed_m_per_s * 60.0)
    edges["senior_slope_factor"] = slope_factor
    edges["signed_grade_fallback_abs"] = signed_missing
    edges["is_steps_edge"] = edges["highway"].astype(str).str.lower().str.contains("steps", na=False)
    edges["base_slope_time_min"] = edges["senior_base_time_min"] * edges["senior_slope_factor"]
    return edges


def variant_edge_weights(
    edges: pd.DataFrame,
    *,
    weather_profile: str,
    step_policy: str,
) -> pd.DataFrame:
    profile = WEATHER_PROFILES[weather_profile]
    weather_factor = 1.0 + profile["beta_weather"] * profile["intensity"]
    work = edges
    if step_policy == "steps_barrier":
        # barrier: steps edge를 보행망에서 제거해 도달 불가/우회를 강제한다.
        work = edges.loc[~edges["is_steps_edge"]]
        step_factor = 1.0
        weight = work["base_slope_time_min"] * weather_factor * step_factor
    elif step_policy == "steps_penalty":
        step_factor = np.where(work["is_steps_edge"], STEP_PENALTY_FACTOR, 1.0)
        weight = work["base_slope_time_min"] * weather_factor * step_factor
    else:
        weight = work["base_slope_time_min"] * weather_factor
    out = work[["u", "v"]].copy()
    out["weight"] = np.asarray(weight, dtype=float)
    return out.dropna(subset=["weight"])


def nearest_destination_minutes(
    weighted_edges: pd.DataFrame,
    destination_nodes: list[int],
) -> dict[int, float]:
    """역방향 multi-source Dijkstra로 각 node에서 가장 가까운 D까지 시간을 구한다."""
    # (v,u) 방향으로 그래프를 직접 만들면 reverse() 호출 없이 같은 의미가 된다.
    dedup = weighted_edges.groupby(["v", "u"], sort=False)["weight"].min().reset_index()
    graph = nx.DiGraph()
    graph.add_weighted_edges_from(dedup.itertuples(index=False, name=None))
    sources = [node for node in destination_nodes if node in graph]
    if not sources:
        raise ValueError("그래프에 포함된 D 후보 node가 없습니다.")
    return nx.multi_source_dijkstra_path_length(graph, sources, weight="weight")


def main() -> None:
    run_started = datetime.now(UTC)
    params = SeniorCostParameters(flat_speed_m_per_s=SENIOR_SPEED_PROFILES_M_PER_S[REFERENCE_SPEED])
    hex_df = load_hex_frame()
    destination_nodes = load_destination_nodes()
    edges = build_edge_components(params)

    weather_names = list(WEATHER_PROFILES)
    variants: list[tuple[str, str]] = [(w, p) for w in weather_names for p in STEP_POLICIES]

    # 9개 변형 각각 Dijkstra 재탐색
    access: dict[tuple[str, str], pd.Series] = {}
    for weather_profile, step_policy in variants:
        weighted = variant_edge_weights(edges, weather_profile=weather_profile, step_policy=step_policy)
        lengths = nearest_destination_minutes(weighted, destination_nodes)
        access[(weather_profile, step_policy)] = hex_df["origin_node_id"].map(lengths).astype(float)
        print(
            f"[m4] {weather_profile} x {step_policy}: reachable "
            f"{int(access[(weather_profile, step_policy)].notna().sum())}/{len(hex_df)}"
        )

    ref_key = (REFERENCE_WEATHER, REFERENCE_STEP_POLICY)
    ref_cost = access[ref_key]
    senior_exposure = pd.to_numeric(hex_df["registered_senior_population"], errors="coerce").fillna(0.0)

    # 기준 변형에서 한 번만 fit한 FrozenBaseline을 9개 변형 모두에 재사용한다.
    fit_mask = ref_cost.notna()
    frozen = FrozenBaseline.fit(
        ref_cost[fit_mask],
        senior_exposure[fit_mask],
        vulnerable_quantile=VULNERABLE_QUANTILE,
    )

    m3_vulnerable_set = set(hex_df.loc[hex_df["vulnerable_m3_final"].fillna(False).astype(bool), "hex_id"])
    official_ok = hex_df["official_400m_ok_m0"].fillna(False).astype(bool)

    # 노출축 변화와 비용모형 변화를 분리하기 위한 비교 집합:
    # M3 비용 × 고령 노출(같은 노출축)에서 상위 20% 취약집합을 따로 만든다.
    # M4 취약집합이 m3_vulnerable_877과 다른 정도는 노출축 교체 효과가 섞여 있고,
    # 이 집합과 다른 정도가 순수 임피던스(M4 vs M3 비용) 효과다.
    m3_cost_senior_frozen = FrozenBaseline.fit(
        hex_df["access_cost_m3"],
        senior_exposure,
        vulnerable_quantile=VULNERABLE_QUANTILE,
    )
    m3cost_senior_mask = pd.Series(
        m3_cost_senior_frozen.vulnerability(hex_df["access_cost_m3"], senior_exposure)
        >= m3_cost_senior_frozen.vulnerability_threshold,
        index=hex_df.index,
    )
    m3cost_senior_set = set(hex_df.loc[m3cost_senior_mask, "hex_id"])

    # 1차 패스: 모든 변형의 취약 mask를 먼저 만든다 (참조 변형 비교가 순서에 의존하지 않도록).
    vulnerable_masks: dict[tuple[str, str], pd.Series] = {}
    vulnerability_by_key: dict[tuple[str, str], pd.Series] = {}
    for key in variants:
        cost = access[key]
        unreachable = cost.isna()
        vulnerability = pd.Series(
            frozen.vulnerability(cost, senior_exposure),
            index=hex_df.index,
        )
        vulnerability_by_key[key] = vulnerability
        vulnerable_masks[key] = (vulnerability >= frozen.vulnerability_threshold) | unreachable

    ref_vulnerable_set = set(hex_df.loc[vulnerable_masks[ref_key], "hex_id"])

    # 2차 패스: 변형별 지표와 long-format 산출물을 만든다.
    variant_rows: list[dict[str, Any]] = []
    long_rows: list[pd.DataFrame] = []
    for key in variants:
        weather_profile, step_policy = key
        cost = access[key]
        unreachable = cost.isna()
        vulnerability = vulnerability_by_key[key]
        vulnerable = vulnerable_masks[key]
        senior_hidden = official_ok & vulnerable
        vulnerable_set = set(hex_df.loc[vulnerable, "hex_id"])

        variant_rows.append(
            {
                "weather_profile": weather_profile,
                "step_policy": step_policy,
                "is_reference_variant": key == ref_key,
                "reachable_hex_count": int((~unreachable).sum()),
                "unreachable_hex_count": int(unreachable.sum()),
                "mean_access_min_base_speed": float(cost.mean()),
                "p90_access_min_base_speed": float(cost.quantile(0.90)),
                "spearman_vs_m0": spearman(cost, hex_df["access_cost_m0"]),
                "spearman_vs_m3": spearman(cost, hex_df["access_cost_m3"]),
                "spearman_vs_reference_variant": spearman(cost, ref_cost),
                "senior_vulnerable_count": int(vulnerable.sum()),
                "senior_hidden_count": int(senior_hidden.sum()),
                "jaccard_vs_m3_vulnerable_877": jaccard(vulnerable_set, m3_vulnerable_set),
                "jaccard_vs_m3cost_senior_exposure": jaccard(vulnerable_set, m3cost_senior_set),
                "jaccard_vs_reference_vulnerable": jaccard(vulnerable_set, ref_vulnerable_set),
                "senior_hidden_senior_population": float(
                    hex_df.loc[senior_hidden, "registered_senior_population"].sum()
                ),
            }
        )

        frame = pd.DataFrame(
            {
                "hex_id": hex_df["hex_id"],
                "weather_profile": weather_profile,
                "step_policy": step_policy,
                "access_cost_m4_senior_min": cost,
                "access_cost_m4_senior_reachable": ~unreachable,
                "senior_vulnerability_m4": vulnerability,
                "senior_vulnerable_m4": vulnerable,
                "senior_hidden_m4": senior_hidden,
            }
        )
        # 속도 프로필은 경로를 바꾸지 않으므로 시간만 비례 환산한다.
        for speed_name, speed in SENIOR_SPEED_PROFILES_M_PER_S.items():
            frame[f"access_min_speed_{speed_name}"] = cost * (
                SENIOR_SPEED_PROFILES_M_PER_S[REFERENCE_SPEED] / speed
            )
        long_rows.append(frame)

    variant_metrics = pd.DataFrame(variant_rows)
    hex_long = pd.concat(long_rows, ignore_index=True)

    # 계단 경로 의존: allowed 대비 barrier 비용 차이로 steps 경로 사용 여부를 판정한다.
    steps_usage: dict[str, pd.DataFrame] = {}
    for weather_profile in weather_names:
        allowed = access[(weather_profile, "steps_allowed")]
        barrier = access[(weather_profile, "steps_barrier")]
        uses_steps = (barrier.isna() & allowed.notna()) | ((barrier - allowed) > EPS_MIN)
        steps_usage[weather_profile] = pd.DataFrame(
            {
                "hex_id": hex_df["hex_id"],
                "uses_steps_on_m4_path": uses_steps.fillna(False),
                "alternative_without_steps_exists": barrier.notna(),
                "steps_detour_extra_min": (barrier - allowed),
            }
        )

    # robust senior core: 9개 변형 전부에서 취약(또는 도달불가)으로 잡히는 hex
    all_vulnerable = pd.concat([vulnerable_masks[key] for key in variants], axis=1).all(axis=1)
    robust_core = hex_df.loc[all_vulnerable, [
        "hex_id",
        "registered_population",
        "registered_senior_population",
        "demand_index_final",
        "access_cost_m0",
        "access_cost_m3",
        "official_400m_ok_m0",
        "vulnerable_m3_final",
        "hidden_vulnerable_final",
    ]].copy()
    robust_core["access_cost_m4_ref_min"] = ref_cost.loc[robust_core.index]
    robust_core["senior_hidden_robust"] = official_ok.loc[robust_core.index]

    # 행정동 라벨 결합: hidden 진단 CSV는 632개만 커버하므로,
    # 전체 hex는 hex centroid와 행정동 polygon의 공간조인으로 라벨을 만든다.
    hex_geometry = gpd.read_file(
        QGIS_DIR / "out_hex_vulnerability_final.gpkg",
        layer="out_hex_vulnerability_final",
    )[["hex_id", "geometry"]]
    admin_polygons = gpd.read_file(QGIS_DIR / "wrk_admin_dong_seoul_5179.gpkg")[
        ["district_name", "admin_name", "admin_code", "geometry"]
    ]
    centroids = hex_geometry.copy()
    centroids["geometry"] = centroids.geometry.centroid
    admin = (
        gpd.sjoin(centroids, admin_polygons, how="left", predicate="within")
        .loc[:, ["hex_id", "district_name", "admin_name", "admin_code"]]
        .drop_duplicates("hex_id")
    )
    robust_core = robust_core.merge(admin, on="hex_id", how="left")

    # QGIS 레이어: 기준 변형 + steps 의존 + robust core flag
    ref_vulnerability = pd.Series(frozen.vulnerability(ref_cost, senior_exposure), index=hex_df.index)
    gpkg_frame = pd.DataFrame(
        {
            "hex_id": hex_df["hex_id"],
            "access_cost_m4_ref_min": ref_cost,
            "access_cost_m4_ref_reachable": ref_cost.notna(),
            "senior_vulnerability_m4_ref": ref_vulnerability,
            "senior_vulnerable_m4_ref": vulnerable_masks[ref_key],
            "senior_hidden_m4_ref": official_ok & vulnerable_masks[ref_key],
            "robust_senior_core": all_vulnerable,
            "registered_senior_population": hex_df["registered_senior_population"],
            "access_cost_m0": hex_df["access_cost_m0"],
            "access_cost_m3": hex_df["access_cost_m3"],
            "vulnerable_m3_final": hex_df["vulnerable_m3_final"],
            "hidden_vulnerable_final": hex_df["hidden_vulnerable_final"],
        }
    )
    for speed_name in SENIOR_SPEED_PROFILES_M_PER_S:
        gpkg_frame[f"access_min_speed_{speed_name}"] = ref_cost * (
            SENIOR_SPEED_PROFILES_M_PER_S[REFERENCE_SPEED] / SENIOR_SPEED_PROFILES_M_PER_S[speed_name]
        )
    rain_steps = steps_usage[REFERENCE_WEATHER]
    gpkg_frame = gpkg_frame.merge(rain_steps, on="hex_id", how="left")
    gpkg_frame = gpkg_frame.merge(admin, on="hex_id", how="left")

    gdf = gpd.GeoDataFrame(hex_geometry.merge(gpkg_frame, on="hex_id", how="inner"), geometry="geometry", crs=CRS_METRIC)

    # edge 구성요소 산출물 (기준 변형 비용 포함)
    edge_out = edges[[
        "u",
        "v",
        "length_m",
        "grade_percent",
        "grade_abs_percent",
        "is_steps_edge",
        "signed_grade_fallback_abs",
        "senior_base_time_min",
        "senior_slope_factor",
    ]].copy()
    ref_weather_factor = 1.0 + WEATHER_PROFILES[REFERENCE_WEATHER]["beta_weather"] * WEATHER_PROFILES[REFERENCE_WEATHER]["intensity"]
    for weather_profile in weather_names:
        profile = WEATHER_PROFILES[weather_profile]
        edge_out[f"senior_weather_factor_{weather_profile}"] = 1.0 + profile["beta_weather"] * profile["intensity"]
    edge_out["senior_step_factor_penalty"] = np.where(edge_out["is_steps_edge"], STEP_PENALTY_FACTOR, 1.0)
    edge_out["cost_m4_senior_min_ref"] = (
        edge_out["senior_base_time_min"]
        * edge_out["senior_slope_factor"]
        * ref_weather_factor
        * edge_out["senior_step_factor_penalty"]
    )

    # 핵심 판정문 (v2.2 §0-quater.6)
    # 판정은 노출축을 고정한 비교(jaccard_vs_m3cost_senior_exposure)로 한다.
    # m3_vulnerable_877과의 차이는 노출축 교체(수요지수 -> 고령인구) 효과가 섞여 있다.
    ref_metrics = variant_metrics.loc[variant_metrics["is_reference_variant"]].iloc[0]
    barrier_snow = variant_metrics.loc[
        (variant_metrics["weather_profile"] == "snow") & (variant_metrics["step_policy"] == "steps_barrier")
    ].iloc[0]
    reordering_detected = bool(
        ref_metrics["spearman_vs_m3"] < 0.98
        or ref_metrics["jaccard_vs_m3cost_senior_exposure"] < 0.80
    )
    verdict = (
        "M4-senior impedance reordered candidates vs M3(cost)+senior exposure; "
        "cross-check the changed candidates with field review."
        if reordering_detected
        else "M4-senior kept nearly the same ranking as M3; do not claim that senior "
        "impedance alone revealed new vulnerable areas. Exposure-axis change and "
        "barrier/snow burden shifts are the defensible findings."
    )

    summary = {
        "run_date": run_started.date().isoformat(),
        "run_timestamp": run_started.isoformat(),
        "valid_hex_rows": int(len(hex_df)),
        "destination_node_count": int(len(destination_nodes)),
        "steps_edge_count": int(edges["is_steps_edge"].sum()),
        "signed_grade_fallback_abs_count": int(edges["signed_grade_fallback_abs"].sum()),
        "reference_variant": {
            "speed_profile": REFERENCE_SPEED,
            "speed_m_per_s": SENIOR_SPEED_PROFILES_M_PER_S[REFERENCE_SPEED],
            "weather_profile": REFERENCE_WEATHER,
            "step_policy": REFERENCE_STEP_POLICY,
        },
        "speed_profiles_m_per_s": SENIOR_SPEED_PROFILES_M_PER_S,
        "speed_scaling_analytic": True,
        "frozen_threshold": frozen.vulnerability_threshold,
        "senior_exposure_definition": "registered_senior_population (raw, FrozenBaseline minmax)",
        "reference_spearman_vs_m0": float(ref_metrics["spearman_vs_m0"]),
        "reference_spearman_vs_m3": float(ref_metrics["spearman_vs_m3"]),
        "reference_jaccard_vs_m3_vulnerable": float(ref_metrics["jaccard_vs_m3_vulnerable_877"]),
        "reference_jaccard_vs_m3cost_senior_exposure": float(
            ref_metrics["jaccard_vs_m3cost_senior_exposure"]
        ),
        "m3cost_senior_exposure_vulnerable_count": int(m3cost_senior_mask.sum()),
        "barrier_snow_unreachable_hex": int(barrier_snow["unreachable_hex_count"]),
        "robust_senior_core_count": int(all_vulnerable.sum()),
        "robust_senior_core_hidden_count": int((all_vulnerable & official_ok).sum()),
        "uses_steps_on_rain_path_count": int(rain_steps["uses_steps_on_m4_path"].sum()),
        "no_alternative_without_steps_count": int((~rain_steps["alternative_without_steps_exists"]).sum()),
        "reordering_detected": reordering_detected,
        "verdict": verdict,
        "claim_boundary": (
            "M4-senior는 관측 보행자료로 보정된 모델이 아니라 profile scenario다. "
            "고령자 실측 보행시간 예측이나 탑승수요 예측에 쓰지 않는다."
        ),
        "acceptance_check": {
            "implementation_separated_from_m0_m3": True,
            "speed_profiles_4": sorted(SENIOR_SPEED_PROFILES_M_PER_S),
            "signed_grade_first_abs_fallback": True,
            "step_policies_3": list(STEP_POLICIES),
            "weather_profiles_3_with_asos_caveat": weather_names,
            "dijkstra_research_per_variant": True,
            "validity_metrics_reported": ["spearman_m0_m3", "jaccard_vs_m3", "replacement_vs_reference"],
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = OUT_DIR / "m4_senior_variant_metrics.csv"
    long_path = OUT_DIR / "m4_senior_hex_long.csv"
    robust_path = OUT_DIR / "m4_senior_robust_core.csv"
    summary_path = OUT_DIR / "m4_senior_summary.json"
    manifest_path = OUT_DIR / "m4_senior.manifest.json"
    gpkg_path = QGIS_DIR / "m4_senior_access_runner.gpkg"
    edge_path = ROOT / "data" / "derived" / "edge_costs_m4_senior_components.parquet"

    write_csv(metrics_path, variant_metrics)
    write_csv(long_path, hex_long)
    write_csv(robust_path, robust_core)
    write_json(summary_path, summary)
    overwrite_gpkg(gdf, gpkg_path, "m4_senior_access_runner")
    edge_path.parent.mkdir(parents=True, exist_ok=True)
    edge_out.to_parquet(edge_path, index=False)

    ref_frame = hex_long.loc[
        (hex_long["weather_profile"] == REFERENCE_WEATHER)
        & (hex_long["step_policy"] == REFERENCE_STEP_POLICY)
    ]
    manifest = {
        "model_id": "M4_senior_v1",
        "run_timestamp": run_started.isoformat(),
        "code_version_id": "workspace",
        "effect_output_label": "senior_profile_sensitivity",
        "counterfactual_effect_claim_allowed": False,
        "cost_unit": "minutes",
        "cost_formula": (
            "length_m / (flat_speed*60) * max(1, exp(3.5*(|s+0.05|-0.05))) "
            "* (1 + beta_weather*intensity) * step_factor"
        ),
        "parameters": {
            "speed_profiles_m_per_s": SENIOR_SPEED_PROFILES_M_PER_S,
            "slope_cap_percent": params.slope_cap_percent,
            "tobler_scale": params.tobler_scale,
            "tobler_offset": params.tobler_offset,
            "step_penalty_factor": STEP_PENALTY_FACTOR,
            "weather_profiles": WEATHER_PROFILES,
            "parameter_status": "profile scenario parameters, not calibrated coefficients",
        },
        "path_research_run": True,
        "path_research_method": "networkx multi_source_dijkstra_path_length per variant (9 variants)",
        "speed_scaling_analytic": True,
        "frozen_baseline_threshold_hash": stable_hash(
            {
                "threshold": frozen.vulnerability_threshold,
                "quantile": VULNERABLE_QUANTILE,
                "universe": "M4 reference variant reachable final hexes",
            }
        ),
        "reference_cost_hash": frame_hash(
            ref_frame.rename(columns={"access_cost_m4_senior_min": "cost"}),
            ["hex_id", "cost"],
        ),
        "senior_exposure_hash": frame_hash(
            pd.DataFrame({"hex_id": hex_df["hex_id"], "exposure": senior_exposure}),
            ["hex_id", "exposure"],
        ),
        "input_paths": [
            "data/derived/hex_vulnerability_final.parquet",
            "data/interim/walking_edge_costs.parquet",
            "data/walking_network_nodes_with_elevation.csv",
            "qgis/out_transit_d_candidates.gpkg",
        ],
        "output_paths": [
            str(metrics_path.relative_to(ROOT)),
            str(long_path.relative_to(ROOT)),
            str(robust_path.relative_to(ROOT)),
            str(summary_path.relative_to(ROOT)),
            str(gpkg_path.relative_to(ROOT)),
            str(edge_path.relative_to(ROOT)),
        ],
        "notes": (
            "Steps-path dependence is derived by comparing steps_allowed vs steps_barrier "
            "costs instead of reconstructing path geometries."
        ),
    }
    write_json(manifest_path, manifest)

    print(variant_metrics.to_string(index=False))
    print(f"robust senior core: {summary['robust_senior_core_count']}")
    print(f"verdict: {verdict}")


if __name__ == "__main__":
    main()
