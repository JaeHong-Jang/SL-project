from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.font_manager as fm

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "figures" / "midterm"


COLORS = {
    "ink": "#1f2937",
    "muted": "#6b7280",
    "grid": "#e5e7eb",
    "base": "#f3f4f6",
    "boundary": "#d1d5db",
    "blue": "#2563eb",
    "teal": "#0f766e",
    "red": "#dc2626",
    "orange": "#ea580c",
    "amber": "#f59e0b",
    "green": "#16a34a",
    "purple": "#7c3aed",
    "slate": "#475569",
}


REASON_LABELS = {
    "slope_weather_penalty": "경사·기상 부담형",
    "high_demand": "수요집중형",
    "high_demand_plus_slope_weather_penalty": "복합형",
    "mixed": "혼합형",
    "near_400m_distance": "400m 경계형",
    "high_demand_plus_near_400m_distance": "수요+경계형",
}


def setup_plot_style() -> None:
    font_candidates = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            fm.fontManager.addfont(str(font_path))
            prop = fm.FontProperties(fname=str(font_path))
            plt.rcParams["font.family"] = prop.get_name()
            break

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": COLORS["boundary"],
            "axes.labelcolor": COLORS["ink"],
            "axes.titleweight": "bold",
            "axes.titlesize": 14,
            "axes.labelsize": 10,
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["muted"],
            "text.color": COLORS["ink"],
            "legend.frameon": False,
            "axes.unicode_minus": False,
        }
    )


def save_figure(fig: plt.Figure, stem: str, manifest: list[dict], title: str, claim: str, sources: list[str]) -> None:
    png = OUT_DIR / f"{stem}.png"
    pdf = OUT_DIR / f"{stem}.pdf"
    fig.savefig(png, dpi=240, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        {
            "id": stem,
            "title": title,
            "claim_supported": claim,
            "png": str(png.relative_to(ROOT)).replace("\\", "/"),
            "pdf": str(pdf.relative_to(ROOT)).replace("\\", "/"),
            "sources": sources,
        }
    )


def add_footnote(fig: plt.Figure, text: str) -> None:
    fig.text(0.01, 0.015, text, ha="left", va="bottom", fontsize=8.5, color=COLORS["muted"])


def clean_axes(ax) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    for spine in ax.spines.values():
        spine.set_visible(False)


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def load_inputs() -> dict:
    return {
        "final": gpd.read_file(ROOT / "qgis" / "out_hex_vulnerability_final.gpkg"),
        "robust": gpd.read_file(ROOT / "qgis" / "hidden_vulnerable_robust_core.gpkg"),
        "shift": gpd.read_file(ROOT / "qgis" / "m0_m3_environment_burden_shift.gpkg"),
        "reasons": pd.read_csv(ROOT / "outputs" / "reports" / "hidden_vulnerability_reason_diagnostics.csv"),
        "robustness": pd.read_csv(ROOT / "outputs" / "reports" / "v2_2_execution" / "normalization_combination_threshold_robustness.csv"),
        "quadrant": pd.read_csv(ROOT / "outputs" / "reports" / "v2_2_execution" / "quadrant_4x4_matrix.csv"),
        "summary": read_json("outputs/reports/hex_vulnerability_final_qa.json"),
        "audit": read_json("outputs/reports/hex_vulnerability_final_audit.json"),
        "reason_qa": read_json("outputs/reports/hidden_vulnerability_reason_diagnostics_qa.json"),
        "burden": read_json("outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.json"),
        "robust_core": read_json("outputs/reports/v2_2_execution/hidden_vulnerable_robust_core_summary.json"),
        "m4": read_json("outputs/reports/m4_senior/m4_senior_summary.json"),
        "s1": read_json("outputs/reports/scenario_counterfactual/S1_delta_vulnerability_summary.json"),
        "s3": read_json("outputs/reports/scenario_counterfactual/S3_delta_vulnerability_summary.json"),
        "s4": read_json("outputs/reports/scenario_counterfactual/S4_weather_off_delta_vulnerability_summary.json"),
    }


