"""Unit tests for the derivation of Z normalization and pt corrections."""

import correctionlib
import numpy as np
import pytest

from xyh.core.z_pt_reweighting import (
    Binned,
    build_correction_set,
    compute_normalization,
    compute_pt_correction,
    find_merge_groups,
    parse_multiplicities,
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
    corr = compute_pt_correction(data, z, others, norm, err)
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
    assert parse_multiplicities("mm_eq2j_eq1b") == (2, 1)
    assert parse_multiplicities("mm_geq4j_geq3b") == (4, 3)
    with pytest.raises(ValueError):
        parse_multiplicities("mm_eq2j")


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
        for i, c in enumerate(categories)
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

    assert pt.evaluate(2, 1, 5.0) == pytest.approx(0.1)
    assert pt.evaluate(2, 2, 15.0) == pytest.approx(1.2)
    assert pt.evaluate(5, 4, 25.0) == pytest.approx(4.3)
    # Overflow in pt is clamped to the last bin
    assert pt.evaluate(2, 1, 500.0) == pytest.approx(0.3)


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
