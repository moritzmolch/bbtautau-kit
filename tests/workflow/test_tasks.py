"""Tests for the workflow tasks (stage execution is mocked)."""

from pathlib import Path
from unittest.mock import patch

from xyh import ROOT_DIR
from xyh.workflow.tasks import (
    MergeHistograms,
    PlotShapes,
    RunGraphs,
    RunGraphsSnapshots,
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


def test_snapshot_task_forces_snapshot_mode():
    task = RunGraphsSnapshots(overrides=OVERRIDES)
    assert task.override_list == [
        *OVERRIDES.split(),
        "graph_processing.mode=snapshot",
    ]
    assert task.cfg.graph_processing.mode == "snapshot"


def test_snapshot_task_overrides_user_mode():
    task = RunGraphsSnapshots(
        overrides=f"{OVERRIDES} graph_processing.mode=histogram"
    )
    assert task.override_list.count("graph_processing.mode=snapshot") == 1
    assert not any(o.endswith("=histogram") for o in task.override_list)


def test_snapshot_task_has_separate_marker_and_runs_run_graphs():
    task = RunGraphsSnapshots(overrides=OVERRIDES)
    assert task.output().path.endswith("/.workflow/run_graphs_snapshots.done")
    assert task.output().path != RunGraphs(overrides=OVERRIDES).output().path
    with (
        patch("xyh.workflow.base.run_stage") as run,
        patch.object(type(task.output()), "dump"),
    ):
        task.run()
    stage, overrides = run.call_args.args
    assert stage == "run_graphs"
    assert overrides[-1] == "graph_processing.mode=snapshot"


def test_snapshot_task_does_not_change_histogram_task():
    task = RunGraphs(overrides=OVERRIDES)
    assert task.override_list == OVERRIDES.split()