def figure_01_problem_copy(manifest: list[dict]) -> None:
    src = ROOT / "outputs" / "figures" / "s3_walkshed_comparison.png"
    if not src.exists():
        return
    dst_png = OUT_DIR / "fig01_problem_walkshed.png"
    shutil.copy2(src, dst_png)
    manifest.append(
        {
            "id": "fig01_problem_walkshed",
            "title": "400m 직선거리 기준과 실제 보행권의 차이",
            "claim_supported": "정류장 반경 400m 안에서도 실제 보행망과 경사 때문에 도달 가능 영역이 달라질 수 있음을 도입부에서 설명한다.",
            "png": str(dst_png.relative_to(ROOT)).replace("\\", "/"),
            "pdf": None,
            "sources": ["outputs/figures/s3_walkshed_comparison.png"],
        }
    )


def figure_02_data_qa(data: dict, manifest: list[dict]) -> None:
    summary = data["summary"]
    audit = data["audit"]
    cards = [
        ("보행망", "467,556 → 466,626", "오류 930개 제외"),
        ("목적지", "10,887 / 10,967", "정류장·역 좌표 유효"),
        ("분석격자", f"{summary['hex_count']:,} → {summary['analysis_valid_count']:,}", "H3 res9 valid"),
        ("취약후보", f"{summary['vulnerable_m3_final_count']:,} / {summary['hidden_vulnerable_final_count']:,}", "M3 취약 / hidden 후보"),
        ("QA", "PASS", f"geometry invalid {audit['gpkg_comparison']['geometry_invalid_count']}"),
    ]
    fig, ax = plt.subplots(figsize=(13.5, 4.4))
    ax.axis("off")
    fig.suptitle("데이터 정합 및 품질관리 대시보드", x=0.02, y=0.96, ha="left", fontsize=18, fontweight="bold")
    fig.text(0.02, 0.88, "보행망, 목적지, 수요, 격자를 같은 분석 단위로 맞추고 오류·도달성·공식 일치 여부를 검증", fontsize=11, color=COLORS["muted"])
    x_positions = np.linspace(0.08, 0.92, len(cards))
    for x, (label, value, note) in zip(x_positions, cards):
        display_value = value.replace(" → ", "\n→ ").replace(" / ", "\n/ ")
        ax.text(x, 0.62, display_value, ha="center", va="center", fontsize=16, fontweight="bold", color=COLORS["ink"], transform=ax.transAxes, linespacing=1.0)
        ax.text(x, 0.42, label, ha="center", va="center", fontsize=12, fontweight="bold", color=COLORS["blue"], transform=ax.transAxes)
        ax.text(x, 0.29, note, ha="center", va="center", fontsize=9.5, color=COLORS["muted"], transform=ax.transAxes)
        ax.add_patch(
            plt.Rectangle((x - 0.085, 0.19), 0.17, 0.55, fill=False, linewidth=1.2, edgecolor=COLORS["boundary"], transform=ax.transAxes)
        )
    add_footnote(fig, "Sources: data_loss_ledger_v2_2.csv; hex_vulnerability_final_audit.json")
    save_figure(
        fig,
        "fig02_data_qa_dashboard",
        manifest,
        "데이터 정합 및 품질관리 대시보드",
        "분석 결과가 단순 지도 색칠이 아니라 정제·유효성 검사를 통과한 분석셋에서 산출됐음을 보여준다.",
        ["outputs/reports/v2_2_execution/data_loss_ledger_v2_2.csv", "outputs/reports/hex_vulnerability_final_audit.json"],
    )


