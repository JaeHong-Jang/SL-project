"""프로젝트 데이터 처리 파이프라인을 실행하는 Typer CLI.

각 명령은 원자료를 직접 수정하지 않고 `data/interim`, `data/derived`, `qgis`,
`outputs/reports`에 재현 가능한 산출물을 남긴다. `prelim` 명령은 생활인구+POI
기준 초안이고, `final` 명령은 등록인구 공간분배까지 붙은 뒤 보고서용 수요지수로
승격하는 경로다.
"""

from __future__ import annotations

import json
from glob import glob
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import polars as pl
import typer

from sl_accessibility.accessibility.costs import CostParameters
from sl_accessibility.accessibility.edge_cost_table import add_edge_cost_columns_lazy, build_edge_cost_table
from sl_accessibility.accessibility.routing import (
    COST_COLUMNS,
    build_hex_accessibility_table,
    read_network_nodes,
    snap_points_to_nodes,
)
from sl_accessibility.accessibility.typology import (
    classify_vulnerability_typology,
    vulnerability_type_summary,
)
from sl_accessibility.accessibility.vulnerability import (
    attach_admin_context_to_hexes,
    audit_vulnerability_table,
    build_hidden_vulnerability_diagnostics,
    build_preliminary_vulnerability,
    build_vulnerability,
    vulnerability_score_stats,
)
from sl_accessibility.config import load_config, resolve_data_source
from sl_accessibility.data.contracts import CONTRACTS
from sl_accessibility.data.validation import validate_contract
from sl_accessibility.geo.hex_grid import build_analysis_hexes, hex_summary, write_analysis_hex_outputs
from sl_accessibility.io.csv_reader import CsvReadOptions, read_csv_sample, read_csv_schema, scan_csv
from sl_accessibility.population.local_resident import (
    aggregate_local_resident_250m_csvs,
    join_summary_to_grid,
)
from sl_accessibility.population.hex_features import (
    build_final_hex_demand_features,
    build_preliminary_hex_demand_features,
)
from sl_accessibility.population.mobility import (
    MOBILITY_ADDITIVE_COLUMNS,
    aggregate_life_mobility_od_admin_csv,
    build_hex_mobility_aux,
    build_mobility_admin_geography,
    profile_life_mobility_header,
)
from sl_accessibility.population.registered import (
    build_registered_population_admin_layer,
    parse_registered_population_xlsx,
)
from sl_accessibility.run_manifest import validate_run_manifest, write_run_manifest
from sl_accessibility.transit.d_candidates import (
    build_bus_d_candidates,
    build_subway_d_candidates,
    write_transit_d_candidates,
)

app = typer.Typer(help="서울 경사·기상 보행접근성 프로젝트 하네스")


@app.command("profile-data")
def profile_data(config_dir: str = "configs") -> None:
    config = load_config(config_dir)
    for name in config.data_sources:
        source = resolve_data_source(name, config)
        path_value = source.get("path") or source.get("glob")
        typer.echo(f"{name}: {path_value}")
        if source.get("path") and Path(source["path"]).exists():
            size_mb = Path(source["path"]).stat().st_size / 1024 / 1024
            typer.echo(f"  size_mb: {size_mb:.1f}")
            try:
                schema = read_csv_schema(source["path"], source.get("encoding", "utf-8"), n_rows=5)
                typer.echo(f"  columns: {', '.join(schema.keys())}")
            except Exception as exc:  # pragma: no cover - 진단용 CLI
                typer.echo(f"  schema_error: {exc}")


@app.command("validate-data")
def validate_data(config_dir: str = "configs", output: str = "outputs/reports/data_validation.json") -> None:
    config = load_config(config_dir)
    reports = []
    input_paths = []
    for name, contract in CONTRACTS.items():
        source_name = name
        if name == "poi":
            continue
        if source_name not in config.data_sources:
            continue
        source = resolve_data_source(source_name, config)
        path = source.get("path") or source.get("glob")
        paths = sorted(glob(path)) if source.get("glob") else [path]
        if not paths:
            raise FileNotFoundError(path)
        for sample_path in paths:
            input_paths.append(sample_path)
            sample = read_csv_sample(
                sample_path,
                CsvReadOptions(encoding=source.get("encoding", "utf-8")),
                n_rows=100,
            )
            report = validate_contract(sample, contract).to_dict()
            if source.get("glob"):
                report["path"] = sample_path
            reports.append(report)
    output_path = config.root / output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="validate-data",
        config=config,
        config_dir=config_dir,
        cli_args={"config_dir": config_dir, "output": output},
        inputs={"data_sources": input_paths},
        outputs={"report": output_path},
        anchor_path=output_path,
    )
    typer.echo(str(output_path))


@app.command("validate-run-manifest")
def validate_run_manifest_cmd(
    manifest: str,
    output: str | None = None,
    strict: bool = True,
) -> None:
    """run manifest의 파일 hash와 필수 스키마를 검증한다."""
    result = validate_run_manifest(manifest)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        typer.echo(f"{output_path} ({result['status']})")
    else:
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if strict and result["status"] != "pass":
        raise typer.Exit(code=1)


@app.command("build-edge-cost-sample")
def build_edge_cost_sample(
    config_dir: str = "configs",
    output: str = "data/interim/walking_edge_costs_sample.parquet",
    n_rows: int = 1000,
    rain_mm: float = 0.0,
    snow_cm: float = 0.0,
) -> None:
    """보행망 edge 샘플에 M0-M3 비용 컬럼을 붙여 Parquet로 저장한다."""
    config = load_config(config_dir)
    source = resolve_data_source("walking_edges", config)
    sample = read_csv_sample(
        source["path"],
        CsvReadOptions(encoding=source.get("encoding", "utf-8"), n_rows=n_rows),
        n_rows=n_rows,
    )
    params = CostParameters.from_mapping(config.model_params)
    rows = build_edge_cost_table(
        sample.to_dicts(),
        rain_mm=rain_mm,
        snow_cm=snow_cm,
        params=params,
    )
    output_path = config.root / output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(output_path)
    _write_cli_run_manifest(
        command="build-edge-cost-sample",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "output": output,
            "n_rows": n_rows,
            "rain_mm": rain_mm,
            "snow_cm": snow_cm,
        },
        inputs={"walking_edges": source["path"]},
        outputs={"parquet": output_path},
        anchor_path=output_path,
    )
    typer.echo(f"{output_path} ({len(rows)} rows)")


@app.command("build-edge-costs")
def build_edge_costs(
    config_dir: str = "configs",
    output: str = "data/interim/walking_edge_costs.parquet",
    rain_mm: float = 0.0,
    snow_cm: float = 0.0,
) -> None:
    """전체 보행망 edge에 M0-M3 비용 컬럼을 붙여 Parquet로 저장한다."""
    config = load_config(config_dir)
    source = resolve_data_source("walking_edges", config)
    params = CostParameters.from_mapping(config.model_params)
    frame = scan_csv(source["path"], CsvReadOptions(encoding=source.get("encoding", "utf-8")))
    output_path = config.root / output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    add_edge_cost_columns_lazy(frame, rain_mm=rain_mm, snow_cm=snow_cm, params=params).sink_parquet(
        output_path
    )
    row_count = pl.scan_parquet(output_path).select(pl.len()).collect().item()
    _write_cli_run_manifest(
        command="build-edge-costs",
        config=config,
        config_dir=config_dir,
        cli_args={"config_dir": config_dir, "output": output, "rain_mm": rain_mm, "snow_cm": snow_cm},
        inputs={"walking_edges": source["path"]},
        outputs={"parquet": output_path},
        anchor_path=output_path,
    )
    typer.echo(f"{output_path} ({row_count} rows)")


@app.command("build-analysis-hexes")
def build_analysis_hexes_cmd(
    config_dir: str = "configs",
    mask: str = "qgis/out_analysis_mask_5179_fixed.gpkg",
    output: str = "qgis/out_analysis_hex_h3res9.gpkg",
    resolution: int = 9,
) -> None:
    """분석영역 마스크에서 H3 hex와 중심점 레이어를 만든다."""
    config = load_config(config_dir)
    hexes = build_analysis_hexes(
        config.root / mask,
        resolution=resolution,
        mask_crs=config.crs_metric,
        output_crs=config.crs_metric,
    )
    output_path = config.root / output
    layer_suffix = f"h3res{resolution}"
    write_analysis_hex_outputs(
        hexes,
        output_path,
        hex_layer=f"out_analysis_hex_{layer_suffix}",
        centroid_layer=f"out_analysis_hex_centroids_{layer_suffix}",
    )
    summary = hex_summary(hexes)
    _write_cli_run_manifest(
        command="build-analysis-hexes",
        config=config,
        config_dir=config_dir,
        cli_args={"config_dir": config_dir, "mask": mask, "output": output, "resolution": resolution},
        inputs={"mask": config.root / mask},
        outputs={"gpkg": output_path},
        anchor_path=output_path,
    )
    typer.echo(f"{output_path} ({summary['rows']} hexes, {summary['crs']})")


