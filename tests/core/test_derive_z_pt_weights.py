"""Tests for the Z pt weight derivation: per-category smoothing settings,
the binned correction and its plotting."""

import numpy as np
import pytest

pytest.importorskip("ROOT")

import correctionlib  # noqa: E402
import ROOT  # noqa: E402

from xyh.process_corrections._pt import (  # noqa: E402
    SmoothingSettings,
    _binned_ratio,
    _choose_bandwidth,
    _compute_pt_weights_and_shifts,
    build_correction_set,
    scan_bandwidth,
)
from xyh.process_corrections.derive_z_pt_weights import (  # noqa: E402
    _resolve_smoothing_settings,
)

SMOOTHING = {
    "bw": 1.0,
    "n_samples": 10,
    "var_min": 0.0,
    "var_max": 100.0,
    "var_steps": 200,
    "bw_down_factor": 0.5,
    "bw_up_factor": 2.0,
    "bw_scan_min": 0.5,
    "bw_scan_max": 100.0,
    "bw_scan_steps": 20,
    "chi2_ndf_max": 1.0,
    "overrides": {
        "2024_nano_v15": {
            "mm_eq0j": {"bw": 5.0},
            "mm_eq1j": {"bw": 2.0, "n_samples": 20},
        },
    },
}
CATEGORIES = ["mm_eq0j", "mm_eq1j", "mm_eq2j"]


def _hist(name, values, errors=None):
    h = ROOT.TH1D(name, name, len(values), 0.0, 10.0 * len(values))
    h.Sumw2()
    for i, v in enumerate(values, start=1):
        h.SetBinContent(i, v)
        h.SetBinError(i, np.sqrt(v) if errors is None else errors[i - 1])
    return h


def test_resolve_defaults_for_campaign_without_overrides():
    settings = _resolve_smoothing_settings(
        SMOOTHING, "2025_nano_v15", CATEGORIES
    )
    assert set(settings) == set(CATEGORIES)
    assert all(s.bw == 1.0 and s.n_samples == 10 for s in settings.values())


def test_resolve_override_and_default_mix():
    settings = _resolve_smoothing_settings(
        SMOOTHING, "2024_nano_v15", CATEGORIES
    )
    assert settings["mm_eq0j"].bw == 5.0
    assert settings["mm_eq1j"] == SmoothingSettings(
        bw=2.0,
        n_samples=20,
        var_min=0.0,
        var_max=100.0,
        var_steps=200,
        bw_down_factor=0.5,
        bw_up_factor=2.0,
        bw_scan_min=0.5,
        bw_scan_max=100.0,
        bw_scan_steps=20,
        chi2_ndf_max=1.0,
    )
    assert settings["mm_eq2j"].bw == 1.0


def test_resolve_unknown_key_raises():
    smoothing = {
        **SMOOTHING,
        "overrides": {"c": {"mm_eq0j": {"sigma": 1.0}}},
    }
    with pytest.raises(ValueError, match="sigma"):
        _resolve_smoothing_settings(smoothing, "c", CATEGORIES)


def test_resolve_unknown_category_raises():
    smoothing = {**SMOOTHING, "overrides": {"c": {"mm_eq9j": {"bw": 1.0}}}}
    with pytest.raises(ValueError, match="mm_eq9j"):
        _resolve_smoothing_settings(smoothing, "c", CATEGORIES)


def test_binned_ratio_normalizes_and_handles_empty_bins():
    data = _hist("d", [100.0, 200.0, 300.0])
    proc = _hist("p", [100.0, 0.0, 600.0])
    edges, y, yerr = _binned_ratio(data, proc)
    np.testing.assert_allclose(edges, [0.0, 10.0, 20.0, 30.0])
    # Empty process bin: neutral ratio without uncertainty
    assert y[1] == 1.0 and yerr[1] == 0.0
    assert np.isfinite(y).all() and np.isfinite(yerr).all()


