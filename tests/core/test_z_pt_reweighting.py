"""Unit tests for the derivation of Z normalization and pt corrections."""

import correctionlib
import numpy as np
import pytest

from xyh.core.z_pt_reweighting import (
    Binned,
    build_correction_set,
    compute_normalization,
    compute_pt_correction,
    compute_pt_ratio,
    find_merge_groups,
    parse_multiplicities,
    smooth_gaussian,
)

EDGES = [0.0, 10.0, 20.0, 30.0]


def _hist(values):
    values = np.asarray(values, dtype=float)
    return Binned(EDGES, values, values.copy())


def test_normalization():
    data = _hist([100, 200, 300])
    z = _hist([200, 200, 200])
    others = [_hist([10, 20, 30])]
    norm, err = compute_normalization(data, z, others)
    assert norm == pytest.approx((600 - 60) / 600)
    assert err > 0


def test_normalization_without_z():
    assert compute_normalization(_hist([1, 1, 1]), _hist([0, 0, 0]), []) == (
        1.0,
        0.0,
    )


def test_pt_correction_matches_data():
    data = _hist([100, 200, 300])
    z = _hist([200, 200, 200])
    others = [_hist([10, 20, 30])]
    norm, err = compute_normalization(data, z, others)
    corr = compute_pt_correction(data, z, others, norm)
    prediction = z.values * norm * corr.values + np.sum(
        [h.values for h in others], axis=0
    )
    assert prediction == pytest.approx(data.values)


def test_pt_correction_empty_bins_and_clip():
    data = _hist([100, 0, 1000])
    z = _hist([100, 100, 0])
    corr = compute_pt_correction(data, z, [], max_value=1.5)
    assert corr.values.tolist() == [1.0, 1.0, 1.0]
    corr = compute_pt_correction(_hist([300, 1, 1]), z, [], max_value=1.5)
    assert corr.values[0] == 1.5


def test_rebin():
    h = Binned([0, 1, 2, 3, 4], [1, 2, 3, 4], [1, 2, 3, 4])
    r = h.rebin(2)
    assert r.edges.tolist() == [0, 2, 4]
    assert r.values.tolist() == [3, 7]
    with pytest.raises(ValueError):
        h.rebin(3)


def test_parse_multiplicities():
    assert parse_multiplicities("mm_eq2j") == 2
    assert parse_multiplicities("mm_geq4j") == 4
    with pytest.raises(ValueError):
        parse_multiplicities("mm_base")


def test_correction_set_evaluation():
    categories = ["mm_eq2j", "mm_eq3j", "mm_geq4j"]
    norms = {c: 1.0 + 0.1 * i for i, c in enumerate(categories)}
    pts = {
        c: Binned(EDGES, [i + 0.1, i + 0.2, i + 0.3], [0, 0, 0])
        for i, c in enumerate(categories)
    }
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set(norms, pts).model_dump_json(exclude_unset=True)
    )
    norm = cset["z_normalization"]
    pt = cset["z_pt_correction"]

    assert norm.evaluate(2) == pytest.approx(1.0)
    assert norm.evaluate(3) == pytest.approx(1.1)
    assert norm.evaluate(4) == pytest.approx(1.2)
    # Out-of-range multiplicities are clamped to the nearest bin
    assert norm.evaluate(7) == pytest.approx(1.2)
    assert norm.evaluate(0) == pytest.approx(1.0)

    assert pt.evaluate(2, 5.0) == pytest.approx(0.1)
    assert pt.evaluate(3, 15.0) == pytest.approx(1.2)
    assert pt.evaluate(5, 25.0) == pytest.approx(2.3)
    # Overflow in pt is clamped to the last bin
    assert pt.evaluate(2, 500.0) == pytest.approx(0.3)


def test_find_merge_groups():
    edges = np.arange(7.0)
    data = Binned(
        edges,
        [10000, 10000, 100, 100, 100, 100],
        [10000, 10000, 100, 100, 100, 100],
    )
    z = Binned(edges, [10000, 10000, 100, 100, 100, 100], [0.0] * 6)
    starts = find_merge_groups(data, z, [], 0.05)
    # First two bins are precise; the small ones are merged until < 5 %
    assert starts[:3] == [0, 1, 2]
    merged = data.merge(starts)
    assert merged.edges[0] == 0 and merged.edges[-1] == 6
    assert merged.values.sum() == data.values.sum()
    rel = np.sqrt(merged.variances) / merged.values
    assert (rel[:-1] < 0.05).all()


def test_find_merge_groups_remainder_joins_last_group():
    edges = np.arange(4.0)
    data = Binned(edges, [10000, 10000, 1], [10000, 10000, 1])
    z = Binned(edges, [1, 1, 1], [0.0] * 3)
    assert find_merge_groups(data, z, [], 0.05) == [0, 1]


