from unittest.mock import create_autospec

import pytest

from xyh.core.graph import builder
from xyh.core.specs.specs import Context, WeightProduct
from xyh.core.specs.storage import SpecsStorage


@pytest.fixture
def context():
    return Context(
        campaign="c",
        channel="ch",
        category="cat",
        dataset="ds",
        process="p",
        variation="nominal",
    )


@pytest.fixture
def storage(make_dataset, make_filter, make_weight, make_histogram):
    s = create_autospec(SpecsStorage, instance=True)
    s.get_dataset_spec.return_value = make_dataset()
    s.get_filters_specs.return_value = [
        make_filter(name="f1"),
        make_filter(name="f2"),
    ]
    s.get_weights_specs.return_value = [
        make_weight(name="w1"),
        make_weight(name="w2"),
    ]
    s.get_histogram_specs.side_effect = lambda ctx, var: make_histogram(
        variable=var
    )
    return s


def _chain(node):
    out = []
    while node is not None:
        out.append(node)
        node = node.parents[0] if node.parents else None
    return out[::-1]


class TestFiltersAndWeights:
    def test_chain_order_is_input_filters_weights_product(
        self, context, storage
    ):
        last = builder._build_context_nodes_for_filters_and_weights_operations(
            context, storage
        )
        ops = [n.operation for n in _chain(last)]
        assert ops == [
            "input_files",
            "filter",
            "filter",
            "weight",
            "weight",
            "weight_product",
        ]

    def test_chain_preserves_spec_order_and_single_parents(
        self, context, storage
    ):
        last = builder._build_context_nodes_for_filters_and_weights_operations(
            context, storage
        )
        chain = _chain(last)
        assert all(len(n.parents) <= 1 for n in chain)
        assert [n.data.name for n in chain[1:3]] == ["f1", "f2"]
        assert [n.data.name for n in chain[3:5]] == ["w1", "w2"]

    def test_product_node_carries_all_weights(self, context, storage):
        last = builder._build_context_nodes_for_filters_and_weights_operations(
            context, storage
        )
        assert isinstance(last.data, WeightProduct)
        assert last.data.weights == storage.get_weights_specs.return_value

    def test_specs_requested_for_given_context(self, context, storage):
        builder._build_context_nodes_for_filters_and_weights_operations(
            context, storage
        )
        storage.get_dataset_spec.assert_called_once_with(context)
        storage.get_filters_specs.assert_called_once_with(context)
        storage.get_weights_specs.assert_called_once_with(context)

    def test_no_filters_no_weights_chain_is_input_then_product(
        self, context, storage
    ):
        storage.get_filters_specs.return_value = []
        storage.get_weights_specs.return_value = []
        last = builder._build_context_nodes_for_filters_and_weights_operations(
            context, storage
        )
        assert [n.operation for n in _chain(last)] == [
            "input_files",
            "weight_product",
        ]

    def test_chain_is_deterministic(self, context, storage):
        f = builder._build_context_nodes_for_filters_and_weights_operations
        assert f(context, storage).hash == f(context, storage).hash


class TestHistograms:
    def test_one_leaf_per_variable_with_shared_parent(self, context, storage):
        leaves = builder._build_context_nodes_for_histograms(
            context, storage, ["pt", "eta", "mass"]
        )
        assert [n.operation for n in leaves] == ["histogram"] * 3
        assert [n.data.variable for n in leaves] == ["pt", "eta", "mass"]
        parent = leaves[0].parents[0]
        assert parent.operation == "weight_product"
        assert all(n.parents == (parent,) for n in leaves)
        assert len({n.hash for n in leaves}) == 3

    def test_histogram_specs_requested_per_variable(self, context, storage):
        builder._build_context_nodes_for_histograms(
            context, storage, ["pt", "eta"]
        )
        calls = [c.args for c in storage.get_histogram_specs.call_args_list]
        assert calls == [(context, "pt"), (context, "eta")]

    def test_no_variables_returns_empty_list(self, context, storage):
        assert (
            builder._build_context_nodes_for_histograms(context, storage, [])
            == []
        )
