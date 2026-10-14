"""Tests for the evaluation of correctionlib corrections in RDataFrame."""

import numpy as np
import pytest

ROOT = pytest.importorskip("ROOT")
correctionlib = pytest.importorskip("correctionlib")

from xyh.core.correctionlib_cpp import ensure_declared  # noqa: E402
from xyh.core.z_pt_reweighting import Binned, build_correction_set  # noqa: E402

EDGES = [0.0, 10.0, 20.0, 30.0]


@pytest.fixture
def correction_file(tmp_path):
    categories = ["mm_eq2j_eq1b", "mm_eq2j_eq2b", "mm_geq4j_eq1b"]
    norms = {c: 1.0 + 0.1 * i for i, c in enumerate(categories)}
    pts = {
        c: Binned(EDGES, [i + 0.1, i + 0.2, i + 0.3], [0.0] * 3)
        for i, c in enumerate(["mm_eq2j", "mm_eq3j", "mm_geq4j"])
    }
    path = tmp_path / "z_pt_weights.json"
    path.write_text(
        build_correction_set(norms, pts).model_dump_json(exclude_unset=True)
    )
    return path


def test_rdataframe_matches_python_evaluation(correction_file):
    n_jets = np.array([2, 2, 3, 5, 7, 0], dtype=np.int32)
    n_bjets = np.array([1, 2, 1, 1, 4, 0], dtype=np.int32)
    pt = np.array([5.0, 15.0, 25.0, 12.0, 500.0, 5.0])

    data_frame = ROOT.RDF.FromNumpy(
        {"n_jets": n_jets, "n_bjets": n_bjets, "pt": pt}
    )
    path = str(correction_file)
    expressions = {
        "norm": f'xyh_z_normalization("{path}", n_jets, n_bjets)',
        "pt_corr": f'xyh_z_pt_correction("{path}", n_jets, pt)',
    }
    for name, expression in expressions.items():
        ensure_declared(expression)
        data_frame = data_frame.Define(name, expression)
    result = data_frame.AsNumpy(["norm", "pt_corr"])

    cset = correctionlib.CorrectionSet.from_file(path)
    expected_norm = [
        cset["z_normalization"].evaluate(int(j), int(b))
        for j, b in zip(n_jets, n_bjets, strict=True)
    ]
    expected_pt = [
        cset["z_pt_correction"].evaluate(int(j), float(p))
        for j, p in zip(n_jets, pt, strict=True)
    ]
    assert result["norm"] == pytest.approx(expected_norm)
    assert result["pt_corr"] == pytest.approx(expected_pt)


def test_ensure_declared_ignores_unrelated_expressions():
    ensure_declared("pt_1 > 20")


def test_file_is_loaded_only_once(correction_file):
    n_events = 100_000
    data_frame = ROOT.RDF.FromNumpy(
        {
            "n_jets": np.full(n_events, 2, dtype=np.int32),
            "n_bjets": np.full(n_events, 1, dtype=np.int32),
            "pt": np.linspace(0.0, 40.0, n_events),
        }
    )
    path = str(correction_file)
    expressions = {
        "norm": f'xyh_z_normalization("{path}", n_jets, n_bjets)',
        "pt_corr": f'xyh_z_pt_correction("{path}", n_jets, pt)',
    }
    for name, expression in expressions.items():
        ensure_declared(expression)
        data_frame = data_frame.Define(name, expression)
    before = ROOT.xyh_n_correction_sets_loaded()
    data_frame.AsNumpy(["norm", "pt_corr"])
    # Both corrections share the single loaded file
    assert ROOT.xyh_n_correction_sets_loaded() - before == 1