def test_correction_set_stat_unc():
    pts = {"mm_eq2j": Binned(EDGES, [1.0, 2.0, 3.0], [0.04, 0.09, 0.16])}
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set({"mm_eq2j": 1.0}, pts).model_dump_json(
            exclude_unset=True
        )
    )
    unc = cset["z_pt_correction_stat_unc"]
    assert unc.evaluate(2, 5.0) == pytest.approx(0.2)
    assert unc.evaluate(2, 25.0) == pytest.approx(0.4)


def test_smooth_gaussian_constant_and_noise():
    edges = np.arange(0.0, 101.0, 2.0)
    n = len(edges) - 1
    rng = np.random.default_rng(1)
    noisy = Binned(edges, 1.0 + 0.1 * rng.normal(size=n), np.full(n, 0.01))
    smooth = smooth_gaussian(noisy, sigma=10.0, grid_step=1.0)
    assert len(smooth.values) == 100
    assert smooth.edges[0] == 0 and smooth.edges[-1] == 100
    # Smoothing reduces fluctuations and uncertainties
    assert smooth.values.std() < noisy.values.std()
    assert (smooth.variances < noisy.variances.max()).all()
    const = Binned(edges, np.full(n, 1.3), np.full(n, 0.01))
    assert smooth_gaussian(const, 5.0).values == pytest.approx(1.3)


def test_smooth_gaussian_ignores_invalid_bins():
    edges = np.arange(0.0, 11.0)
    values = np.full(10, 2.0)
    variances = np.full(10, 0.01)
    values[4], variances[4] = 1.0, 0.0  # invalid bin with factor 1
    smooth = smooth_gaussian(Binned(edges, values, variances), 2.0)
    assert smooth.values == pytest.approx(2.0)
    assert smooth_gaussian(
        Binned(edges, np.ones(10), np.zeros(10)), 2.0
    ).values == pytest.approx(1.0)
    # Far away from the only valid bin the nearest bin is used
    only = Binned(
        np.arange(0.0, 1001.0, 10.0),
        np.r_[2.0, np.ones(99)],
        np.r_[0.01, np.zeros(99)],
    )
    assert smooth_gaussian(only, 1.0).values[-1] == pytest.approx(2.0)


def test_pt_ratio_keeps_nonpositive_bins_and_weights():
    data = _hist([0, 100, 100])
    z = Binned(EDGES, [100.0, 100.0, 0.0], [0.0, 0.0, 0.0])
    ratio, weights = compute_pt_ratio(data, z, [])
    assert ratio.values.tolist() == [0.0, 1.0, 1.0]
    # Expected-variance weights: 1 / ((z + 0) / z**2) = z; zero without Z
    assert weights.tolist() == pytest.approx([100.0, 100.0, 0.0])
    # Statistical uncertainty of the bin contents only
    assert ratio.variances[1] == pytest.approx(100 / 100**2)


def test_pt_correction_excludes_normalization_uncertainty():
    data = _hist([100, 100, 100])
    z = Binned(EDGES, [100.0] * 3, [0.0] * 3)
    corr = compute_pt_correction(data, z, [])
    assert corr.variances == pytest.approx(100 / 100**2)


def test_smoothing_with_expected_weights_is_unbiased():
    rng = np.random.default_rng(3)
    edges = np.arange(0.0, 201.0, 2.0)
    z = Binned(edges, np.full(100, 50.0), np.zeros(100))
    biases = []
    for _ in range(200):
        d = rng.poisson(50.0, size=100).astype(float)
        ratio, w = compute_pt_ratio(Binned(edges, d, d.copy()), z, [], 1.0)
        biases.append(smooth_gaussian(ratio, 10.0, 2.0, w).values.mean() - 1)
    assert abs(np.mean(biases)) < 3 * np.std(biases) / np.sqrt(200)


def test_correction_set_normalization_unc():
    pts = {"mm_eq2j": Binned(EDGES, [1.0, 2.0, 3.0], [0.0] * 3)}
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set(
            {"mm_eq2j": 1.2}, pts, {"mm_eq2j": 0.03}
        ).model_dump_json(exclude_unset=True)
    )
    assert cset["z_normalization_stat_unc"].evaluate(2) == pytest.approx(0.03)


def test_correction_set_unsmoothed_ratios():
    smooth = {"mm_eq2j": Binned(EDGES, [1.0, 1.1, 1.2], [0.0] * 3)}
    raw = {"mm_eq2j": Binned(EDGES, [0.8, 1.3, 1.1], [0.04, 0.09, 0.16])}
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set(
            {"mm_eq2j": 1.0}, smooth, raw_pt_ratios=raw
        ).model_dump_json(exclude_unset=True)
    )
    assert cset["z_pt_ratio_unsmoothed"].evaluate(2, 15.0) == pytest.approx(1.3)
    assert cset["z_pt_ratio_unsmoothed_stat_unc"].evaluate(
        2, 25.0
    ) == pytest.approx(0.4)
    assert cset["z_pt_correction"].evaluate(2, 15.0) == pytest.approx(1.1)
