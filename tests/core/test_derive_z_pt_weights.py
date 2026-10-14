"""Tests for the per-category settings of the Z pt weight derivation."""

import pytest

pytest.importorskip("ROOT")

from xyh.shape_processor.derive_z_pt_weights import (  # noqa: E402
    DerivationSettings,
    resolve_settings,
)

SETTINGS = {
    "default": {"rebin": 1, "smoothing_sigma": 1.0, "pt_clip": 100},
    "mm_eq2j": {"rebin": 2, "smoothing_sigma": None},
}


def test_category_overrides_default():
    assert resolve_settings(SETTINGS, "mm_eq2j") == DerivationSettings(
        rebin=2, smoothing_sigma=None, pt_clip=100
    )


def test_unlisted_category_uses_default():
    assert resolve_settings(SETTINGS, "mm_eq3j") == DerivationSettings(
        rebin=1, smoothing_sigma=1.0, pt_clip=100
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

    def read(base_dir, inventory, category, variable):
        n_jets = int(category.split("_")[1][2])
        z = z_hist[category]
        if variable == "yield":
            z, bkg, shape = z[:1] * 10, background[:1] * 10, 1.0
        else:
            bkg, shape = background, true_shape[n_jets]
        # The data follow the true normalization and shape
        data = true_norm[category] * z * shape + bkg
        wrap = lambda v: Binned(  # noqa: E731
            np.linspace(0, 1, len(v) + 1) if variable == "yield" else edges,
            v,
            v,
        )
        return wrap(data), wrap(z), [wrap(bkg)]

    monkeypatch.setattr(stage, "_read_processes", read)
    monkeypatch.setattr(stage, "load_inventory", lambda *a, **k: None)
    output = tmp_path / "out.json"
    stage.derive_z_pt_weights(
        "unused",
        {},
        "2024_nano_v15",
        "mm",
        list(true_norm),
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
    # The pt correction is the shape relative to the normalized prediction,
    # averaged over the b-jet categories of each jet multiplicity
    for n_jets in (2, 3):
        for pt, expected in zip(centers, true_shape[n_jets], strict=True):
            assert cset["z_pt_correction"].evaluate(
                n_jets, float(pt)
            ) == pytest.approx(expected)
