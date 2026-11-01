"""Unit tests for the creation of filters and weights specs."""

from types import SimpleNamespace

import pytest

from xyh.core.specs import filters_and_weights as module
from xyh.core.specs.filters_and_weights import (
    create_filters_and_weights_spec,
    create_filters_and_weights_specs,
)
from xyh.core.specs.specs import FiltersAndWeights


def _make_fn(nominal, record=None):
    """Factory function returning an object with a `nominal()` method."""

    def fn(**kwargs):
        if record is not None:
            record.append(kwargs)
        return SimpleNamespace(nominal=lambda: dict(nominal))

    return fn


def make_variation(name, skip=False, suffix="up"):
    class Variation:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def skip(self):
            return skip

        def apply(self, filters, weights):
            return (
                {f"{k}_{suffix}": v for k, v in filters.items()},
                {k: f"({v})*{suffix}" for k, v in weights.items()},
            )

    Variation.name = name
    return Variation


@pytest.fixture
def insts():
    return {
        "campaign_inst": SimpleNamespace(name="camp"),
        "channel_inst": SimpleNamespace(name="tt"),
        "category_inst": SimpleNamespace(name="cat"),
        "dataset_inst": SimpleNamespace(name="ds"),
        "process_inst": SimpleNamespace(name="proc"),
    }


@pytest.fixture
def set_variations(monkeypatch):
    def _set(*variations):
        monkeypatch.setattr(module, "default_variations", list(variations))

    _set()
    return _set


class TestCreateFiltersAndWeightsSpec:
    def test_nominal_spec_created_without_variations(
        self, insts, set_variations
    ):
        specs = create_filters_and_weights_spec(
            **insts,
            filters_fn=_make_fn({"f1": "x>0"}),
            weights_fn=_make_fn({"w1": "1.5"}),
        )
        (spec,) = specs
        assert isinstance(spec, FiltersAndWeights)
        assert (
            spec.campaign,
            spec.channel,
            spec.category,
            spec.process,
            spec.dataset,
            spec.variation,
        ) == ("camp", "tt", "cat", "proc", "ds", "nominal")
        assert [(f.name, f.expression) for f in spec.filters] == [("f1", "x>0")]
        assert [(w.name, w.expression) for w in spec.weights] == [("w1", "1.5")]

    def test_filter_and_weight_factories_receive_all_instances(
        self, insts, set_variations
    ):
        f_calls, w_calls = [], []
        create_filters_and_weights_spec(
            **insts,
            filters_fn=_make_fn({}, f_calls),
            weights_fn=_make_fn({}, w_calls),
        )
        assert f_calls == [insts]
        assert w_calls == [insts]

    def test_variations_follow_nominal_in_order(self, insts, set_variations):
        set_variations(make_variation("a_up"), make_variation("b_up"))
        specs = create_filters_and_weights_spec(
            **insts,
            filters_fn=_make_fn({"f": "1"}),
            weights_fn=_make_fn({"w": "2"}),
        )
        assert [s.variation for s in specs] == ["nominal", "a_up", "b_up"]

    def test_variation_modifies_filters_and_weights(
        self, insts, set_variations
    ):
        set_variations(make_variation("v", suffix="sfx"))
        _, varied = create_filters_and_weights_spec(
            **insts,
            filters_fn=_make_fn({"f": "1"}),
            weights_fn=_make_fn({"w": "2"}),
        )
        assert [(f.name, f.expression) for f in varied.filters] == [
            ("f_sfx", "1")
        ]
        assert [(w.name, w.expression) for w in varied.weights] == [
            ("w", "(2)*sfx")
        ]
        assert varied.process == "proc"

    def test_skipped_variation_is_omitted(self, insts, set_variations):
        set_variations(
            make_variation("skipped", skip=True), make_variation("kept")
        )
        specs = create_filters_and_weights_spec(
            **insts,
            filters_fn=_make_fn({}),
            weights_fn=_make_fn({}),
        )
        assert [s.variation for s in specs] == ["nominal", "kept"]

    def test_variation_constructed_with_context_instances(
        self, insts, set_variations
    ):
        seen = []
        base = make_variation("v")

        class Recording(base):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                seen.append(kwargs)

        Recording.name = "v"
        set_variations(Recording)
        create_filters_and_weights_spec(
            **insts, filters_fn=_make_fn({}), weights_fn=_make_fn({})
        )
        assert seen == [insts]

    def test_nominal_dicts_are_not_mutated_by_variations(
        self, insts, set_variations
    ):
        set_variations(make_variation("v"))
        specs = create_filters_and_weights_spec(
            **insts,
            filters_fn=_make_fn({"f": "1"}),
            weights_fn=_make_fn({"w": "2"}),
        )
        assert specs[0].weights[0].expression == "2"


