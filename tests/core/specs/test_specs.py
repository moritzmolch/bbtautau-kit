from dataclasses import FrozenInstanceError, asdict

import pytest

from xyh.core.specs.specs import (
    Binning,
    Context,
    Dataset,
    Filter,
    FiltersAndWeights,
    Histogram,
    HistogramsOutput,
    Snapshot,
    Spec,
    Weight,
    WeightProduct,
)


@pytest.fixture
def spec():
    return HistogramsOutput(output_dir="/out", subgraph_hash="abc123")


class TestHistogramsOutput:
    def test_repr_contains_class_name_and_both_fields(self, spec):
        assert repr(spec) == (
            "HistogramsOutput<output_dir=/out, subgraph_hash=abc123>"
        )

    def test_asdict_contains_both_fields(self, spec):
        assert asdict(spec) == {
            "output_dir": "/out",
            "subgraph_hash": "abc123",
        }

    def test_asdict_roundtrips_to_equal_fields(self, spec):
        clone = HistogramsOutput(**asdict(spec))
        assert asdict(clone) == asdict(spec)

    def test_fields_are_keyword_only(self):
        with pytest.raises(TypeError):
            HistogramsOutput("/out", "abc123")


class TestDataset:
    def test_missing_main_tree_raises(self):
        with pytest.raises(ValueError, match="'main'"):
            Dataset(campaign="c", channel="tt", dataset="d", files={"ff": []})

    def test_empty_files_raises(self):
        with pytest.raises(ValueError, match="d must contain a main tree"):
            Dataset(campaign="c", channel="tt", dataset="d", files={})

    def test_main_tree_with_friends_is_accepted(self):
        spec = Dataset(
            campaign="c",
            channel="tt",
            dataset="d",
            files={"main": ["a.root"], "ff": ["b.root"]},
        )
        assert spec.files["ff"] == ["b.root"]

    def test_repr_lists_tree_names_not_files(self):
        spec = Dataset(
            campaign="c",
            channel="tt",
            dataset="d",
            files={"main": ["a.root"], "ff": ["b.root"]},
        )
        assert repr(spec) == (
            "Dataset<campaign=c, channel=tt, dataset=d, files=<main, ff>>"
        )


def _weights():
    return [
        Weight(name="w1", expression="1"),
        Weight(name="w2", expression="2"),
    ]


def _binning(**kwargs):
    defaults = {
        "campaign": "c",
        "channel": "tt",
        "category": "cat",
        "variable": "pt",
        "expression": "pt[0]",
        "bin_edges": [0, 1, 2],
    }
    defaults.update(kwargs)
    return Binning(**defaults)


class TestReprs:
    def test_filter(self):
        assert repr(Filter(name="f", expression="x>0")) == (
            "Filter<name=f, expression=x>0>"
        )

    def test_weight(self):
        assert repr(Weight(name="w", expression="1.5")) == (
            "Weight<name=w, expression=1.5>"
        )

    def test_weight_product_lists_weight_names(self):
        assert repr(WeightProduct(weights=_weights())) == (
            "WeightProduct<weights=<w1, w2>>"
        )

    def test_weight_product_without_weights(self):
        assert repr(WeightProduct(weights=[])) == "WeightProduct<weights=<>>"

    def test_filters_and_weights(self):
        spec = FiltersAndWeights(
            campaign="c",
            channel="tt",
            category="cat",
            process="p",
            dataset="d",
            variation="nominal",
            filters=[Filter(name="f1", expression="1")],
            weights=_weights(),
        )
        assert repr(spec) == (
            "FiltersAndWeights<campaign=c, channel=tt, category=cat, "
            "process=p, dataset=d, variation=nominal, filters=<f1>, "
            "weights=<w1, w2>>"
        )

    def test_binning(self):
        assert repr(_binning()) == (
            "Binning<campaign=c, channel=tt, category=cat, variable=pt, "
            "expression=pt[0], bin_edges=[0, 1, 2]>"
        )

    def test_histogram_uses_binning_fields(self):
        spec = Histogram(
            binning=_binning(), dataset="d", process="p", variation="nominal"
        )
        assert repr(spec) == (
            "Histogram<campaign=c, channel=tt, category=cat, dataset=d, "
            "process=p, variation=nominal, variable=pt, expression=pt[0], "
            "bin_edges=[0, 1, 2]>"
        )

    def test_snapshot_without_columns_shows_all(self):
        spec = Snapshot(
            campaign="c",
            channel="tt",
            category="cat",
            dataset="d",
            process="p",
            variation="nominal",
        )
        assert spec.columns is None
        assert repr(spec).endswith("variation=nominal, columns=<all>>")

    def test_snapshot_with_columns_joins_them(self):
        spec = Snapshot(
            campaign="c",
            channel="tt",
            category="cat",
            dataset="d",
            process="p",
            variation="nominal",
            columns=["pt_.*", "eta"],
        )
        assert repr(spec).endswith("columns=pt_.*,eta>")

    def test_snapshot_with_empty_columns_shows_all(self):
        # An empty list is falsy and is rendered like `None`
        spec = Snapshot(
            campaign="c",
            channel="tt",
            category="cat",
            dataset="d",
            process="p",
            variation="nominal",
            columns=[],
        )
        assert repr(spec).endswith("columns=<all>>")


class TestHistogram:
    def test_wraps_binning_object(self):
        binning = _binning()
        spec = Histogram(
            binning=binning, dataset="d", process="p", variation="v"
        )
        assert spec.binning is binning

    def test_binning_is_required(self):
        with pytest.raises(TypeError):
            Histogram(dataset="d", process="p", variation="v")  # type: ignore[call-arg]


class TestBinning:
    def test_expression_defaults_to_none(self):
        spec = Binning(
            campaign="c",
            channel="tt",
            category="cat",
            variable="pt",
            bin_edges=[0, 1],
        )
        assert spec.expression is None


class TestFrozenAndKeywordOnly:
    @pytest.mark.parametrize(
        ("factory", "field"),
        [
            (lambda: Filter(name="f", expression="1"), "name"),
            (lambda: Weight(name="w", expression="1"), "expression"),
            (lambda: WeightProduct(weights=[]), "weights"),
            (_binning, "bin_edges"),
            (
                lambda: Context(
                    campaign="c",
                    channel="tt",
                    category="cat",
                    dataset="d",
                    process="p",
                    variation="v",
                ),
                "campaign",
            ),
            (
                lambda: Dataset(
                    campaign="c",
                    channel="tt",
                    dataset="d",
                    files={"main": []},
                ),
                "dataset",
            ),
        ],
        ids=[
            "filter",
            "weight",
            "weight-product",
            "binning",
            "context",
            "dataset",
        ],
    )
    def test_assigning_a_field_raises(self, factory, field):
        with pytest.raises(FrozenInstanceError):
            setattr(factory(), field, "other")

    @pytest.mark.parametrize(
        "cls, args",
        [
            (Filter, ("f", "1")),
            (Weight, ("w", "1")),
            (WeightProduct, ([],)),
            (Spec, (1,)),
        ],
        ids=["filter", "weight", "weight-product", "spec"],
    )
    def test_positional_arguments_raise(self, cls, args):
        with pytest.raises(TypeError):
            cls(*args)

    def test_specs_use_identity_based_equality_and_hash(self):
        a = Filter(name="f", expression="1")
        b = Filter(name="f", expression="1")
        assert a != b
        assert len({a, b}) == 2
