"""Unit tests for `xyh.fit.combine`."""

import subprocess

import pytest

from xyh.fit import combine as cmb
from xyh.fit.combine import (
    CMSSET_DEFAULT,
    CombineConfig,
    check_environment,
    combine_command,
    environment_prefix,
    limit_file_name,
    limits_from_entries,
    read_limit_entries,
    run_in_env,
    text2workspace_command,
    wrap_command,
)

FULL_ENTRIES = [
    (1.0, 0.025),
    (2.0, 0.16),
    (3.0, 0.5),
    (4.0, 0.84),
    (5.0, 0.975),
    (3.5, -1.0),
]


class TestEnvironmentPrefix:
    def test_setup_cmd_replaces_default(self):
        assert environment_prefix("/cms", "arch", "my setup") == "my setup"

    def test_neither_cmssw_dir_nor_setup_cmd_raises(self):
        with pytest.raises(ValueError, match="cmssw_dir"):
            environment_prefix()

    def test_default_snippet_sources_and_enters_cmssw(self):
        prefix = environment_prefix("/cms/CMSSW_16_0_0", "el9_amd64_gcc13")
        parts = prefix.split(" && ")
        assert parts[0] == "export SCRAM_ARCH=el9_amd64_gcc13"
        assert parts[1] == f"source {CMSSET_DEFAULT}"
        assert parts[2] == "pushd /cms/CMSSW_16_0_0/src > /dev/null"
        assert parts[3] == "eval $(scramv1 runtime -sh)"
        assert parts[4] == "popd > /dev/null"

    def test_without_scram_arch_no_export(self):
        assert "SCRAM_ARCH" not in environment_prefix("/cms")

    def test_paths_with_spaces_are_quoted(self):
        prefix = environment_prefix("/my dir/CMSSW")
        assert "pushd '/my dir/CMSSW/src'" in prefix


class TestWrapCommand:
    def test_with_prefix(self):
        assert wrap_command("setup", ["combine", "-M", "A B"]) == [
            "bash",
            "-c",
            "setup && combine -M 'A B'",
        ]

    def test_without_prefix(self):
        assert wrap_command("", ["ls"]) == ["bash", "-c", "ls"]


class TestCommandBuilders:
    def test_text2workspace_command(self):
        assert text2workspace_command("d.txt", "w.root", ["-P", "X"]) == [
            "text2workspace.py",
            "d.txt",
            "-o",
            "w.root",
            "-P",
            "X",
        ]

    def test_combine_command_defaults(self):
        assert combine_command("w.root", 2000) == [
            "combine",
            "-M",
            "AsymptoticLimits",
            "w.root",
            "--run",
            "both",
            "-m",
            "2000",
            "-n",
            ".fit",
        ]

    def test_combine_command_range_name_and_extra_args(self):
        command = combine_command(
            "w.root", 1, name=".x", r_range=(0.0, 5.5), extra_args=["-v", "2"]
        )
        assert command[-8:] == [
            "-n",
            ".x",
            "--rMin",
            "0.0",
            "--rMax",
            "5.5",
            "-v",
            "2",
        ]

    def test_limit_file_name_matches_combine_output_convention(self):
        assert (
            limit_file_name(2000)
            == "higgsCombine.fit.AsymptoticLimits.mH2000.root"
        )
        assert (
            limit_file_name(125, ".a")
            == "higgsCombine.a.AsymptoticLimits.mH125.root"
        )

    def test_combine_config_defaults(self):
        cfg = CombineConfig()
        assert cfg.r_range is None
        assert cfg.extra_args == ()


class TestLimitsFromEntries:
    def test_maps_all_quantiles_to_names(self):
        assert limits_from_entries(FULL_ENTRIES) == {
            "exp_m2": 1.0,
            "exp_m1": 2.0,
            "exp": 3.0,
            "exp_p1": 4.0,
            "exp_p2": 5.0,
            "obs": 3.5,
        }

    def test_tolerates_float_noise_in_quantiles(self):
        entries = [(v, q + 5e-7) for v, q in FULL_ENTRIES]
        assert len(limits_from_entries(entries)) == 6

    def test_unknown_quantiles_are_ignored(self):
        result = limits_from_entries([*FULL_ENTRIES, (9.0, 0.3)])
        assert 9.0 not in result.values()

    @pytest.mark.parametrize("missing", range(6))
    def test_missing_entry_raises_naming_it(self, missing):
        entries = [e for i, e in enumerate(FULL_ENTRIES) if i != missing]
        with pytest.raises(ValueError, match="Limit tree lacks entries"):
            limits_from_entries(entries)

    def test_empty_entries_raises(self):
        with pytest.raises(ValueError, match="lacks entries"):
            limits_from_entries([])


