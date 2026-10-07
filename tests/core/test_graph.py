import logging
from collections import OrderedDict

import networkx
import ROOT

from xyh.core.specs.graph import (
    _capture_logging_config,
    _enable_rdf_progress_bar,
    _init_worker_logging,
    _list_leaf_nodes,
    _subgraph_label,
    create_graph_specs,
)
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


def test_subgraph_label_reports_root_node_info():
    dataset_specs = [
        Dataset(
            campaign="2024_nano_v15",
            channel="ee",
            dataset="tt_4q_powheg",
            nicks=["tt"],
            files={"main": ["ntuple.root"]},
        )
    ]
    filters_and_weights_specs = [
        FiltersAndWeights(
            campaign="2024_nano_v15",
            channel="ee",
            category="ee_base",
            process="tt",
            dataset="tt_4q_powheg",
            variation="nominal",
            filters=OrderedDict([("trigger_selection", "x > 0.0")]),
            weights=OrderedDict([("weight", "1.0")]),
        )
    ]
    histogram_specs = [
        Histogram(
            campaign="2024_nano_v15",
            channel="ee",
            category="ee_base",
            variable="x",
            expression="x",
            bin_edges=[0.0, 1.0],
        )
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

    label = _subgraph_label(subgraph)
    assert "campaign='2024_nano_v15'" in label
    assert "channel='ee'" in label
    assert "dataset='tt_4q_powheg'" in label


def test_subgraph_label_falls_back_for_empty_graph():
    assert _subgraph_label(networkx.DiGraph()) == "subgraph with 0 root nodes"


def test_worker_logging_initializer_replays_parent_config(capsys):
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    root.handlers.clear()
    try:
        # Configure the root logger as the entry point would
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(levelname)s|%(name)s|%(message)s")
        )
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)

        config = _capture_logging_config()

        # Replay the configuration in a "fresh" worker interpreter
        root.handlers.clear()
        root.setLevel(logging.NOTSET)
        _init_worker_logging(config)

        logging.getLogger("xyh.test.worker").info("hello from worker")
        captured = capsys.readouterr()
        assert "INFO|xyh.test.worker|hello from worker" in captured.err
    finally:
        root.handlers.clear()
        root.handlers.extend(old_handlers)
        root.setLevel(old_level)


def test_rdf_progress_bar_guards_against_missing_api(monkeypatch):
    def _boom(*args, **kwargs):
        raise AttributeError("AddProgressBar is not available")

    monkeypatch.setattr(ROOT.RDF.Experimental, "AddProgressBar", _boom)

    subgraph = networkx.DiGraph()
    subgraph.add_node("root", type="InputFilesNode", spec={})
    artifacts = {"root": {"data_frame": object()}}

    # Missing or broken progress bar API must never break the processing
    _enable_rdf_progress_bar(subgraph, artifacts)