@app.command("build-transit-d-candidates")
def build_transit_d_candidates_cmd(
    config_dir: str = "configs",
    output: str = "qgis/out_transit_d_candidates.gpkg",
    boundary: str = "qgis/wrk_seoul_boundary_5179.gpkg",
    boundary_buffer_m: float = 0.0,
) -> None:
    """버스/지하철 원자료에서 좌표가 유효한 서울 내부 D 후보 레이어를 만든다."""
    config = load_config(config_dir)
    bus_source = resolve_data_source("bus_ridership", config)
    subway_source = resolve_data_source("subway_ridership", config)
    bus = scan_csv(
        bus_source["path"],
        CsvReadOptions(
            encoding=bus_source.get("encoding", "utf-8"),
        ),
    )
    subway = scan_csv(
        subway_source["path"],
        CsvReadOptions(
            encoding=subway_source.get("encoding", "utf-8"),
            columns=["지하철역", "passengers", "lon", "lat", "location_matched"],
        ),
    )
    candidates = pl.concat(
        [
            build_bus_d_candidates(bus).collect(),
            build_subway_d_candidates(subway).collect(),
        ],
        how="vertical",
    )
    output_path = config.root / output
    inside_count, outside_count = write_transit_d_candidates(
        candidates,
        output_path,
        boundary_path=config.root / boundary if boundary else None,
        boundary_buffer_m=boundary_buffer_m,
    )
    _write_cli_run_manifest(
        command="build-transit-d-candidates",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "output": output,
            "boundary": boundary,
            "boundary_buffer_m": boundary_buffer_m,
        },
        inputs={
            "bus_ridership": bus_source["path"],
            "subway_ridership": subway_source["path"],
            "boundary": config.root / boundary if boundary else None,
        },
        outputs={"gpkg": output_path},
        anchor_path=output_path,
    )
    typer.echo(f"{output_path} ({inside_count} candidates, {outside_count} outside QA)")


@app.command("aggregate-local-resident-250m")
def aggregate_local_resident_250m_cmd(
    config_dir: str = "configs",
    output: str = "data/interim/local_resident_250m_grid_summary.parquet",
    chunksize: int = 250_000,
) -> None:
    """250m 생활인구 CSV 30일치를 격자당 1행 요약 테이블로 집계한다."""
    config = load_config(config_dir)
    source = resolve_data_source("local_resident_250m", config)
    summary = aggregate_local_resident_250m_csvs(
        source["glob"],
        encoding=source.get("encoding", "cp949"),
        chunksize=chunksize,
    )
    output_path = config.root / output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pl.from_pandas(summary).write_parquet(output_path)
    _write_cli_run_manifest(
        command="aggregate-local-resident-250m",
        config=config,
        config_dir=config_dir,
        cli_args={"config_dir": config_dir, "output": output, "chunksize": chunksize},
        inputs={"local_resident_250m": sorted(glob(source["glob"]))},
        outputs={"parquet": output_path},
        anchor_path=output_path,
    )
    typer.echo(f"{output_path} ({len(summary)} grids)")


@app.command("join-local-resident-grid")
def join_local_resident_grid_cmd(
    config_dir: str = "configs",
    grid: str = "qgis/wrk_livingpop_250m_grid_5179.gpkg",
    summary: str = "data/interim/local_resident_250m_grid_summary.parquet",
    output: str = "qgis/out_livingpop_250m_join_5179.gpkg",
    layer: str = "out_livingpop_250m_join_5179",
    grid_key: str = "CELL_ID",
) -> None:
    """250m 격자 polygon에 생활인구 요약값을 조인해 GeoPackage로 저장한다."""
    config = load_config(config_dir)
    summary_frame = pl.read_parquet(config.root / summary).to_pandas()
    joined = join_summary_to_grid(config.root / grid, summary_frame, grid_key=grid_key)
    output_path = config.root / output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joined.to_file(output_path, layer=layer, driver="GPKG")
    matched = int(joined["livingpop_joined"].sum())
    _write_cli_run_manifest(
        command="join-local-resident-grid",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "grid": grid,
            "summary": summary,
            "output": output,
            "layer": layer,
            "grid_key": grid_key,
        },
        inputs={"grid": config.root / grid, "summary": config.root / summary},
        outputs={"gpkg": output_path},
        anchor_path=output_path,
    )
    typer.echo(f"{output_path} ({matched}/{len(joined)} grids joined)")


