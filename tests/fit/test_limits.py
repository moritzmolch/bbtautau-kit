"""Unit tests for `xyh.fit.limits`."""

import csv

import pytest

from xyh.fit.limits import (
    LIMITS_CSV,
    LIMITS_JSON,
    LimitResult,
    collect_limits,
    find_limit_files,
    read_limits_json,
    write_limits_csv,
    write_limits_json,
)
from xyh.fit.mass_points import MassPoint

VALUES = {
    "exp_m2": 0.1,
    "exp_m1": 0.2,
    "exp": 0.3,
    "exp_p1": 0.4,
    "exp_p2": 0.5,
    "obs": 0.35,
}


def _result(ydm="y2b", hdm="h2tau", mx=2000, my=500):
    return LimitResult.from_values(MassPoint(ydm, hdm, mx, my), VALUES)


def _write_point(base, result):
    directory = (
        base / f"{result.ydm}_{result.hdm}" / f"mx{result.mx}_my{result.my}"
    )
    write_limits_json(result, directory / LIMITS_JSON)


def test_from_values_maps_point_and_values():
    result = _result()
    assert (result.ydm, result.hdm, result.mx, result.my) == (
        "y2b",
        "h2tau",
        2000,
        500,
    )
    assert result.exp == 0.3
    assert result.obs == 0.35
    assert result.unit == "pb"


def test_from_values_missing_key_raises():
    values = {k: v for k, v in VALUES.items() if k != "exp_p2"}
    with pytest.raises(KeyError, match="exp_p2"):
        LimitResult.from_values(MassPoint("a", "b", 1, 2), values)


def test_json_roundtrip_creates_parents(tmp_path):
    path = tmp_path / "a" / "b" / LIMITS_JSON
    write_limits_json(_result(), path)
    assert read_limits_json(path) == _result()


def test_find_limit_files_matches_only_point_layout(tmp_path):
    _write_point(tmp_path, _result())
    (tmp_path / "y2b_h2tau" / "other").mkdir(parents=True)
    (tmp_path / "y2b_h2tau" / "other" / LIMITS_JSON).write_text("{}")
    (tmp_path / LIMITS_JSON).write_text("{}")
    files = find_limit_files(tmp_path)
    assert [f.parent.name for f in files] == ["mx2000_my500"]


def test_collect_limits_sorted_by_decay_masses(tmp_path):
    results = [
        _result("y2tau", "h2b", 1000, 100),
        _result("y2b", "h2tau", 3000, 100),
        _result("y2b", "h2tau", 2000, 500),
        _result("y2b", "h2tau", 2000, 100),
    ]
    for r in results:
        _write_point(tmp_path, r)
    collected = collect_limits(tmp_path)
    assert [(r.ydm, r.mx, r.my) for r in collected] == [
        ("y2b", 2000, 100),
        ("y2b", 2000, 500),
        ("y2b", 3000, 100),
        ("y2tau", 1000, 100),
    ]


def test_collect_limits_empty_directory_returns_empty(tmp_path):
    assert collect_limits(tmp_path) == []


def test_write_limits_csv_header_and_rows(tmp_path):
    path = tmp_path / "sub" / LIMITS_CSV
    write_limits_csv([_result(), _result(mx=3000)], path)
    with path.open() as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == [
        "ydm",
        "hdm",
        "mx",
        "my",
        "exp_m2",
        "exp_m1",
        "exp",
        "exp_p1",
        "exp_p2",
        "obs",
        "unit",
    ]
    assert [r["mx"] for r in rows] == ["2000", "3000"]
    assert float(rows[0]["exp"]) == pytest.approx(0.3)
    assert rows[0]["unit"] == "pb"


def test_write_limits_csv_no_results_writes_header_only(tmp_path):
    path = tmp_path / LIMITS_CSV
    write_limits_csv([], path)
    assert len(path.read_text().strip().splitlines()) == 1