def figure_03_model_framework(data: dict, manifest: list[dict]) -> None:
    final = data["final"]
    valid = final[final["analysis_valid_final"] == True].copy()
    means = valid[["access_cost_m0", "access_cost_m1", "access_cost_m2", "access_cost_m3"]].mean()
    labels = ["M0\n거리", "M1\n+경사", "M2\n+기상", "M3\n+상호작용"]
    values = [means["access_cost_m0"], means["access_cost_m1"], means["access_cost_m2"], means["access_cost_m3"]]

    demand_cols = [
        ("registered_population_norm", "등록인구"),
        ("registered_senior_population_norm", "고령인구"),
        ("living_population_norm", "생활인구"),
        ("poi_total_norm", "POI"),
    ]
    demand_means = [valid[col].mean() for col, _ in demand_cols]
    demand_labels = [label for _, label in demand_cols]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), gridspec_kw={"width_ratios": [1.05, 0.95]})
    ax = axes[0]
    bars = ax.bar(labels, values, color=[COLORS["slate"], COLORS["teal"], COLORS["amber"], COLORS["red"]], width=0.62)
    ax.set_title("보행비용 모형: M0에서 M3까지")
    ax.set_ylabel("평균 접근비용 (m)")
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 3, f"{val:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.text(2.65, values[-1] - 17, "M0→M3\n+15.4%", ha="center", va="center", fontsize=12, fontweight="bold", color=COLORS["red"])

    ax2 = axes[1]
    bars2 = ax2.barh(demand_labels, demand_means, color=[COLORS["blue"], COLORS["purple"], COLORS["teal"], COLORS["orange"]])
    ax2.set_title("수요지수 구성 요소 평균")
    ax2.set_xlabel("정규화 평균값")
    ax2.grid(axis="x", color=COLORS["grid"], linewidth=0.8)
    ax2.invert_yaxis()
    for bar, val in zip(bars2, demand_means):
        ax2.text(val + 0.005, bar.get_y() + bar.get_height() / 2, f"{val:.3f}", va="center", fontsize=9.5)

    fig.suptitle("분석 프레임: 보행비용 × 수요 = 취약도", x=0.02, y=1.02, ha="left", fontsize=18, fontweight="bold")
    add_footnote(fig, "Cost model is scenario-based; values support relative comparison and spatial screening, not observed walking-time prediction.")
    save_figure(
        fig,
        "fig03_model_cost_demand_framework",
        manifest,
        "보행비용과 수요지수 분석 프레임",
        "M0~M3 단계적 비용 증가와 수요지수 구성요소를 함께 보여 분석 프레임을 설명한다.",
        ["data/derived/hex_vulnerability_final.parquet", "outputs/reports/hex_vulnerability_summary_stats_v3.csv"],
    )


def figure_04_burden_map(data: dict, manifest: list[dict]) -> None:
    shift = data["shift"]
    valid = shift[shift["access_cost_m3"].notna()].copy()
    bounds = [0, 10, 25, 50, 75, 100, valid["cost_gap_m3_minus_m0"].quantile(0.995)]
    cmap = LinearSegmentedColormap.from_list("burden", ["#eff6ff", "#bfdbfe", "#60a5fa", "#f59e0b", "#ef4444", "#7f1d1d"])
    norm = BoundaryNorm(bounds, cmap.N)

    fig, ax = plt.subplots(figsize=(8.8, 9.4))
    valid.plot(column="cost_gap_m3_minus_m0", cmap=cmap, norm=norm, linewidth=0, ax=ax)
    valid.boundary.plot(ax=ax, linewidth=0.05, color="white", alpha=0.35)
    clean_axes(ax)
    ax.set_title("경사·기상 반영 후 접근비용 증가량 (M3-M0)", loc="left", fontsize=16, pad=10)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("비용 증가량 (m)")
    ax.text(0.01, 0.02, "평균 +28.4m / P90 +66.4m", transform=ax.transAxes, fontsize=11, fontweight="bold", bbox=dict(facecolor="white", edgecolor=COLORS["boundary"], boxstyle="round,pad=0.35"))
    add_footnote(fig, "Source: qgis/m0_m3_environment_burden_shift.gpkg")
    save_figure(
        fig,
        "fig04_environment_burden_map",
        manifest,
        "M0-M3 환경부담 증가 지도",
        "경사·기상 반영이 서울 전역에서 접근비용을 얼마나 늘렸는지 공간적으로 보여준다.",
        ["qgis/m0_m3_environment_burden_shift.gpkg", "outputs/reports/v2_2_execution/m0_m3_environment_burden_effect.json"],
    )


