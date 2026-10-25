"""Tests for the b-jet normalization correctionlib files.

The pure-Python tests do not require ROOT, so they run everywhere. The
RDataFrame tests verify the C++ helper `xyh_bjet_normalization` declared by
`xyh.core.correctionlib_cpp`, as for the Z corrections.
"""

import numpy as np
import pytest

from xyh.core.bjet_normalization import build_correction_set

# (channel, process, n_jets) -> scale factor
SCALE_FACTORS = {
    ("ee", "tt_tautau", 0): 1.1,
    ("ee", "tt_tautau", 1): 1.2,
    ("ee", "tt_tautau", 2): 1.3,
    ("ee", "tt_tautau", 3): 1.4,
    ("ee", "z_2e_2mu_rem", 1): 0.9,
    ("mm", "tt_tautau", 2): 2.0,
}


@pytest.fixture
def correction_path(tmp_path):
    path = tmp_path / "bjet_normalization.json"
    path.write_text(
        build_correction_set(
            SCALE_FACTORS, description="b-jet normalization for the test"
        ).model_dump_json(exclude_unset=True)
    )
    return path


def _correction(correction_path):
    correctionlib = pytest.importorskip("correctionlib")
    return correctionlib.CorrectionSet.from_file(str(correction_path))[
        "bjet_normalization"
    ]


def test_correction_inputs(correction_path):
    correction = _correction(correction_path)
    assert [v.name for v in correction.inputs] == [
        "channel",
        "process",
        "n_jets",
    ]


def test_evaluation_matches_scale_factors(correction_path):
    correction = _correction(correction_path)
    for (channel, process, n_jets), sf in SCALE_FACTORS.items():
        assert correction.evaluate(channel, process, n_jets) == pytest.approx(
            sf
        )


def test_n_jets_clamps_to_outer_bins(correction_path):
    correction = _correction(correction_path)
    # Above the highest edge, the open last bin is used
    assert correction.evaluate("ee", "tt_tautau", 7) == pytest.approx(1.4)
    assert correction.evaluate("mm", "tt_tautau", 7) == pytest.approx(2.0)


def test_missing_channel_and_process_evaluate_to_one(correction_path):
    correction = _correction(correction_path)
    assert correction.evaluate("tt", "tt_tautau", 0) == pytest.approx(1.0)
    assert correction.evaluate("ee", "zz", 1) == pytest.approx(1.0)


def test_rdataframe_matches_python_evaluation(correction_path):
    ROOT = pytest.importorskip("ROOT")
    from xyh.core.correctionlib_cpp import ensure_declared

    channels = ["ee", "ee", "ee", "mm", "tt"]
    processes = [
        "tt_tautau",
        "tt_tautau",
        "z_2e_2mu_rem",
        "tt_tautau",
        "tt_tautau",
    ]
    n_jets = [0, 1, 2, 2, 0]

    data_frame = ROOT.RDF.FromNumpy(
        {
            "channel": np.array(channels, dtype=object),
            "process": np.array(processes, dtype=object),
            "n_jets": np.array(n_jets, dtype=np.int32),
        }
    )
    path = str(correction_path)
    expression = f'xyh_bjet_normalization("{path}", channel, process, n_jets)'
    ensure_declared(expression)
    result = data_frame.Define("weight", expression).AsNumpy(["weight"])

    correction = _correction(correction_path)
    expected = [
        correction.evaluate(c, p, int(j))
        for c, p, j in zip(channels, processes, n_jets, strict=True)
    ]
    assert result["weight"] == pytest.approx(expected)
