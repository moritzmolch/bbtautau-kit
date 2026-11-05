"""Unit tests for the `run_graphs` stage."""

import cProfile
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from omegaconf import OmegaConf

import xyh.binning
from xyh import ROOT_DIR
from xyh.core.specs.specs import Binning, Dataset, FiltersAndWeights
from xyh.shape_processor import run_graphs
from xyh.shape_processor.run_graphs import (
    _log_report_summary,
    _peak_rss_mb,
    _run,
    _run_with_cprofile,
    _summarize_cprofile_stats,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def test_peak_rss_mb_is_positive():
    assert _peak_rss_mb() > 0.0


class TestSummarizeCprofileStats:
    def test_summary_from_dumped_file_contains_profiled_function(
        self, tmp_path
    ):
        profiler = cProfile.Profile()
        profiler.enable()
        _ = sum(range(1000))  # noqa: F841 - profiled work
        profiler.disable()
        cprofile_file = tmp_path / "profile_output.prof"
        profiler.dump_stats(str(cprofile_file))

        text = _summarize_cprofile_stats(cprofile_file)

        assert text is not None
        assert "sum" in text

    def test_missing_file_returns_none_and_warns(self, tmp_path, caplog):
        with caplog.at_level(logging.WARNING, logger=run_graphs.__name__):
            assert _summarize_cprofile_stats(tmp_path / "missing.prof") is None
        assert "Failed to summarize cProfile output" in caplog.text


class TestRunWithCprofile:
    @pytest.fixture
    def cprofile_file(self, tmp_path):
        return tmp_path / "sub" / "profile_output.prof"

    def test_profiling_data_is_stored_and_summarized(
        self, cprofile_file, monkeypatch
    ):
        # The profiler must be enabled so that profiling data is collected
        # (regression test for a missing `profiler.enable()` call).
        report = {"python": {"cprofile": True}, "totals": {}}
        run = MagicMock(return_value=report)
        monkeypatch.setattr(run_graphs, "_run", run)
        cfg = OmegaConf.create({"cprofile_file": str(cprofile_file)})
        profiling_cfg = OmegaConf.create({"enabled": True})

        result = _run_with_cprofile(cfg, profiling_cfg)

        run.assert_called_once_with(cfg, profiling_cfg, cprofile=True)
        assert cprofile_file.exists()
        assert result["python"]["cprofile_summary"] is not None
        assert result["python"]["cprofile_file"] == str(cprofile_file)

    def test_report_none_is_returned_unchanged(
        self, cprofile_file, monkeypatch
    ):
        monkeypatch.setattr(run_graphs, "_run", MagicMock(return_value=None))
        cfg = OmegaConf.create({"cprofile_file": str(cprofile_file)})
        assert _run_with_cprofile(cfg, OmegaConf.create({})) is None
        assert cprofile_file.exists()

    def test_exception_from_run_propagates_without_dumping_profile(
        self, cprofile_file, monkeypatch
    ):
        monkeypatch.setattr(
            run_graphs, "_run", MagicMock(side_effect=RuntimeError("boom"))
        )
        cfg = OmegaConf.create({"cprofile_file": str(cprofile_file)})
        with pytest.raises(RuntimeError, match="boom"):
            _run_with_cprofile(cfg, OmegaConf.create({}))
        # The exception propagates before the profile is written
        assert not cprofile_file.exists()

    def test_summary_none_is_stored_in_report(self, cprofile_file, monkeypatch):
        report = {"python": {}}
        monkeypatch.setattr(run_graphs, "_run", MagicMock(return_value=report))
        monkeypatch.setattr(
            run_graphs, "_summarize_cprofile_stats", lambda f: None
        )
        cfg = OmegaConf.create({"cprofile_file": str(cprofile_file)})
        result = _run_with_cprofile(cfg, OmegaConf.create({}))
        assert result["python"]["cprofile_summary"] is None


class TestLogReportSummary:
    def test_totals_and_memory_are_logged(self, caplog):
        report = {
            "totals": {
                "subgraphs": 3,
                "nodes_declared": 10,
                "leaf_nodes": 4,
                "events_processed": 1000,
                "run_s": 2.5,
            },
            "memory": {"peak_rss_mb": 123.4},
        }
        with caplog.at_level(logging.INFO, logger=run_graphs.__name__):
            _log_report_summary(report)
        assert (
            "Profiling report: 3 subgraphs, 10 nodes declared, 4 leaf "
            "outputs, 1000 events processed, subgraph processing 2.50 s, "
            "peak RSS 123.4 MB"
        ) in caplog.text

    def test_empty_report_uses_defaults(self, caplog):
        with caplog.at_level(logging.INFO, logger=run_graphs.__name__):
            _log_report_summary({})
        assert (
            "Profiling report: 0 subgraphs, 0 nodes declared, 0 leaf "
            "outputs, 0 events processed, subgraph processing 0.00 s, "
            "peak RSS -1.0 MB"
        ) in caplog.text

    def test_subgraph_named_after_first_leaf_node(self, caplog):
        leaf = {
            "campaign": "c",
            "channel": "tt",
            "category": "cat",
            "dataset": "d",
            "process": "p",
            "variation": "nominal",
        }
        report = {
            "subgraphs": [
                {
                    "leaf_nodes": [leaf, {"campaign": "other"}],
                    "times_s": {"declare": 1.0, "run": 2.0, "write": 0.5},
                    "events_processed": 7,
                    "memory": {"rss_mb_end": 50.0},
                }
            ]
        }
        with caplog.at_level(logging.INFO, logger=run_graphs.__name__):
            _log_report_summary(report)
        assert (
            "Subgraph c__tt__cat__d__p__nominal: declare 1.00 s, run 2.00 s, "
            "write 0.50 s, total 1.00 s, events 7, rss 50.0 MB"
        ) in caplog.text

    def test_subgraph_without_leaf_nodes_and_missing_keys(self, caplog):
        report = {
            "subgraphs": [{"leaf_nodes": [{"campaign": "c"}], "times_s": {}}]
        }
        with caplog.at_level(logging.INFO, logger=run_graphs.__name__):
            _log_report_summary(report)
        assert "Subgraph c__?__?__?__?__?: declare 0.00 s" in caplog.text

        caplog.clear()
        with caplog.at_level(logging.INFO, logger=run_graphs.__name__):
            _log_report_summary({"subgraphs": [{}]})
        assert "Subgraph no leaf outputs:" in caplog.text

    def test_explicit_total_time_takes_precedence(self, caplog):
        report = {"subgraphs": [{"times_s": {"declare": 1.0, "total": 9.0}}]}
        with caplog.at_level(logging.INFO, logger=run_graphs.__name__):
            _log_report_summary(report)
        assert "total 9.00 s" in caplog.text


# -----------------------------------------------------------------------------
# _run
# -----------------------------------------------------------------------------


def _dataset_spec():
    return Dataset(
        campaign="c",
        channel="tt",
        dataset="d",
        files={"main": ["a", "b", "c"], "ff": ["x", "y", "z"]},
    )


def _binning_spec():
    return Binning(
        campaign="c",
        channel="tt",
        category="cat",
        variable="pt",
        expression="pt",
        bin_edges=[0, 1],
    )


def _faw(process="data_proc", variation="nominal"):
    return FiltersAndWeights(
        campaign="c",
        channel="tt",
        category="cat",
        process=process,
        dataset="d",
        variation=variation,
        filters=[],
        weights=[],
    )


def make_cfg(mode="histogram", profiling=False, **extra):
    cfg = {
        "inventory": {
            "factory_fn": "pkg:inv",
            "factory_fn_kwargs": {"opt": 1},
            "campaigns": ["c"],
            "channels": ["tt"],
            "categories": ["cat"],
            "variables": ["pt", "eta"],
            "filters_fn": "pkg:filters",
            "weights_fn": "pkg:weights",
        },
        "ntuples": {
            "xrootd_server": "root://srv",
            "base_dir": "/store",
            "friends": ["ff"],
        },
        "tags": {"ntuple_tag": "ntag"},
        "graph_processing": {
            "mode": mode,
            "num_workers": 3,
            "num_threads": 2,
        },
        "binning": {
            "n_files": None,
            "data_process_group": "data",
            "variables": {"pt": {}, "mass": {}},
            "output_file": "out/binning.json",
            "plots_dir": "out/plots",
            "n_bins": 10,
        },
        "snapshots": {"columns": None},
        "dataset_specs_file": "specs/datasets.json.gz",
        "binning_specs_file": "specs/binning.json.gz",
        "filters_and_weights_specs_file": "specs/faw.json.gz",
        "graph_specs_file": "specs/graphs.json.gz",
        "histogram_keys_file": "hist/histogram_keys.json.gz",
        "histograms_output_dir": "hist",
        "snapshots_output_dir": "snaps",
        "binning_output_dir": "binning",
    }
    cfg.update(extra)
    return OmegaConf.create(cfg), OmegaConf.create({"enabled": profiling})


@pytest.fixture
def mocks(monkeypatch):
    """Patch all collaborators of `_run` and record the calls."""
    graphs = ["g1", "g2"]
    m = SimpleNamespace(
        graphs=graphs,
        dataset_specs=[_dataset_spec()],
        binning_specs=[_binning_spec()],
        faw_specs=[
            _faw("data_proc"),
            _faw("data_proc", "up"),
            _faw("mc_proc"),
        ],
        dump_json=MagicMock(name="dump_json"),
        execute=MagicMock(name="execute"),
        build_histograms=MagicMock(return_value=graphs),
        build_snapshots=MagicMock(return_value=graphs),
        build_binning=MagicMock(return_value=graphs),
        graphs_to_specs=MagicMock(return_value="graph-specs"),
        histogram_keys=MagicMock(return_value="hist-keys"),
        derive_binning=MagicMock(name="derive_binning"),
        load_binning_overrides=MagicMock(return_value="overrides"),
    )
    m.create_dataset_specs = MagicMock(return_value=m.dataset_specs)
    m.create_binning_specs = MagicMock(return_value=m.binning_specs)
    m.create_faw_specs = MagicMock(return_value=m.faw_specs)
    variable = SimpleNamespace(name="pt", x_title="p_T")
    m.inventory = SimpleNamespace(
        variables=[variable, SimpleNamespace(name="eta", x_title=None)]
    )
    m.load_inventory = MagicMock(return_value=m.inventory)
    m.resolve_processes = MagicMock(return_value=["data_proc"])

    monkeypatch.setattr(run_graphs, "dump_json", m.dump_json)
    monkeypatch.setattr(run_graphs, "execute", m.execute)
    monkeypatch.setattr(
        run_graphs, "build_histograms_graph", m.build_histograms
    )
    monkeypatch.setattr(run_graphs, "build_snapshots_graph", m.build_snapshots)
    monkeypatch.setattr(run_graphs, "build_binning_graph", m.build_binning)
    monkeypatch.setattr(run_graphs, "graphs_to_specs", m.graphs_to_specs)
    monkeypatch.setattr(run_graphs, "histogram_keys", m.histogram_keys)
    monkeypatch.setattr(
        run_graphs, "create_dataset_specs", m.create_dataset_specs
    )
    monkeypatch.setattr(
        run_graphs, "create_binning_specs", m.create_binning_specs
    )
    monkeypatch.setattr(
        run_graphs, "create_filters_and_weights_specs", m.create_faw_specs
    )
    monkeypatch.setattr(run_graphs, "load_inventory", m.load_inventory)
    monkeypatch.setattr(run_graphs, "resolve_processes", m.resolve_processes)
    monkeypatch.setattr(
        run_graphs, "load_binning_overrides", m.load_binning_overrides
    )
    monkeypatch.setattr(xyh.binning, "derive_binning", m.derive_binning)
    return m


def _dumped(mocks):
    """Map of dump target path to dumped data."""
    return {
        str(call.args[1]): call.args[0]
        for call in mocks.dump_json.call_args_list
    }


class TestRunHistogramMode:
    def test_specs_are_created_from_config(self, mocks):
        _run(*make_cfg())
        mocks.create_dataset_specs.assert_called_once_with(
            inventory_factory_fn_path="pkg:inv",
            inventory_factory_kwargs={"opt": 1},
            campaigns=["c"],
            channels=["tt"],
            xrootd_server="root://srv",
            ntuple_base_dir=Path("/store"),
            ntuple_tag="ntag",
            ntuple_friends=["ff"],
        )
        kwargs = mocks.create_binning_specs.call_args.kwargs
        assert kwargs["variables"] == ["pt", "eta"]
        assert kwargs["binning_overrides"] is None
        kwargs = mocks.create_faw_specs.call_args.kwargs
        assert kwargs["filters_fn_path"] == "pkg:filters"
        assert kwargs["weights_fn_path"] == "pkg:weights"
        assert kwargs["categories"] == ["cat"]

    def test_specs_and_graph_specs_are_dumped(self, mocks):
        _run(*make_cfg())
        dumped = _dumped(mocks)
        assert dumped["specs/datasets.json.gz"][0]["dataset"] == "d"
        assert dumped["specs/binning.json.gz"][0]["variable"] == "pt"
        assert len(dumped["specs/faw.json.gz"]) == 3
        assert dumped["specs/graphs.json.gz"] == "graph-specs"

    def test_histogram_graphs_built_and_executed(self, mocks):
        _run(*make_cfg())
        mocks.build_histograms.assert_called_once()
        contexts, second, storage, output_dir = (
            mocks.build_histograms.call_args.args
        )
        assert second is None
        assert output_dir == Path("hist")
        assert [(c.process, c.variation) for c in contexts] == [
            ("data_proc", "nominal"),
            ("data_proc", "up"),
            ("mc_proc", "nominal"),
        ]
        assert contexts[0].dataset == "d"
        assert storage.get_variables(contexts[0]) == ["pt"]
        mocks.build_snapshots.assert_not_called()
        mocks.build_binning.assert_not_called()
        mocks.execute.assert_called_once_with(
            mocks.graphs, num_workers=3, num_threads=2
        )

    def test_histogram_keys_dumped_to_configured_file(self, mocks):
        _run(*make_cfg())
        mocks.histogram_keys.assert_called_once_with(mocks.graphs)
        assert _dumped(mocks)["hist/histogram_keys.json.gz"] == "hist-keys"

    def test_binning_derivation_not_run(self, mocks):
        _run(*make_cfg())
        mocks.derive_binning.assert_not_called()

    def test_report_is_none_without_profiling(self, mocks):
        assert _run(*make_cfg()) is None

    def test_n_files_is_ignored_outside_binning_mode(self, mocks):
        cfg, profiling = make_cfg()
        cfg["binning"]["n_files"] = 1
        _run(cfg, profiling)
        files = _dumped(mocks)["specs/datasets.json.gz"][0]["files"]
        assert files["main"] == ["a", "b", "c"]

    def test_binning_overrides_loaded_relative_to_repo_root(self, mocks):
        cfg, profiling = make_cfg(binning_overrides={"file": "data/b.json"})
        _run(cfg, profiling)
        mocks.load_binning_overrides.assert_called_once_with(
            ROOT_DIR / "data/b.json"
        )
        kwargs = mocks.create_binning_specs.call_args.kwargs
        assert kwargs["binning_overrides"] == "overrides"

    def test_empty_binning_overrides_file_is_not_loaded(self, mocks):
        cfg, profiling = make_cfg(binning_overrides={"file": None})
        _run(cfg, profiling)
        mocks.load_binning_overrides.assert_not_called()


class TestRunSnapshotMode:
    def test_columns_none_passed_as_none(self, mocks):
        _run(*make_cfg("snapshot"))
        contexts, columns, storage, output_dir = (
            mocks.build_snapshots.call_args.args
        )
        assert columns is None
        assert output_dir == Path("snaps")
        assert len(contexts) == 3

    def test_empty_columns_passed_as_none(self, mocks):
        cfg, profiling = make_cfg("snapshot")
        cfg["snapshots"]["columns"] = []
        _run(cfg, profiling)
        assert mocks.build_snapshots.call_args.args[1] is None

    def test_columns_passed_as_plain_list(self, mocks):
        cfg, profiling = make_cfg("snapshot")
        cfg["snapshots"]["columns"] = ["pt_.*", "eta"]
        _run(cfg, profiling)
        columns = mocks.build_snapshots.call_args.args[1]
        assert type(columns) is list
        assert columns == ["pt_.*", "eta"]

    def test_histogram_keys_not_dumped(self, mocks):
        _run(*make_cfg("snapshot"))
        mocks.histogram_keys.assert_not_called()
        assert "hist/histogram_keys.json.gz" not in _dumped(mocks)
        mocks.build_histograms.assert_not_called()
        mocks.execute.assert_called_once()
        mocks.derive_binning.assert_not_called()


class TestRunBinningMode:
    def test_binning_graph_built_for_data_only_and_binning_derived(self, mocks):
        _run(*make_cfg("binning"))
        contexts, storage, output_dir = mocks.build_binning.call_args.args
        # Only nominal data events are used
        assert [(c.process, c.variation) for c in contexts] == [
            ("data_proc", "nominal")
        ]
        assert output_dir == Path("binning")
        mocks.execute.assert_called_once_with(
            mocks.graphs, num_workers=3, num_threads=2
        )
        mocks.histogram_keys.assert_not_called()
        assert "hist/histogram_keys.json.gz" not in _dumped(mocks)

        mocks.derive_binning.assert_called_once()
        args = mocks.derive_binning.call_args.args
        assert args[0] == Path("binning")
        assert args[1] == ROOT_DIR / "out/binning.json"
        assert args[2] == ROOT_DIR / "out/plots"
        assert args[3]["n_bins"] == 10
        assert type(args[3]) is dict
        assert mocks.derive_binning.call_args.kwargs["labels"] == {
            ("tt", "pt"): "p_T",
            ("tt", "eta"): "eta",
        }

    def test_only_binning_variables_are_considered(self, mocks):
        _run(*make_cfg("binning"))
        kwargs = mocks.create_binning_specs.call_args.kwargs
        assert kwargs["variables"] == ["pt", "mass"]

    def test_data_process_group_is_resolved_per_inventory(self, mocks):
        _run(*make_cfg("binning"))
        mocks.load_inventory.assert_called_once_with(
            "pkg:inv", "c", "tt", opt=1
        )
        mocks.resolve_processes.assert_called_once_with(mocks.inventory, "data")

    def test_n_files_limits_files_of_every_tree(self, mocks):
        cfg, profiling = make_cfg("binning")
        cfg["binning"]["n_files"] = 2
        _run(cfg, profiling)
        files = _dumped(mocks)["specs/datasets.json.gz"][0]["files"]
        assert files == {"main": ["a", "b"], "ff": ["x", "y"]}
        # The original spec object is not modified
        assert mocks.dataset_specs[0].files["main"] == ["a", "b", "c"]

    def test_unset_n_files_keeps_all_files(self, mocks):
        _run(*make_cfg("binning"))
        files = _dumped(mocks)["specs/datasets.json.gz"][0]["files"]
        assert files["main"] == ["a", "b", "c"]


class TestRunInvalidMode:
    def test_invalid_mode_raises_after_dumping_specs(self, mocks):
        with pytest.raises(ValueError, match="Invalid graph processing mode"):
            _run(*make_cfg("bogus"))
        assert mocks.dump_json.call_count == 3
        mocks.execute.assert_not_called()


class TestRunProfilingReport:
    def test_report_metadata_and_totals(self, mocks):
        report = _run(*make_cfg(profiling=True))
        assert report["python"]["cprofile"] is False
        assert report["python"]["mode"] == "histogram"
        assert report["python"]["num_workers"] == 3
        assert report["python"]["num_threads"] == 2
        assert report["python"]["total_wall_s"] >= report["subgraphs_wall_s"]
        assert report["totals"]["subgraphs"] == 2
        assert report["memory"]["peak_rss_mb"] > 0
        assert report["subgraphs"] == []

    def test_cprofile_flag_is_recorded(self, mocks):
        cfg, profiling = make_cfg(profiling=True)
        report = _run(cfg, profiling, cprofile=True)
        assert report["python"]["cprofile"] is True


# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------


class TestMain:
    @pytest.fixture
    def main(self):
        return run_graphs.main.__wrapped__

    @pytest.fixture
    def patched(self, monkeypatch):
        m = SimpleNamespace(
            run=MagicMock(return_value=None),
            cprofile=MagicMock(return_value=None),
            dump=MagicMock(),
            summary=MagicMock(),
        )
        monkeypatch.setattr(run_graphs, "_run", m.run)
        monkeypatch.setattr(run_graphs, "_run_with_cprofile", m.cprofile)
        monkeypatch.setattr(run_graphs, "dump_json", m.dump)
        monkeypatch.setattr(run_graphs, "_log_report_summary", m.summary)
        monkeypatch.setattr(logging, "basicConfig", MagicMock())
        return m

    def test_plain_run_without_profiling(self, main, patched):
        cfg = OmegaConf.create({"log_level": "INFO"})
        main(cfg)
        patched.run.assert_called_once()
        patched.cprofile.assert_not_called()
        patched.dump.assert_not_called()

    def test_cprofile_used_when_enabled(self, main, patched):
        report = {"totals": {}}
        patched.cprofile.return_value = report
        cfg = OmegaConf.create(
            {
                "log_level": "INFO",
                "profiling": {"enabled": True, "cprofile": True},
                "profiling_report_file": "report.json.gz",
            }
        )
        main(cfg)
        patched.cprofile.assert_called_once()
        patched.run.assert_not_called()
        patched.dump.assert_called_once_with(report, Path("report.json.gz"))
        patched.summary.assert_called_once_with(report)

    def test_cprofile_not_used_when_disabled_in_profiling_config(
        self, main, patched
    ):
        patched.run.return_value = {"totals": {}}
        cfg = OmegaConf.create(
            {
                "log_level": "INFO",
                "profiling": {"enabled": True, "cprofile": False},
                "profiling_report_file": "report.json.gz",
            }
        )
        main(cfg)
        patched.run.assert_called_once()
        patched.cprofile.assert_not_called()
        patched.dump.assert_called_once()
