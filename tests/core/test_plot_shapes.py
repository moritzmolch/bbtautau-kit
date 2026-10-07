"""Unit tests for the parallel control plot production."""

from xyh.core.plotting.control_plots import _build_plot_tasks, plot_shapes


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


def test_build_plot_tasks_groups_histogram_nodes():
    nodes = [
        _histogram_node("c1", "ee", "base", "yield", "tt", "tt_4q"),
        _histogram_node("c1", "ee", "base", "pt", "tt", "tt_4q"),
        _histogram_node("c1", "ee", "jets", "yield", "tt", "tt_4q"),
        _histogram_node("c1", "mm", "base", "yield", "tt", "tt_4q"),
        _histogram_node("c2", "ee", "base", "yield", "tt", "tt_4q"),
    ]

    tasks = _build_plot_tasks(
        _graph_specs(nodes),
        "some.factory_fn",
        "merged",
        "output",
        ["png", "pdf"],
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
        assert task["merged_histograms_dir"] == "merged"
        assert task["output_dir"] == "output"
        assert task["extensions"] == ["png", "pdf"]


def test_plot_shapes_serial_invokes_worker_per_task(tmp_path, monkeypatch):
    import xyh.core.plotting.control_plots as plotting

    calls = []

    def stub_worker(task):
        calls.append(task)
        return ["output.png"]

    monkeypatch.setattr(plotting, "_plot_category_variable", stub_worker)

    nodes = [
        _histogram_node("c1", "ee", "base", "yield", "tt", "tt_4q"),
        _histogram_node("c1", "ee", "base", "pt", "tt", "tt_4q"),
    ]
    plot_shapes(
        "some.factory_fn",
        _graph_specs(nodes),
        tmp_path / "merged",
        tmp_path / "output",
        ["png"],
    )

    assert len(calls) == 2
    assert {c["variable"] for c in calls} == {"yield", "pt"}


def test_plot_shapes_parallel_delegates_to_run_in_parallel(
    tmp_path, monkeypatch
):
    import xyh.core.plotting.control_plots as plotting

    dispatched = {}

    def fake_run_in_parallel(fn, tasks, num_workers):
        dispatched["fn"] = fn
        dispatched["tasks"] = tasks
        dispatched["num_workers"] = num_workers
        return ["output.png"]

    monkeypatch.setattr(plotting, "run_in_parallel", fake_run_in_parallel)

    nodes = [_histogram_node("c1", "ee", "base", "yield", "tt", "tt_4q")]
    plot_shapes(
        "some.factory_fn",
        _graph_specs(nodes),
        tmp_path / "merged",
        tmp_path / "output",
        ["png"],
        num_workers=4,
    )

    assert dispatched["num_workers"] == 4
    assert dispatched["fn"] is plotting._plot_category_variable
    assert len(dispatched["tasks"]) == 1
    assert dispatched["tasks"][0]["variable"] == "yield"
