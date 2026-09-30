from collections import OrderedDict

import networkx

from xyh.core.specs.graph import _list_leaf_nodes, create_graph_specs
from xyh.core.specs.specs import Dataset, FiltersAndWeights, Histogram


def test_list_leaf_nodes_selects_all_sinks(tmp_path):
    # Two categories share the same input node but have filter chains of
    # different lengths: "ee_base" is shorter than "ee_eq2j_eq1b", which adds
    # two jet category filters. The sinks of the shorter chain are located in
    # an earlier topological generation, so taking only the last generation
    # would silently drop them.
    dataset_specs = [
        Dataset(
            campaign="2024_nano_v15",
            channel="ee",
            dataset="tt_4q_powheg",
            nicks=["tt"],
            files={"main": ["ntuple.root"]},
        )
    ]

    base_filters = OrderedDict([("trigger_selection", "gen_weight > 0.0")])
    jet_filters = OrderedDict(
        [
            ("n_jets_selection", "n_jets == 2"),
            ("n_bjets_selection", "n_bjets == 1"),
        ]
    )
    weights = OrderedDict([("weight", "gen_weight")])

    filters_and_weights_specs = []
    for category, extra_filters in (
        ("ee_base", None),
        ("ee_eq2j_eq1b", jet_filters),
    ):
        filters = OrderedDict(base_filters)
        if extra_filters is not None:
            filters.update(extra_filters)
        filters_and_weights_specs.append(
            FiltersAndWeights(
                campaign="2024_nano_v15",
                channel="ee",
                category=category,
                process="tt",
                dataset="tt_4q_powheg",
                variation="nominal",
                filters=filters,
                weights=weights,
            )
        )

    histogram_specs = [
        Histogram(
            campaign="2024_nano_v15",
            channel="ee",
            category=category,
            variable="yield",
            expression="1.0",
            bin_edges=[0.0, 1.0],
        )
        for category in ("ee_base", "ee_eq2j_eq1b")
    ]

    graph = networkx.readwrite.json_graph.node_link_graph(
        create_graph_specs(
            dataset_specs,
            histogram_specs,
            filters_and_weights_specs,
            "histogram",
        )
    )
    subgraph = graph.subgraph(
        next(iter(networkx.weakly_connected_components(graph)))
    ).copy()

    # Verify that the graph reproduces the bug scenario: the sinks are placed
    # in different topological generations.
    sinks = [n for n in subgraph.nodes if subgraph.out_degree(n) == 0]
    assert len(sinks) == 2
    last_generation = set(list(networkx.topological_generations(subgraph))[-1])
    assert any(s not in last_generation for s in sinks)

    # Fabricate artifacts with output files that do not exist yet
    artifacts = {
        n: {"output_file": tmp_path / f"{n}.root"} for n in subgraph.nodes
    }

    # All sinks are selected, independent of the depth of their branch
    leaf_nodes = _list_leaf_nodes(subgraph, artifacts)
    assert sorted(leaf_nodes) == sorted(sinks)
