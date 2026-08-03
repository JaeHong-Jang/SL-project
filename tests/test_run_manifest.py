import json
from pathlib import Path

from sl_accessibility.config import ProjectConfig
from sl_accessibility.run_manifest import (
    build_run_manifest,
    file_sha256,
    stable_json_hash,
    validate_run_manifest,
    write_run_manifest,
)


def test_file_sha256_and_stable_json_hash_are_deterministic(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")

    assert file_sha256(path) == file_sha256(path)
    assert stable_json_hash({"b": 2, "a": 1}) == stable_json_hash({"a": 1, "b": 2})


def test_build_run_manifest_records_config_inputs_cli_args_and_outputs(tmp_path):
    config = _write_config(tmp_path)
    source = tmp_path / "data" / "source.csv"
    output = tmp_path / "data" / "out.parquet"
    source.parent.mkdir(parents=True)
    source.write_text("source", encoding="utf-8")
    output.write_text("output", encoding="utf-8")

    manifest = build_run_manifest(
        command="build-example",
        config=config,
        config_dir="configs",
        cli_args={"output": "data/out.parquet", "rain_mm": 2.0},
        inputs={"source": "data/source.csv"},
        outputs={"parquet": "data/out.parquet"},
    )

    assert manifest["schema_version"] == "1.0"
    assert manifest["command"] == "build-example"
    assert manifest["cli_args_hash"] == stable_json_hash(manifest["cli_args"])
    assert manifest["config"]["hash"]
    assert manifest["input_hash"]
    assert manifest["output_hash"]
    assert manifest["inputs"][0]["path"] == "data/source.csv"
    assert manifest["outputs"][0]["path"] == "data/out.parquet"
    assert manifest["inputs"][0]["sha256"] == file_sha256(source)
    assert manifest["outputs"][0]["sha256"] == file_sha256(output)


def test_validate_run_manifest_fails_after_output_changes(tmp_path):
    config = _write_config(tmp_path)
    source = tmp_path / "input.txt"
    output = tmp_path / "output.txt"
    source.write_text("input", encoding="utf-8")
    output.write_text("output", encoding="utf-8")
    manifest_path = tmp_path / "outputs" / "reports" / "example.manifest.json"

    write_run_manifest(
        manifest_path,
        command="example",
        config=config,
        config_dir="configs",
        cli_args={"output": "output.txt"},
        inputs={"source": "input.txt"},
        outputs={"output": "output.txt"},
    )
    assert validate_run_manifest(manifest_path)["status"] == "pass"

    output.write_text("changed", encoding="utf-8")
    result = validate_run_manifest(manifest_path)
    assert result["status"] == "fail"
    assert not result["file_checks"][-1]["hash_matches"]


def test_validate_run_manifest_fails_when_recorded_output_is_missing(tmp_path):
    config = _write_config(tmp_path)
    source = tmp_path / "input.txt"
    source.write_text("input", encoding="utf-8")
    manifest_path = tmp_path / "outputs" / "reports" / "missing-output.manifest.json"

    write_run_manifest(
        manifest_path,
        command="example",
        config=config,
        config_dir="configs",
        cli_args={"output": "missing.txt"},
        inputs={"source": "input.txt"},
        outputs={"output": "missing.txt"},
    )

    result = validate_run_manifest(manifest_path)

    assert result["status"] == "fail"
    output_check = result["file_checks"][-1]
    assert output_check["expected_exists"] is False
    assert output_check["exists"] is False
    assert output_check["exists_matches"]
    assert output_check["hash_matches"]


def test_validate_run_manifest_fails_after_cli_args_change(tmp_path):
    config = _write_config(tmp_path)
    source = tmp_path / "input.txt"
    output = tmp_path / "output.txt"
    source.write_text("input", encoding="utf-8")
    output.write_text("output", encoding="utf-8")
    manifest_path = tmp_path / "outputs" / "reports" / "example.manifest.json"

    write_run_manifest(
        manifest_path,
        command="example",
        config=config,
        config_dir="configs",
        cli_args={"output": "output.txt"},
        inputs={"source": "input.txt"},
        outputs={"output": "output.txt"},
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cli_args"]["output"] = "different.txt"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    result = validate_run_manifest(manifest_path)
    assert result["status"] == "fail"
    assert not result["cli_args_hash_matches"]


def test_validate_data_cli_writes_sidecar_manifest(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from sl_accessibility.cli import app

    data_path = tmp_path / "data" / "sample_edges.csv"
    data_path.parent.mkdir(parents=True)
    data_path.write_text(
        "\n".join(
            [
                "u,v,key,osmid,highway,length_m,elev_u_m,elev_v_m,elevation_diff_m,"
                "grade_percent,grade_abs_percent,slope_available,geometry_wkt",
                '1,2,0,10,residential,12.3,1.0,2.0,1.0,8.1,8.1,true,"LINESTRING (0 0, 1 1)"',
            ]
        ),
        encoding="utf-8",
    )
    _write_config(
        tmp_path,
        data_sources={"walking_edges": {"path": "data/sample_edges.csv", "encoding": "utf-8"}},
    )

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "validate-data",
            "--config-dir",
            "configs",
            "--output",
            "outputs/reports/data_validation.json",
        ],
    )

    assert result.exit_code == 0, result.output
    manifest_path = tmp_path / "outputs" / "reports" / "data_validation.manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["command"] == "validate-data"
    assert manifest["cli_args"] == {
        "config_dir": "configs",
        "output": "outputs/reports/data_validation.json",
    }
    assert validate_run_manifest(manifest_path)["status"] == "pass"


def _write_config(root: Path, data_sources: dict | None = None) -> ProjectConfig:
    config_dir = root / "configs"
    config_dir.mkdir()
    (config_dir / "default.yaml").write_text(
        json.dumps({"project": {"crs_metric": "EPSG:5179"}, "runtime": {"max_eager_bytes": 1}}),
        encoding="utf-8",
    )
    sources = data_sources or {"source": {}}
    (config_dir / "data_sources.yaml").write_text(
        json.dumps(sources, ensure_ascii=False),
        encoding="utf-8",
    )
    (config_dir / "model_params.yaml").write_text("alpha: 1\n", encoding="utf-8")
    return ProjectConfig(
        values={"project": {"crs_metric": "EPSG:5179"}, "runtime": {"max_eager_bytes": 1}},
        data_sources=sources,
        model_params={"alpha": 1},
        root=root,
    )
