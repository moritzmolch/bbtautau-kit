"""Unit tests for the creation of binning specs."""

import logging
from types import SimpleNamespace

import pytest

from xyh.core.specs import binning as binning_module
from xyh.core.specs.binning import (
    _parse_variable_name,
    create_binning_spec,
    create_binning_specs,
)
from xyh.core.specs.specs import Binning


def _variable(name, expression=None, bin_edges=(0.0, 1.0, 2.0)):
    return SimpleNamespace(
        name=name, expression=expression, bin_edges=list(bin_edges)
    )


def _inventory(campaign, channel, categories, variables):
    return SimpleNamespace(
        campaign=SimpleNamespace(name=campaign),
        channel=SimpleNamespace(
            name=channel,
            has_category=lambda c: c in categories,
            get_category=lambda c: SimpleNamespace(name=c),
        ),
        variables=SimpleNamespace(get=lambda n: variables[n]),
    )


class TestParseVariableName:
    @pytest.mark.parametrize(
        ("arg", "expected"),
        [
            ("pt_1", ("pt_1", None)),
            ("pt_1[tt]", ("pt_1", ["tt"])),
            ("pt_1[tt,et]", ("pt_1", ["tt", "et"])),
            ("pt_1[ tt , et ]", ("pt_1", ["tt", "et"])),
            ("pt_1[tt,,et,]", ("pt_1", ["tt", "et"])),
            ("pt_1[ , ]", ("pt_1", [])),
            (" pt_1 [tt]", ("pt_1", ["tt"])),
        ],
        ids=[
            "pure",
            "one-channel",
            "two-channels",
            "whitespace-stripped",
            "empty-entries-dropped",
            "only-empty-entries",
            "name-stripped",
        ],
    )
    def test_valid_name_returns_name_and_channels(self, arg, expected):
        assert _parse_variable_name(arg) == expected

    @pytest.mark.parametrize(
        "arg",
        ["", "pt_1[tt", "pt_1[]", "pt_1[tt]x", "[tt]", "a[b][c]"],
    )
    def test_invalid_name_raises_value_error(self, arg):
        with pytest.raises(ValueError, match="did not match expected pattern"):
            _parse_variable_name(arg)


class TestCreateBinningSpec:
    @pytest.fixture
    def insts(self):
        return (
            SimpleNamespace(name="camp"),
            SimpleNamespace(name="tt"),
            SimpleNamespace(name="cat"),
        )

    def test_fields_taken_from_instances(self, insts):
        variable = _variable("pt_1", expression="pt[0]", bin_edges=(0, 5, 10))
        spec = create_binning_spec(*insts, variable)
        assert (
            spec.campaign,
            spec.channel,
            spec.category,
            spec.variable,
            spec.expression,
            spec.bin_edges,
        ) == ("camp", "tt", "cat", "pt_1", "pt[0]", [0, 5, 10])

    def test_missing_expression_falls_back_to_variable_name(self, insts):
        spec = create_binning_spec(*insts, _variable("pt_1"))
        assert spec.expression == "pt_1"

    def test_bin_edges_override_replaces_variable_binning(self, insts):
        spec = create_binning_spec(
            *insts, _variable("pt_1", bin_edges=(0, 1)), bin_edges=[3, 4, 5]
        )
        assert spec.bin_edges == [3, 4, 5]

    def test_empty_bin_edges_override_is_not_ignored(self, insts):
        # Only `None` means "no override"
        spec = create_binning_spec(*insts, _variable("pt_1"), bin_edges=[])
        assert spec.bin_edges == []


class TestCreateBinningSpecCallableExpression:
    @pytest.fixture
    def insts(self):
        return (
            SimpleNamespace(name="camp"),
            SimpleNamespace(name="tt"),
            SimpleNamespace(name="cat"),
        )

    def test_callable_expression_is_resolved_with_category(self, insts):
        received = []

        def expression(category_inst):
            received.append(category_inst)
            return f"col_{category_inst.name}"

        spec = create_binning_spec(*insts, _variable("v", expression))
        assert received == [insts[2]]
        assert spec.expression == "col_cat"
        assert isinstance(spec.expression, str)

    def test_callable_returning_none_falls_back_to_variable_name(self, insts):
        spec = create_binning_spec(*insts, _variable("v", lambda c: None))
        assert spec.expression == "v"

    def test_error_from_callable_propagates(self, insts):
        def expression(category_inst):
            raise ValueError("needs clf category")

        with pytest.raises(ValueError, match="needs clf category"):
            create_binning_spec(*insts, _variable("v", expression))

    def test_string_expression_is_unchanged(self, insts):
        spec = create_binning_spec(*insts, _variable("v", "a + b"))
        assert spec.expression == "a + b"