def figure_05_hidden_map(data: dict, manifest: list[dict]) -> None:
    final = data["final"]
    robust = data["robust"]
    valid = final[final["analysis_valid_final"] == True].copy()
    hidden = valid[valid["hidden_vulnerable_final"] == True].copy()
    robust_core = robust[robust["robust_core_hidden_flag"] == True].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 7.4))
    for ax in axes:
        valid.plot(ax=ax, color="#f3f4f6", edgecolor="white", linewidth=0.05)
        clean_axes(ax)

    valid[valid["official_400m_ok_m0"] == True].plot(ax=axes[0], color="#d1fae5", edgecolor="white", linewidth=0.04)
    axes[0].set_title("현행 400m 기준: 접근성 양호로 보이는 영역", loc="left", fontsize=14)
    axes[0].legend(handles=[Patch(facecolor="#d1fae5", label="M0 400m 이내"), Patch(facecolor="#f3f4f6", label="그 외")], loc="lower left")

    hidden.plot(ax=axes[1], color="#fecaca", edgecolor="white", linewidth=0.04)
    if len(robust_core) > 0:
        robust_core.boundary.plot(ax=axes[1], color=COLORS["red"], linewidth=0.75)
    axes[1].set_title("M3+수요 기준: hidden 후보와 robust-core", loc="left", fontsize=14)
    axes[1].legend(
        handles=[
            Patch(facecolor="#fecaca", label="hidden 후보 632"),
            Line2D([0], [0], color=COLORS["red"], lw=2, label="robust-core 429"),
            Patch(facecolor="#f3f4f6", label="분석 유효 격자"),
        ],
        loc="lower left",
    )
    fig.suptitle("현행 거리 기준이 놓칠 수 있는 hidden 후보 선별", x=0.02, y=0.99, ha="left", fontsize=18, fontweight="bold")
    add_footnote(fig, "Hidden 후보는 확정 취약지역이 아니라 비용×수요 모형 기준 현장검토 후보. Source: out_hex_vulnerability_final.gpkg; hidden_vulnerable_robust_core.gpkg")
    save_figure(
        fig,
        "fig05_hidden_candidates_before_after_map",
        manifest,
        "현행 400m 기준과 hidden 후보 비교 지도",
        "현행 거리 기준으로는 양호해 보이는 영역 안에서 M3+수요 기준 hidden 후보가 어떻게 나타나는지 보여준다.",
        ["qgis/out_hex_vulnerability_final.gpkg", "qgis/hidden_vulnerable_robust_core.gpkg"],
    )