class TestCreateFiltersAndWeightsSpecs:
    @pytest.fixture
    def patch_config(self, monkeypatch, set_variations):
        loaded_fns = []
        loads = []
        categories = {"tt": {"cat1", "cat2"}, "et": {"cat1"}}
        fns = {
            "pkg:filters": _make_fn({"f": "1"}),
            "pkg:weights": _make_fn({"w": "2"}),
        }

        def fake_load_fn(path):
            loaded_fns.append(path)
            return fns[path]

        def fake_load_inventory(path, campaign, channel, **kwargs):
            loads.append((path, campaign, channel, kwargs))
            return SimpleNamespace(
                campaign=SimpleNamespace(name=campaign),
                channel=SimpleNamespace(
                    name=channel,
                    has_category=lambda c: c in categories[channel],
                    get_category=lambda c: SimpleNamespace(name=c),
                ),
            )

        monkeypatch.setattr(module, "load_fn", fake_load_fn)
        monkeypatch.setattr(module, "load_inventory", fake_load_inventory)
        monkeypatch.setattr(
            module,
            "gen_process_and_dataset_insts",
            lambda inv: [
                (SimpleNamespace(name="p1"), SimpleNamespace(name="d1")),
                (SimpleNamespace(name="p1"), SimpleNamespace(name="d2")),
                (SimpleNamespace(name="p2"), SimpleNamespace(name="d3")),
            ],
        )
        return SimpleNamespace(loaded_fns=loaded_fns, loads=loads)

    def _run(self, **overrides):
        kwargs = {
            "inventory_factory_fn_path": "pkg:inv",
            "inventory_factory_kwargs": {"opt": 1},
            "filters_fn_path": "pkg:filters",
            "weights_fn_path": "pkg:weights",
            "campaigns": ["c"],
            "channels": ["tt"],
            "categories": ["cat1"],
        }
        kwargs.update(overrides)
        return create_filters_and_weights_specs(**kwargs)

    def test_spec_created_per_process_dataset_pair(self, patch_config):
        specs = self._run()
        assert [(s.process, s.dataset) for s in specs] == [
            ("p1", "d1"),
            ("p1", "d2"),
            ("p2", "d3"),
        ]

    def test_functions_and_inventory_loaded_from_paths(self, patch_config):
        self._run()
        assert patch_config.loaded_fns == ["pkg:filters", "pkg:weights"]
        assert patch_config.loads == [("pkg:inv", "c", "tt", {"opt": 1})]

    def test_categories_not_in_channel_are_skipped(self, patch_config):
        specs = self._run(
            channels=["tt", "et"], categories=["cat1", "cat2", "cat3"]
        )
        assert sorted({(s.channel, s.category) for s in specs}) == [
            ("et", "cat1"),
            ("tt", "cat1"),
            ("tt", "cat2"),
        ]

    def test_all_campaign_channel_combinations_are_loaded(self, patch_config):
        self._run(campaigns=["c1", "c2"], channels=["tt", "et"])
        assert [(c, ch) for _, c, ch, _ in patch_config.loads] == [
            ("c1", "tt"),
            ("c1", "et"),
            ("c2", "tt"),
            ("c2", "et"),
        ]

    def test_no_matching_category_gives_no_specs(self, patch_config):
        assert self._run(categories=["nope"]) == []

    def test_variations_multiply_specs(self, patch_config, set_variations):
        set_variations(make_variation("v"))
        specs = self._run()
        assert len(specs) == 6
        assert {s.variation for s in specs} == {"nominal", "v"}
