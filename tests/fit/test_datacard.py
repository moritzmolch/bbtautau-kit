"""Unit tests for `xyh.fit.datacard`."""

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from xyh.fit import datacard
from xyh.fit.datacard import (
    BinSpec,
    DatacardSpec,
    build_datacard_spec,
    datacard_script_command,
    read_spec,
    run_datacard_script,
    write_spec,
)
from xyh.fit.mass_points import MassPoint
from xyh.fit.scope import FitBin
from xyh.fit.shapes import BinShapes, Shape

POINT = MassPoint("y2b", "h2tau", 2000, 500)


def _shape():
    return Shape(np.array([0.0, 1.0]), np.array([1.0]), np.array([1.0]))


def _bin_shapes(signal=True, backgrounds=("tt", "dy")):
    return BinShapes(
        _shape() if signal else None,
        {name: _shape() for name in backgrounds},
        _shape(),
    )


@pytest.fixture
def spec():
    return DatacardSpec(
        analysis="xyh",
        mass=2000,
        bins=(
            BinSpec("c_tt_xyh", "c", "tt", ("signal",), ("dy", "tt")),
            BinSpec("c_tt_t_tt", "c", "tt", (), ("dy",)),
        ),
        auto_mc_stats=10.0,
        systematics=({"name": "lumi", "type": "lnN", "value": 1.02},),
    )


class TestBuildDatacardSpec:
    def test_bin_spec_fields_from_fit_bin(self):
        fit_bin = FitBin("2024_nano_v15", "tt", "xyh")
        spec = build_datacard_spec(POINT, {fit_bin: _bin_shapes()})
        assert spec.mass == 2000
        assert spec.analysis == "xyh"
        assert spec.auto_mc_stats is None
        assert spec.systematics == ()
        assert spec.bins == (
            BinSpec(
                "tt_xyh_2024_nano_v15",
                "2024_nano_v15",
                "tt",
                ("signal",),
                ("dy", "tt"),
            ),
        )

    def test_backgrounds_sorted_and_missing_signal_gives_no_signals(self):
        fit_bin = FitBin("c", "mt", "z2tau")
        spec = build_datacard_spec(
            POINT,
            {fit_bin: _bin_shapes(signal=False, backgrounds=("zz", "aa"))},
            auto_mc_stats=5.0,
            analysis="foo",
        )
        assert spec.bins[0].signals == ()
        assert spec.bins[0].backgrounds == ("aa", "zz")
        assert spec.auto_mc_stats == 5.0
        assert spec.analysis == "foo"

    def test_preserves_bin_order(self):
        bins = {
            FitBin("c", "tt", "xyh"): _bin_shapes(),
            FitBin("c", "et", "xyh"): _bin_shapes(),
        }
        spec = build_datacard_spec(POINT, bins)
        assert [b.name for b in spec.bins] == ["tt_xyh_c", "et_xyh_c"]


class TestSpecSerialization:
    def test_to_dict_is_json_serializable(self, spec):
        json.dumps(spec.to_dict())

    def test_dict_roundtrip(self, spec):
        assert DatacardSpec.from_dict(spec.to_dict()) == spec

    def test_from_dict_converts_lists_to_tuples(self, spec):
        loaded = DatacardSpec.from_dict(json.loads(json.dumps(spec.to_dict())))
        assert loaded == spec
        assert isinstance(loaded.bins, tuple)
        assert isinstance(loaded.bins[0].backgrounds, tuple)

    def test_file_roundtrip_creates_parent(self, spec, tmp_path):
        path = tmp_path / "a" / "b" / "datacard_spec.json"
        write_spec(spec, path)
        assert read_spec(path) == spec
        assert json.loads(path.read_text())["mass"] == 2000

    def test_from_dict_without_systematics_defaults_to_empty(self, spec):
        data = spec.to_dict()
        del data["systematics"]
        assert DatacardSpec.from_dict(data).systematics == ()

    def test_defaults_of_file_names(self):
        spec = DatacardSpec("xyh", 1, ())
        assert (
            spec.shapes_in_file,
            spec.datacard_file,
            spec.shapes_out_file,
        ) == ("shapes_in.root", "datacard.txt", "shapes.root")


class TestScriptCommand:
    def test_without_prefix_runs_script_only(self):
        command = datacard_script_command("", "spec.json", Path("/x/s.py"))
        assert command == ["bash", "-c", "python3 /x/s.py spec.json"]

    def test_with_prefix_chains_with_and(self):
        command = datacard_script_command("source env", "spec.json")
        assert command[:2] == ["bash", "-c"]
        assert command[2].startswith("source env && python3 ")
        assert command[2].endswith(f"{datacard.CH_SCRIPT} spec.json")

    def test_default_script_exists_and_parses(self):
        import ast

        assert datacard.CH_SCRIPT.is_file()
        ast.parse(datacard.CH_SCRIPT.read_text())


class TestRunDatacardScript:
    def test_success_runs_in_workdir_and_writes_log(self, tmp_path, mocker):
        run = mocker.patch(
            "xyh.fit.datacard.subprocess.run",
            autospec=True,
            return_value=subprocess.CompletedProcess([], 0, "out", "err"),
        )
        run_datacard_script("setup", tmp_path / "spec.json", tmp_path)
        args, kwargs = run.call_args
        assert args[0] == datacard_script_command("setup", "spec.json")
        assert kwargs["cwd"] == tmp_path
        assert (tmp_path / "write_datacard.log").read_text() == "outerr"

    def test_failure_raises_with_stderr_tail(self, tmp_path, mocker):
        mocker.patch(
            "xyh.fit.datacard.subprocess.run",
            autospec=True,
            return_value=subprocess.CompletedProcess([], 3, "", "boom"),
        )
        with pytest.raises(RuntimeError, match=r"(?s)failed \(3\).*boom"):
            run_datacard_script("", tmp_path / "spec.json", tmp_path)
        assert (tmp_path / "write_datacard.log").read_text() == "boom"
