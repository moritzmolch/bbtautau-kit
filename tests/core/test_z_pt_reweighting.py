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
    concatenate,
    find_merge_groups,
    is_possible_category,
    jet_category,
    parse_multiplicities,
    parse_n_jets,
    smooth_kernel,
    sparsify,
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


def test_pt_correction_empty_bins():
    data = _hist([100, 0, 1000])
    z = _hist([100, 100, 0])
    corr = compute_pt_correction(data, z, [])
    assert corr.values.tolist() == [1.0, 1.0, 1.0]
    corr = compute_pt_correction(_hist([300, 1, 1]), z, [])
    assert corr.values[0] == 3.0


def test_rebin():
    h = Binned([0, 1, 2, 3, 4], [1, 2, 3, 4], [1, 2, 3, 4])
    r = h.rebin(2)
    assert r.edges.tolist() == [0, 2, 4]
    assert r.values.tolist() == [3, 7]
    with pytest.raises(ValueError):
        h.rebin(3)


def test_parse_multiplicities():
    assert parse_multiplicities("mm_eq2j_eq1b") == (2, 1)
    assert parse_multiplicities("mm_geq4j_geq3b") == (4, 3)
    with pytest.raises(ValueError):
        parse_multiplicities("mm_eq2j")
    assert parse_n_jets("mm_geq4j") == 4
    assert parse_n_jets("mm_eq2j_eq1b") == 2
    with pytest.raises(ValueError):
        parse_n_jets("mm_base")
    assert jet_category("mm_geq4j_geq3b") == "mm_geq4j"
    with pytest.raises(ValueError):
        jet_category("mm_geq4j")


def test_is_possible_category():
    assert is_possible_category("mm_eq0j_eq0b")
    assert is_possible_category("mm_eq3j_geq3b")
    assert is_possible_category("mm_geq4j_geq3b")
    assert not is_possible_category("mm_eq0j_eq1b")
    assert not is_possible_category("mm_eq1j_eq2b")
    assert not is_possible_category("mm_eq2j_geq3b")


def test_correction_set_evaluation():
    categories = [
        "mm_eq2j_eq1b",
        "mm_eq2j_eq2b",
        "mm_eq3j_eq1b",
        "mm_geq4j_eq1b",
        "mm_geq4j_geq3b",
    ]
    norms = {c: 1.0 + 0.1 * i for i, c in enumerate(categories)}
    pts = {
        c: Binned(EDGES, [i + 0.1, i + 0.2, i + 0.3], [0, 0, 0])
        for i, c in enumerate(["mm_eq2j", "mm_eq3j", "mm_geq4j"])
    }
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set(norms, pts).model_dump_json(exclude_unset=True)
    )
    norm = cset["z_normalization"]
    pt = cset["z_pt_correction"]

    assert norm.evaluate(2, 1) == pytest.approx(1.0)
    assert norm.evaluate(2, 2) == pytest.approx(1.1)
    assert norm.evaluate(3, 1) == pytest.approx(1.2)
    # Out-of-range multiplicities are clamped to the nearest bin
    assert norm.evaluate(7, 1) == pytest.approx(1.3)
    assert norm.evaluate(7, 5) == pytest.approx(1.4)
    assert norm.evaluate(2, 3) == pytest.approx(1.1)
    assert norm.evaluate(3, 0) == pytest.approx(1.2)

    # The pt correction depends on the jet multiplicity only
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
        build_correction_set({"mm_eq2j_eq1b": 1.0}, pts).model_dump_json(
            exclude_unset=True
        )
    )
    unc = cset["z_pt_correction_stat_unc"]
    assert unc.evaluate(2, 5.0) == pytest.approx(0.2)
    assert unc.evaluate(2, 25.0) == pytest.approx(0.4)


def test_smooth_kernel_constant_and_noise():
    edges = np.arange(0.0, 101.0, 2.0)
    n = len(edges) - 1
    rng = np.random.default_rng(1)
    noisy = Binned(edges, 1.0 + 0.1 * rng.normal(size=n), np.full(n, 0.01))
    smooth = smooth_kernel(noisy, bandwidth=25.0, grid_factor=4)
    assert len(smooth.nominal.values) == 4 * n
    assert smooth.nominal.edges[0] == 0 and smooth.nominal.edges[-1] == 100
    # Smoothing reduces fluctuations and uncertainties
    assert smooth.nominal.values.std() < noisy.values.std()
    assert (smooth.nominal.variances < noisy.variances.max()).all()
    const = Binned(edges, np.full(n, 1.3), np.full(n, 0.0))
    smoothed = smooth_kernel(const, 10.0, grid_factor=2)
    assert smoothed.nominal.values == pytest.approx(1.3)
    # Without a shape the bandwidth variations do not change the curve
    for values in smoothed.variations.values():
        assert values == pytest.approx(1.3)


def test_smooth_kernel_is_reproducible_and_matches_the_formula():
    edges = np.arange(0.0, 11.0)
    values = np.arange(10.0)
    hist = Binned(edges, values, np.zeros(10))
    a = smooth_kernel(hist, 4.0, grid_factor=1)
    b = smooth_kernel(hist, 4.0, grid_factor=1)
    assert a.nominal.values == pytest.approx(b.nominal.values)
    # Without uncertainties the result is the plain kernel average
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = 0.3706506 * 4.0
    u = (centers[3] - centers) / width
    w = np.where(np.abs(u) <= 4, np.exp(-0.5 * u**2), 0.0)
    assert a.nominal.values[3] == pytest.approx((w * values).sum() / w.sum())
    # A larger bandwidth flattens the slope
    slope = lambda v: v[-1] - v[0]  # noqa: E731
    assert slope(a.variations["band_asym_up"]) < slope(a.nominal.values)
    assert slope(a.variations["band_asym_down"]) > slope(a.nominal.values)


