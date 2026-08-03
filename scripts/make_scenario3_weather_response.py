from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(".")
OUT_DIR = BASE / "scenario3_weather_response"
OUT_DIR.mkdir(exist_ok=True)

df = pd.read_csv(
    BASE / "SL_outputs/outputs/reports/hidden_vulnerability_reason_diagnostics.csv"
)

df["weather_effect"] = (
    df["weather_additive_increment_m2_m1"] + df["interaction_increment_m3_m2"]
)
df["weather_effect_share"] = (
    df["weather_additive_increment_share"] + df["interaction_increment_share"]
)
df["snow_ice_pressure"] = (
    df["slope_increment_m1_m0"] + df["interaction_increment_m3_m2"]
)
df["anti_slip_pressure"] = (
    df["slope_increment_m1_m0"] * 0.7 + df["interaction_increment_m3_m2"] * 1.3
)
df["drainage_pressure"] = (
    df["weather_additive_increment_m2_m1"] * 0.85
    + df["interaction_increment_m3_m2"] * 0.35
)

for col in [
    "weather_effect",
    "weather_effect_share",
    "snow_ice_pressure",
    "anti_slip_pressure",
    "drainage_pressure",
    "vulnerability_m3_final",
    "demand_index_final",
    "access_cost_m3",
    "total_env_increment_m3_m0",
    "registered_senior_population",
]:
    df[f"{col}_pct"] = df[col].rank(pct=True)

df["scenario3_score"] = (
    0.34 * df["weather_effect_pct"]
    + 0.18 * df["total_env_increment_m3_m0_pct"]
    + 0.16 * df["vulnerability_m3_final_pct"]
    + 0.12 * df["demand_index_final_pct"]
    + 0.10 * df["access_cost_m3_pct"]
    + 0.10 * df["registered_senior_population_pct"]
)


def actions(row):
    acts = []
    if row["snow_ice_pressure_pct"] >= 0.75 or (
        row["slope_increment_share"] >= 0.65 and row["weather_effect_pct"] >= 0.6
    ):
        acts.append("제설 우선순위")
    if row["drainage_pressure_pct"] >= 0.75 or (
        row["weather_additive_increment_share"] >= 0.22
        and row["weather_effect_pct"] >= 0.7
    ):
        acts.append("배수/침수 점검")
    if row["anti_slip_pressure_pct"] >= 0.75 or row["interaction_increment_share"] >= 0.06:
        acts.append("미끄럼 방지 포장")
    return ", ".join(dict.fromkeys(acts or ["현장 점검"]))


def primary(row):
    vals = {
        "제설 우선구간": row["snow_ice_pressure_pct"],
        "배수 불량/침수 가능": row["drainage_pressure_pct"],
        "미끄럼 방지 포장": row["anti_slip_pressure_pct"],
    }
    return max(vals, key=vals.get)


df["recommended_actions"] = df.apply(actions, axis=1)
df["primary_low_cost_type"] = df.apply(primary, axis=1)

keep = [
    "rank",
    "district_name",
    "admin_name",
    "admin_code",
    "hex_id",
    "scenario3_score",
    "primary_low_cost_type",
    "recommended_actions",
    "vulnerability_m3_final",
    "demand_index_final",
    "access_cost_m3",
    "cost_m3_percentile_final",
    "weather_effect",
    "weather_additive_increment_m2_m1",
    "interaction_increment_m3_m2",
    "total_env_increment_m3_m0",
    "env_penalty_percentile_final",
    "slope_increment_m1_m0",
    "slope_increment_share",
    "weather_additive_increment_share",
    "interaction_increment_share",
    "near_400m_distance_pressure",
    "high_demand_pressure",
    "high_m3_cost_pressure",
    "high_env_penalty",
    "registered_population",
    "registered_senior_population",
    "centroid_x",
    "centroid_y",
    "primary_reason",
]


def round_cols(data):
    data = data.copy()
    num_cols = data.select_dtypes(include=[np.number]).columns
    data[num_cols] = data[num_cols].round(4)
    return data


top20 = df.sort_values("scenario3_score", ascending=False).head(20).copy()
top20.insert(0, "scenario3_rank", range(1, len(top20) + 1))
top20_out = round_cols(top20[["scenario3_rank"] + keep])
top20_out.to_csv(
    OUT_DIR / "scenario3_weather_response_top20.csv",
    index=False,
    encoding="utf-8-sig",
)

for score_col, file_name in [
    ("snow_ice_pressure_pct", "scenario3_snow_priority_top20.csv"),
    ("drainage_pressure_pct", "scenario3_drainage_check_top20.csv"),
    ("anti_slip_pressure_pct", "scenario3_anti_slip_paving_top20.csv"),
]:
    sub = df.sort_values([score_col, "scenario3_score"], ascending=False).head(20).copy()
    sub.insert(0, "type_rank", range(1, len(sub) + 1))
    round_cols(sub[["type_rank"] + keep]).to_csv(
        OUT_DIR / file_name, index=False, encoding="utf-8-sig"
    )


def md_table(data, cols):
    rows = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in data[cols].iterrows():
        vals = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                value = f"{value:.4f}"
            vals.append(str(value))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


md_cols = [
    "scenario3_rank",
    "district_name",
    "admin_name",
    "hex_id",
    "scenario3_score",
    "primary_low_cost_type",
    "recommended_actions",
    "weather_effect",
    "slope_increment_m1_m0",
    "vulnerability_m3_final",
    "registered_senior_population",
]

district_counts = top20["district_name"].value_counts().to_dict()
action_counts = (
    top20["recommended_actions"]
    .str.get_dummies(sep=", ")
    .sum()
    .sort_values(ascending=False)
    .to_dict()
)

report_lines = [
    "# 시나리오3(2학년 전체): 기상 대응 필요 후보 분석",
    "",
    "## 분석 기준",
    "- 대상: 기존 `hidden_vulnerability_reason_diagnostics.csv`의 hidden vulnerable 632개 hex",
    "- 기상 취약성: `weather_additive_increment_m2_m1 + interaction_increment_m3_m2`가 큰 곳",
    "- 우선순위 보정: 최종 취약도, 수요지수, M3 접근비용, 환경 페널티, 고령 등록인구를 함께 반영",
    "- 저비용 대응 분류: 제설 우선순위, 배수/침수 점검, 미끄럼 방지 포장",
    "",
    "## Top 20 후보",
    md_table(top20_out, md_cols),
    "",
    "## 해석 요약",
    f"- Top 20 자치구 분포: {district_counts}",
    f"- Top 20 권장 대책 빈도: {action_counts}",
    "- `제설 우선구간`은 경사 증가분과 기상-경사 상호작용이 큰 후보입니다.",
    "- `배수 불량/침수 가능`은 비/눈 자체로 추가 비용이 크게 증가하는 후보입니다. 실제 침수 이력 자료가 없으므로 현장 배수구 막힘, 저지대 여부, 빗물받이 간격 확인이 필요합니다.",
    "- `미끄럼 방지 포장`은 경사와 기상 상호작용이 커서 노면 마찰 저하의 영향이 클 가능성이 있는 후보입니다.",
    "",
    "## 산출 파일",
]
for path in sorted(OUT_DIR.glob("*.csv")):
    report_lines.append(f"- `{path.name}`")

(OUT_DIR / "scenario3_weather_response_report.md").write_text(
    "\n".join(report_lines), encoding="utf-8"
)

print(OUT_DIR.resolve())
print(top20_out[md_cols].to_string(index=False))
