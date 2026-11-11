"""Tests for the evaluation of correctionlib corrections in RDataFrame."""

import numpy as np
import pytest

ROOT = pytest.importorskip("ROOT")
correctionlib = pytest.importorskip("correctionlib")

from correctionlib import schemav2  # noqa: E402

from xyh.core.correctionlib_cpp import ensure_declared  # noqa: E402
from xyh.process_corrections import _norm, _pt  # noqa: E402

# NOTE: RDataFrame substitutes column names even inside string literals of an
# expression, so no column may be named like a token of the (tmp) file path;
# hence `boson_pt` instead of `pt`.

_X = np.array([5.0, 15.0, 25.0])
_JETS = {2: 0, 3: 1, 4: 2}
_NORM_KEYS = [(2, 1), (2, 2), (3, 1), (3, 2), (5, 1)]


@pytest.fixture
def correction_file(tmp_path):
    norm_results = {
        key: (
            1.0 + 0.1 * i,
            {
                "stat_up": 1.5 + 0.1 * i,
                "stat_down": 0.5 + 0.1 * i,
                "norm_other_up": 1.2 + 0.1 * i,
                "norm_other_down": 0.8 + 0.1 * i,
            },
        )
        for i, key in enumerate(_NORM_KEYS)
    }
    pt_results = {
        n_jets: (
            (_X, np.array([i + 0.1, i + 0.2, i + 0.3])),
            {
                "stat_up": (_X, np.array([i + 0.4, i + 0.5, i + 0.6])),
                "stat_down": (_X, np.array([i - 0.4, i - 0.5, i - 0.6])),
            },
        )
        for n_jets, i in _JETS.items()
    }
    norm_set = _norm.build_correction_set(norm_results, process_tag="z")
    pt_set = _pt.build_correction_set(pt_results, process_tag="z")

    # Both corrections in one file
    combined = schemav2.CorrectionSet(
        schema_version=2,
        corrections=[*norm_set.corrections, *pt_set.corrections],
    )
    path = tmp_path / "z_corrections.json"
    path.write_text(combined.model_dump_json(exclude_unset=True))
    return path


def _define(data_frame, path, variation):
    expressions = {
        "norm": (
            f'xyh_z_normalization("{path}", n_jets, n_bjets, "{variation}")'
        ),
        "pt_corr": (
            f'xyh_z_pt_correction("{path}", n_jets, boson_pt, "{variation}")'
        ),
    }
    for name, expression in expressions.items():
        ensure_declared(expression)
        data_frame = data_frame.Define(name, expression)
    return data_frame


@pytest.mark.parametrize("variation", ["nominal", "stat_up", "stat_down"])
def test_rdataframe_matches_python_evaluation(correction_file, variation):
    # Includes n_jets/n_bjets/pt out of range (clamped)
    n_jets = np.array([2, 2, 3, 3, 5, 0, 4], dtype=np.int32)
    n_bjets = np.array([1, 2, 1, 2, 1, 1, 7], dtype=np.int32)
    boson_pt = np.array([5.0, 15.0, 25.0, 12.0, 500.0, -5.0, 20.0])

    data_frame = ROOT.RDF.FromNumpy(
        {"n_jets": n_jets, "n_bjets": n_bjets, "boson_pt": boson_pt}
    )
    path = str(correction_file)
    result = _define(data_frame, path, variation).AsNumpy(
        ["norm", "pt_corr"]
    )

    cset = correctionlib.CorrectionSet.from_file(path)
    expected_norm = [
        cset["z_normalization"].evaluate(int(j), int(b), variation)
        for j, b in zip(n_jets, n_bjets, strict=True)
    ]
    expected_pt = [
        cset["z_pt"].evaluate(int(j), float(p), variation)
        for j, p in zip(n_jets, boson_pt, strict=True)
    ]
    assert result["norm"] == pytest.approx(expected_norm)
    assert result["pt_corr"] == pytest.approx(expected_pt)


def test_variations_differ_from_nominal(correction_file):
    data_frame = ROOT.RDF.FromNumpy(
        {
            "n_jets": np.array([2], dtype=np.int32),
            "n_bjets": np.array([1], dtype=np.int32),
            "boson_pt": np.array([5.0]),
        }
    )
    path = str(correction_file)
    nominal = _define(data_frame, path, "nominal").AsNumpy(
        ["norm", "pt_corr"]
    )
    up = _define(data_frame, path, "stat_up").AsNumpy(["norm", "pt_corr"])
    assert up["norm"][0] != pytest.approx(nominal["norm"][0])
    assert up["pt_corr"][0] != pytest.approx(nominal["pt_corr"][0])


def test_ensure_declared_ignores_unrelated_expressions():
    ensure_declared("pt_1 > 20")


def test_file_is_loaded_only_once(correction_file):
    n_events = 100_000
    data_frame = ROOT.RDF.FromNumpy(
        {
            "n_jets": np.full(n_events, 2, dtype=np.int32),
            "n_bjets": np.full(n_events, 1, dtype=np.int32),
            "boson_pt": np.linspace(0.0, 40.0, n_events),
        }
    )
    data_frame = _define(data_frame, str(correction_file), "nominal")
    before = ROOT.xyh_n_correction_sets_loaded()
    data_frame.AsNumpy(["norm", "pt_corr"])
    # Both corrections share the single loaded file
    assert ROOT.xyh_n_correction_sets_loaded() - before == 1
