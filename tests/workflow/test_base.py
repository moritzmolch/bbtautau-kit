"""Tests for the Z correction handling of `xyh.workflow.base.HydraTask`.

Only the Hydra composition is exercised, no stage is run.
"""

import pytest

pytest.importorskip("law")

from xyh import ROOT_DIR  # noqa: E402
from xyh.workflow.base import HydraTask  # noqa: E402


class _Task(HydraTask):
    stage = "run_graphs"

    def run(self):
        pass


class _DerivingTask(_Task):
    derives_z_corrections = True


def test_override_list_without_correction_tag_is_user_plus_forced():
    class Forced(_Task):
        forced_overrides = {"graph_processing.mode": "snapshot"}

    task = Forced(overrides="tags.shapes_tag=foo binning.n_bins=60")

    assert not task.applies_z_corrections
    assert task.override_list == [
        "tags.shapes_tag=foo",
        "binning.n_bins=60",
        "graph_processing.mode=snapshot",
    ]


def test_forced_override_replaces_user_override_of_same_key():
    class Forced(_Task):
        forced_overrides = {"graph_processing.mode": "snapshot"}

    task = Forced(
        overrides="tags.shapes_tag=foo graph_processing.mode=histogram"
    )

    assert task.override_list == [
        "tags.shapes_tag=foo",
        "graph_processing.mode=snapshot",
    ]


def test_correction_tag_equal_to_shapes_tag_applies_nothing():
    task = _Task(overrides="tags.shapes_tag=foo z_pt_corrections.tag=foo")

    assert not task.applies_z_corrections
    assert "z_pt_corrections.input_dir" not in " ".join(task.override_list)


def test_derivation_overrides_set_tags_and_inventory():
    task = _Task(
        overrides="tags.shapes_tag=foo z_pt_corrections.tag=foo-deriv"
    )

    assert task.z_corrections_tag == "foo-deriv"
    assert task.applies_z_corrections
    derivation = task.derivation_overrides
    assert "tags.shapes_tag=foo-deriv" in derivation
    assert "tags.z_pt_tag=foo-deriv" in derivation
    assert "z_pt_corrections.tag=foo-deriv" in derivation
    assert "inventory=control_regions_z_pt" in derivation
    assert "tags.shapes_tag=foo" not in derivation


def test_derivation_overrides_drop_user_input_dir():
    task = _Task(
        overrides="tags.shapes_tag=foo z_pt_corrections.tag=foo-deriv "
        "z_pt_corrections.input_dir=data/other"
    )

    assert not any(
        o.startswith("z_pt_corrections.input_dir=")
        for o in task.derivation_overrides
    )


def test_override_list_ends_with_derived_correction_dir():
    task = _Task(
        overrides="tags.shapes_tag=foo z_pt_corrections.tag=foo-deriv"
    )

    expected = (
        f"z_pt_corrections.input_dir="
        f"{ROOT_DIR}/data/corrections/z_pt/foo-deriv"
    )
    assert task.override_list[-1] == expected
    assert task.override_list[0] == "tags.shapes_tag=foo"


def test_deriving_task_runs_in_the_derivation_production():
    task = _DerivingTask(
        overrides="tags.shapes_tag=foo z_pt_corrections.tag=foo-deriv"
    )

    assert not task.applies_z_corrections
    assert "tags.shapes_tag=foo-deriv" in task.override_list
    assert "tags.shapes_tag=foo" not in task.override_list
    assert not any(
        o.startswith("z_pt_corrections.input_dir=") for o in task.override_list
    )