def figure_06_robustness(data: dict, manifest: list[dict]) -> None:
    robustness = data["robustness"].copy()
    quadrant = data["quadrant"].copy()

    display_variants = {
        "baseline_minmax_product": "Baseline",
        "winsorize_1_99_product": "Winsor 1-99",
        "log1p_product": "log1p",
        "rank_product": "Rank",
        "additive_minmax": "Additive",
        "threshold_top_10pct": "Top 10%",
        "threshold_top_20pct": "Top 20%",
        "threshold_top_30pct": "Top 30%",
    }
    robustness["label"] = robustness["variant"].map(display_variants).fillna(robustness["variant"])
    robustness = robustness.sort_values("hidden_hex_count", ascending=True)

    heat = quadrant.pivot(index="demand_quartile", columns="cost_quartile", values="hidden_count")
    demand_order = ["D4_high", "D3", "D2", "D1_low"]
    cost_order = ["C1_low", "C2", "C3", "C4_high"]
    heat = heat.reindex(index=demand_order, columns=cost_order)

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.6), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    colors = [COLORS["red"] if label == "Baseline" else COLORS["slate"] for label in robustness["label"]]
    ax.barh(robustness["label"], robustness["hidden_hex_count"], color=colors)
    ax.axvline(632, color=COLORS["red"], linestyle="--", linewidth=1)
    ax.axvline(429, color=COLORS["blue"], linestyle=":", linewidth=2)
    ax.set_title("정규화·임계값별 hidden 후보 수")
    ax.set_xlabel("hidden 후보 격자 수")
    ax.grid(axis="x", color=COLORS["grid"])
    ax.text(635, 0.6, "Baseline 632", color=COLORS["red"], fontsize=9, fontweight="bold")
    ax.text(432, 1.3, "Robust-core 429", color=COLORS["blue"], fontsize=9, fontweight="bold")

    ax2 = axes[1]
    im = ax2.imshow(heat.values, cmap=LinearSegmentedColormap.from_list("heat", ["#f8fafc", "#bfdbfe", "#f59e0b", "#dc2626"]))
    ax2.set_title("비용×수요 4분면 교차검증: hidden 수")
    ax2.set_xticks(range(len(cost_order)), labels=["비용 낮음", "C2", "C3", "비용 높음"], rotation=30, ha="right")
    ax2.set_yticks(range(len(demand_order)), labels=["수요 높음", "D3", "D2", "수요 낮음"])
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            val = heat.values[i, j]
            ax2.text(j, i, f"{int(val)}", ha="center", va="center", fontsize=11, fontweight="bold", color="white" if val > np.nanmax(heat.values) * 0.55 else COLORS["ink"])
    fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.04, label="hidden 후보 수")
    fig.suptitle("강건성 점검: 숫자가 흔들리는 부분과 반복 확인되는 부분 분리", x=0.02, y=1.02, ha="left", fontsize=18, fontweight="bold")
    add_footnote(fig, "Robustness is a screening stability check, not a Monte Carlo uncertainty estimate.")
    save_figure(
        fig,
        "fig06_robustness_and_quadrant",
        manifest,
        "강건성 및 비용×수요 교차검증",
        "baseline 632개와 robust-core 429개를 분리하고, 곱셈 점수 외 비용·수요 직접 교차검증 결과를 보여준다.",
        ["outputs/reports/v2_2_execution/normalization_combination_threshold_robustness.csv", "outputs/reports/v2_2_execution/quadrant_4x4_matrix.csv"],
    )


def figure_07_reason_diagnostics(data: dict, manifest: list[dict]) -> None:
    reason_qa = data["reason_qa"]
    counts = pd.Series(reason_qa["primary_reason_counts"]).sort_values(ascending=True)
    labels = [REASON_LABELS.get(idx, idx) for idx in counts.index]
    districts = pd.Series(reason_qa["top_district_counts"]).head(10).sort_values(ascending=True)

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.8), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    reason_colors = {
        "경사·기상 부담형": COLORS["red"],
        "수요집중형": COLORS["blue"],
        "복합형": COLORS["purple"],
        "혼합형": COLORS["slate"],
        "400m 경계형": COLORS["amber"],
        "수요+경계형": COLORS["orange"],
    }
    colors = [reason_colors.get(label, COLORS["muted"]) for label in labels]
    ax.barh(labels, counts.values, color=colors)
    ax.set_title("hidden 후보 원인 진단 범주")
    ax.set_xlabel("격자 수")
    ax.grid(axis="x", color=COLORS["grid"])
    total = counts.sum()
    for y, val in enumerate(counts.values):
        ax.text(val + 3, y, f"{int(val)} ({val / total:.1%})", va="center", fontsize=9.5)

    ax2 = axes[1]
    ax2.barh(districts.index, districts.values, color=COLORS["teal"])
    ax2.set_title("hidden 후보 상위 자치구")
    ax2.set_xlabel("격자 수")
    ax2.grid(axis="x", color=COLORS["grid"])
    for y, val in enumerate(districts.values):
        ax2.text(val + 1, y, f"{int(val)}", va="center", fontsize=9.5)

    fig.suptitle("원인은 하나가 아니다: 경사·기상형, 수요집중형, 복합형", x=0.02, y=1.02, ha="left", fontsize=18, fontweight="bold")
    add_footnote(fig, "Primary reason is a diagnostic category, not causal proof.")
    save_figure(
        fig,
        "fig07_reason_diagnostics",
        manifest,
        "hidden 후보 원인 진단 및 자치구 분포",
        "hidden 후보가 경사·기상 부담형, 수요집중형, 복합형 등으로 나뉘며 정책 후보도 유형별로 달라져야 함을 보여준다.",
        ["outputs/reports/hidden_vulnerability_reason_diagnostics_qa.json", "outputs/reports/hidden_vulnerability_reason_diagnostics.csv"],
    )


