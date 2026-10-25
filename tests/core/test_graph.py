import array
import logging
from collections import OrderedDict

import networkx
import ROOT

from xyh.core.parallel import _capture_logging_config, _init_worker_logging
from xyh.core.specs.graph import (
    SnapshotNode,
    _enable_rdf_progress_bar,
    _list_leaf_nodes,
    _prepare_snapshot_columns,
    _snapshot,
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


def test_prepare_snapshot_columns_selects_patterns():
    all_columns = ["x", "ntuple.fEta", "ntuple.fM", "ntuple.fPhi", "ntuple.fPt"]

    # Without an explicit list, all columns are kept, with friend prefixes
    # stripped to plain names
    assert _prepare_snapshot_columns(all_columns) == [
        "x",
        "fEta",
        "fM",
        "fPhi",
        "fPt",
    ]

    # Only the explicitly listed columns are kept
    assert _prepare_snapshot_columns(all_columns, ("fEta", "fM")) == [
        "fEta",
        "fM",
    ]

    # Shell-style patterns also match friend-qualified names
    assert _prepare_snapshot_columns(all_columns, ("ntuple.f*",)) == [
        "fEta",
        "fM",
        "fPhi",
        "fPt",
    ]

    # The qualified name is kept when the plain name clashes with another
    # column, and patterns match either form
    clash = ["fPt", "ntuple.fPt"]
    assert _prepare_snapshot_columns(clash, ("ntuple.fPt",)) == ["ntuple.fPt"]
    assert _prepare_snapshot_columns(clash, ("fPt",)) == ["fPt"]


def test_prepare_snapshot_columns_honors_channel_restrictions():
    columns = ["mass_1", "mt_1", "pt_1", "tau_decaymode_1"]

    # Unrestricted entries apply in every channel
    assert _prepare_snapshot_columns(columns, ("pt_1",), channel="et") == [
        "pt_1"
    ]

    # A column restricted to a channel set is only written in those channels
    restricted = ("mass_1[tt]", "tau_decaymode_1[tt]", "mt_1[et,mt,tt]")
    assert _prepare_snapshot_columns(columns, restricted, channel="tt") == [
        "mass_1",
        "mt_1",
        "tau_decaymode_1",
    ]
    assert _prepare_snapshot_columns(columns, restricted, channel="mt") == [
        "mt_1",
    ]
    assert _prepare_snapshot_columns(columns, restricted, channel="et") == [
        "mt_1",
    ]

    # Without a channel, restrictions are ignored
    assert _prepare_snapshot_columns(columns, restricted) == [
        "mass_1",
        "mt_1",
        "tau_decaymode_1",
    ]


def test_create_graph_specs_passes_snapshot_columns_to_nodes():
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

    graph = networkx.readwrite.json_graph.node_link_graph(
        create_graph_specs(
            dataset_specs,
            [],
            filters_and_weights_specs,
            "snapshot",
            columns=["fEta", "fM"],
        )
    )
    snapshots = [
        data["spec"]
        for data in graph.nodes.values()
        if data["type"] == "SnapshotNode"
    ]
    assert len(snapshots) == 1
    # Tuples are only converted to lists when the spec is dumped to JSON
    assert snapshots[0]["columns"] == ("fEta", "fM")

    # Without an explicit list, the snapshot covers all columns
    graph = networkx.readwrite.json_graph.node_link_graph(
        create_graph_specs(
            dataset_specs,
            [],
            filters_and_weights_specs,
            "snapshot",
        )
    )
    snapshots = [
        data["spec"]
        for data in graph.nodes.values()
        if data["type"] == "SnapshotNode"
    ]
    assert snapshots[0]["columns"] is None


class _FriendDataFrame:
    """RDataFrame with the TChain objects kept alive.

    In production the chains stay alive through the artifacts dict (see
    `_input_files`). A helper-local reference would be garbage-collected and
    corrupt the friend tree, so the chains are stored on this wrapper, which
    forwards the `RDataFrame` interface used by the snapshot code.
    """

    def __init__(self, data_frame, main_chain, friend_chain):
        self._data_frame = data_frame
        self._main_chain = main_chain
        self._friend_chain = friend_chain

    def HasColumn(self, column):
        return self._data_frame.HasColumn(column)

    def GetColumnNames(self):
        return self._data_frame.GetColumnNames()

    def Snapshot(self, *args, **kwargs):
        return self._data_frame.Snapshot(*args, **kwargs)


def _make_friend_data_frame(tmp_path):
    """Create a main tree with `x` and a friend with the four-momentum
    columns, returning an RDataFrame filtered on `x > 0`."""
    # Main tree with a single column
    f = ROOT.TFile(str(tmp_path / "main.root"), "RECREATE")
    t = ROOT.TTree("ntuple", "ntuple")
    x = array.array("f", [0.0])
    t.Branch("x", x, "x/F")
    for i in range(10):
        x[0] = i
        t.Fill()
    t.Write()
    f.Close()

    # Friend tree carrying the four-momentum columns
    f = ROOT.TFile(str(tmp_path / "friend.root"), "RECREATE")
    t = ROOT.TTree("ntuple", "ntuple")
    columns = {}
    for name in ("fPt", "fEta", "fPhi", "fM"):
        columns[name] = array.array("f", [0.0])
        t.Branch(name, columns[name], f"{name}/F")
    for i in range(10):
        x[0] = i
        for j, name in enumerate(("fPt", "fEta", "fPhi", "fM")):
            columns[name][0] = i * (j + 1)
        t.Fill()
    t.Write()
    f.Close()

    main_chain = ROOT.TChain("ntuple")
    main_chain.Add(str(tmp_path / "main.root"))
    friend_chain = ROOT.TChain("ntuple")
    friend_chain.Add(str(tmp_path / "friend.root"))
    main_chain.AddFriend(friend_chain)

    return _FriendDataFrame(
        ROOT.RDataFrame(main_chain).Filter("x > 0", "sel"),
        main_chain,
        friend_chain,
    )


class _DataFrameWithoutColumn:
    """Wrap an RDataFrame and pretend a given column is not available."""

    def __init__(self, data_frame, missing):
        self._data_frame = data_frame
        self._missing = missing

    def HasColumn(self, column):
        if column in self._missing:
            return False
        return self._data_frame.HasColumn(column)

    def GetColumnNames(self):
        return self._data_frame.GetColumnNames()

    def Snapshot(self, *args, **kwargs):
        return self._data_frame.Snapshot(*args, **kwargs)


def test_snapshot_writes_only_configured_columns(tmp_path):
    data_frame = _make_friend_data_frame(tmp_path)

    # `fEta` is restricted to the `tt` channel and must not be written in the
    # `ee` snapshot
    node = SnapshotNode(
        campaign="2024_nano_v15",
        channel="ee",
        category="ee_base",
        dataset="tt_4q_powheg",
        process="tt",
        variation="nominal",
        output_file="out/ntuple.root",
        columns=("fEta[tt]", "fM"),
    )
    result = _snapshot(node, {"id": {"data_frame": data_frame}}, tmp_path)

    # Trigger the lazy snapshot
    ROOT.RDF.RunGraphs([result["lazy_object"]])

    output_file = ROOT.TFile.Open(str(result["output_file"]))
    output_tree = output_file.Get("ntuple")
    branches = sorted(b.GetName() for b in output_tree.GetListOfBranches())
    events = output_tree.GetEntriesFast()
    output_file.Close()

    assert branches == ["fM"]
    assert events == 9


def test_snapshot_ignores_columns_unavailable_for_sample(tmp_path):
    # A sample whose data frame reports `fEta` as not available
    data_frame = _DataFrameWithoutColumn(
        _make_friend_data_frame(tmp_path), missing={"fEta"}
    )

    node = SnapshotNode(
        campaign="2024_nano_v15",
        channel="ee",
        category="ee_base",
        dataset="tt_4q_powheg",
        process="tt",
        variation="nominal",
        output_file="out/ntuple.root",
        columns=("fEta", "fM"),
    )
    result = _snapshot(node, {"id": {"data_frame": data_frame}}, tmp_path)

    # Trigger the lazy snapshot
    ROOT.RDF.RunGraphs([result["lazy_object"]])

    output_file = ROOT.TFile.Open(str(result["output_file"]))
    output_tree = output_file.Get("ntuple")
    branches = sorted(b.GetName() for b in output_tree.GetListOfBranches())
    events = output_tree.GetEntriesFast()
    output_file.Close()

    # `fEta` is unavailable for this sample and must be ignored
    assert branches == ["fM"]
    assert events == 9
