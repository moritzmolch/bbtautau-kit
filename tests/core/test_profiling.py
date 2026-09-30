"""Unit tests for the profiling infrastructure of the graph processing."""

import networkx
import pytest

from xyh.core.specs.graph import (
    _capture_rdf_report,
    _new_subgraph_profile,
    _peak_rss_mb,
    _rss_mb,
    _summarize_profiles,
    run_graph,
    run_subgraph,
)

# -----------------------------------------------------------------------------
# Memory helpers
# -----------------------------------------------------------------------------


def test_rss_mb_is_positive():
    assert _rss_mb() > 0.0


def test_peak_rss_mb_is_positive():
    assert _peak_rss_mb() > 0.0


# -----------------------------------------------------------------------------
# Profile helpers
# -----------------------------------------------------------------------------


def test_new_subgraph_profile_contains_enabled_components():
    profile = _new_subgraph_profile(
        {"stages": True, "rdataframe": True, "memory": True}
    )

    assert set(profile) == {
        "times_s",
        "nodes",
        "leaf_nodes",
        "events_processed",
        "rdf_report",
        "memory",
    }
    assert set(profile["times_s"]) == {"declare", "run", "write", "total"}
    assert set(profile["memory"]) == {
        "rss_mb_start",
        "rss_mb_end",
        "peak_rss_mb",
    }


def test_new_subgraph_profile_omits_disabled_components():
    profile = _new_subgraph_profile(
        {"stages": False, "rdataframe": False, "memory": False}
    )

    assert set(profile) == {"times_s", "nodes", "leaf_nodes"}
    assert set(profile["times_s"]) == {"total"}


def test_summarize_profiles_aggregates_values():
    profiles = [
        {
            "times_s": {"declare": 0.5, "run": 10.0, "write": 1.0},
            "nodes": {"FilterNode": {"count": 3, "declare_s": 0.3}},
            "leaf_nodes": [{}, {}],
            "events_processed": 100,
        },
        {
            "times_s": {"declare": 0.2, "run": 5.0, "write": 0.5},
            "nodes": {"FilterNode": {"count": 2, "declare_s": 0.2}},
            "leaf_nodes": [{}],
            "events_processed": 50,
        },
    ]

    totals = _summarize_profiles(profiles)

    assert totals == {
        "subgraphs": 2,
        "nodes_declared": 5,
        "leaf_nodes": 3,
        "events_processed": 150,
        "declare_s": 0.7,
        "run_s": 15.0,
        "write_s": 1.5,
    }


def test_summarize_profiles_handles_absent_components():
    profiles = [
        {
            "times_s": {"total": 1.0},
            "nodes": {},
            "leaf_nodes": [],
        }
    ]

    totals = _summarize_profiles(profiles)

    assert totals["subgraphs"] == 1
    assert totals["nodes_declared"] == 0
    assert totals["leaf_nodes"] == 0
    assert totals["events_processed"] == 0


def test_summarize_profiles_empty():
    totals = _summarize_profiles([])
    assert totals == {
        "subgraphs": 0,
        "nodes_declared": 0,
        "leaf_nodes": 0,
        "events_processed": 0,
        "declare_s": 0.0,
        "run_s": 0.0,
        "write_s": 0.0,
    }


# -----------------------------------------------------------------------------
# run_subgraph / run_graph
# -----------------------------------------------------------------------------


@pytest.fixture
def empty_subgraph():
    """An empty subgraph that requires no ROOT processing."""
    return networkx.DiGraph()


def test_run_subgraph_returns_none_without_profiling(empty_subgraph, tmp_path):
    assert run_subgraph(empty_subgraph, tmp_path, None) is None


def test_run_subgraph_returns_profile_with_profiling(empty_subgraph, tmp_path):
    profile = run_subgraph(
        empty_subgraph,
        tmp_path,
        {"stages": True, "rdataframe": True, "memory": True},
    )

    assert profile is not None
    assert profile["times_s"]["total"] >= 0.0
    assert profile["leaf_nodes"] == []
    assert profile["events_processed"] == 0


def test_run_graph_none_without_profiling(tmp_path):
    graph_specs = networkx.readwrite.json_graph.node_link_data(
        networkx.DiGraph()
    )
    report = run_graph(graph_specs, tmp_path, 1, None)
    assert report is None


def test_run_graph_returns_report_with_profiling(tmp_path):
    graph_specs = networkx.readwrite.json_graph.node_link_data(
        networkx.DiGraph()
    )
    report = run_graph(
        graph_specs,
        tmp_path,
        1,
        {"stages": True, "rdataframe": True, "memory": True},
    )

    assert report is not None
    assert report["subgraphs"] == []
    assert report["wall_s"] >= 0.0
    assert report["memory"]["peak_rss_mb"] > 0.0
    assert report["totals"]["subgraphs"] == 0


# -----------------------------------------------------------------------------
# ROOT RDataFrame report
# -----------------------------------------------------------------------------


@pytest.mark.integration
def test_capture_rdf_report():
    import ROOT

    data_frame = ROOT.RDataFrame(100)
    data_frame = data_frame.Define("x", "1.0")
    data_frame = data_frame.Filter("x > 0.5", "positive")
    report = data_frame.Report()
    ROOT.RDF.RunGraphs([report])

    text = _capture_rdf_report(report)

    assert "positive" in text