def figure_08_scenario_policy(data: dict, manifest: list[dict]) -> None:
    scenarios = [
        ("S1\n후보 정류장\n상한", data["s1"]),
        ("S3\n경사 cap\n진단", data["s3"]),
        ("S4\n기상항 제거\n상한", data["s4"]),
    ]
    baseline = [s["baseline_hidden_count"] for _, s in scenarios]
    scenario = [s["scenario_hidden_count"] for _, s in scenarios]
    resolved = [s["resolved_hidden_count"] for _, s in scenarios]
    labels = [label for label, _ in scenarios]

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    fig.subplots_adjust(left=0.11, right=0.98, top=0.86, bottom=0.22)
    x = np.arange(len(labels))
    width = 0.34
    ax.bar(x - width / 2, baseline, width, color="#e5e7eb", label="Baseline hidden")
    ax.bar(x + width / 2, scenario, width, color=[COLORS["blue"], COLORS["slate"], COLORS["orange"]], label="Scenario hidden")
    for i, val in enumerate(resolved):
        ax.text(x[i], max(baseline[i], scenario[i]) + 18, f"완화 {val}개", ha="center", fontsize=11, fontweight="bold", color=COLORS["red"] if val else COLORS["muted"])
    ax.set_xticks(x, labels)
    ax.set_ylabel("hidden 후보 격자 수")
    ax.set_title("정책 시나리오는 효과 입증이 아니라 상한·진단으로 해석")
    ax.grid(axis="y", color=COLORS["grid"])
    ax.legend(loc="lower right", frameon=False)
    ax.set_ylim(0, max(baseline) * 1.18)
    ax.text(
        0.02,
        0.94,
        "정책 메시지: 사업 확정이 아니라 현장검토 우선순위 후보",
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        color=COLORS["ink"],
        bbox=dict(facecolor="white", edgecolor=COLORS["boundary"], boxstyle="round,pad=0.35"),
    )
    add_footnote(fig, "S1 and S4 are upper-bound counterfactuals; S3 is a diagnostic cap scenario. Do not read as proven intervention effects.")
    save_figure(
        fig,
        "fig08_policy_scenario_diagnostics",
        manifest,
        "정책 시나리오 상한·진단 결과",
        "후보 정류장, 경사 cap, 기상항 제거 시나리오가 실제 정책효과가 아니라 우선순위 검토용 상한·진단임을 보여준다.",
        [
            "outputs/reports/scenario_counterfactual/S1_delta_vulnerability_summary.json",
            "outputs/reports/scenario_counterfactual/S3_delta_vulnerability_summary.json",
            "outputs/reports/scenario_counterfactual/S4_weather_off_delta_vulnerability_summary.json",
        ],
    )


