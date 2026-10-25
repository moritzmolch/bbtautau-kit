"""Tests for the equipopulated binning derivation in `xyh.binning`."""

import numpy as np

from xyh.binning import (
    derive_binning,
    iter_value_files,
    resolve_binning_settings,
)
from xyh.core.binning import load_binning_overrides, lookup_binning


def _write_values(
    input_dir, campaign, channel, category, variable, dataset, values
):
    """Write a value file in the layout of the graph's binning mode."""
    path = (
        input_dir
        / campaign
        / f"{channel}__{category}"
        / variable
        / f"{dataset}.npz"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, values=values)


def _settings(**overrides):
    settings = {
        "n_bins": 10,
        "precision": None,
        "variables": {"pt_vis": {}, "m_vis": {"n_bins": 20}},
        "campaigns": {},
    }
    settings.update(overrides)
    return settings


def test_iter_value_files_parses_paths(tmp_path):
    _write_values(
        tmp_path, "2024", "tt", "tt_base", "pt_vis", "data_A", [1, 2, 3]
    )
    files = list(iter_value_files(tmp_path))
    assert files == [
        (
            "2024",
            "tt",
            "tt_base",
            "pt_vis",
            tmp_path / "2024" / "tt__tt_base" / "pt_vis" / "data_A.npz",
        )
    ]


def test_derive_binning_splits_events_equipopulated(tmp_path):
    rng = np.random.default_rng(1)
    values = rng.exponential(30.0, 4000)
    # Values are split across two datasets, as the graph writes one file per
    # dataset
    _write_values(
        tmp_path, "2024", "tt", "tt_base", "pt_vis", "data_A", values[:2000]
    )
    _write_values(
        tmp_path, "2024", "tt", "tt_base", "pt_vis", "data_B", values[2000:]
    )
    _write_values(tmp_path, "2024", "tt", "tt_base", "m_vis", "data_A", values)

    output_file = tmp_path / "binning.json"
    derive_binning(tmp_path, output_file, tmp_path / "plots", _settings())

    overrides = load_binning_overrides(output_file)
    edges = lookup_binning(overrides, "2024", "tt", "tt_base", "pt_vis")
    assert len(edges) == 11
    counts, _ = np.histogram(values, bins=edges)
    assert counts.max() - counts.min() <= 1

    # Per-variable `n_bins` overrides the top-level default
    edges_m = lookup_binning(overrides, "2024", "tt", "tt_base", "m_vis")
    assert len(edges_m) == 21

    # A control plot is written per campaign, category, and variable
    assert (tmp_path / "plots" / "2024" / "tt_base__pt_vis.png").exists()
    assert (tmp_path / "plots" / "2024" / "tt_base__m_vis.png").exists()


def test_derive_binning_applies_campaign_and_channel_overrides(tmp_path):
    values = np.linspace(0.0, 100.0, 1000)
    for campaign, channel, category in (
        ("2024", "tt", "tt_base"),
        ("2024", "mt", "mt_base"),
        ("2025", "tt", "tt_base"),
    ):
        _write_values(
            tmp_path, campaign, channel, category, "pt_vis", "data", values
        )

    settings = _settings(
        n_bins=4,
        variables={"pt_vis": {}},
        campaigns={
            "2024": {
                "n_bins": 8,
                "channels": {"tt": {"n_bins": 16}},
            }
        },
    )
    overrides = derive_binning(
        tmp_path, tmp_path / "binning.json", tmp_path / "plots", settings
    )
    assert (
        len(lookup_binning(overrides, "2024", "mt", "mt_base", "pt_vis")) == 9
    )
    assert (
        len(lookup_binning(overrides, "2024", "tt", "tt_base", "pt_vis")) == 17
    )
    assert (
        len(lookup_binning(overrides, "2025", "tt", "tt_base", "pt_vis")) == 5
    )


def test_resolve_binning_settings_precedence():
    settings = _settings(
        n_bins=100,
        variables={"x": {"n_bins": 30, "range": [0.0, 10.0]}},
        campaigns={
            "2024": {
                "n_bins": 80,
                "channels": {
                    "tt": {
                        "n_bins": 60,
                        "categories": {"tt_base": {"n_bins": 40}},
                    }
                },
            }
        },
    )
    # The variable-specific number of bins takes precedence over all scopes
    assert resolve_binning_settings(settings, "2024", "tt", "tt_base", "x") == (
        30,
        None,
        [0.0, 10.0],
    )
    assert resolve_binning_settings(settings, "2024", "tt", "tt_base", "y") == (
        40,
        None,
        None,
    )
    assert resolve_binning_settings(settings, "2024", "mt", "mt_base", "y") == (
        80,
        None,
        None,
    )
    assert resolve_binning_settings(settings, "2025", "mt", "mt_base", "y") == (
        100,
        None,
        None,
    )


def test_derive_binning_skips_unusable_data(tmp_path):
    _write_values(
        tmp_path, "2024", "tt", "tt_base", "pt_vis", "data", [5.0, 5.0, 5.0]
    )
    overrides = derive_binning(
        tmp_path, tmp_path / "binning.json", tmp_path / "plots", _settings()
    )
    assert overrides == {}
    assert load_binning_overrides(tmp_path / "binning.json") == {}