ROOT = pytest.importorskip("ROOT")


def _write_limit_tree(path, entries, tree_name="limit"):
    from array import array

    root_file = ROOT.TFile.Open(str(path), "RECREATE")
    tree = ROOT.TTree(tree_name, tree_name)
    limit = array("d", [0.0])
    quantile = array("f", [0.0])
    tree.Branch("limit", limit, "limit/D")
    tree.Branch("quantileExpected", quantile, "quantileExpected/F")
    for lim, q in entries:
        limit[0] = lim
        quantile[0] = q
        tree.Fill()
    tree.Write()
    root_file.Close()


class TestReadLimitEntries:
    def test_reads_limit_and_quantile_pairs(self, tmp_path):
        path = tmp_path / "l.root"
        _write_limit_tree(path, FULL_ENTRIES)
        entries = read_limit_entries(path)
        assert [e[0] for e in entries] == pytest.approx(
            [e[0] for e in FULL_ENTRIES]
        )
        assert [e[1] for e in entries] == pytest.approx(
            [e[1] for e in FULL_ENTRIES]
        )

    def test_roundtrip_through_limits_from_entries(self, tmp_path):
        # Quantiles are stored as float32 in the Combine output
        path = tmp_path / "l.root"
        _write_limit_tree(path, FULL_ENTRIES)
        result = limits_from_entries(read_limit_entries(path))
        assert result["exp"] == pytest.approx(3.0)
        assert result["obs"] == pytest.approx(3.5)

    def test_missing_tree_raises(self, tmp_path):
        path = tmp_path / "l.root"
        _write_limit_tree(path, FULL_ENTRIES, tree_name="other")
        with pytest.raises(KeyError, match="No 'limit' tree"):
            read_limit_entries(path)

    def test_missing_file_raises(self, tmp_path):
        # PyROOT raises a plain OSError before the FileNotFoundError branch
        with pytest.raises(OSError, match="Failed to open"):
            read_limit_entries(tmp_path / "nope.root")


class TestRunInEnv:
    def _patch_run(self, mocker, returncode=0, stdout="out", stderr="err"):
        return mocker.patch(
            "xyh.fit.combine.subprocess.run",
            autospec=True,
            return_value=subprocess.CompletedProcess(
                [], returncode, stdout, stderr
            ),
        )

    def test_success_returns_stdout_and_runs_wrapped_in_workdir(
        self, tmp_path, mocker
    ):
        run = self._patch_run(mocker)
        assert run_in_env("setup", ["combine", "-h"], tmp_path) == "out"
        args, kwargs = run.call_args
        assert args[0] == wrap_command("setup", ["combine", "-h"])
        assert kwargs["cwd"] == tmp_path
        assert kwargs["check"] is False

    def test_log_file_receives_stdout_and_stderr(self, tmp_path, mocker):
        self._patch_run(mocker)
        log = tmp_path / "x.log"
        run_in_env("", ["ls"], tmp_path, log)
        assert log.read_text() == "outerr"

    def test_failure_raises_with_command_and_stderr_tail(
        self, tmp_path, mocker
    ):
        self._patch_run(mocker, returncode=2, stderr="x" * 5000 + "TAIL")
        with pytest.raises(RuntimeError, match=r"combine failed \(2\)") as exc:
            run_in_env("", ["combine"], tmp_path)
        assert str(exc.value).endswith("TAIL")
        assert len(str(exc.value)) < 2200

    def test_log_is_written_even_on_failure(self, tmp_path, mocker):
        self._patch_run(mocker, returncode=1)
        log = tmp_path / "x.log"
        with pytest.raises(RuntimeError):
            run_in_env("", ["ls"], tmp_path, log)
        assert log.exists()


class TestCheckEnvironment:
    def test_runs_three_checks(self, tmp_path, mocker):
        run = mocker.patch.object(cmb, "run_in_env", autospec=True)
        check_environment("setup", tmp_path)
        commands = [c.args[1] for c in run.call_args_list]
        assert commands[0] == ["which", "combine"]
        assert commands[1] == ["which", "text2workspace.py"]
        assert "CombineHarvester" in commands[2][-1]

    def test_failure_is_wrapped_with_hint(self, tmp_path, mocker):
        mocker.patch.object(
            cmb, "run_in_env", autospec=True, side_effect=RuntimeError("nope")
        )
        with pytest.raises(
            RuntimeError, match="check failed for which combine.*setup_combine"
        ) as exc:
            check_environment("setup", tmp_path)
        assert isinstance(exc.value.__cause__, RuntimeError)
