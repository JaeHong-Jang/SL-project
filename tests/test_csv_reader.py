from pathlib import Path

import pytest

from sl_accessibility.io.csv_reader import CsvReadOptions, LargeFileReadError, read_csv_eager, scan_csv

pl = pytest.importorskip("polars")

FIXTURES = Path(__file__).parent / "fixtures"


def test_large_file_guard_raises():
    path = FIXTURES / "sample_population.csv"
    with pytest.raises(LargeFileReadError):
        read_csv_eager(path, max_bytes=1)


def test_lazy_scan_projects_columns():
    path = FIXTURES / "sample_population.csv"
    frame = scan_csv(path, CsvReadOptions(columns=["250M격자"])).collect()
    assert frame.columns == ["250M격자"]
    assert frame["250M격자"].to_list() == ["다사52255325", "다사52255325"]