def test_smooth_kernel_ignores_invalid_bins():
    edges = np.arange(0.0, 11.0)
    values = np.full(10, 2.0)
    variances = np.full(10, 0.0)
    values[4] = 100.0
    valid = np.ones(10, dtype=bool)
    valid[4] = False
    smooth = smooth_kernel(Binned(edges, values, variances), 2.0, valid)
    assert smooth.nominal.values == pytest.approx(2.0)
    # Far away from the only valid bin the nearest bin is used
    only = Binned(
        np.arange(0.0, 1001.0, 10.0), np.r_[2.0, np.ones(99)], np.zeros(100)
    )
    valid = np.r_[True, np.zeros(99, dtype=bool)]
    assert smooth_kernel(only, 1.0, valid, grid_factor=1).nominal.values[
        -1
    ] == pytest.approx(2.0)


def test_sparsify():
    edges = np.linspace(0, 100, 1001)
    values = np.where(edges[:-1] < 50, 1.0, 2.0)
    new_edges, new_values = sparsify(edges, values, 0.01)
    assert len(new_values) < 10
    assert new_edges[0] == 0 and new_edges[-1] == 100
    assert len(new_edges) == len(new_values) + 1
    flat_edges, flat_values = sparsify(edges, np.ones(1000))
    assert list(flat_edges) == [0, 100] and list(flat_values) == [1.0]


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


def test_correction_set_normalization_unc():
    pts = {"mm_eq2j": Binned(EDGES, [1.0, 2.0, 3.0], [0.0] * 3)}
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set(
            {"mm_eq2j_eq1b": 1.2}, pts, {"mm_eq2j_eq1b": 0.03}
        ).model_dump_json(exclude_unset=True)
    )
    assert cset["z_normalization_stat_unc"].evaluate(2, 1) == pytest.approx(
        0.03
    )


def test_correction_set_unsmoothed_ratios():
    smooth = {"mm_eq2j": Binned(EDGES, [1.0, 1.1, 1.2], [0.0] * 3)}
    raw = {"mm_eq2j": Binned(EDGES, [0.8, 1.3, 1.1], [0.04, 0.09, 0.16])}
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set(
            {"mm_eq2j_eq1b": 1.0}, smooth, raw_pt_ratios=raw
        ).model_dump_json(exclude_unset=True)
    )
    assert cset["z_pt_ratio_unsmoothed"].evaluate(2, 15.0) == pytest.approx(1.3)
    assert cset["z_pt_ratio_unsmoothed_stat_unc"].evaluate(
        2, 25.0
    ) == pytest.approx(0.4)
    assert cset["z_pt_correction"].evaluate(2, 15.0) == pytest.approx(1.1)


def test_merge_above():
    h = Binned([0, 10, 20, 30, 40], [1, 2, 3, 4], [1, 2, 3, 4])
    merged, has_tail = h.merge_above(20)
    assert has_tail
    assert merged.edges.tolist() == [0, 10, 20, 40]
    assert merged.values.tolist() == [1, 2, 7]
    # A bin containing pt_clip is kept
    assert h.merge_above(25)[0].edges.tolist() == [0, 10, 20, 30, 40]
    assert h.merge_above(25)[0].values.tolist() == [1, 2, 3, 4]
    merged, has_tail = h.merge_above(100)
    assert not has_tail and merged.values.tolist() == [1, 2, 3, 4]
    assert h.merge_above(0)[0].values.tolist() == [10]


def test_concatenate_and_slice():
    h = Binned([0, 1, 2, 3], [1, 2, 3], [1, 2, 3])
    joined = concatenate(h.slice(0, 2), h.slice(2))
    assert joined.edges.tolist() == h.edges.tolist()
    assert joined.values.tolist() == h.values.tolist()
    with pytest.raises(ValueError):
        concatenate(h.slice(0, 1), h.slice(2))


def test_correction_set_variations_and_stat_unc():
    pts = {"mm_eq2j": Binned(EDGES, [1.0, 1.1, 1.2], [0.0] * 3)}
    stat = {"mm_eq2j": Binned([0.0, 30.0], [0.05], [0.0])}
    var = {
        "band_asym_up": {"mm_eq2j": Binned([0.0, 15.0, 30.0], [1, 2], [0, 0])}
    }
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set(
            {"mm_eq2j_eq1b": 1.0},
            pts,
            pt_stat_uncs=stat,
            pt_variations=var,
        ).model_dump_json(exclude_unset=True)
    )
    assert cset["z_pt_correction_stat_unc"].evaluate(2, 5.0) == pytest.approx(
        0.05
    )
    assert cset["z_pt_correction_band_asym_up"].evaluate(
        2, 20.0
    ) == pytest.approx(2.0)


def test_correction_set_jet_normalizations():
    pts = {"mm_eq2j": Binned(EDGES, [1.0, 1.1, 1.2], [0.0] * 3)}
    cset = correctionlib.CorrectionSet.from_string(
        build_correction_set(
            {"mm_eq2j_eq1b": 1.0},
            pts,
            jet_normalizations={"mm_eq2j": 0.9, "mm_geq4j": 1.3},
            jet_normalization_errors={"mm_eq2j": 0.01, "mm_geq4j": 0.02},
        ).model_dump_json(exclude_unset=True)
    )
    assert cset["z_normalization_jets"].evaluate(2) == pytest.approx(0.9)
    assert cset["z_normalization_jets"].evaluate(5) == pytest.approx(1.3)
    assert cset["z_normalization_jets_stat_unc"].evaluate(
        4
    ) == pytest.approx(0.02)
