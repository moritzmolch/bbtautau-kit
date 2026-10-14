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
