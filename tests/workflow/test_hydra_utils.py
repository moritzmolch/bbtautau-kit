"""Tests for the Hydra helpers used by the workflow tasks."""

from unittest.mock import patch

from xyh import ROOT_DIR
from xyh.workflow.hydra_utils import (
    compose_cfg,
    resolve_cfg,
    run_stage,
    stage_command,
)


def test_compose_cfg_applies_overrides():
    cfg = compose_cfg("merge_histograms", ["tags.shapes_tag=foo"])
    assert cfg.tags.shapes_tag == "foo"


def test_compose_cfg_resolves_artifact_paths_from_tag():
    cfg = resolve_cfg(compose_cfg("merge_histograms", ["tags.shapes_tag=foo"]))
    assert cfg["graph_specs_file"] == "data/output/foo/specs/graphs.json.gz"
    assert cfg["output_dir"] == "data/output/foo/merged_histograms"


def test_compose_cfg_can_be_called_repeatedly():
    first = compose_cfg("run_graphs", ["tags.shapes_tag=a"])
    second = compose_cfg("run_graphs", ["tags.shapes_tag=b"])
    assert first.tags.shapes_tag == "a"
    assert second.tags.shapes_tag == "b"


def test_compose_cfg_exposes_binning_settings():
    cfg = resolve_cfg(compose_cfg("run_graphs", ["tags.shapes_tag=foo"]))
    assert cfg["binning"]["n_bins"] == 100
    assert cfg["binning"]["data_process_group"] == "data"
    assert cfg["binning_output_dir"] == "data/output/foo/binning"
    assert (
        cfg["binning"]["output_file"]
        == "data/output/foo/binning/binning.json"
    )


def test_stage_command_appends_overrides():
    cmd = stage_command("run_graphs", ["a=1", "b=2"])
    assert cmd[1:3] == ["-m", "xyh.shape_processor.run_graphs"]
    assert cmd[3:] == ["a=1", "b=2"]


def test_run_stage_runs_from_repo_root():
    with patch("xyh.workflow.hydra_utils.subprocess.run") as run:
        run_stage("plot_shapes", ["a=1"])
    run.assert_called_once()
    assert run.call_args.kwargs["cwd"] == ROOT_DIR
    assert run.call_args.kwargs["check"] is True
