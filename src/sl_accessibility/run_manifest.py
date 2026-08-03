"""파이프라인 실행 manifest를 만들고 검증하는 유틸리티."""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sl_accessibility.config import ProjectConfig, resolve_path

MANIFEST_SCHEMA_VERSION = "1.0"
CONFIG_FILENAMES = ("default.yaml", "data_sources.yaml", "model_params.yaml")
REQUIRED_TOP_LEVEL_KEYS = (
    "schema_version",
    "created_at_utc",
    "command",
    "project_root",
    "environment",
    "cli_args",
    "cli_args_hash",
    "config",
    "inputs",
    "input_hash",
    "outputs",
    "output_hash",
)


def file_sha256(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """파일 내용을 streaming 방식으로 읽어 SHA-256을 계산한다."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json_hash(value: Any) -> str:
    """dict/list 값을 정렬된 JSON 표현으로 바꿔 SHA-256을 계산한다."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_run_manifest(
    *,
    command: str,
    config: ProjectConfig,
    config_dir: str | Path,
    cli_args: dict[str, Any],
    inputs: dict[str, str | Path | list[str | Path] | None],
    outputs: dict[str, str | Path | list[str | Path] | None],
) -> dict[str, Any]:
    """입력/config/CLI 인자/출력 hash를 포함한 manifest 본문을 만든다."""
    input_entries = _path_entries(inputs, config=config)
    output_entries = _path_entries(outputs, config=config)
    config_entries = _config_entries(config=config, config_dir=config_dir)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "command": command,
        "project_root": str(config.root.resolve()),
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "cli_args": cli_args,
        "cli_args_hash": stable_json_hash(cli_args),
        "config": {
            "config_dir": str(resolve_path(config_dir, config)),
            "files": config_entries,
            "hash": _aggregate_hash(config_entries),
        },
        "inputs": input_entries,
        "input_hash": _aggregate_hash(input_entries),
        "outputs": output_entries,
        "output_hash": _aggregate_hash(output_entries),
    }


def write_run_manifest(
    path: str | Path,
    *,
    command: str,
    config: ProjectConfig,
    config_dir: str | Path,
    cli_args: dict[str, Any],
    inputs: dict[str, str | Path | list[str | Path] | None],
    outputs: dict[str, str | Path | list[str | Path] | None],
) -> dict[str, Any]:
    """manifest JSON을 쓰고 본문을 반환한다."""
    manifest = build_run_manifest(
        command=command,
        config=config,
        config_dir=config_dir,
        cli_args=cli_args,
        inputs=inputs,
        outputs=outputs,
    )
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def validate_run_manifest(path: str | Path) -> dict[str, Any]:
    """manifest의 필수 구조와 현재 파일 hash 일치 여부를 검증한다."""
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    project_root = _manifest_project_root(manifest, manifest_path)
    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in manifest]
    file_checks = [
        *_validate_entries(manifest.get("config", {}).get("files", []), root=project_root),
        *_validate_entries(manifest.get("inputs", []), root=project_root),
        *_validate_entries(manifest.get("outputs", []), root=project_root),
    ]
    schema_version_matches = manifest.get("schema_version") == MANIFEST_SCHEMA_VERSION
    cli_args_hash_matches = stable_json_hash(manifest.get("cli_args", {})) == manifest.get(
        "cli_args_hash"
    )
    config_hash_matches = _aggregate_hash(
        manifest.get("config", {}).get("files", [])
    ) == manifest.get("config", {}).get("hash")
    input_hash_matches = _aggregate_hash(manifest.get("inputs", [])) == manifest.get("input_hash")
    output_hash_matches = _aggregate_hash(manifest.get("outputs", [])) == manifest.get(
        "output_hash"
    )
    return {
        "manifest": str(manifest_path),
        "schema_version": manifest.get("schema_version"),
        "required_keys_present": not missing,
        "missing_keys": missing,
        "schema_version_matches": schema_version_matches,
        "cli_args_hash_matches": cli_args_hash_matches,
        "config_hash_matches": config_hash_matches,
        "input_hash_matches": input_hash_matches,
        "output_hash_matches": output_hash_matches,
        "file_checks": file_checks,
        "status": "pass"
        if not missing
        and schema_version_matches
        and cli_args_hash_matches
        and config_hash_matches
        and input_hash_matches
        and output_hash_matches
        and all(item["exists"] and item["exists_matches"] and item["hash_matches"] for item in file_checks)
        else "fail",
    }


