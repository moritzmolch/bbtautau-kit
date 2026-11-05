"""Unit tests for the control plot production."""

import pickle
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import ROOT

from xyh.core.plotting import control_plots
from xyh.core.plotting.control_plots import (
    _build_plot_tasks,
    _plot_category_variable,
    plot_shapes,
)


@pytest.fixture(autouse=True)
def restore_th1_directory_status():
    previous = ROOT.TH1.AddDirectoryStatus()
    yield
    ROOT.TH1.AddDirectory(previous)


def _group(name, processes, scale_factor=None):
    return SimpleNamespace(
        name=name,
        processes=list(processes),
        color=f"color_{name}",
        label=f"label_{name}",
        scale_factor=scale_factor,
    )


def _inventory(
    channel="tt",
    categories=("cat",),
    blinded=False,
    process_set=None,
    category_aux=None,
    process_insts=None,
):
    category_aux = category_aux or {}
    if process_set is None:
        process_set = SimpleNamespace(
            data=[_group("data", ["d1", "d2"])],
            signals=[_group("sig", ["s1"])],
            backgrounds=[
                _group("bkg_a", ["a1", "a2"], scale_factor={"tt": 2.0}),
                _group("bkg_b", ["b1"], scale_factor={"et": 3.0}),
            ],
        )
    return SimpleNamespace(
        campaign=SimpleNamespace(
            name="c", x=SimpleNamespace(lumi=100.0), ecm=13.6
        ),
        channel=SimpleNamespace(
            name=channel,
            has_category=lambda c: c in categories,
            get_category=lambda c: SimpleNamespace(
                name=c,
                label=f"label_{c}",
                has_tag=lambda tag: blinded and tag == "blinded",
                has_aux=lambda key: key in category_aux,
                x=SimpleNamespace(**category_aux),
            ),
        ),
        processes=SimpleNamespace(
            get=lambda n: (process_insts or {}).get(n, SimpleNamespace(name=n))
        ),
        process_set=process_set,
        variables=SimpleNamespace(
            get=lambda n: SimpleNamespace(
                name=n, get_full_x_title=lambda: f"title_{n}"
            )
        ),
    )


@pytest.fixture
def inventories(monkeypatch):
    state = SimpleNamespace(by_channel={}, loads=[])

    def fake_load_inventory(path, campaign, channel, **kwargs):
        state.loads.append((path, campaign, channel, kwargs))
        return state.by_channel[channel]

    monkeypatch.setattr(control_plots, "load_inventory", fake_load_inventory)
    return state


@pytest.fixture
def plot_mock(monkeypatch):
    fig = MagicMock(name="fig")
    mock = MagicMock(name="plot", return_value=(fig, MagicMock(name="ax")))
    monkeypatch.setattr(control_plots, "plot", mock)
    mock.fig = fig
    return mock


def _task_args(**overrides):
    kwargs = {
        "inventory_factory_fn_path": "pkg:fn",
        "inventory_factory_kwargs": {"opt": 1},
        "campaigns": ["c"],
        "channels": ["tt"],
        "categories": ["cat"],
        "variables": ["pt"],
        "merged_histograms_file": Path("/in/merged.root"),
        "output_dir": Path("/out"),
        "extensions": ["png"],
    }
    kwargs.update(overrides)
    return kwargs


