"""대용량 CSV를 안전하게 샘플링하거나 lazy scan으로 여는 공통 유틸."""

from __future__ import annotations

from dataclasses import dataclass
from glob import glob
from pathlib import Path

import polars as pl


DEFAULT_MAX_EAGER_BYTES = 100 * 1024 * 1024


class LargeFileReadError(RuntimeError):
    """대용량 원본을 실수로 한 번에 읽으려 할 때 발생하는 예외."""


@dataclass(frozen=True)
class CsvReadOptions:
    """CSV reader 옵션 묶음.

    `columns`를 지정하면 필요한 컬럼만 읽어 대용량 원본의 메모리 사용량을 줄인다.
    """

    encoding: str = "utf-8"
    columns: list[str] | None = None
    n_rows: int | None = None
    ignore_errors: bool = True


def _normalize_encoding(encoding: str) -> str:
    lowered = encoding.lower().replace("_", "-")
    if lowered in {"utf-8", "utf8", "utf-8-sig"}:
        return "utf8"
    return encoding


def ensure_eager_allowed(path: Path, max_bytes: int = DEFAULT_MAX_EAGER_BYTES, *, force: bool = False) -> None:
    """큰 원본 CSV를 실수로 eager read하지 않도록 파일 크기를 확인한다."""
    if path.exists() and path.stat().st_size > max_bytes and not force:
        size_mb = path.stat().st_size / 1024 / 1024
        limit_mb = max_bytes / 1024 / 1024
        raise LargeFileReadError(
            f"{path}를 한 번에 읽지 않습니다 ({size_mb:.1f} MB > {limit_mb:.1f} MB). "
            "scan_csv(), 필요한 컬럼만 읽기, 샘플링, chunk 변환을 사용하세요."
        )


def scan_csv(path: str | Path, options: CsvReadOptions | None = None) -> pl.LazyFrame:
    """Polars lazy frame으로 CSV를 연다.

    실제 계산은 `.collect()`나 sink 단계에서 일어나므로 대용량 파일의 기본 경로로 쓴다.
    """
    opts = options or CsvReadOptions()
    return pl.scan_csv(
        str(path),
        encoding=_normalize_encoding(opts.encoding),
        has_header=True,
        ignore_errors=opts.ignore_errors,
    ).select(opts.columns) if opts.columns else pl.scan_csv(
        str(path),
        encoding=_normalize_encoding(opts.encoding),
        has_header=True,
        ignore_errors=opts.ignore_errors,
    )

def read_csv_sample(path: str | Path, options: CsvReadOptions | None = None, n_rows: int = 1000) -> pl.DataFrame:
    """CSV 앞부분만 읽는다.

    glob 패턴이면 첫 번째 매칭 파일만 읽어 스키마/계약 검증에 사용한다.
    """
    path_text = str(path)
    if any(token in path_text for token in ("*", "?", "[")):
        matches = sorted(glob(path_text))
        if not matches:
            raise FileNotFoundError(path_text)
        path_text = matches[0]
    opts = options or CsvReadOptions(n_rows=n_rows)
    read_rows = opts.n_rows or n_rows
    return pl.read_csv(
        path_text,
        encoding=_normalize_encoding(opts.encoding),
        columns=opts.columns,
        n_rows=read_rows,
        ignore_errors=opts.ignore_errors,
    )


def read_csv_eager(
    path: str | Path,
    options: CsvReadOptions | None = None,
    *,
    max_bytes: int = DEFAULT_MAX_EAGER_BYTES,
    force: bool = False,
) -> pl.DataFrame:
    """작은 CSV만 eager read한다.

    `force=True`가 아니면 `max_bytes`보다 큰 파일은 `LargeFileReadError`로 막는다.
    """
    path = Path(path)
    ensure_eager_allowed(path, max_bytes=max_bytes, force=force)
    opts = options or CsvReadOptions()
    return pl.read_csv(
        str(path),
        encoding=_normalize_encoding(opts.encoding),
        columns=opts.columns,
        n_rows=opts.n_rows,
        ignore_errors=opts.ignore_errors,
    )


def read_csv_schema(path: str | Path, encoding: str = "utf-8", n_rows: int = 50) -> dict[str, str]:
    """샘플 행으로 CSV 컬럼명과 Polars dtype 문자열을 반환한다."""
    sample = read_csv_sample(path, CsvReadOptions(encoding=encoding), n_rows=n_rows)
    return {name: str(dtype) for name, dtype in sample.schema.items()}
