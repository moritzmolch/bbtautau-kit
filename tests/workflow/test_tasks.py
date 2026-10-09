"""Tests for the workflow tasks (stage execution is mocked)."""

from pathlib import Path
from unittest.mock import patch

from xyh import ROOT_DIR
from xyh.workflow.tasks import (
    MergeHistograms,
    PlotShapes,
    RunGraphs,
    Shapes,
)

OVERRIDES = "tags.shapes_tag=wf-test inventory.campaigns=[2024_nano_v15]"


def test_dir_task_marker_is_next_to_specs_dir():
    task = RunGraphs(overrides=OVERRIDES)
    assert task.output().path == str(
        ROOT_DIR / "data/output/wf-test/.workflow/run_graphs.done"
    )


def test_run_graphs_has_no_requirements():
    # the specs are created inside `run_graphs`
    assert RunGraphs(overrides=OVERRIDES).requires() == []


def test_unresolvable_unrelated_keys_do_not_break_outputs():
    task = RunGraphs(overrides=OVERRIDES)
    assert task.output().path.endswith("run_graphs.done")


def test_requirements_propagate_overrides():
    task = MergeHistograms(overrides=OVERRIDES)
    assert task.requires().overrides == OVERRIDES


def test_fake_factors_switch_changes_upstream_stage():
    without = MergeHistograms(overrides=OVERRIDES).requires()
    with_ff = MergeHistograms(overrides=OVERRIDES, fake_factors=True).requires()
    assert without.stage == "run_graphs"
    assert with_ff.stage == "run_fake_factor_histograms"


def test_plot_shapes_forwards_fake_factors():
    req = PlotShapes(overrides=OVERRIDES, fake_factors=True).requires()
    assert req.fake_factors is True


def test_run_forwards_overrides_and_writes_marker(tmp_path: Path):
    overrides = f"tags.shapes_tag=wf-test-{tmp_path.name}"
    task = RunGraphs(overrides=overrides)
    marker = Path(task.output().path)
    try:
        with patch("xyh.workflow.base.run_stage") as run:
            task.run()
        run.assert_called_once_with("run_graphs", [overrides])
        assert marker.exists()
    finally:
        marker.unlink(missing_ok=True)
        for d in (marker.parent, marker.parent.parent):
            try:
                d.rmdir()
            except OSError:
                pass


def test_shapes_wrapper_requires_plot_shapes():
    req = Shapes(overrides=OVERRIDES, fake_factors=True).requires()
    assert isinstance(req, PlotShapes)
    assert req.fake_factors is True