class TestBuildPlotTasks:
    def test_one_task_per_campaign_channel_category_variable(self, inventories):
        inventories.by_channel["tt"] = _inventory("tt", ("c1", "c2"))
        inventories.by_channel["et"] = _inventory("et", ("c1",))
        tasks = _build_plot_tasks(
            **_task_args(
                channels=["tt", "et"],
                categories=["c1", "c2"],
                variables=["pt", "eta"],
            )
        )
        assert [
            (t["channel"], t["category"], t["variable"]) for t in tasks
        ] == [
            ("tt", "c1", "pt"),
            ("tt", "c1", "eta"),
            ("tt", "c2", "pt"),
            ("tt", "c2", "eta"),
            ("et", "c1", "pt"),
            ("et", "c1", "eta"),
        ]

    def test_task_contains_all_worker_inputs(self, inventories):
        inventories.by_channel["tt"] = _inventory("tt")
        (task,) = _build_plot_tasks(**_task_args())
        assert task == {
            "inventory_factory_fn_path": "pkg:fn",
            "inventory_factory_kwargs": {"opt": 1},
            "campaign": "c",
            "channel": "tt",
            "category": "cat",
            "variable": "pt",
            "merged_histograms_file": Path("/in/merged.root"),
            "output_dir": Path("/out"),
            "extensions": ["png"],
        }

    def test_tasks_are_picklable(self, inventories):
        inventories.by_channel["tt"] = _inventory("tt")
        tasks = _build_plot_tasks(**_task_args(variables=["pt", "eta"]))
        assert tasks
        for task in tasks:
            assert pickle.loads(pickle.dumps(task)) == task

    def test_channel_restricted_variable_is_skipped(self, inventories):
        inventories.by_channel["tt"] = _inventory("tt")
        inventories.by_channel["et"] = _inventory("et")
        tasks = _build_plot_tasks(
            **_task_args(channels=["tt", "et"], variables=["pt", "mass[tt]"])
        )
        assert [(t["channel"], t["variable"]) for t in tasks] == [
            ("tt", "pt"),
            ("tt", "mass"),
            ("et", "pt"),
        ]

    def test_variable_name_has_channel_restriction_stripped(self, inventories):
        inventories.by_channel["tt"] = _inventory("tt")
        (task,) = _build_plot_tasks(**_task_args(variables=["mass[tt,et]"]))
        assert task["variable"] == "mass"

    def test_category_not_in_channel_is_skipped(self, inventories):
        inventories.by_channel["tt"] = _inventory("tt", ("cat",))
        tasks = _build_plot_tasks(**_task_args(categories=["x", "cat"]))
        assert [t["category"] for t in tasks] == ["cat"]

    def test_inventory_loaded_once_per_campaign_and_channel(self, inventories):
        inventories.by_channel["tt"] = _inventory("tt")
        _build_plot_tasks(**_task_args(variables=["a", "b", "c"]))
        assert inventories.loads == [("pkg:fn", "c", "tt", {"opt": 1})]

    def test_no_campaigns_gives_no_tasks(self, inventories):
        assert _build_plot_tasks(**_task_args(campaigns=[])) == []


def _write_merged(path, entries):
    root_file = ROOT.TFile.Open(str(path), "RECREATE")
    for key, value in entries.items():
        dir_name, _, name = key.rpartition("/")
        directory = root_file.GetDirectory(dir_name) or root_file.mkdir(
            dir_name
        )
        directory.cd()
        hist = ROOT.TH1D(name, name, 2, 0.0, 2.0)
        hist.SetBinContent(1, value)
        hist.SetBinContent(2, 2 * value)
        hist.Write()
    root_file.Close()


def _key(process, variable="pt"):
    return f"c/tt/cat/{process}/{variable}__nominal"


@pytest.fixture
def merged_file(tmp_path):
    path = tmp_path / "merged.root"
    _write_merged(
        path,
        {
            _key("d1"): 1.0,
            _key("d2"): 2.0,
            _key("s1"): 5.0,
            _key("a1"): 10.0,
            _key("a2"): 20.0,
            _key("b1"): 100.0,
        },
    )
    return path


def _task(merged_file, tmp_path, **overrides):
    task = {
        "inventory_factory_fn_path": "pkg:fn",
        "inventory_factory_kwargs": {"opt": 1},
        "campaign": "c",
        "channel": "tt",
        "category": "cat",
        "variable": "pt",
        "merged_histograms_file": merged_file,
        "output_dir": tmp_path / "plots",
        "extensions": ["png", "pdf"],
    }
    task.update(overrides)
    return task


def _contents(hist):
    return [hist.GetBinContent(i) for i in (1, 2)]


