from unittest.mock import create_autospec

import networkx as nx
import pytest

from xyh.core.graph import builder
from xyh.core.graph.node import Node
from xyh.core.specs.specs import Context, HistogramsOutput, WeightProduct
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


class TestBuildGraphFromLeafNodes:
    def test_empty_leaf_list_gives_empty_graph(self):
        graph = builder.build_graph_from_leaf_nodes([])
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_single_node_without_parents_gives_one_node_no_edges(
        self, make_dataset
    ):
        node = Node(operation="input_files", data=make_dataset())
        graph = builder.build_graph_from_leaf_nodes([node])
        assert graph.number_of_nodes() == 1
        assert graph.number_of_edges() == 0

    def test_linear_chain_has_edges_from_parent_to_child(
        self, make_dataset, make_filter, make_histogram
    ):
        inp = Node(operation="input_files", data=make_dataset())
        flt = Node(operation="filter", data=make_filter(), parents=(inp,))
        hist = Node(
            operation="histogram", data=make_histogram(), parents=(flt,)
        )
        graph = builder.build_graph_from_leaf_nodes([hist])
        assert graph.number_of_nodes() == 3
        assert graph.number_of_edges() == 2
        assert set(graph.edges) == {
            (inp.hash, flt.hash),
            (flt.hash, hist.hash),
        }

    def test_full_context_with_three_variables_counts(self, context, storage):
        leaves = builder._build_context_nodes_for_histograms(
            context, storage, ["pt", "eta", "mass"]
        )
        graph = builder.build_graph_from_leaf_nodes(leaves)
        assert graph.number_of_nodes() == 9
        assert graph.number_of_edges() == 8
        product = leaves[0].parents[0]
        assert graph.out_degree(product.hash) == 3

    def test_node_ids_are_hashes_and_attribute_is_original_node(
        self, context, storage
    ):
        leaves = builder._build_context_nodes_for_histograms(
            context, storage, ["pt", "eta"]
        )
        graph = builder.build_graph_from_leaf_nodes(leaves)
        for leaf in leaves:
            assert leaf.hash in graph
            assert graph.nodes[leaf.hash]["node"] is leaf
        parent = leaves[0].parents[0]
        assert graph.nodes[parent.hash]["node"] is parent

    def test_equal_content_distinct_objects_collapse_to_one_node(
        self, make_dataset
    ):
        a = Node(operation="input_files", data=make_dataset())
        b = Node(operation="input_files", data=make_dataset())
        assert a is not b
        assert a.hash == b.hash
        graph = builder.build_graph_from_leaf_nodes([a, b])
        assert graph.number_of_nodes() == 1
        assert graph.nodes[a.hash]["node"] is a

    def test_duplicate_leaf_is_added_once(self, make_dataset, make_filter):
        inp = Node(operation="input_files", data=make_dataset())
        flt = Node(operation="filter", data=make_filter(), parents=(inp,))
        graph = builder.build_graph_from_leaf_nodes([flt, flt])
        assert graph.number_of_nodes() == 2
        assert graph.number_of_edges() == 1

    def test_diamond_adds_shared_grandparent_once(
        self, make_dataset, make_filter, make_weight, make_histogram
    ):
        root = Node(operation="input_files", data=make_dataset())
        left = Node(operation="filter", data=make_filter(), parents=(root,))
        right = Node(operation="weight", data=make_weight(), parents=(root,))
        child = Node(
            operation="histogram",
            data=make_histogram(),
            parents=(left, right),
        )
        graph = builder.build_graph_from_leaf_nodes([child])
        assert graph.number_of_nodes() == 4
        assert graph.number_of_edges() == 4
        assert graph.out_degree(root.hash) == 2
        assert graph.in_degree(child.hash) == 2

    def test_two_contexts_share_common_prefix_only(
        self, context, storage, make_filter
    ):
        leaves_a = builder._build_context_nodes_for_histograms(
            context, storage, ["pt"]
        )
        # Second context differs from the first one from the second filter on
        storage.get_filters_specs.return_value = [
            make_filter(name="f1"),
            make_filter(name="f3"),
        ]
        leaves_b = builder._build_context_nodes_for_histograms(
            context, storage, ["pt"]
        )
        graph = builder.build_graph_from_leaf_nodes(leaves_a + leaves_b)
        # Shared: input_files and f1. Distinct: f2/f3 and everything after
        # (2 weights, product, histogram) -> 2 + 5 + 5 nodes.
        assert graph.number_of_nodes() == 12
        assert graph.number_of_edges() == 11
        shared = leaves_a[0].parents[0]
        while shared.operation != "input_files":
            shared = shared.parents[0]
        assert graph.out_degree(shared.hash) == 1
        f1 = next(iter(graph.successors(shared.hash)))
        assert graph.out_degree(f1) == 2

    def test_identical_contexts_collapse_completely(self, context, storage):
        leaves_a = builder._build_context_nodes_for_histograms(
            context, storage, ["pt"]
        )
        leaves_b = builder._build_context_nodes_for_histograms(
            context, storage, ["pt"]
        )
        graph = builder.build_graph_from_leaf_nodes(leaves_a + leaves_b)
        assert graph.number_of_nodes() == 7
        assert graph.number_of_edges() == 6

    def test_result_is_dag_with_leaves_as_sinks_and_input_as_source(
        self, context, storage
    ):
        leaves = builder._build_context_nodes_for_histograms(
            context, storage, ["pt", "eta", "mass"]
        )
        graph = builder.build_graph_from_leaf_nodes(leaves)
        assert nx.is_directed_acyclic_graph(graph)
        assert all(graph.out_degree(n.hash) == 0 for n in leaves)
        sources = [n for n in graph if graph.in_degree(n) == 0]
        assert len(sources) == 1
        assert graph.nodes[sources[0]]["node"].operation == "input_files"


