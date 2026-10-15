"""Unit tests for the xyh.core.binning module."""

import numpy as np
import pytest

from xyh.core.binning import (
    dump_binning_overrides,
    equipopulated_edges,
    load_binning_overrides,
    lookup_binning,
    set_binning,
)


def test_equipopulated_counts():
    rng = np.random.default_rng(1)
    values = rng.exponential(30.0, 10000)
    edges = equipopulated_edges(values, 10)
    counts, _ = np.histogram(values, bins=edges)
    assert len(counts) == 10
    assert counts.max() - counts.min() <= 1


def test_range_clips_outer_edges():
    values = np.linspace(-50, 150, 2001)
    edges = equipopulated_edges(values, 4, range=(0, 100))
    assert edges[0] == 0 and edges[-1] == 100
    assert len(edges) == 5


def test_precision_rounding():
    edges = equipopulated_edges(np.linspace(0.123456, 987.654, 1000), 2, precision=3)
    assert all(float(f"{e:.3g}") == e for e in edges)


def test_discrete_data_drops_duplicate_edges():
    values = np.repeat([0, 1, 2], 100)
    edges = equipopulated_edges(values, 10)
    assert edges == sorted(set(edges))
    assert len(edges) < 11


def test_nonfinite_ignored_and_errors():
    edges = equipopulated_edges([1, 2, 3, np.nan, np.inf], 2)
    assert edges[0] == 1 and edges[-1] == 3
    with pytest.raises(ValueError):
        equipopulated_edges([], 2)
    with pytest.raises(ValueError):
        equipopulated_edges([5, 5, 5], 2)


def test_roundtrip_and_lookup(tmp_path):
    overrides = {}
    set_binning(overrides, "c", "tt", "tt_base", "pt_1", [0, 1, 2])
    path = tmp_path / "sub" / "binning.json"
    dump_binning_overrides(overrides, path)
    loaded = load_binning_overrides(path)
    assert lookup_binning(loaded, "c", "tt", "tt_base", "pt_1") == [0, 1, 2]
    assert lookup_binning(loaded, "c", "tt", "tt_base", "eta_1") is None
    assert lookup_binning(None, "c", "tt", "tt_base", "pt_1") is None


def test_invalid_edges_rejected(tmp_path):
    overrides = {}
    set_binning(overrides, "c", "tt", "tt_base", "pt_1", [0, 2, 1])
    path = tmp_path / "binning.json"
    dump_binning_overrides(overrides, path)
    with pytest.raises(ValueError):
        load_binning_overrides(path)