@app.command("extract-registered-population")
def extract_registered_population_cmd(
    config_dir: str = "configs",
    output_parquet: str = "data/interim/registered_population_admin_2025q4.parquet",
    output_csv: str = "data/interim/registered_population_admin_2025q4.csv",
    report: str = "outputs/reports/registered_population_admin_qa.json",
) -> None:
    """서울시 등록인구 XLSX를 행정동 단위 정규화 테이블로 변환한다."""
    config = load_config(config_dir)
    source = resolve_data_source("registered_population", config)
    frame = parse_registered_population_xlsx(source["path"], sheet_name=source.get("sheet"))

    parquet_path = config.root / output_parquet
    csv_path = config.root / output_csv
    report_path = config.root / report
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_parquet(parquet_path, index=False)
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")

    duplicated_names = frame.loc[
        frame["admin_name"].duplicated(keep=False),
        ["district_name", "admin_name", "registered_population"],
    ].to_dict(orient="records")
    qa_report = {
        "source": source["path"],
        "sheet": source.get("sheet"),
        "record_count": int(len(frame)),
        "district_count": int(frame["district_name"].nunique()),
        "registered_population_total": int(frame["registered_population"].sum()),
        "registered_senior_population_total": int(frame["registered_senior_population"].sum()),
        "registered_senior_share_total": float(
            frame["registered_senior_population"].sum() / frame["registered_population"].sum()
        ),
        "duplicated_admin_name_count": int(frame["admin_name"].duplicated().sum()),
        "duplicated_admin_names": duplicated_names,
        "senior_age_definition": source.get("senior_age_definition", "65세 이상"),
        "spatial_status": source.get("spatial_status", "admin_boundary_required"),
        "status": "normalized: registered population table extracted; spatial allocation requires 행정동 boundary",
    }
    report_path.write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="extract-registered-population",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "output_parquet": output_parquet,
            "output_csv": output_csv,
            "report": report,
        },
        inputs={"registered_population": source["path"]},
        outputs={"parquet": parquet_path, "csv": csv_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{parquet_path} ({len(frame)} admin dongs)")
    typer.echo(str(csv_path))
    typer.echo(str(report_path))


@app.command("build-registered-admin-layer")
def build_registered_admin_layer_cmd(
    config_dir: str = "configs",
    boundary: str = "qgis/BND_ADM_DONG_PG/BND_ADM_DONG_PG.shp",
    population_csv: str = "data/interim/registered_population_admin_2025q4.csv",
    output: str = "qgis/wrk_registered_population_admin_5179.gpkg",
    layer: str = "wrk_registered_population_admin_5179",
    report: str = "outputs/reports/registered_population_admin_layer_qa.json",
    boundary_layer: str | None = None,
    boundary_encoding: str = "cp949",
) -> None:
    """서울 행정동 경계에 등록인구를 조인해 final demand 입력 레이어를 만든다."""
    config = load_config(config_dir)
    population = pd.read_csv(config.root / population_csv)
    joined, qa_report = build_registered_population_admin_layer(
        config.root / boundary,
        population,
        boundary_layer=boundary_layer,
        boundary_encoding=boundary_encoding,
        target_crs=config.crs_metric,
    )

    output_path = config.root / output
    report_path = config.root / report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joined.to_file(output_path, layer=layer, driver="GPKG")
    qa_report["output"] = str(output_path)
    qa_report["layer"] = layer
    report_path.write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-registered-admin-layer",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "boundary": boundary,
            "population_csv": population_csv,
            "output": output,
            "layer": layer,
            "report": report,
            "boundary_layer": boundary_layer,
            "boundary_encoding": boundary_encoding,
        },
        inputs={"boundary": config.root / boundary, "population_csv": config.root / population_csv},
        outputs={"gpkg": output_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{output_path} ({len(joined)} admin dongs)")
    typer.echo(str(report_path))


@app.command("build-hex-demand-prelim")
def build_hex_demand_prelim_cmd(
    config_dir: str = "configs",
    output_gpkg: str = "qgis/out_hex_demand_features_prelim_h3res9.gpkg",
    output_parquet: str = "data/derived/hex_demand_features_prelim_h3res9.parquet",
    report: str = "outputs/reports/hex_demand_features_prelim_qa.json",
    layer: str = "out_hex_demand_features_prelim_h3res9",
) -> None:
    """생활인구와 POI를 H3 res9로 재집계한 수요 피처 초안을 만든다."""
    config = load_config(config_dir)
    commercial_source = resolve_data_source("commercial_poi", config)
    medical_source = resolve_data_source("medical_poi", config)
    senior_welfare_source = resolve_data_source("senior_welfare_poi", config)
    poi_sources = {
        "commercial": commercial_source["path"],
        "medical": medical_source["path"],
        "senior_welfare": senior_welfare_source["path"],
    }
    features = build_preliminary_hex_demand_features(
        hex_path=config.root / "qgis/out_analysis_hex_h3res9.gpkg",
        living_grid_path=config.root / "qgis/out_livingpop_250m_join_5179.gpkg",
        poi_sources=poi_sources,
    )
    gpkg_path = config.root / output_gpkg
    parquet_path = config.root / output_parquet
    report_path = config.root / report
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_file(gpkg_path, layer=layer, driver="GPKG")
    features.drop(columns="geometry").to_parquet(parquet_path, index=False)
    qa_report = {
        "hex_count": int(len(features)),
        "crs": str(features.crs),
        "nonzero_living_hex_count": int((features["living_mean_living_population"] > 0).sum()),
        "nonzero_poi_hex_count": int((features["poi_total_count"] > 0).sum()),
        "mean_living_population_sum": float(features["living_mean_living_population"].sum()),
        "mean_senior_population_sum": float(features["living_mean_senior_population"].sum()),
        "poi_total_sum": int(features["poi_total_count"].sum()),
        "commercial_poi_sum": int(features["commercial_poi_count"].sum()),
        "medical_poi_sum": int(features["medical_poi_count"].sum()),
        "senior_welfare_poi_sum": int(features["senior_welfare_poi_count"].sum()),
        "coverage_ratio_min": float(features["living_joined_coverage_ratio"].min()),
        "coverage_ratio_mean": float(features["living_joined_coverage_ratio"].mean()),
        "coverage_ratio_max": float(features["living_joined_coverage_ratio"].max()),
        "demand_index_min": float(features["demand_index_prelim"].min()),
        "demand_index_mean": float(features["demand_index_prelim"].mean()),
        "demand_index_max": float(features["demand_index_prelim"].max()),
        "status": "preliminary: uses living population and POI only; registered population is not yet joined",
    }
    report_path.write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-hex-demand-prelim",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "output_gpkg": output_gpkg,
            "output_parquet": output_parquet,
            "report": report,
            "layer": layer,
        },
        inputs={
            "analysis_hex": config.root / "qgis/out_analysis_hex_h3res9.gpkg",
            "living_grid": config.root / "qgis/out_livingpop_250m_join_5179.gpkg",
            "commercial_poi": commercial_source["path"],
            "medical_poi": medical_source["path"],
            "senior_welfare_poi": senior_welfare_source["path"],
        },
        outputs={"gpkg": gpkg_path, "parquet": parquet_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{gpkg_path} ({len(features)} hexes)")
    typer.echo(str(parquet_path))
    typer.echo(str(report_path))


@app.command("build-hex-demand-final")
def build_hex_demand_final_cmd(
    config_dir: str = "configs",
    registered_admin: str = "qgis/wrk_registered_population_admin_5179.gpkg",
    registered_admin_layer: str = "wrk_registered_population_admin_5179",
    output_gpkg: str = "qgis/out_hex_demand_features_final_h3res9.gpkg",
    output_parquet: str = "data/derived/hex_demand_features_final_h3res9.parquet",
    report: str = "outputs/reports/hex_demand_features_final_qa.json",
    layer: str = "out_hex_demand_features_final_h3res9",
) -> None:
    """등록인구 공간분배까지 포함한 H3 final 수요 피처를 만든다."""
    config = load_config(config_dir)
    registered_admin_path = config.root / registered_admin
    if not registered_admin_path.exists():
        raise typer.BadParameter(
            f"행정동 등록인구 polygon 레이어가 없습니다: {registered_admin_path}. "
            "행정동 경계에 registered_population_admin_2025q4를 먼저 조인해 주세요."
        )

    commercial_source = resolve_data_source("commercial_poi", config)
    medical_source = resolve_data_source("medical_poi", config)
    senior_welfare_source = resolve_data_source("senior_welfare_poi", config)
    poi_sources = {
        "commercial": commercial_source["path"],
        "medical": medical_source["path"],
        "senior_welfare": senior_welfare_source["path"],
    }
    features = build_final_hex_demand_features(
        hex_path=config.root / "qgis/out_analysis_hex_h3res9.gpkg",
        living_grid_path=config.root / "qgis/out_livingpop_250m_join_5179.gpkg",
        registered_admin_path=registered_admin_path,
        registered_admin_layer=registered_admin_layer,
        poi_sources=poi_sources,
    )

    gpkg_path = config.root / output_gpkg
    parquet_path = config.root / output_parquet
    report_path = config.root / report
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_file(gpkg_path, layer=layer, driver="GPKG")
    features.drop(columns="geometry").to_parquet(parquet_path, index=False)

    qa_report = {
        "hex_count": int(len(features)),
        "crs": str(features.crs),
        "registered_admin_layer": str(registered_admin_path),
        "registered_admin_layer_name": registered_admin_layer,
        "nonzero_living_hex_count": int((features["living_mean_living_population"] > 0).sum()),
        "nonzero_registered_hex_count": int((features["registered_population"] > 0).sum()),
        "nonzero_poi_hex_count": int((features["poi_total_count"] > 0).sum()),
        "registered_population_sum": float(features["registered_population"].sum()),
        "registered_senior_population_sum": float(features["registered_senior_population"].sum()),
        "mean_living_population_sum": float(features["living_mean_living_population"].sum()),
        "poi_total_sum": int(features["poi_total_count"].sum()),
        "registered_coverage_ratio_min": float(features["registered_hex_coverage_ratio"].min()),
        "registered_coverage_ratio_mean": float(features["registered_hex_coverage_ratio"].mean()),
        "registered_coverage_ratio_max": float(features["registered_hex_coverage_ratio"].max()),
        "demand_component_columns": [
            "registered_population_norm",
            "registered_senior_population_norm",
            "living_population_norm",
            "poi_total_norm",
        ],
        "demand_component_weights": {
            "registered_population_norm": 0.25,
            "registered_senior_population_norm": 0.25,
            "living_population_norm": 0.25,
            "poi_total_norm": 0.25,
        },
        "demand_index_min": float(features["demand_index_final"].min()),
        "demand_index_mean": float(features["demand_index_final"].mean()),
        "demand_index_max": float(features["demand_index_final"].max()),
        "status": "final: includes living population, registered population, registered senior population, and POI",
    }
    report_path.write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-hex-demand-final",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "registered_admin": registered_admin,
            "registered_admin_layer": registered_admin_layer,
            "output_gpkg": output_gpkg,
            "output_parquet": output_parquet,
            "report": report,
            "layer": layer,
        },
        inputs={
            "analysis_hex": config.root / "qgis/out_analysis_hex_h3res9.gpkg",
            "living_grid": config.root / "qgis/out_livingpop_250m_join_5179.gpkg",
            "registered_admin": registered_admin_path,
            "commercial_poi": commercial_source["path"],
            "medical_poi": medical_source["path"],
            "senior_welfare_poi": senior_welfare_source["path"],
        },
        outputs={"gpkg": gpkg_path, "parquet": parquet_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{gpkg_path} ({len(features)} hexes)")
    typer.echo(str(parquet_path))
    typer.echo(str(report_path))


@app.command("build-accessibility-prelim")
def build_accessibility_prelim_cmd(
    config_dir: str = "configs",
    output_gpkg: str = "qgis/out_hex_accessibility_prelim_M0_M3.gpkg",
    output_parquet: str = "data/derived/hex_accessibility_prelim_M0_M3.parquet",
    report: str = "outputs/reports/hex_accessibility_prelim_qa.json",
    layer: str = "out_hex_accessibility_prelim_M0_M3",
    max_origin_snap_m: float = 100.0,
    max_destination_snap_m: float = 100.0,
) -> None:
    """H3 origin에서 가장 가까운 대중교통 D까지 M0-M3 접근비용을 계산한다."""
    config = load_config(config_dir)
    nodes_source = resolve_data_source("walking_nodes", config)
    nodes = read_network_nodes(nodes_source["path"], crs=config.crs_metric)
    hexes = gpd.read_file(config.root / "qgis/out_analysis_hex_h3res9.gpkg", layer="out_analysis_hex_h3res9")
    centroids = gpd.read_file(
        config.root / "qgis/out_analysis_hex_h3res9.gpkg",
        layer="out_analysis_hex_centroids_h3res9",
    )
    d_candidates = gpd.read_file(config.root / "qgis/out_transit_d_candidates.gpkg", layer="out_transit_d_candidates")
    origin_snaps = snap_points_to_nodes(
        centroids,
        nodes,
        id_columns=["hex_id", "h3_res"],
        max_distance_m=max_origin_snap_m,
    )
    d_snaps = snap_points_to_nodes(
        d_candidates,
        nodes,
        id_columns=["mode", "stop_id", "stop_name"],
        max_distance_m=max_destination_snap_m,
    )
    edges = pd.read_parquet(
        config.root / "data/interim/walking_edge_costs.parquet",
        columns=["u", "v", *COST_COLUMNS],
    )
    accessibility = build_hex_accessibility_table(
        hexes,
        origin_snaps,
        d_snaps,
        edges,
        max_origin_snap_m=max_origin_snap_m,
        max_destination_snap_m=max_destination_snap_m,
    )

    gpkg_path = config.root / output_gpkg
    parquet_path = config.root / output_parquet
    report_path = config.root / report
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    accessibility.to_file(gpkg_path, layer=layer, driver="GPKG")
    accessibility.drop(columns="geometry").to_parquet(parquet_path, index=False)

    qa_report = {
        "hex_count": int(len(accessibility)),
        "origin_snap_valid_count": int(accessibility["origin_snap_valid"].sum()),
        "origin_snap_invalid_count": int((~accessibility["origin_snap_valid"]).sum()),
        "d_candidate_count": int(len(d_candidates)),
        "d_snap_valid_count": int(d_snaps["node_id"].notna().sum()),
        "d_snap_invalid_count": int(d_snaps["node_id"].isna().sum()),
        "max_origin_snap_m": max_origin_snap_m,
        "max_destination_snap_m": max_destination_snap_m,
        "origin_snap_distance_mean": float(accessibility["origin_snap_distance_m"].dropna().mean()),
        "origin_snap_distance_max": float(accessibility["origin_snap_distance_m"].dropna().max()),
    }
    for cost_column in COST_COLUMNS:
        access_column = f"access_{cost_column}"
        reachable_column = f"{access_column}_reachable"
        qa_report[f"{access_column}_reachable_count"] = int(accessibility[reachable_column].sum())
        qa_report[f"{access_column}_mean"] = float(accessibility[access_column].dropna().mean())
        qa_report[f"{access_column}_p90"] = float(accessibility[access_column].dropna().quantile(0.9))
    report_path.write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-accessibility-prelim",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "output_gpkg": output_gpkg,
            "output_parquet": output_parquet,
            "report": report,
            "layer": layer,
            "max_origin_snap_m": max_origin_snap_m,
            "max_destination_snap_m": max_destination_snap_m,
        },
        inputs={
            "walking_nodes": nodes_source["path"],
            "analysis_hex": config.root / "qgis/out_analysis_hex_h3res9.gpkg",
            "transit_d_candidates": config.root / "qgis/out_transit_d_candidates.gpkg",
            "walking_edge_costs": config.root / "data/interim/walking_edge_costs.parquet",
        },
        outputs={"gpkg": gpkg_path, "parquet": parquet_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{gpkg_path} ({len(accessibility)} hexes)")
    typer.echo(str(parquet_path))
    typer.echo(str(report_path))


@app.command("build-vulnerability-prelim")
def build_vulnerability_prelim_cmd(
    config_dir: str = "configs",
    output_gpkg: str = "qgis/out_hex_vulnerability_prelim.gpkg",
    output_parquet: str = "data/derived/hex_vulnerability_prelim.parquet",
    report: str = "outputs/reports/hex_vulnerability_prelim_qa.json",
    layer: str = "out_hex_vulnerability_prelim",
    vulnerable_quantile: float = 0.8,
    official_distance_m: float = 400.0,
) -> None:
    """preliminary demand와 M0-M3 접근비용으로 취약도와 숨은 취약지역을 만든다."""
    config = load_config(config_dir)
    demand = gpd.read_file(
        config.root / "qgis/out_hex_demand_features_prelim_h3res9.gpkg",
        layer="out_hex_demand_features_prelim_h3res9",
    )
    accessibility = pd.read_parquet(config.root / "data/derived/hex_accessibility_prelim_M0_M3.parquet")
    merged = demand.merge(
        accessibility.drop(columns=[column for column in ("h3_res",) if column in accessibility.columns]),
        on="hex_id",
        how="left",
    )
    vulnerability = build_preliminary_vulnerability(
        merged,
        vulnerable_quantile=vulnerable_quantile,
        official_distance_m=official_distance_m,
    )

    gpkg_path = config.root / output_gpkg
    parquet_path = config.root / output_parquet
    report_path = config.root / report
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    vulnerability.to_file(gpkg_path, layer=layer, driver="GPKG")
    vulnerability.drop(columns="geometry").to_parquet(parquet_path, index=False)

    valid = vulnerability["analysis_valid_prelim"]
    score_stats = vulnerability_score_stats(vulnerability.loc[valid, "vulnerability_m3_prelim"])
    report_body = {
        "hex_count": int(len(vulnerability)),
        "analysis_valid_count": int(valid.sum()),
        "analysis_invalid_count": int((~valid).sum()),
        "vulnerable_quantile": vulnerable_quantile,
        "vulnerability_threshold_prelim": _first_non_null_float(
            vulnerability["vulnerability_threshold_prelim"]
        ),
        "vulnerability_m3_prelim_min": score_stats["min"],
        "vulnerability_m3_prelim_median": score_stats["median"],
        "vulnerability_m3_prelim_max": score_stats["max"],
        "vulnerability_m3_prelim_mean": score_stats["mean"],
        "vulnerable_m3_prelim_count": int(vulnerability["vulnerable_m3_prelim"].sum()),
        "official_400m_ok_m0_count": int(vulnerability["official_400m_ok_m0"].sum()),
        "hidden_vulnerable_prelim_count": int(vulnerability["hidden_vulnerable_prelim"].sum()),
        "cost_gap_m3_minus_m0_mean": float(vulnerability["cost_gap_m3_minus_m0"].dropna().mean()),
        "cost_gap_m3_minus_m0_p90": float(vulnerability["cost_gap_m3_minus_m0"].dropna().quantile(0.9)),
        "status": "preliminary: demand uses living population and POI only",
    }
    report_path.write_text(json.dumps(report_body, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-vulnerability-prelim",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "output_gpkg": output_gpkg,
            "output_parquet": output_parquet,
            "report": report,
            "layer": layer,
            "vulnerable_quantile": vulnerable_quantile,
            "official_distance_m": official_distance_m,
        },
        inputs={
            "demand": config.root / "qgis/out_hex_demand_features_prelim_h3res9.gpkg",
            "accessibility": config.root / "data/derived/hex_accessibility_prelim_M0_M3.parquet",
        },
        outputs={"gpkg": gpkg_path, "parquet": parquet_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{gpkg_path} ({len(vulnerability)} hexes)")
    typer.echo(str(parquet_path))
    typer.echo(str(report_path))


@app.command("build-vulnerability-final")
def build_vulnerability_final_cmd(
    config_dir: str = "configs",
    output_gpkg: str = "qgis/out_hex_vulnerability_final.gpkg",
    output_parquet: str = "data/derived/hex_vulnerability_final.parquet",
    report: str = "outputs/reports/hex_vulnerability_final_qa.json",
    layer: str = "out_hex_vulnerability_final",
    vulnerable_quantile: float = 0.8,
    official_distance_m: float = 400.0,
) -> None:
    """final demand와 M0-M3 접근비용으로 취약도와 숨은 취약지역을 재산출한다."""
    config = load_config(config_dir)
    demand_path = config.root / "qgis/out_hex_demand_features_final_h3res9.gpkg"
    if not demand_path.exists():
        raise typer.BadParameter(
            f"final demand 레이어가 없습니다: {demand_path}. build-hex-demand-final을 먼저 실행해 주세요."
        )

    demand = gpd.read_file(demand_path, layer="out_hex_demand_features_final_h3res9")
    accessibility = pd.read_parquet(config.root / "data/derived/hex_accessibility_prelim_M0_M3.parquet")
    merged = demand.merge(
        accessibility.drop(columns=[column for column in ("h3_res",) if column in accessibility.columns]),
        on="hex_id",
        how="left",
    )
    vulnerability = build_vulnerability(
        merged,
        demand_col="demand_index_final",
        suffix="final",
        vulnerable_quantile=vulnerable_quantile,
        official_distance_m=official_distance_m,
    )

    gpkg_path = config.root / output_gpkg
    parquet_path = config.root / output_parquet
    report_path = config.root / report
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    vulnerability.to_file(gpkg_path, layer=layer, driver="GPKG")
    vulnerability.drop(columns="geometry").to_parquet(parquet_path, index=False)

    valid = vulnerability["analysis_valid_final"]
    hidden = vulnerability["hidden_vulnerable_final"]
    score_stats = vulnerability_score_stats(vulnerability.loc[valid, "vulnerability_m3_final"])
    report_body = {
        "hex_count": int(len(vulnerability)),
        "analysis_valid_count": int(valid.sum()),
        "analysis_invalid_count": int((~valid).sum()),
        "vulnerable_quantile": vulnerable_quantile,
        "vulnerability_threshold_final": _first_non_null_float(
            vulnerability["vulnerability_threshold_final"]
        ),
        "vulnerability_m3_final_min": score_stats["min"],
        "vulnerability_m3_final_median": score_stats["median"],
        "vulnerability_m3_final_max": score_stats["max"],
        "vulnerability_m3_final_mean": score_stats["mean"],
        "vulnerable_m3_final_count": int(vulnerability["vulnerable_m3_final"].sum()),
        "official_400m_ok_m0_count": int(vulnerability["official_400m_ok_m0"].sum()),
        "hidden_vulnerable_final_count": int(hidden.sum()),
        "hidden_vulnerable_registered_population_sum": float(
            vulnerability.loc[hidden, "registered_population"].sum()
        ),
        "hidden_vulnerable_registered_senior_population_sum": float(
            vulnerability.loc[hidden, "registered_senior_population"].sum()
        ),
        "cost_gap_m3_minus_m0_mean": float(vulnerability["cost_gap_m3_minus_m0"].dropna().mean()),
        "cost_gap_m3_minus_m0_p90": float(vulnerability["cost_gap_m3_minus_m0"].dropna().quantile(0.9)),
        "status": "final: demand includes registered population and registered senior population",
    }
    report_path.write_text(json.dumps(report_body, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-vulnerability-final",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "output_gpkg": output_gpkg,
            "output_parquet": output_parquet,
            "report": report,
            "layer": layer,
            "vulnerable_quantile": vulnerable_quantile,
            "official_distance_m": official_distance_m,
        },
        inputs={
            "demand": demand_path,
            "accessibility": config.root / "data/derived/hex_accessibility_prelim_M0_M3.parquet",
        },
        outputs={"gpkg": gpkg_path, "parquet": parquet_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{gpkg_path} ({len(vulnerability)} hexes)")
    typer.echo(str(parquet_path))
    typer.echo(str(report_path))


@app.command("build-vulnerability-typology")
def build_vulnerability_typology_cmd(
    config_dir: str = "configs",
    vulnerability_gpkg: str = "qgis/out_hex_vulnerability_final.gpkg",
    vulnerability_layer: str = "out_hex_vulnerability_final",
    output_gpkg: str = "qgis/out_hex_vulnerability_typology.gpkg",
    output_parquet: str = "data/derived/hex_vulnerability_typology.parquet",
    output_summary_csv: str = "outputs/reports/vulnerability_typology_summary.csv",
    report: str = "outputs/reports/vulnerability_typology_qa.json",
    layer: str = "out_hex_vulnerability_typology",
    suffix: str = "final",
    distance_quantile: float = 0.75,
    slope_share_threshold: float = 0.40,
    interaction_share_threshold: float = 0.25,
) -> None:
    """final vulnerability hex를 원인별 4유형으로 분류해 GeoPackage와 요약 CSV를 만든다.

    유형 정의:
      supply_shortage  - 정류장까지 거리가 멀어 취약 (S1 정류장 위치할당 대상)
      slope_vulnerable - 경사 비용 비율이 높아 취약 (S3 경사 개선 대상)
      weather_amplified - 경사×기상 상호작용이 커서 취약 (S4 기상 대응 대상)
      high_demand      - 수요 집중형 (서비스 수준 개선 논의 대상)
    """
    config = load_config(config_dir)
    vulnerability = gpd.read_file(config.root / vulnerability_gpkg, layer=vulnerability_layer)
    typed = classify_vulnerability_typology(
        vulnerability,
        suffix=suffix,
        distance_quantile=distance_quantile,
        slope_share_threshold=slope_share_threshold,
        interaction_share_threshold=interaction_share_threshold,
    )
    summary = vulnerability_type_summary(typed, suffix=suffix)

    gpkg_path = config.root / output_gpkg
    parquet_path = config.root / output_parquet
    summary_csv_path = config.root / output_summary_csv
    report_path = config.root / report
    for path in (gpkg_path, parquet_path, summary_csv_path, report_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    typed.to_file(gpkg_path, layer=layer, driver="GPKG")
    typed.drop(columns="geometry").to_parquet(parquet_path, index=False)
    summary.to_csv(summary_csv_path, index=False, encoding="utf-8-sig")

    type_counts = typed["vulnerability_type"].value_counts(dropna=True).to_dict()
    # 취약 hex 중 유형이 배정되지 않은 수: 분류 로직이 올바르면 항상 0이어야 한다
    vulnerable_mask_col = typed[f"vulnerable_m3_{suffix}"].fillna(False)
    vulnerable_no_type_count = int((vulnerable_mask_col & typed["vulnerability_type"].isna()).sum())
    non_vulnerable_count = int((~vulnerable_mask_col).sum())
    report_body = {
        "hex_count": int(len(typed)),
        "vulnerable_count": int(vulnerable_mask_col.sum()),
        "non_vulnerable_count": non_vulnerable_count,
        "type_counts": type_counts,
        "vulnerable_no_type_count": vulnerable_no_type_count,
        "suffix": suffix,
        "distance_quantile": distance_quantile,
        "slope_share_threshold": slope_share_threshold,
        "interaction_share_threshold": interaction_share_threshold,
        "status": "typology: 4-type classification of vulnerable hexes",
    }
    report_path.write_text(json.dumps(report_body, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-vulnerability-typology",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "vulnerability_gpkg": vulnerability_gpkg,
            "vulnerability_layer": vulnerability_layer,
            "output_gpkg": output_gpkg,
            "output_parquet": output_parquet,
            "output_summary_csv": output_summary_csv,
            "report": report,
            "layer": layer,
            "suffix": suffix,
            "distance_quantile": distance_quantile,
            "slope_share_threshold": slope_share_threshold,
            "interaction_share_threshold": interaction_share_threshold,
        },
        inputs={"vulnerability_gpkg": config.root / vulnerability_gpkg},
        outputs={
            "gpkg": gpkg_path,
            "parquet": parquet_path,
            "summary_csv": summary_csv_path,
            "report": report_path,
        },
        anchor_path=report_path,
    )

    typer.echo(f"{gpkg_path} ({len(typed)} hexes)")
    typer.echo(str(parquet_path))
    typer.echo(str(summary_csv_path))
    typer.echo(str(report_path))


def _first_non_null_float(values: pd.Series) -> float:
    """QA JSON에는 값이 없을 때도 크래시 대신 NaN을 남긴다."""
    non_null = values.dropna()
    if non_null.empty:
        return float("nan")
    return float(non_null.iloc[0])


def _float_matches(actual: float, expected: object, tolerance: float) -> bool:
    if expected is None:
        return False
    try:
        expected_float = float(expected)
    except (TypeError, ValueError):
        return False
    return bool(np.isclose(actual, expected_float, atol=tolerance, equal_nan=True))


@app.command("validate-vulnerability-final")
def validate_vulnerability_final_cmd(
    config_dir: str = "configs",
    parquet: str = "data/derived/hex_vulnerability_final.parquet",
    gpkg: str = "qgis/out_hex_vulnerability_final.gpkg",
    layer: str = "out_hex_vulnerability_final",
    qa_report: str = "outputs/reports/hex_vulnerability_final_qa.json",
    output: str = "outputs/reports/hex_vulnerability_final_audit.json",
    vulnerable_quantile: float = 0.8,
    official_distance_m: float = 400.0,
    tolerance: float = 1e-9,
    strict: bool = True,
) -> None:
    """final vulnerability Parquet/GPKG/QA JSON의 정의 일치성을 검사한다."""
    config = load_config(config_dir)
    parquet_path = config.root / parquet
    gpkg_path = config.root / gpkg
    qa_path = config.root / qa_report
    output_path = config.root / output

    parquet_frame = pd.read_parquet(parquet_path)
    gpkg_frame = gpd.read_file(gpkg_path, layer=layer)
    qa_body = json.loads(qa_path.read_text(encoding="utf-8"))

    parquet_audit = audit_vulnerability_table(
        parquet_frame,
        suffix="final",
        vulnerable_quantile=vulnerable_quantile,
        official_distance_m=official_distance_m,
        tolerance=tolerance,
    )
    gpkg_audit = audit_vulnerability_table(
        gpkg_frame.drop(columns="geometry"),
        suffix="final",
        vulnerable_quantile=vulnerable_quantile,
        official_distance_m=official_distance_m,
        tolerance=tolerance,
    )

    qa_comparison = {
        "hex_count_matches": parquet_audit["row_count"] == qa_body.get("hex_count"),
        "analysis_valid_count_matches": parquet_audit["analysis_valid_count"]
        == qa_body.get("analysis_valid_count"),
        "analysis_invalid_count_matches": parquet_audit["analysis_invalid_count"]
        == qa_body.get("analysis_invalid_count"),
        "vulnerable_count_matches": parquet_audit["vulnerable_count"]
        == qa_body.get("vulnerable_m3_final_count"),
        "hidden_count_matches": parquet_audit["hidden_vulnerable_count"]
        == qa_body.get("hidden_vulnerable_final_count"),
        "threshold_matches": _float_matches(
            parquet_audit["actual_threshold"],
            qa_body.get("vulnerability_threshold_final"),
            tolerance,
        ),
        "score_min_matches": _float_matches(
            parquet_audit["vulnerability_score_min"],
            qa_body.get("vulnerability_m3_final_min"),
            tolerance,
        ),
        "score_median_matches": _float_matches(
            parquet_audit["vulnerability_score_median"],
            qa_body.get("vulnerability_m3_final_median"),
            tolerance,
        ),
        "score_max_matches": _float_matches(
            parquet_audit["vulnerability_score_max"],
            qa_body.get("vulnerability_m3_final_max"),
            tolerance,
        ),
        "score_mean_matches": _float_matches(
            parquet_audit["vulnerability_score_mean"],
            qa_body.get("vulnerability_m3_final_mean"),
            tolerance,
        ),
    }
    gpkg_comparison = {
        "row_count_matches_parquet": gpkg_audit["row_count"] == parquet_audit["row_count"],
        "hex_id_set_matches_parquet": set(gpkg_frame["hex_id"]) == set(parquet_frame["hex_id"]),
        "analysis_valid_count_matches_parquet": gpkg_audit["analysis_valid_count"]
        == parquet_audit["analysis_valid_count"],
        "vulnerable_count_matches_parquet": gpkg_audit["vulnerable_count"] == parquet_audit["vulnerable_count"],
        "hidden_count_matches_parquet": gpkg_audit["hidden_vulnerable_count"]
        == parquet_audit["hidden_vulnerable_count"],
        "crs": str(gpkg_frame.crs),
        "crs_is_epsg_5179": bool(gpkg_frame.crs is not None and gpkg_frame.crs.to_epsg() == 5179),
        "geometry_valid_count": int(gpkg_frame.geometry.is_valid.sum()),
        "geometry_invalid_count": int((~gpkg_frame.geometry.is_valid).sum()),
        "geometry_all_valid": bool(gpkg_frame.geometry.is_valid.all()),
    }
    all_checks = [
        parquet_audit["hex_id_is_unique"],
        parquet_audit["threshold_matches_quantile"],
        parquet_audit["hidden_formula_ok"],
        parquet_audit["official_400m_formula_ok"],
        parquet_audit["cost_monotonic_ok"],
        parquet_audit["valid_required_null_ok"],
        parquet_audit["numeric_inf_ok"],
        gpkg_audit["hidden_formula_ok"],
        gpkg_comparison["row_count_matches_parquet"],
        gpkg_comparison["hex_id_set_matches_parquet"],
        gpkg_comparison["crs_is_epsg_5179"],
        gpkg_comparison["geometry_all_valid"],
        *qa_comparison.values(),
    ]
    report_body = {
        "status": "pass" if all(all_checks) else "fail",
        "parquet": str(parquet_path),
        "gpkg": str(gpkg_path),
        "qa_report": str(qa_path),
        "parquet_audit": parquet_audit,
        "gpkg_audit": gpkg_audit,
        "gpkg_comparison": gpkg_comparison,
        "qa_comparison": qa_comparison,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report_body, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="validate-vulnerability-final",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "parquet": parquet,
            "gpkg": gpkg,
            "layer": layer,
            "qa_report": qa_report,
            "output": output,
            "vulnerable_quantile": vulnerable_quantile,
            "official_distance_m": official_distance_m,
            "tolerance": tolerance,
            "strict": strict,
        },
        inputs={"parquet": parquet_path, "gpkg": gpkg_path, "qa_report": qa_path},
        outputs={"audit": output_path},
        anchor_path=output_path,
    )

    typer.echo(f"{output_path} ({report_body['status']})")
    if strict and report_body["status"] != "pass":
        raise typer.Exit(code=1)


@app.command("export-hidden-vulnerability-shortlist")
def export_hidden_vulnerability_shortlist_cmd(
    config_dir: str = "configs",
    vulnerability_gpkg: str = "qgis/out_hex_vulnerability_final.gpkg",
    vulnerability_layer: str = "out_hex_vulnerability_final",
    admin_boundary: str = "qgis/wrk_registered_population_admin_5179.gpkg",
    admin_layer: str = "wrk_registered_population_admin_5179",
    output_csv: str = "outputs/reports/hidden_vulnerability_final_shortlist.csv",
    output_gpkg: str = "qgis/out_hidden_vulnerability_final_shortlist.gpkg",
    output_layer: str = "out_hidden_vulnerability_final_shortlist",
    hidden_only: bool = True,
    limit: int = 0,
) -> None:
    """최종 취약 hex를 행정동명과 함께 읽기 쉬운 shortlist로 내보낸다."""
    config = load_config(config_dir)
    vulnerability = gpd.read_file(config.root / vulnerability_gpkg, layer=vulnerability_layer)
    admin = gpd.read_file(config.root / admin_boundary, layer=admin_layer)
    labelled = attach_admin_context_to_hexes(vulnerability, admin)

    flag_column = "hidden_vulnerable_final" if hidden_only else "vulnerable_m3_final"
    if flag_column not in labelled.columns:
        raise typer.BadParameter(f"{vulnerability_layer}에 {flag_column!r} 컬럼이 없습니다.")

    shortlist = labelled[labelled[flag_column].fillna(False)].copy()
    shortlist = shortlist.sort_values("vulnerability_m3_final", ascending=False)
    if limit > 0:
        shortlist = shortlist.head(limit).copy()
    shortlist["rank"] = range(1, len(shortlist) + 1)
    centroids = shortlist.geometry.representative_point()
    shortlist["centroid_x"] = centroids.x
    shortlist["centroid_y"] = centroids.y

    preferred_columns = [
        "rank",
        "district_name",
        "admin_name",
        "admin_code",
        "hex_id",
        "vulnerability_m3_final",
        "demand_index_final",
        "access_cost_m0",
        "access_cost_m3",
        "cost_gap_m3_minus_m0",
        "registered_population",
        "registered_senior_population",
        "hidden_vulnerable_final",
        "vulnerable_m3_final",
        "centroid_x",
        "centroid_y",
    ]
    csv_columns = [column for column in preferred_columns if column in shortlist.columns]

    csv_path = config.root / output_csv
    gpkg_path = config.root / output_gpkg
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)
    shortlist.loc[:, csv_columns].to_csv(csv_path, index=False, encoding="utf-8-sig")
    shortlist.to_file(gpkg_path, layer=output_layer, driver="GPKG")
    _write_cli_run_manifest(
        command="export-hidden-vulnerability-shortlist",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "vulnerability_gpkg": vulnerability_gpkg,
            "vulnerability_layer": vulnerability_layer,
            "admin_boundary": admin_boundary,
            "admin_layer": admin_layer,
            "output_csv": output_csv,
            "output_gpkg": output_gpkg,
            "output_layer": output_layer,
            "hidden_only": hidden_only,
            "limit": limit,
        },
        inputs={
            "vulnerability_gpkg": config.root / vulnerability_gpkg,
            "admin_boundary": config.root / admin_boundary,
        },
        outputs={"csv": csv_path, "gpkg": gpkg_path},
        anchor_path=csv_path,
    )

    typer.echo(f"{csv_path} ({len(shortlist)} hexes)")
    typer.echo(str(gpkg_path))


@app.command("export-hidden-vulnerability-diagnostics")
def export_hidden_vulnerability_diagnostics_cmd(
    config_dir: str = "configs",
    vulnerability_gpkg: str = "qgis/out_hex_vulnerability_final.gpkg",
    vulnerability_layer: str = "out_hex_vulnerability_final",
    admin_boundary: str = "qgis/wrk_registered_population_admin_5179.gpkg",
    admin_layer: str = "wrk_registered_population_admin_5179",
    output_csv: str = "outputs/reports/hidden_vulnerability_reason_diagnostics.csv",
    output_gpkg: str = "qgis/out_hidden_vulnerability_reason_diagnostics.gpkg",
    output_layer: str = "out_hidden_vulnerability_reason_diagnostics",
    report: str = "outputs/reports/hidden_vulnerability_reason_diagnostics_qa.json",
    official_distance_m: float = 400.0,
    high_quantile: float = 0.75,
) -> None:
    """hidden 취약지역별 수요/경사/기상/거리 원인 진단표를 내보낸다."""
    config = load_config(config_dir)
    vulnerability = gpd.read_file(config.root / vulnerability_gpkg, layer=vulnerability_layer)
    admin = gpd.read_file(config.root / admin_boundary, layer=admin_layer)
    labelled = attach_admin_context_to_hexes(vulnerability, admin)
    diagnostics = build_hidden_vulnerability_diagnostics(
        labelled,
        suffix="final",
        official_distance_m=official_distance_m,
        high_quantile=high_quantile,
    ).sort_values("vulnerability_m3_final", ascending=False)
    diagnostics["rank"] = range(1, len(diagnostics) + 1)
    centroids = diagnostics.geometry.representative_point()
    diagnostics["centroid_x"] = centroids.x
    diagnostics["centroid_y"] = centroids.y

    preferred_columns = [
        "rank",
        "district_name",
        "admin_name",
        "admin_code",
        "hex_id",
        "primary_reason",
        "vulnerability_m3_final",
        "demand_index_final",
        "demand_percentile_final",
        "access_cost_m0",
        "access_cost_m1",
        "access_cost_m2",
        "access_cost_m3",
        "cost_m3_percentile_final",
        "slope_increment_m1_m0",
        "weather_additive_increment_m2_m1",
        "interaction_increment_m3_m2",
        "total_env_increment_m3_m0",
        "env_penalty_percentile_final",
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
    ]
    csv_columns = [column for column in preferred_columns if column in diagnostics.columns]

    csv_path = config.root / output_csv
    gpkg_path = config.root / output_gpkg
    report_path = config.root / report
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics.loc[:, csv_columns].to_csv(csv_path, index=False, encoding="utf-8-sig")
    diagnostics.to_file(gpkg_path, layer=output_layer, driver="GPKG")

    report_body = {
        "hidden_vulnerable_count": int(len(diagnostics)),
        "primary_reason_counts": diagnostics["primary_reason"].value_counts(dropna=False).to_dict(),
        "top_district_counts": diagnostics["district_name"].value_counts(dropna=False).head(15).to_dict()
        if "district_name" in diagnostics.columns
        else {},
        "mean_total_env_increment_m3_m0": float(diagnostics["total_env_increment_m3_m0"].mean()),
        "median_total_env_increment_m3_m0": float(diagnostics["total_env_increment_m3_m0"].median()),
        "p90_total_env_increment_m3_m0": float(diagnostics["total_env_increment_m3_m0"].quantile(0.9)),
        "mean_slope_increment_m1_m0": float(diagnostics["slope_increment_m1_m0"].mean()),
        "mean_weather_additive_increment_m2_m1": float(
            diagnostics["weather_additive_increment_m2_m1"].mean()
        ),
        "mean_interaction_increment_m3_m2": float(diagnostics["interaction_increment_m3_m2"].mean()),
        "official_distance_m": official_distance_m,
        "high_quantile": high_quantile,
        "status": "diagnostic: explains hidden vulnerable hexes using M0-M3 increments and demand/cost percentiles",
    }
    report_path.write_text(json.dumps(report_body, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="export-hidden-vulnerability-diagnostics",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "vulnerability_gpkg": vulnerability_gpkg,
            "vulnerability_layer": vulnerability_layer,
            "admin_boundary": admin_boundary,
            "admin_layer": admin_layer,
            "output_csv": output_csv,
            "output_gpkg": output_gpkg,
            "output_layer": output_layer,
            "report": report,
            "official_distance_m": official_distance_m,
            "high_quantile": high_quantile,
        },
        inputs={
            "vulnerability_gpkg": config.root / vulnerability_gpkg,
            "admin_boundary": config.root / admin_boundary,
        },
        outputs={"csv": csv_path, "gpkg": gpkg_path, "report": report_path},
        anchor_path=report_path,
    )

    typer.echo(f"{csv_path} ({len(diagnostics)} hexes)")
    typer.echo(str(gpkg_path))
    typer.echo(str(report_path))


@app.command("profile-life-mobility-od")
def profile_life_mobility_od_cmd(
    config_dir: str = "configs",
    report: str = "outputs/reports/life_mobility_od_profile.json",
) -> None:
    """생활이동 OD 원본을 전체 로딩하지 않고 스키마와 파일 크기만 점검한다."""
    config = load_config(config_dir)
    source = resolve_data_source("life_mobility_admin", config)
    source_path = config.root / source["path"]
    schema = profile_life_mobility_header(source_path, encoding=source.get("encoding", "utf-8"))
    report_body = {
        "source": str(source_path),
        "source_size_bytes": int(source_path.stat().st_size),
        "encoding": source.get("encoding", "utf-8"),
        "access": source.get("access", "metadata_or_partitioned_only"),
        "schema": schema,
        "status": "profile only: use build-life-mobility-od-aux for chunk aggregation",
    }
    report_path = config.root / report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_body, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="profile-life-mobility-od",
        config=config,
        config_dir=config_dir,
        cli_args={"config_dir": config_dir, "report": report},
        inputs={"life_mobility_admin": source_path},
        outputs={"report": report_path},
        anchor_path=report_path,
    )
    typer.echo(str(report_path))


@app.command("build-life-mobility-od-aux")
def build_life_mobility_od_aux_cmd(
    config_dir: str = "configs",
    admin_boundary: str = "qgis/wrk_registered_population_admin_5179.gpkg",
    admin_layer: str = "wrk_registered_population_admin_5179",
    output_parquet: str = "data/interim/life_mobility_od_admin_aux.parquet",
    output_csv: str = "data/interim/life_mobility_od_admin_aux.csv",
    output_gpkg: str = "qgis/out_life_mobility_admin_aux_5179.gpkg",
    output_layer: str = "out_life_mobility_admin_aux_5179",
    report: str = "outputs/reports/life_mobility_od_aux_qa.json",
    chunksize: int = 500_000,
    max_rows: int | None = None,
    progress_every_chunks: int = 20,
    force: bool = False,
) -> None:
    """생활이동 OD를 행정동 이동압력 보조 지표로 chunk 집계한다."""
    config = load_config(config_dir)
    source = resolve_data_source("life_mobility_admin", config)
    source_path = config.root / source["path"]
    parquet_path = config.root / output_parquet
    csv_path = config.root / output_csv
    gpkg_path = config.root / output_gpkg
    report_path = config.root / report
    progress_report_path = report_path.with_name(f"{report_path.stem}.progress.json")
    for path in (parquet_path, csv_path, gpkg_path, report_path, progress_report_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    if not force and _life_mobility_outputs_are_reusable(
        source_path=source_path,
        parquet_path=parquet_path,
        csv_path=csv_path,
        gpkg_path=gpkg_path,
        report_path=report_path,
        max_rows=max_rows,
    ):
        typer.echo("기존 생활이동 OD 집계 산출물이 complete 상태라서 89GB CSV 읽기를 건너뜁니다.")
        typer.echo(f"{parquet_path} (reused)")
        typer.echo(str(gpkg_path))
        typer.echo(str(report_path))
        return

    def write_progress(progress: dict[str, object]) -> None:
        progress_body = {
            "source": source["path"],
            "max_rows": max_rows,
            "chunksize": chunksize,
            **progress,
        }
        progress_report_path.write_text(json.dumps(progress_body, ensure_ascii=False, indent=2), encoding="utf-8")
        typer.echo(
            "life mobility OD progress: "
            f"{progress_body['input_row_count']:,} rows, "
            f"{progress_body['chunk_index']:,} chunks"
        )

    boundary = gpd.read_file(config.root / admin_boundary, layer=admin_layer)
    mobility_geography = build_mobility_admin_geography(boundary)
    mobility, qa_report = aggregate_life_mobility_od_admin_csv(
        source_path,
        mobility_geography["mobility_admin_code"],
        encoding=source.get("encoding", "utf-8"),
        chunksize=chunksize,
        max_rows=max_rows,
        progress_every_chunks=progress_every_chunks if progress_every_chunks > 0 else None,
        progress_callback=write_progress if progress_every_chunks > 0 else None,
    )

    mobility.to_parquet(parquet_path, index=False)
    mobility.to_csv(csv_path, index=False, encoding="utf-8-sig")
    admin_output = mobility_geography.merge(mobility, on="mobility_admin_code", how="left")
    admin_output.to_file(gpkg_path, layer=output_layer, driver="GPKG")

    qa_report.update(
        {
            "admin_boundary": str(config.root / admin_boundary),
            "admin_layer": admin_layer,
            "output_parquet": str(parquet_path),
            "output_csv": str(csv_path),
            "output_gpkg": str(gpkg_path),
            "output_layer": output_layer,
            "progress_every_chunks": progress_every_chunks,
            "progress_report": str(progress_report_path) if progress_every_chunks > 0 else None,
        }
    )
    report_path.write_text(json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-life-mobility-od-aux",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "admin_boundary": admin_boundary,
            "admin_layer": admin_layer,
            "output_parquet": output_parquet,
            "output_csv": output_csv,
            "output_gpkg": output_gpkg,
            "output_layer": output_layer,
            "report": report,
            "chunksize": chunksize,
            "max_rows": max_rows,
            "progress_every_chunks": progress_every_chunks,
            "force": force,
        },
        inputs={"life_mobility_admin": source_path, "admin_boundary": config.root / admin_boundary},
        outputs={"parquet": parquet_path, "csv": csv_path, "gpkg": gpkg_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{parquet_path} ({len(mobility)} mobility admin units)")
    typer.echo(str(gpkg_path))
    typer.echo(str(report_path))


def _life_mobility_outputs_are_reusable(
    *,
    source_path: Path,
    parquet_path: Path,
    csv_path: Path,
    gpkg_path: Path,
    report_path: Path,
    max_rows: int | None,
) -> bool:
    if not all(path.exists() for path in (parquet_path, csv_path, gpkg_path, report_path)):
        return False
    try:
        report_body = json.loads(report_path.read_text(encoding="utf-8"))
        parquet_probe = pd.read_parquet(parquet_path, columns=["mobility_admin_code"])
    except Exception:
        return False
    expected_status = "sample" if max_rows is not None else "complete"
    return (
        report_body.get("status") == expected_status
        and report_body.get("max_rows") == max_rows
        and report_body.get("source_size_bytes") == int(source_path.stat().st_size)
        and int(report_body.get("input_row_count", 0)) > 0
        and len(parquet_probe) > 0
    )


def _write_cli_run_manifest(
    *,
    command: str,
    config_dir: str,
    config,
    cli_args: dict[str, object],
    inputs: dict[str, object],
    outputs: dict[str, object],
    anchor_path: Path,
) -> None:
    manifest_path = anchor_path.with_name(f"{anchor_path.stem}.manifest.json")
    write_run_manifest(
        manifest_path,
        command=command,
        config=config,
        config_dir=config_dir,
        cli_args=cli_args,
        inputs=inputs,
        outputs=outputs,
    )
    typer.echo(str(manifest_path))


@app.command("build-hex-mobility-aux")
def build_hex_mobility_aux_cmd(
    config_dir: str = "configs",
    mobility_admin: str = "data/interim/life_mobility_od_admin_aux.parquet",
    admin_boundary: str = "qgis/wrk_registered_population_admin_5179.gpkg",
    admin_layer: str = "wrk_registered_population_admin_5179",
    hex_path: str = "qgis/out_analysis_hex_h3res9.gpkg",
    hex_layer: str = "out_analysis_hex_h3res9",
    output_gpkg: str = "qgis/out_hex_mobility_aux_h3res9.gpkg",
    output_layer: str = "out_hex_mobility_aux_h3res9",
    output_parquet: str = "data/derived/hex_mobility_aux_h3res9.parquet",
    report: str = "outputs/reports/hex_mobility_aux_qa.json",
) -> None:
    """행정동 생활이동 보조 지표를 H3 분석 hex에 배분한다."""
    config = load_config(config_dir)
    hexes = gpd.read_file(config.root / hex_path, layer=hex_layer)
    boundary = gpd.read_file(config.root / admin_boundary, layer=admin_layer)
    mobility = pd.read_parquet(config.root / mobility_admin)
    features = build_hex_mobility_aux(hexes=hexes, admin_boundary=boundary, mobility_admin=mobility)

    gpkg_path = config.root / output_gpkg
    parquet_path = config.root / output_parquet
    report_path = config.root / report
    for path in (gpkg_path, parquet_path, report_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    features.to_file(gpkg_path, layer=output_layer, driver="GPKG")
    features.drop(columns="geometry").to_parquet(parquet_path, index=False)

    additive_sums = {column: float(features[column].sum()) for column in MOBILITY_ADDITIVE_COLUMNS}
    report_body = {
        "hex_count": int(len(features)),
        "crs": str(features.crs),
        "mobility_admin": str(config.root / mobility_admin),
        "admin_boundary": str(config.root / admin_boundary),
        "hex_with_mobility_count": int((features["mobility_total_trips"] > 0).sum()),
        "mobility_hex_coverage_ratio_min": float(features["mobility_hex_coverage_ratio"].min()),
        "mobility_hex_coverage_ratio_mean": float(features["mobility_hex_coverage_ratio"].mean()),
        "mobility_hex_coverage_ratio_max": float(features["mobility_hex_coverage_ratio"].max()),
        "mobility_aux_index_min": float(features["mobility_aux_index"].min()),
        "mobility_aux_index_mean": float(features["mobility_aux_index"].mean()),
        "mobility_aux_index_max": float(features["mobility_aux_index"].max()),
        "additive_sums": additive_sums,
        "status": "auxiliary: not mixed into final demand automatically",
    }
    report_path.write_text(json.dumps(report_body, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_cli_run_manifest(
        command="build-hex-mobility-aux",
        config=config,
        config_dir=config_dir,
        cli_args={
            "config_dir": config_dir,
            "mobility_admin": mobility_admin,
            "admin_boundary": admin_boundary,
            "admin_layer": admin_layer,
            "hex_path": hex_path,
            "hex_layer": hex_layer,
            "output_gpkg": output_gpkg,
            "output_layer": output_layer,
            "output_parquet": output_parquet,
            "report": report,
        },
        inputs={
            "mobility_admin": config.root / mobility_admin,
            "admin_boundary": config.root / admin_boundary,
            "hex_path": config.root / hex_path,
        },
        outputs={"gpkg": gpkg_path, "parquet": parquet_path, "report": report_path},
        anchor_path=report_path,
    )
    typer.echo(f"{gpkg_path} ({len(features)} hexes)")
    typer.echo(str(parquet_path))
    typer.echo(str(report_path))


if __name__ == "__main__":
    app()
