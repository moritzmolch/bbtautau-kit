"""Tests for the per-category settings of the Z pt weight derivation."""

import pytest

pytest.importorskip("ROOT")

from xyh.shape_processor.derive_z_pt_weights import (  # noqa: E402
    DerivationSettings,
    resolve_settings,
)

SETTINGS = {
    "default": {"rebin": 1, "bandwidth": 1.0, "pt_clip": 100},
    "mm_eq2j": {"rebin": 2, "bandwidth": None},
}


def test_category_overrides_default():
    assert resolve_settings(SETTINGS, "mm_eq2j") == DerivationSettings(
        rebin=2, bandwidth=None, pt_clip=100
    )


def test_unlisted_category_uses_default():
    assert resolve_settings(SETTINGS, "mm_eq3j") == DerivationSettings(
        rebin=1, bandwidth=1.0, pt_clip=100
    )


def test_unknown_key_raises():
    with pytest.raises(TypeError):
        resolve_settings({"default": {"sigma": 1.0}}, "mm_eq2j")


def test_two_stage_derivation(tmp_path, monkeypatch):
    import correctionlib
    import numpy as np

    from xyh.core.z_pt_reweighting import Binned
    from xyh.shape_processor import derive_z_pt_weights as stage

    edges = np.arange(0.0, 101.0, 10.0)
    centers = 0.5 * (edges[:-1] + edges[1:])
    true_norm = {
        "mm_eq2j_eq1b": 0.8,
        "mm_eq2j_eq2b": 1.2,
        "mm_eq3j_eq1b": 1.1,
    }
    true_shape = {2: 1.0 + 0.004 * centers, 3: 1.2 - 0.003 * centers}
    z_hist = {
        "mm_eq2j_eq1b": 1000.0 + 0 * centers,
        "mm_eq2j_eq2b": 300.0 + 0 * centers,
        "mm_eq3j_eq1b": 500.0 + 0 * centers,
    }
    background = 50.0 + 0 * centers

    # Inclusive in b jets: the Z yields and backgrounds add up. The yields
    # are the z histograms times 10.
    jet_cats = {"mm_eq2j": ["mm_eq2j_eq1b", "mm_eq2j_eq2b"],
                "mm_eq3j": ["mm_eq3j_eq1b"]}
    effective = {
        jc: sum(true_norm[c] * z_hist[c][0] for c in cs)
        / sum(z_hist[c][0] for c in cs)
        for jc, cs in jet_cats.items()
    }

    def read(base_dir, inventory, category, variable):
        wrap = lambda v, e=edges: Binned(e, v, v)  # noqa: E731
        if variable == "yield":
            z = z_hist[category][:1] * 10
            bkg = background[:1] * 10
            data = true_norm[category] * z + bkg
            e = np.linspace(0, 1, 2)
            return wrap(data, e), wrap(z, e), [wrap(bkg, e)]
        n_jets = int(category.split("_")[1][2])
        z = sum(z_hist[c] for c in jet_cats[category])
        bkg = background * len(jet_cats[category])
        # The data follow the effective normalization and the true shape
        data = effective[category] * z * true_shape[n_jets] + bkg
        return wrap(data), wrap(z), [wrap(bkg)]

    monkeypatch.setattr(stage, "_read_processes", read)
    monkeypatch.setattr(stage, "load_inventory", lambda *a, **k: None)
    output = tmp_path / "out.json"
    stage.derive_z_pt_weights(
        "unused",
        {},
        "2024_nano_v15",
        "mm",
        # Empty by construction, must be ignored
        [*true_norm, "mm_eq0j_eq1b"],
        tmp_path,
        output,
        {"default": {}},
    )

    cset = correctionlib.CorrectionSet.from_file(str(output))
    for category, norm in true_norm.items():
        n_jets = int(category.split("_")[1][2])
        assert cset["z_normalization"].evaluate(
            n_jets, int(category[-2])
        ) == pytest.approx(norm)
    # The pt correction is the shape relative to the normalized prediction of
    # the jet multiplicity inclusive in b jets
    for n_jets in (2, 3):
        for pt, expected in zip(centers, true_shape[n_jets], strict=True):
            assert cset["z_pt_correction"].evaluate(
                n_jets, float(pt)
            ) == pytest.approx(expected)
