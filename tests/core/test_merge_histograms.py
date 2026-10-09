"""Unit tests for the parallel histogram merging."""

from xyh.core.histograms.util import _build_merge_tasks, merge_histograms


def _histogram_node(campaign, channel, category, variable, process, dataset):
    return {
        "id": f"{campaign}-{channel}-{category}-{variable}-{process}-{dataset}",
        "type": "HistogramNode",
        "spec": {
            "campaign": campaign,
            "channel": channel,
            "category": category,
            "dataset": dataset,
            "process": process,
            "variation": "nominal",
            "variable": variable,
            "expression": variable,
            "bin_edges": [0.0, 1.0],
            "output_file": (
                f"{campaign}/{channel}__{category}/{process}__{dataset}__"
                f"{variable}__nominal.root"
            ),
        },
    }


def _graph_specs(nodes):
    return {"nodes": nodes, "links": []}


def test_build_merge_tasks_groups_histogram_nodes():
    nodes = [
        # Two variables in the same category of campaign c1 / channel ee
        _histogram_node("c1", "ee", "base", "yield", "tt", "tt_4q"),
        _histogram_node("c1", "ee", "base", "pt", "tt", "tt_4q"),
        # A different category of the same campaign and channel
        _histogram_node("c1", "ee", "jets", "yield", "tt", "tt_4q"),
        # A different channel of the same campaign
        _histogram_node("c1", "mm", "base", "yield", "tt", "tt_4q"),
        # A different campaign
        _histogram_node("c2", "ee", "base", "yield", "tt", "tt_4q"),
    ]
    # Non-histogram nodes must be ignored
    input_node = {
        "id": "input",
        "type": "InputFilesNode",
        "spec": {"campaign": "c1", "channel": "ee", "dataset": "tt_4q"},
    }
    graph_specs = _graph_specs(nodes + [input_node])

    tasks = _build_merge_tasks(
        graph_specs,
        "some.factory_fn",
        "histograms",
        "output",
    )

    keys = {
        (t["campaign"], t["channel"], t["category"], t["variable"])
        for t in tasks
    }
    assert keys == {
        ("c1", "ee", "base", "yield"),
        ("c1", "ee", "base", "pt"),
        ("c1", "ee", "jets", "yield"),
        ("c1", "mm", "base", "yield"),
        ("c2", "ee", "base", "yield"),
    }

    for task in tasks:
        assert task["inventory_factory_fn_path"] == "some.factory_fn"
        assert task["histograms_dir"] == "histograms"
        assert task["output_dir"] == "output"
        assert len(task["nodes"]) == 1
        assert task["nodes"][0]["variable"] == task["variable"]


def test_merge_histograms_serial_invokes_worker_per_task(tmp_path, monkeypatch):
    import xyh.core.histograms.util as util

    calls = []

    def stub_worker(task):
        calls.append(task)
        return "output"

    monkeypatch.setattr(util, "_merge_category_variable", stub_worker)

    nodes = [
        _histogram_node("c1", "ee", "base", "yield", "tt", "tt_4q"),
        _histogram_node("c1", "ee", "base", "pt", "tt", "tt_4q"),
    ]
    merge_histograms(
        "some.factory_fn",
        _graph_specs(nodes),
        tmp_path / "histograms",
        tmp_path / "output",
    )

    assert len(calls) == 2
    assert {c["variable"] for c in calls} == {"yield", "pt"}


def test_merge_histograms_parallel_delegates_to_run_in_parallel(
    tmp_path, monkeypatch
):
    import xyh.core.histograms.util as util

    dispatched = {}

    def fake_run_in_parallel(fn, tasks, num_workers):
        dispatched["fn"] = fn
        dispatched["tasks"] = tasks
        dispatched["num_workers"] = num_workers
        return ["output"]

    monkeypatch.setattr(util, "run_in_parallel", fake_run_in_parallel)

    nodes = [_histogram_node("c1", "ee", "base", "yield", "tt", "tt_4q")]
    merge_histograms(
        "some.factory_fn",
        _graph_specs(nodes),
        tmp_path / "histograms",
        tmp_path / "output",
        num_workers=4,
    )

    assert dispatched["num_workers"] == 4
    assert dispatched["fn"] is util._merge_category_variable
    assert len(dispatched["tasks"]) == 1
    assert dispatched["tasks"][0]["variable"] == "yield"