@pytest.fixture
def cset_path(tmp_path):
    settings = SmoothingSettings(
        bw=5.0,
        n_samples=5,
        var_min=0.0,
        var_max=40.0,
        var_steps=80,
        bw_down_factor=0.5,
        bw_up_factor=2.0,
        bw_scan_min=0.5,
        bw_scan_max=100.0,
        bw_scan_steps=20,
        chi2_ndf_max=1.0,
    )
    results, binned = {}, {}
    for n_jets in (0, 1):
        data = _hist("d", [400.0, 500.0, 600.0, 700.0])
        proc = _hist("p", [300.0, 400.0, 500.0, 600.0])
        other = _hist("o", [50.0, 50.0, 50.0, 50.0])
        nominal, shifts, b, _ = _compute_pt_weights_and_shifts(
            data, proc, other, settings, 0.1
        )
        results[n_jets], binned[n_jets] = (nominal, shifts), b
    cset = build_correction_set(results, "z", binned_results=binned)
    path = tmp_path / "z_pt.json"
    path.write_text(cset.model_dump_json(exclude_unset=True))
    return path


def test_binned_correction_variations_finite_and_evaluates(cset_path):
    cset = correctionlib.CorrectionSet.from_file(str(cset_path))
    assert "z_pt" in cset and "z_pt_binned" in cset
    corr = cset["z_pt_binned"]
    nominal = corr.evaluate(0, 5.0, "nominal")
    up = corr.evaluate(0, 5.0, "stat_up")
    down = corr.evaluate(0, 5.0, "stat_down")
    assert np.isfinite([nominal, up, down]).all()
    assert up > nominal > down
    # Out-of-range pt is clamped, missing variations raise
    assert corr.evaluate(1, 1000.0, "nominal") == pytest.approx(
        corr.evaluate(1, 35.0, "nominal")
    )
    with pytest.raises(IndexError):
        corr.evaluate(0, 5.0, "bw_up")


def test_plot_load_fills_binned(cset_path):
    from xyh.scripts.plot_z_pt_weights import load

    result = load(cset_path)
    assert set(result) == {0, 1}
    raw = result[0]["binned"]
    np.testing.assert_allclose(raw["centers"], [5.0, 15.0, 25.0, 35.0])
    assert (raw["errors"] > 0).all()
    assert np.isfinite(raw["values"]).all()


def _toy(curved, seed=1):
    rng = np.random.default_rng(seed)
    x = np.arange(2.5, 200.0, 5.0)
    err = np.full_like(x, 0.02)
    y = 1.0 + (0.2 * np.sin(x / 10.0) if curved else 0.0)
    return x, y + rng.normal(size=x.shape) * err, err


def test_scan_bandwidth_tiny_bw_interpolates_data_without_ndf():
    x, y, err = _toy(curved=True)
    chi2, ndf = scan_bandwidth(x, y, err, np.array([1e-3]))
    assert chi2[0] == pytest.approx(0.0, abs=1e-9)
    # The smoother is the identity: trace n, no degrees of freedom left
    assert ndf[0] == pytest.approx(0.0, abs=1e-9)


def test_scan_bandwidth_skips_invalid_bins():
    x, y, err = _toy(curved=False)
    err[3] = 0.0
    chi2, ndf = scan_bandwidth(x, y, err, np.array([5.0]))
    assert np.isfinite(chi2).all() and 0 < ndf[0] < len(x) - 1


def test_choose_bandwidth_curved_smaller_than_flat():
    bws = np.geomspace(0.5, 100.0, 40)
    bw_curved, scan = _choose_bandwidth(*_toy(curved=True), bws, 1.0)
    bw_flat, _ = _choose_bandwidth(*_toy(curved=False), bws, 1.0)
    assert bw_curved < bw_flat
    assert bw_flat == bws[-1]
    assert scan["chosen"] == bw_curved
    assert len(scan["chi2_ndf"]) == len(bws)


def test_choose_bandwidth_none_satisfying_picks_smallest():
    x, y, err = _toy(curved=True)
    bws = np.geomspace(20.0, 100.0, 5)
    bw, scan = _choose_bandwidth(x, y, err, bws, 1.0)
    assert bw == bws[0]


def test_settings_invalid_bw_string_raises():
    kwargs = {k: v for k, v in SMOOTHING.items() if k != "overrides"}
    kwargs["bw"] = "foo"
    with pytest.raises(ValueError, match="foo"):
        SmoothingSettings(**kwargs)


def test_resolve_auto_default_with_numeric_override():
    smoothing = {
        **SMOOTHING,
        "bw": "auto",
        "overrides": {"c": {"mm_eq0j": {"bw": 10.0}}},
    }
    settings = _resolve_smoothing_settings(smoothing, "c", CATEGORIES)
    assert settings["mm_eq0j"].bw == 10.0
    assert settings["mm_eq1j"].bw == "auto"