class TestPlotCategoryVariable:
    def test_histograms_of_process_groups_are_summed_and_passed(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        _plot_category_variable(_task(merged_file, tmp_path))
        kwargs = plot_mock.call_args.kwargs

        hist_data, data_kwargs = kwargs["hist_data"]
        assert _contents(hist_data) == [3.0, 6.0]
        assert data_kwargs == {"color": "color_data", "label": "label_data"}

        ((sig, sig_kwargs),) = kwargs["hist_signals"]
        assert _contents(sig) == [5.0, 10.0]
        assert sig_kwargs == {"color": "color_sig", "label": "label_sig"}

        (bkg_a, kwargs_a), (bkg_b, kwargs_b) = kwargs["hist_backgrounds"]
        assert _contents(bkg_a) == [30.0, 60.0]
        assert _contents(bkg_b) == [100.0, 200.0]
        # Scale factors are looked up for the channel (default 1.0)
        assert kwargs_a["scale_factor"] == 2.0
        assert kwargs_b["scale_factor"] == 1.0

    def test_process_group_without_scale_factor_has_no_scale_kwarg(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        _plot_category_variable(_task(merged_file, tmp_path))
        ((_, sig_kwargs),) = plot_mock.call_args.kwargs["hist_signals"]
        assert "scale_factor" not in sig_kwargs

    def test_plot_receives_labels_and_campaign_information(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        _plot_category_variable(_task(merged_file, tmp_path))
        kwargs = plot_mock.call_args.kwargs
        assert kwargs["x_label_bottom"] == "title_pt"
        assert kwargs["category_label"] == "label_cat"
        assert kwargs["lumi"] == 100.0
        assert kwargs["sqrt_s"] == 13.6

    def test_inventory_loaded_from_task_information(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        _plot_category_variable(_task(merged_file, tmp_path))
        assert inventories.loads == [("pkg:fn", "c", "tt", {"opt": 1})]

    def test_blinded_category_passes_no_data(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt", blinded=True)
        _plot_category_variable(_task(merged_file, tmp_path))
        assert plot_mock.call_args.kwargs["hist_data"] is None

    def test_empty_process_group_is_omitted(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        process_set = SimpleNamespace(
            data=[_group("data", ["d1"])],
            signals=[_group("empty", [])],
            backgrounds=[_group("bkg", ["b1"])],
        )
        inventories.by_channel["tt"] = _inventory(process_set=process_set)
        _plot_category_variable(_task(merged_file, tmp_path))
        assert plot_mock.call_args.kwargs["hist_signals"] == []

    def test_missing_histogram_raises_value_error(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        task = _task(merged_file, tmp_path, variable="unknown")
        with pytest.raises(ValueError, match="unknown__nominal not found"):
            _plot_category_variable(task)
        plot_mock.assert_not_called()

    def test_saves_figure_for_each_extension(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        task = _task(merged_file, tmp_path)
        outputs = _plot_category_variable(task)
        base = tmp_path / "plots" / "c" / "tt__cat"
        assert outputs == [str(base / "pt.png"), str(base / "pt.pdf")]
        assert [c.args for c in plot_mock.fig.savefig.call_args_list] == [
            (base / "pt.png",),
            (base / "pt.pdf",),
        ]

    def test_output_directory_is_created(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        _plot_category_variable(_task(merged_file, tmp_path))
        assert (tmp_path / "plots" / "c" / "tt__cat").is_dir()

    def test_no_extensions_saves_nothing(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        task = _task(merged_file, tmp_path, extensions=[])
        assert _plot_category_variable(task) == []
        plot_mock.fig.savefig.assert_not_called()


class TestPlotShapes:
    def test_tasks_are_run_in_parallel_with_num_workers(
        self, inventories, monkeypatch
    ):
        inventories.by_channel["tt"] = _inventory("tt")
        run = MagicMock()
        monkeypatch.setattr(control_plots, "run_in_parallel", run)
        plot_shapes(**_task_args(variables=["pt", "eta"]), num_workers=4)
        run.assert_called_once()
        fn, tasks, num_workers = run.call_args.args
        assert fn is _plot_category_variable
        assert [t["variable"] for t in tasks] == ["pt", "eta"]
        assert num_workers == 4

    def test_num_workers_defaults_to_one(self, inventories, monkeypatch):
        inventories.by_channel["tt"] = _inventory("tt")
        run = MagicMock()
        monkeypatch.setattr(control_plots, "run_in_parallel", run)
        plot_shapes(**_task_args())
        assert run.call_args.args[2] == 1


class TestPlotCategoryVariableSkippedProcesses:
    """Processes skipped by the category are neither read nor plotted."""

    @staticmethod
    def _skip(names):
        return lambda process_inst: process_inst.name in names

    def test_skipped_signal_needs_no_histogram_and_is_not_plotted(
        self, inventories, plot_mock, tmp_path
    ):
        # The merged file has no histogram for the skipped signal `s1`
        merged = tmp_path / "merged.root"
        _write_merged(
            merged,
            {
                _key("d1"): 1.0,
                _key("d2"): 2.0,
                _key("a1"): 10.0,
                _key("a2"): 20.0,
                _key("b1"): 100.0,
            },
        )
        inventories.by_channel["tt"] = _inventory(
            category_aux={"skip_process_inst": self._skip({"s1"})}
        )
        _plot_category_variable(_task(merged, tmp_path))
        assert plot_mock.call_args.kwargs["hist_signals"] == []

    def test_only_skipped_processes_of_a_group_are_left_out(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        inventories.by_channel["tt"] = _inventory(
            category_aux={"skip_process_inst": self._skip({"a2"})}
        )
        _plot_category_variable(_task(merged_file, tmp_path))
        (bkg_a, _), _ = plot_mock.call_args.kwargs["hist_backgrounds"]
        assert _contents(bkg_a) == [10.0, 20.0]

    def test_skip_function_receives_process_instance(
        self, inventories, plot_mock, merged_file, tmp_path
    ):
        seen = []

        def skip(process_inst):
            seen.append(process_inst.name)
            return False

        inventories.by_channel["tt"] = _inventory(
            category_aux={"skip_process_inst": skip}
        )
        _plot_category_variable(_task(merged_file, tmp_path))
        assert sorted(seen) == ["a1", "a2", "b1", "d1", "d2", "s1"]
