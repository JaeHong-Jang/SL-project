"""프로젝트 설정 파일을 한 곳에서 읽고 절대 경로로 풀어 주는 모듈.

하네스의 모든 실행 단위는 `configs/default.yaml`,
`configs/data_sources.yaml`, `configs/model_params.yaml`을 기준으로 움직인다.
데이터 경로를 코드에 직접 박아 넣지 않기 위해 이 모듈에서 root 기준 경로를
해결한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ProjectConfig:
    """YAML 설정 3종과 프로젝트 root를 함께 들고 다니는 설정 객체."""

    values: dict[str, Any]
    data_sources: dict[str, Any]
    model_params: dict[str, Any]
    root: Path

    @property
    def crs_metric(self) -> str:
        return self.values["project"]["crs_metric"]

    @property
    def max_eager_bytes(self) -> int:
        return int(self.values["runtime"]["max_eager_bytes"])


def repo_root(start: Path | None = None) -> Path:
    """현재 위치에서 위로 올라가며 프로젝트 root를 찾는다."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "configs").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return current


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config(config_dir: str | Path = "configs", root: Path | None = None) -> ProjectConfig:
    """기본 설정, 데이터 소스, 모형 파라미터 YAML을 모두 읽는다."""
    base = repo_root(root)
    cfg_dir = (base / config_dir).resolve()
    return ProjectConfig(
        values=_load_yaml(cfg_dir / "default.yaml"),
        data_sources=_load_yaml(cfg_dir / "data_sources.yaml"),
        model_params=_load_yaml(cfg_dir / "model_params.yaml"),
        root=base,
    )


def resolve_path(path_value: str | Path, config: ProjectConfig) -> Path:
    """상대 경로를 프로젝트 root 기준 절대 경로로 바꾼다."""
    path = Path(path_value)
    return path if path.is_absolute() else config.root / path


def resolve_data_source(name: str, config: ProjectConfig) -> dict[str, Any]:
    """데이터 소스 설정을 복사하고 `path`/`glob`을 절대 경로로 변환한다."""
    if name not in config.data_sources:
        raise KeyError(f"Unknown data source: {name}")
    source = dict(config.data_sources[name])
    for key in ("path", "glob"):
        if key in source:
            source[key] = str(resolve_path(source[key], config))
    return source