BUG_LEAF_COMPREHENSION = (
    "build_histograms_graph: leaf comprehension uses subgraph.out_degree(n) "
    "before n is assigned (UnboundLocalError)"
)
BUG_STRUCTURAL_HASH = (
    "weisfeiler_lehman_graph_hash without node attributes is purely "
    "structural: same-structure subgraphs get the same subgraph_hash"
)


class TestBuildHistogramsGraph:
    @pytest.fixture
    def contexts(self, context):
        return [
            context,
            Context(
                campaign="c",
                channel="ch",
                category="cat",
                dataset="ds2",
                process="p",
                variation="nominal",
            ),
        ]

    @pytest.fixture
    def storage_two_datasets(self, storage, make_dataset):
        storage.get_dataset_spec.side_effect = lambda ctx: make_dataset(
            dataset=ctx.dataset, files={"main": [f"{ctx.dataset}.root"]}
        )
        return storage

    @staticmethod
    def _write_nodes(graph):
        return [
            d["node"]
            for _, d in graph.nodes(data=True)
            if d["node"].operation == "write_histograms"
        ]

    def test_empty_contexts_returns_empty_list(self, storage, tmp_path):
        assert (
            builder.build_histograms_graph([], ["pt"], storage, tmp_path) == []
        )

    @pytest.mark.xfail(
        strict=True, raises=UnboundLocalError, reason=BUG_LEAF_COMPREHENSION
    )
    def test_one_graph_per_dataset_and_graphs_are_disjoint(
        self, contexts, storage_two_datasets, tmp_path
    ):
        graphs = builder.build_histograms_graph(
            contexts, ["pt", "eta"], storage_two_datasets, tmp_path
        )
        assert len(graphs) == 2
        assert not set(graphs[0].nodes) & set(graphs[1].nodes)

    @pytest.mark.xfail(
        strict=True, raises=UnboundLocalError, reason=BUG_LEAF_COMPREHENSION
    )
    def test_each_graph_has_one_write_node_over_histogram_leaves(
        self, contexts, storage_two_datasets, tmp_path
    ):
        graphs = builder.build_histograms_graph(
            contexts, ["pt", "eta"], storage_two_datasets, tmp_path
        )
        for graph in graphs:
            writers = self._write_nodes(graph)
            assert len(writers) == 1
            writer = writers[0]
            hist_nodes = {
                h
                for h, d in graph.nodes(data=True)
                if d["node"].operation == "histogram"
            }
            assert len(hist_nodes) == 2
            assert {p.hash for p in writer.parents} == hist_nodes
            assert set(graph.predecessors(writer.hash)) == hist_nodes
            sinks = [n for n in graph if graph.out_degree(n) == 0]
            assert sinks == [writer.hash]

    @pytest.mark.xfail(
        strict=True, raises=UnboundLocalError, reason=BUG_LEAF_COMPREHENSION
    )
    def test_write_node_output_dir_is_stringified_output_dir(
        self, context, storage, tmp_path
    ):
        (graph,) = builder.build_histograms_graph(
            [context], ["pt"], storage, tmp_path
        )
        (writer,) = self._write_nodes(graph)
        assert isinstance(writer.data, HistogramsOutput)
        assert writer.data.output_dir == str(tmp_path)

    @pytest.mark.xfail(
        strict=True, raises=UnboundLocalError, reason=BUG_LEAF_COMPREHENSION
    )
    def test_graphs_are_dags(self, contexts, storage_two_datasets, tmp_path):
        graphs = builder.build_histograms_graph(
            contexts, ["pt"], storage_two_datasets, tmp_path
        )
        assert all(nx.is_directed_acyclic_graph(g) for g in graphs)

    @pytest.mark.xfail(
        strict=True,
        raises=UnboundLocalError,
        reason=f"{BUG_LEAF_COMPREHENSION}; additionally {BUG_STRUCTURAL_HASH}",
    )
    def test_same_structure_different_specs_give_different_subgraph_hash(
        self, contexts, storage_two_datasets, tmp_path
    ):
        graphs = builder.build_histograms_graph(
            contexts, ["pt"], storage_two_datasets, tmp_path
        )
        hashes = {self._write_nodes(g)[0].data.subgraph_hash for g in graphs}
        assert len(hashes) == 2