class TestCreateBinningSpecs:
    @pytest.fixture
    def run(self, monkeypatch):
        variables = {
            "pt_1": _variable("pt_1", bin_edges=(0, 1, 2)),
            "mass_1": _variable("mass_1", expression="m", bin_edges=(0, 9)),
        }
        inventories = {}
        calls = []

        def fake_load_inventory(path, campaign, channel, **kwargs):
            calls.append((path, campaign, channel, kwargs))
            return inventories.setdefault(
                (campaign, channel),
                _inventory(campaign, channel, {"cat"}, variables),
            )

        monkeypatch.setattr(
            binning_module, "load_inventory", fake_load_inventory
        )

        def _run(**overrides):
            kwargs = {
                "inventory_factory_fn_path": "pkg:fn",
                "inventory_factory_kwargs": {"opt": 1},
                "campaigns": ["c"],
                "channels": ["tt"],
                "categories": ["cat"],
                "variables": ["pt_1"],
            }
            kwargs.update(overrides)
            return create_binning_specs(**kwargs)

        _run.calls = calls
        return _run

    def test_specs_created_for_all_combinations(self, run):
        specs = run(
            campaigns=["c1", "c2"],
            channels=["tt", "et"],
            variables=["pt_1", "mass_1"],
        )
        assert len(specs) == 8
        assert all(isinstance(s, Binning) for s in specs)
        assert {(s.campaign, s.channel, s.variable) for s in specs} == {
            (c, ch, v)
            for c in ("c1", "c2")
            for ch in ("tt", "et")
            for v in ("pt_1", "mass_1")
        }

    def test_inventory_loaded_with_path_and_kwargs(self, run):
        run()
        assert run.calls == [("pkg:fn", "c", "tt", {"opt": 1})]

    def test_category_not_in_channel_is_skipped(self, run):
        specs = run(categories=["other", "cat"])
        assert [s.category for s in specs] == ["cat"]

    def test_no_matching_category_gives_no_specs(self, run):
        assert run(categories=["other"]) == []

    def test_channel_restricted_variable_skipped_in_other_channels(self, run):
        specs = run(channels=["tt", "et"], variables=["pt_1", "mass_1[tt]"])
        assert sorted((s.channel, s.variable) for s in specs) == [
            ("et", "pt_1"),
            ("tt", "mass_1"),
            ("tt", "pt_1"),
        ]

    def test_expression_defaults_to_variable_name(self, run):
        by_var = {s.variable: s for s in run(variables=["pt_1", "mass_1"])}
        assert by_var["pt_1"].expression == "pt_1"
        assert by_var["mass_1"].expression == "m"

    def test_unknown_variable_raises(self, run):
        with pytest.raises(KeyError):
            run(variables=["unknown"])

    def test_invalid_variable_argument_raises(self, run):
        with pytest.raises(ValueError, match="expected pattern"):
            run(variables=["pt_1[tt"])

    def test_binning_override_replaces_only_matching_entry(self, run):
        overrides = {"c": {"tt": {"cat": {"pt_1": [0, 10, 20]}}}}
        specs = {
            s.variable: s
            for s in run(
                variables=["pt_1", "mass_1"], binning_overrides=overrides
            )
        }
        assert specs["pt_1"].bin_edges == [0, 10, 20]
        assert list(specs["mass_1"].bin_edges) == [0, 9]

    def test_unused_override_logs_warning(self, run, caplog):
        overrides = {"c": {"tt": {"cat": {"pt_1": [0, 1], "ghost": [0, 1]}}}}
        with caplog.at_level(logging.INFO, logger=binning_module.__name__):
            run(binning_overrides=overrides)
        warnings = [
            r.getMessage()
            for r in caplog.records
            if r.levelno == logging.WARNING
        ]
        assert warnings == [
            "Binning override matches no histogram: c/tt/cat/ghost"
        ]
        assert "Overrode the binning of 1 histograms" in caplog.text

    def test_used_overrides_give_no_warning(self, run, caplog):
        overrides = {"c": {"tt": {"cat": {"pt_1": [0, 1]}}}}
        with caplog.at_level(logging.INFO, logger=binning_module.__name__):
            run(binning_overrides=overrides)
        assert not [r for r in caplog.records if r.levelno == logging.WARNING]
