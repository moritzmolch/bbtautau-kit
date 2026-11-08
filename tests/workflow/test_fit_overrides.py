"""Unit tests for the pure override helpers of `xyh.workflow.fit`."""

import shlex

import pytest

from xyh.fit.mass_points import MassPoint
from xyh.workflow.fit import point_overrides, strip_fit_overrides

POINT = MassPoint("y2b", "h2tau", 2000, 500)


class TestStripFitOverrides:
    def test_removes_fit_keys_only(self):
        overrides = [
            "tags.shapes_tag=foo",
            "fit.channels=[tt]",
            "fit.data.mode=observed",
            "inventory=nn",
        ]
        assert strip_fit_overrides(overrides) == [
            "tags.shapes_tag=foo",
            "inventory=nn",
        ]

    def test_keeps_keys_that_merely_contain_fit(self):
        overrides = ["fitness=1", "x.fit.y=2", "fit_dir=a"]
        assert strip_fit_overrides(overrides) == overrides

    def test_empty_input_returns_empty_list(self):
        assert strip_fit_overrides([]) == []


class TestPointOverrides:
    def test_adds_point_restrictions(self):
        result = shlex.split(point_overrides([], POINT))
        assert result == [
            "fit.mass_points=[[2000,500]]",
            "fit.ydm=[y2b]",
            "fit.hdm=[h2tau]",
        ]

    def test_replaces_existing_selection_and_keeps_others(self):
        base = [
            "tags.shapes_tag=foo",
            "fit.mass_points=[[1,1],[2,2]]",
            "fit.ydm=[y2tau]",
            "fit.channels=[tt]",
        ]
        result = shlex.split(point_overrides(base, POINT))
        assert result[:2] == ["tags.shapes_tag=foo", "fit.channels=[tt]"]
        assert result[2:] == [
            "fit.mass_points=[[2000,500]]",
            "fit.ydm=[y2b]",
            "fit.hdm=[h2tau]",
        ]
        assert not any("[[1,1]" in o for o in result)

    @pytest.mark.parametrize(
        "override", ["a='b c'", "x=[1, 2]"], ids=["quoted", "space"]
    )
    def test_output_roundtrips_through_shlex(self, override):
        result = shlex.split(point_overrides([override], POINT))
        assert result[0] == override