def _config_entries(*, config: ProjectConfig, config_dir: str | Path) -> list[dict[str, Any]]:
    cfg_dir = resolve_path(config_dir, config)
    return [_file_entry(name, cfg_dir / name, config.root) for name in CONFIG_FILENAMES]


def _path_entries(
    paths: dict[str, str | Path | list[str | Path] | None], *, config: ProjectConfig
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for role, value in paths.items():
        if value is None:
            entries.append(_missing_entry(role, None, config.root))
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            entries.append(_file_entry(role, resolve_path(item, config), config.root))
    return entries


def _file_entry(role: str, path: Path, root: Path) -> dict[str, Any]:
    exists = path.exists()
    entry: dict[str, Any] = {
        "role": role,
        "path": _display_path(path, root),
        "exists": exists,
        "size_bytes": int(path.stat().st_size) if exists and path.is_file() else None,
        "sha256": file_sha256(path) if exists and path.is_file() else None,
    }
    return entry


def _missing_entry(role: str, path: str | Path | None, root: Path) -> dict[str, Any]:
    return {
        "role": role,
        "path": None if path is None else _display_path(Path(path), root),
        "exists": False,
        "size_bytes": None,
        "sha256": None,
    }


def _validate_entries(entries: list[dict[str, Any]], *, root: Path) -> list[dict[str, Any]]:
    checks = []
    for entry in entries:
        path_value = entry.get("path")
        path = _resolve_manifest_path(path_value, root) if path_value else None
        exists = bool(path and path.exists())
        actual_hash = file_sha256(path) if exists and path.is_file() else None
        expected_hash = entry.get("sha256")
        expected_exists = bool(entry.get("exists"))
        checks.append(
            {
                "role": entry.get("role"),
                "path": path_value,
                "exists": exists,
                "expected_exists": expected_exists,
                "exists_matches": exists == expected_exists,
                "hash_matches": actual_hash == expected_hash,
            }
        )
    return checks


def _resolve_manifest_path(path_value: str, root: Path) -> Path:
    native_path = Path(path_value)
    if native_path.is_absolute():
        return native_path
    translated = _windows_path_to_posix(path_value)
    if translated is not None:
        return translated
    path = Path(path_value.replace("\\", "/"))
    return root / path


def _manifest_project_root(manifest: dict[str, Any], manifest_path: Path) -> Path:
    value = manifest.get("project_root")
    if not value:
        return manifest_path.parent.resolve()
    path = Path(value)
    if not path.is_absolute():
        translated = _windows_path_to_posix(str(value))
        if translated is not None:
            path = translated
    return path.resolve()


def _windows_path_to_posix(path_value: str) -> Path | None:
    if len(path_value) < 3 or path_value[1] != ":" or path_value[2] not in ("\\", "/"):
        return None
    drive = path_value[0].lower()
    rest = path_value[3:].replace("\\", "/")
    return Path("/mnt") / drive / rest


def _aggregate_hash(entries: list[dict[str, Any]]) -> str:
    payload = [
        {
            "role": entry.get("role"),
            "path": entry.get("path"),
            "exists": entry.get("exists"),
            "size_bytes": entry.get("size_bytes"),
            "sha256": entry.get("sha256"),
        }
        for entry in entries
    ]
    return stable_json_hash(payload)


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
