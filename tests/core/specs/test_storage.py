"""Unit tests for `SpecsStorage`."""

import pytest

from xyh.core.specs.specs import (
    Binning,
    Context,
    Dataset,
    Filter,
    FiltersAndWeights,
    Histogram,
    Weight,
)
from xyh.core.specs.storage import SpecsStorage


def _context(**kwargs):
    defaults = {
        "campaign": "c",
        "channel": "tt",
        "category": "cat",
        "dataset": "d",
        "process": "p",
        "variation": "nominal",
    }
    defaults.update(kwargs)
    return Context(**defaults)


def _faw(variation="nominal", dataset="d", process="p", category="cat"):
    return FiltersAndWeights(
        campaign="c",
        channel="tt",
        category=category,
        process=process,
        dataset=dataset,
        variation=variation,
        filters=[Filter(name=f"f_{variation}", expression="1")],
        weights=[Weight(name=f"w_{variation}", expression="2")],
    )


def _binning(variable, category="cat", channel="tt"):
    return Binning(
        campaign="c",
        channel=channel,
        category=category,
        variable=variable,
        expression=variable,
        bin_edges=[0, 1],
    )


@pytest.fixture
def dataset_spec():
    return Dataset(
        campaign="c", channel="tt", dataset="d", files={"main": ["a.root"]}
    )


@pytest.fixture
def faw_specs():
    return [_faw("nominal"), _faw("up"), _faw("nominal", dataset="d2")]


@pytest.fixture
def binnings():
    return [_binning("pt"), _binning("eta"), _binning("pt", category="other")]


@pytest.fixture
def storage(dataset_spec, faw_specs, binnings):
    return SpecsStorage([dataset_spec], faw_specs, binnings)


class TestGetDatasetSpec:
    def test_returns_spec_for_campaign_channel_dataset(
        self, storage, dataset_spec
    ):
        assert storage.get_dataset_spec(_context()) is dataset_spec

    def test_ignores_category_process_and_variation(
        self, storage, dataset_spec
    ):
        context = _context(category="x", process="y", variation="z")
        assert storage.get_dataset_spec(context) is dataset_spec

    @pytest.mark.parametrize(
        "field, value",
        [("campaign", "x"), ("channel", "et"), ("dataset", "nope")],
    )
    def test_unknown_key_raises_key_error(self, storage, field, value):
        with pytest.raises(KeyError):
            storage.get_dataset_spec(_context(**{field: value}))


class TestGetFiltersAndWeights:
    def test_filters_for_nominal(self, storage, faw_specs):
        assert storage.get_filters_specs(_context()) is faw_specs[0].filters

    def test_weights_for_variation(self, storage, faw_specs):
        context = _context(variation="up")
        assert storage.get_weights_specs(context) is faw_specs[1].weights

    def test_dataset_distinguishes_entries(self, storage, faw_specs):
        context = _context(dataset="d2")
        assert storage.get_filters_specs(context) is faw_specs[2].filters

    @pytest.mark.parametrize(
        "field, value",
        [
            ("campaign", "x"),
            ("channel", "et"),
            ("category", "x"),
            ("dataset", "x"),
            ("process", "x"),
            ("variation", "x"),
        ],
    )
    def test_unknown_key_raises_key_error(self, storage, field, value):
        context = _context(**{field: value})
        with pytest.raises(KeyError):
            storage.get_filters_specs(context)
        with pytest.raises(KeyError):
            storage.get_weights_specs(context)


class TestGetVariables:
    def test_returns_variables_in_insertion_order(self, storage):
        assert storage.get_variables(_context()) == ["pt", "eta"]

    def test_depends_on_category(self, storage):
        assert storage.get_variables(_context(category="other")) == ["pt"]

    def test_returned_list_is_a_copy(self, storage):
        storage.get_variables(_context()).append("junk")
        assert storage.get_variables(_context()) == ["pt", "eta"]

    @pytest.mark.parametrize(
        "field, value",
        [("campaign", "x"), ("channel", "et"), ("category", "x")],
    )
    def test_unknown_key_raises_value_error(self, storage, field, value):
        with pytest.raises(ValueError, match="Binning specs for campaign"):
            storage.get_variables(_context(**{field: value}))


class TestGetHistogramSpec:
    def test_wraps_binning_with_context_fields(self, storage, binnings):
        context = _context(dataset="d2", process="p2", variation="up")
        spec = storage.get_histogram_spec(context, "eta")
        assert isinstance(spec, Histogram)
        assert spec.binning is binnings[1]
        assert (spec.dataset, spec.process, spec.variation) == (
            "d2",
            "p2",
            "up",
        )

    def test_depends_on_category(self, storage, binnings):
        spec = storage.get_histogram_spec(_context(category="other"), "pt")
        assert spec.binning is binnings[2]

    def test_unknown_variable_raises_key_error(self, storage):
        with pytest.raises(KeyError):
            storage.get_histogram_spec(_context(), "nope")

    def test_variable_not_available_in_category_raises(self, storage):
        with pytest.raises(KeyError):
            storage.get_histogram_spec(_context(category="other"), "eta")


class TestEmptyStorage:
    def test_all_getters_raise_on_empty_storage(self):
        storage = SpecsStorage([], [], [])
        context = _context()
        with pytest.raises(KeyError):
            storage.get_dataset_spec(context)
        with pytest.raises(KeyError):
            storage.get_filters_specs(context)
        with pytest.raises(KeyError):
            storage.get_weights_specs(context)
        with pytest.raises(ValueError):
            storage.get_variables(context)
        with pytest.raises(KeyError):
            storage.get_histogram_spec(context, "pt")
