from __future__ import annotations

import json
import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QGIS = ROOT / "qgis"
OUT = ROOT / "outputs" / "qgis_midterm_layers"


REASON_LABELS = {
    "slope_weather_penalty": "경사·기상 부담형",
    "high_demand": "수요집중형",
    "high_demand_plus_slope_weather_penalty": "복합형",
    "mixed": "혼합형",
    "near_400m_distance": "400m 경계형",
    "high_demand_plus_near_400m_distance": "수요+경계형",
}


def write_layer(gdf: gpd.GeoDataFrame, name: str, columns: list[str]) -> dict:
    path = OUT / f"{name}.gpkg"
    cols = [c for c in columns if c in gdf.columns] + ["geometry"]
    layer = gdf[cols].copy()
    layer.to_file(path, driver="GPKG")
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "features": int(len(layer)),
        "crs": str(layer.crs),
        "columns": [c for c in layer.columns if c != "geometry"],
    }


def classify_burden(value: float) -> str:
    if pd.isna(value):
        return "자료 없음"
    if value < 10:
        return "0-10m"
    if value < 25:
        return "10-25m"
    if value < 50:
        return "25-50m"
    if value < 75:
        return "50-75m"
    if value < 100:
        return "75-100m"
    return "100m 이상"


def policy_label(row: pd.Series) -> str:
    if bool(row.get("step_no_alt", False)):
        return "계단·눈 대체경로 없음"
    if bool(row.get("s4_weather_sensitive", False)):
        return "S4 기상 민감 후보"
    if bool(row.get("s1_resolved_hidden", False)):
        return "S1 정류장·접근로 검토"
    if bool(row.get("uses_steps", False)):
        return "계단 사용 경로"
    return "기타"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    final = gpd.read_file(QGIS / "out_hex_vulnerability_final.gpkg")
    valid = final[final["analysis_valid_final"] == True].copy()
    robust = gpd.read_file(QGIS / "hidden_vulnerable_robust_core.gpkg")
    robust_flags = robust[
        ["hex_id", "robust_core_hidden_flag", "normalization_sensitive_flag", "variant_hidden_count"]
    ].copy()

    hidden = valid[valid["hidden_vulnerable_final"] == True].copy()
    hidden = hidden.merge(robust_flags, on="hex_id", how="left")
    hidden["hidden_class"] = hidden["robust_core_hidden_flag"].fillna(False).map(
        {True: "robust-core 429", False: "baseline-only hidden"}
    )

    burden = gpd.read_file(QGIS / "m0_m3_environment_burden_shift.gpkg")
    burden["burden_class"] = burden["cost_gap_m3_minus_m0"].map(classify_burden)

    reasons = gpd.read_file(QGIS / "out_hidden_vulnerability_reason_diagnostics.gpkg")
    reasons["reason_label"] = reasons["primary_reason"].map(REASON_LABELS).fillna(reasons["primary_reason"])

    s1 = gpd.read_file(QGIS / "S1_delta_vulnerability_runner.gpkg")
    s3 = gpd.read_file(QGIS / "S3_delta_vulnerability_runner.gpkg", ignore_geometry=True)
    s4 = gpd.read_file(QGIS / "S4_weather_off_delta_vulnerability_runner.gpkg", ignore_geometry=True)
    m4 = gpd.read_file(QGIS / "m4_senior_access_runner.gpkg", ignore_geometry=False)

    policy = s1[
        [
            "hex_id",
            "registered_population",
            "registered_senior_population",
            "district_name",
            "admin_name",
            "primary_reason",
            "resolved_hidden",
            "baseline_hidden",
            "scenario_hidden",
            "geometry",
        ]
    ].rename(
        columns={
            "resolved_hidden": "s1_resolved_hidden",
            "scenario_hidden": "s1_scenario_hidden",
        }
    )
    policy = policy.merge(
        s3[["hex_id", "resolved_hidden"]].rename(columns={"resolved_hidden": "s3_resolved_hidden"}),
        on="hex_id",
        how="left",
    )
    policy = policy.merge(
        s4[["hex_id", "resolved_hidden", "scenario_hidden"]].rename(
            columns={"resolved_hidden": "s4_weather_sensitive", "scenario_hidden": "s4_scenario_hidden"}
        ),
        on="hex_id",
        how="left",
    )
    policy = policy.merge(
        m4[["hex_id", "uses_steps_on_m4_path", "alternative_without_steps_exists"]].rename(
            columns={
                "uses_steps_on_m4_path": "uses_steps",
                "alternative_without_steps_exists": "step_alt_exists",
            }
        ),
        on="hex_id",
        how="left",
    )
    policy["step_no_alt"] = policy["step_alt_exists"] == False
    policy["policy_review_type"] = policy.apply(policy_label, axis=1)
    policy = policy[
        policy[["s1_resolved_hidden", "s4_weather_sensitive", "step_no_alt", "uses_steps"]]
        .fillna(False)
        .any(axis=1)
    ].copy()

    seoul_boundary = gpd.read_file(QGIS / "wrk_seoul_boundary_5179.gpkg").to_crs(valid.crs)
    admin = gpd.read_file(QGIS / "wrk_admin_dong_seoul_5179.gpkg")
    admin_gu = admin.dissolve(by="district_name", as_index=False)

    hidden_with_reason = reasons[["hex_id", "district_name", "reason_label"]].merge(
        hidden[["hex_id", "robust_core_hidden_flag"]], on="hex_id", how="left"
    )
    district_counts = hidden_with_reason.groupby("district_name").agg(
        hidden_count=("hex_id", "count"),
        robust_count=("robust_core_hidden_flag", "sum"),
    )
    top_reason = (
        hidden_with_reason.groupby(["district_name", "reason_label"])
        .size()
        .rename("reason_count")
        .reset_index()
        .sort_values(["district_name", "reason_count"], ascending=[True, False])
        .drop_duplicates("district_name")
        .set_index("district_name")
    )
    district_summary = admin_gu.merge(district_counts, on="district_name", how="left").merge(
        top_reason[["reason_label", "reason_count"]], on="district_name", how="left"
    )
    district_summary["hidden_count"] = district_summary["hidden_count"].fillna(0).astype(int)
    district_summary["robust_count"] = district_summary["robust_count"].fillna(0).astype(int)
    district_summary["reason_count"] = district_summary["reason_count"].fillna(0).astype(int)

    manifest: dict[str, dict] = {}
    manifest["00_seoul_boundary"] = write_layer(
        seoul_boundary, "00_seoul_boundary", ["EMD_CD", "EMD_NM", "COL_ADM_SE"]
    )
    manifest["00_admin_dong"] = write_layer(
        admin, "00_admin_dong", ["district_code", "district_name", "admin_code", "admin_name"]
    )
    manifest["00_admin_gu"] = write_layer(
        admin_gu, "00_admin_gu", ["district_name"]
    )
    manifest["01_valid_hex_base"] = write_layer(
        valid,
        "01_valid_hex_base",
        [
            "hex_id",
            "analysis_valid_final",
            "official_400m_ok_m0",
            "vulnerable_m3_final",
            "hidden_vulnerable_final",
            "registered_population",
            "registered_senior_population",
            "demand_index_final",
            "access_cost_m0",
            "access_cost_m3",
            "vulnerability_m3_final",
        ],
    )
    manifest["02_environment_burden_hex"] = write_layer(
        burden,
        "02_environment_burden_hex",
        [
            "hex_id",
            "access_cost_m0",
            "access_cost_m3",
            "cost_gap_m3_minus_m0",
            "cost_gap_ratio_m3_over_m0",
            "burden_class",
            "m0_400_to_m3_over_400",
            "hidden_vulnerable_final",
            "registered_population",
            "registered_senior_population",
        ],
    )
    manifest["03_hidden_candidates"] = write_layer(
        hidden,
        "03_hidden_candidates",
        [
            "hex_id",
            "hidden_class",
            "robust_core_hidden_flag",
            "normalization_sensitive_flag",
            "variant_hidden_count",
            "registered_population",
            "registered_senior_population",
            "demand_index_final",
            "access_cost_m0",
            "access_cost_m3",
            "vulnerability_m3_final",
        ],
    )
    manifest["04_hidden_reason_diagnostics"] = write_layer(
        reasons,
        "04_hidden_reason_diagnostics",
        [
            "hex_id",
            "primary_reason",
            "reason_label",
            "district_name",
            "admin_name",
            "registered_population",
            "registered_senior_population",
            "access_cost_m0",
            "access_cost_m3",
            "slope_increment_m1_m0",
            "weather_additive_increment_m2_m1",
            "interaction_increment_m3_m2",
            "demand_index_final",
        ],
    )
    manifest["05_policy_review_candidates"] = write_layer(
        policy,
        "05_policy_review_candidates",
        [
            "hex_id",
            "policy_review_type",
            "s1_resolved_hidden",
            "s3_resolved_hidden",
            "s4_weather_sensitive",
            "uses_steps",
            "step_alt_exists",
            "step_no_alt",
            "baseline_hidden",
            "s1_scenario_hidden",
            "s4_scenario_hidden",
            "primary_reason",
            "district_name",
            "admin_name",
            "registered_population",
            "registered_senior_population",
        ],
    )
    manifest["06_district_hidden_summary"] = write_layer(
        district_summary,
        "06_district_hidden_summary",
        [
            "district_name",
            "hidden_count",
            "robust_count",
            "reason_label",
            "reason_count",
        ],
    )

    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = OUT / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# QGIS Midterm Layer Pack",
                "",
                "중간발표/논문형 지도 제작을 위해 원본 QGIS 레이어를 발표용으로 정리한 패키지입니다.",
                "QGIS에서 아래 순서로 로드하고, `docs/qgis_논문형_시각화_제작안.md`의 스타일을 적용하세요.",
                "",
                "## 권장 레이어 순서",
                "",
                "1. `00_seoul_boundary.gpkg`",
                "2. `00_admin_dong.gpkg`",
                "3. `01_valid_hex_base.gpkg`",
                "4. 지도 목적에 따라 `02_environment_burden_hex.gpkg`, `03_hidden_candidates.gpkg`, `04_hidden_reason_diagnostics.gpkg`, `05_policy_review_candidates.gpkg` 중 하나",
                "",
                "## 주의",
                "",
                "- `hidden`은 확정 취약지역이 아니라 현장검토 후보입니다.",
                "- `05_policy_review_candidates`는 정책효과 입증이 아니라 상한·진단 후보입니다.",
                "- OSM 배경지도는 발표용 메인 지도에서는 끄는 것을 권장합니다.",
            ]
        ),
        encoding="utf-8",
    )

    shutil.copy2(ROOT / "outputs" / "figures" / "midterm" / "fig06_robustness_and_quadrant.png", OUT / "support_robustness_chart.png")
    shutil.copy2(ROOT / "outputs" / "figures" / "midterm" / "fig07_reason_diagnostics.png", OUT / "support_reason_chart.png")
    print(f"created QGIS layer pack: {OUT}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