def figure_09_summary_panel(data: dict, manifest: list[dict]) -> None:
    s = data["summary"]
    r = data["robust_core"]
    b = data["burden"]
    m4 = data["m4"]
    cards = [
        ("분석 유효 격자", f"{s['analysis_valid_count']:,}", "H3 res9"),
        ("M3 취약 후보", f"{s['vulnerable_m3_final_count']:,}", "상위 20%"),
        ("hidden 후보", f"{s['hidden_vulnerable_final_count']:,}", "baseline"),
        ("robust-core", f"{r['robust_core_hidden_rows']:,}", "반복 확인"),
        ("노출 인구", "166만", "고령 34만"),
        ("비용 증가", f"{b['mean_cost_increase_rate'] * 100:.1f}%", "M0→M3"),
        ("순위상관", f"{b['rank_spearman_m0_m3']:.3f}", "경계 선별"),
        ("계단·눈 단절", f"{m4['barrier_snow_unreachable_hex']}", "후속 후보"),
    ]
    fig, ax = plt.subplots(figsize=(13.5, 6.1))
    ax.axis("off")
    fig.suptitle("발표 핵심 숫자 요약", x=0.02, y=0.96, ha="left", fontsize=20, fontweight="bold")
    fig.text(0.02, 0.89, "숫자는 확정 취약지역이 아니라 현장검토 후보 선별 결과로 해석", fontsize=11, color=COLORS["muted"])

    cols = 4
    for i, (label, value, note) in enumerate(cards):
        row = i // cols
        col = i % cols
        x = 0.08 + col * 0.235
        y = 0.62 - row * 0.34
        ax.add_patch(plt.Rectangle((x - 0.06, y - 0.11), 0.19, 0.22, fill=False, linewidth=1.1, edgecolor=COLORS["boundary"], transform=ax.transAxes))
        ax.text(x + 0.035, y + 0.04, value, ha="center", va="center", fontsize=22, fontweight="bold", color=COLORS["ink"], transform=ax.transAxes)
        ax.text(x + 0.035, y - 0.035, label, ha="center", va="center", fontsize=11, fontweight="bold", color=COLORS["blue"], transform=ax.transAxes)
        ax.text(x + 0.035, y - 0.082, note, ha="center", va="center", fontsize=9, color=COLORS["muted"], transform=ax.transAxes)
    add_footnote(fig, "Use as backup/title summary; avoid saying '166만 명 피해' or '취약지역 확정'.")
    save_figure(
        fig,
        "fig09_key_numbers_summary",
        manifest,
        "핵심 숫자 요약 패널",
        "발표나 부록 첫 장에서 전체 분석 규모, hidden 후보, 강건성, 한계를 한눈에 정리한다.",
        ["outputs/reports/hex_vulnerability_final_qa.json", "outputs/reports/v2_2_execution/v2_2_execution_summary.md", "outputs/reports/m4_senior/m4_senior_summary.json"],
    )


def write_readme(manifest: list[dict]) -> None:
    readme = OUT_DIR / "README.md"
    lines = [
        "# Midterm Visualization Set",
        "",
        "논문/분석 보고서/중간발표에 쓸 수 있도록 같은 입력 데이터에서 생성한 시각화 세트입니다.",
        "",
        "## 사용 원칙",
        "",
        "- `hidden`은 확정 취약지역이 아니라 모형 기준 현장검토 후보입니다.",
        "- 정책 시나리오는 효과 입증이 아니라 상한·진단으로만 해석합니다.",
        "- `632 baseline`과 `429 robust-core`를 함께 보여 기준 민감도 질문을 방어합니다.",
        "- 지도에는 가능하면 후보 정의 주석을 함께 넣습니다.",
        "",
        "## Figures",
        "",
    ]
    for item in manifest:
        lines.extend(
            [
                f"### {item['id']}",
                f"- Title: {item['title']}",
                f"- Claim: {item['claim_supported']}",
                f"- PNG: `{item['png']}`",
                f"- PDF: `{item['pdf']}`" if item["pdf"] else "- PDF: copied source only",
                f"- Sources: {', '.join(item['sources'])}",
                "",
            ]
        )
    readme.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    setup_plot_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    data = load_inputs()

    figure_01_problem_copy(manifest)
    figure_02_data_qa(data, manifest)
    figure_03_model_framework(data, manifest)
    figure_04_burden_map(data, manifest)
    figure_05_hidden_map(data, manifest)
    figure_06_robustness(data, manifest)
    figure_07_reason_diagnostics(data, manifest)
    figure_08_scenario_policy(data, manifest)
    figure_09_summary_panel(data, manifest)

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_readme(manifest)
    print(f"created {len(manifest)} figures in {OUT_DIR}")


if __name__ == "__main__":
    main()
