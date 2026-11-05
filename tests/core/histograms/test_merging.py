"""Unit tests for the merging of the per-dataset histograms."""

from types import SimpleNamespace

import pytest
import ROOT
from order import Channel

from xyh.core.histograms import merging
from xyh.core.histograms.merging import merge_histograms
from xyh.core.io import dump_json


@pytest.fixture(autouse=True)
def restore_th1_directory_status():
    # `load_all` disables the ROOT directory ownership of histograms globally.
    previous = ROOT.TH1.AddDirectoryStatus()
    ROOT.TH1.AddDirectory(False)
    yield
    ROOT.TH1.AddDirectory(previous)


def make_variation(name, skip_processes=()):
    class Variation:
        def __init__(
            self, campaign_inst, channel_inst, category_inst, process_inst
        ):
            self.process_inst = process_inst

        def skip(self):
            return self.process_inst.name in skip_processes

    Variation.name = name
    return Variation


def _channel(name, categories, categories_aux):
    channel_inst = Channel(name=name, id=1)
    for c in categories:
        channel_inst.add_category(name=c, id="+", aux=categories_aux.get(c, {}))
    return channel_inst


def _inventory(
    channel,
    categories=("cat",),
    processes=("proc",),
    variables=("pt",),
    categories_aux=None,
):
    categories_aux = categories_aux or {}
    return SimpleNamespace(
        campaign=SimpleNamespace(name="c"),
        channel=_channel(channel, categories, categories_aux),
        processes=[SimpleNamespace(name=p) for p in processes],
        variables=SimpleNamespace(get=lambda n: SimpleNamespace(name=n)),
    )


@pytest.fixture
def datasets():
    return {"proc": ["ds1", "ds2"], "other": ["ds3"]}


@pytest.fixture
def setup(monkeypatch, datasets):
    """Patch the inventory loading and the process/dataset generation."""
    state = SimpleNamespace(inventories={}, loads=[])

    def fake_load_inventory(path, campaign, channel, **kwargs):
        state.loads.append((path, campaign, channel, kwargs))
        return state.inventories[channel]

    monkeypatch.setattr(merging, "load_inventory", fake_load_inventory)
    monkeypatch.setattr(
        merging, "gen_process_insts", lambda inv: list(inv.processes)
    )
    monkeypatch.setattr(
        merging,
        "gen_dataset_insts",
        lambda inv, process: [
            SimpleNamespace(name=d) for d in datasets[process.name]
        ],
    )
    monkeypatch.setattr(merging, "default_variations", [])
    return state


def _write_inputs(tmp_path, contents):
    """Write `histograms_in.root` and `histogram_keys.json.gz`."""
    path = tmp_path / "histograms_in.root"
    root_file = ROOT.TFile.Open(str(path), "RECREATE")
    for key, values in contents.items():
        dir_name, _, name = key.rpartition("/")
        directory = root_file.GetDirectory(dir_name) or root_file.mkdir(
            dir_name
        )
        directory.cd()
        hist = ROOT.TH1D(name, name, len(values), 0.0, float(len(values)))
        for i, v in enumerate(values, start=1):
            hist.SetBinContent(i, v)
        hist.Write()
    root_file.Close()
    dump_json(
        {path.name: sorted(contents)}, tmp_path / "histogram_keys.json.gz"
    )


def _key(process, dataset, variable="pt", variation="nominal", channel="tt"):
    return f"c/{channel}/cat/{process}/{dataset}/{variable}__{variation}"


def _read(path):
    root_file = ROOT.TFile.Open(str(path), "READ")
    result = {}

    def walk(directory, prefix):
        for key in directory.GetListOfKeys():
            obj = key.ReadObj()
            name = f"{prefix}{key.GetName()}"
            if obj.InheritsFrom("TDirectory"):
                walk(obj, name + "/")
            else:
                result[name] = (
                    obj.GetName(),
                    obj.GetTitle(),
                    [
                        obj.GetBinContent(i)
                        for i in range(1, obj.GetNbinsX() + 1)
                    ],
                )

    walk(root_file, "")
    root_file.Close()
    return result


def _run(tmp_path, **overrides):
    kwargs = {
        "inventory_factory_fn_path": "pkg:fn",
        "inventory_factory_kwargs": {"opt": 1},
        "campaigns": ["c"],
        "channels": ["tt"],
        "categories": ["cat"],
        "variables": ["pt"],
        "histograms_dir": tmp_path,
        "output_file": tmp_path / "merged.root",
    }
    kwargs.update(overrides)
    merge_histograms(**kwargs)
    return kwargs["output_file"]


class TestMergeHistograms:
    def test_datasets_summed_per_process(self, tmp_path, setup):
        setup.inventories["tt"] = _inventory("tt")
        _write_inputs(
            tmp_path,
            {_key("proc", "ds1"): [1, 2, 3], _key("proc", "ds2"): [10, 20, 30]},
        )
        out = _read(_run(tmp_path))
        assert out == {
            "c/tt/cat/proc/pt__nominal": (
                "pt__nominal",
                "pt__nominal",
                [11, 22, 33],
            )
        }

    def test_inventory_loaded_with_path_and_kwargs(self, tmp_path, setup):
        setup.inventories["tt"] = _inventory("tt")
        _write_inputs(
            tmp_path, {_key("proc", "ds1"): [1], _key("proc", "ds2"): [1]}
        )
        _run(tmp_path)
        assert setup.loads == [("pkg:fn", "c", "tt", {"opt": 1})]

    def test_variations_are_merged_and_skipped_ones_omitted(
        self, tmp_path, setup, monkeypatch
    ):
        setup.inventories["tt"] = _inventory("tt", processes=("proc", "other"))
        monkeypatch.setattr(
            merging,
            "default_variations",
            [
                make_variation("up"),
                make_variation("down", skip_processes=("other",)),
            ],
        )
        contents = {}
        for dataset, process in (
            ("ds1", "proc"),
            ("ds2", "proc"),
            ("ds3", "other"),
        ):
            for variation in ("nominal", "up", "down"):
                contents[_key(process, dataset, variation=variation)] = [1.0]
        _write_inputs(tmp_path, contents)
        out = _read(_run(tmp_path))
        assert sorted(out) == [
            "c/tt/cat/other/pt__nominal",
            "c/tt/cat/other/pt__up",
            "c/tt/cat/proc/pt__down",
            "c/tt/cat/proc/pt__nominal",
            "c/tt/cat/proc/pt__up",
        ]
        assert out["c/tt/cat/proc/pt__up"][2] == [2.0]
        assert out["c/tt/cat/other/pt__up"][2] == [1.0]

    def test_jetfakes_taken_from_jetfakes_dataset(
        self, tmp_path, setup, datasets
    ):
        setup.inventories["tt"] = _inventory("tt", processes=("jetfakes",))
        # `gen_dataset_insts` must not be needed for jetfakes
        datasets.clear()
        _write_inputs(tmp_path, {_key("jetfakes", "jetfakes"): [4, 5]})
        out = _read(_run(tmp_path))
        assert out["c/tt/cat/jetfakes/pt__nominal"][2] == [4, 5]

    def test_channel_restricted_variable_skipped_in_other_channels(
        self, tmp_path, setup
    ):
        setup.inventories["tt"] = _inventory("tt")
        setup.inventories["et"] = _inventory("et")
        contents = {}
        for channel in ("tt", "et"):
            for variable in ("pt", "mass"):
                for ds in ("ds1", "ds2"):
                    contents[_key("proc", ds, variable, channel=channel)] = [1]
        _write_inputs(tmp_path, contents)
        out = _read(
            _run(
                tmp_path,
                channels=["tt", "et"],
                variables=["pt", "mass[tt]"],
            )
        )
        assert sorted(out) == [
            "c/et/cat/proc/pt__nominal",
            "c/tt/cat/proc/mass__nominal",
            "c/tt/cat/proc/pt__nominal",
        ]

    def test_category_not_in_channel_is_skipped(self, tmp_path, setup):
        setup.inventories["tt"] = _inventory("tt", categories=("cat",))
        _write_inputs(
            tmp_path, {_key("proc", "ds1"): [1], _key("proc", "ds2"): [1]}
        )
        out = _read(_run(tmp_path, categories=["missing", "cat"]))
        assert list(out) == ["c/tt/cat/proc/pt__nominal"]

    def test_regex_categories_are_expanded_to_category_names(
        self, tmp_path, setup
    ):
        setup.inventories["tt"] = _inventory(
            "tt", categories=("cat_a", "cat_b", "other")
        )
        contents = {}
        for category in ("cat_a", "cat_b"):
            for dataset in ("ds1", "ds2"):
                contents[f"c/tt/{category}/proc/{dataset}/pt__nominal"] = [1.0]
        _write_inputs(tmp_path, contents)
        out = _read(_run(tmp_path, categories=[r"cat_.*"]))
        assert sorted(out) == [
            "c/tt/cat_a/proc/pt__nominal",
            "c/tt/cat_b/proc/pt__nominal",
        ]

    def test_missing_output_parent_directory_is_created(self, tmp_path, setup):
        setup.inventories["tt"] = _inventory("tt")
        _write_inputs(
            tmp_path, {_key("proc", "ds1"): [1], _key("proc", "ds2"): [1]}
        )
        output_file = tmp_path / "a" / "b" / "merged.root"
        assert _run(tmp_path, output_file=output_file).exists()

    def test_nothing_selected_writes_empty_file(self, tmp_path, setup):
        setup.inventories["tt"] = _inventory("tt", categories=())
        _write_inputs(tmp_path, {_key("proc", "ds1"): [1]})
        assert _read(_run(tmp_path)) == {}

    def test_missing_input_histogram_raises_value_error(self, tmp_path, setup):
        setup.inventories["tt"] = _inventory("tt")
        _write_inputs(tmp_path, {_key("proc", "ds1"): [1]})  # ds2 missing
        with pytest.raises(ValueError):
            _run(tmp_path)

    def test_missing_variation_input_raises_value_error(
        self, tmp_path, setup, monkeypatch
    ):
        setup.inventories["tt"] = _inventory("tt")
        monkeypatch.setattr(
            merging, "default_variations", [make_variation("up")]
        )
        _write_inputs(
            tmp_path, {_key("proc", "ds1"): [1], _key("proc", "ds2"): [1]}
        )
        with pytest.raises(ValueError):
            _run(tmp_path)

    def test_invalid_variable_argument_raises(self, tmp_path, setup):
        setup.inventories["tt"] = _inventory("tt")
        _write_inputs(tmp_path, {_key("proc", "ds1"): [1]})
        with pytest.raises(ValueError, match="expected pattern"):
            _run(tmp_path, variables=["pt[tt"])


class TestMergeHistogramsSkippedProcesses:
    """Processes skipped by the category need no input and give no output."""

    @staticmethod
    def _skip_other(process_inst):
        return process_inst.name == "other"

    def test_skipped_process_needs_no_input_and_gives_no_output(
        self, tmp_path, setup
    ):
        setup.inventories["tt"] = _inventory(
            "tt",
            processes=("proc", "other"),
            categories_aux={"cat": {"skip_process_inst": self._skip_other}},
        )
        # Inputs only exist for the kept process
        _write_inputs(
            tmp_path,
            {_key("proc", "ds1"): [1.0], _key("proc", "ds2"): [2.0]},
        )
        out = _read(_run(tmp_path))
        assert sorted(out) == ["c/tt/cat/proc/pt__nominal"]

    def test_skipped_process_variations_are_not_merged(
        self, tmp_path, setup, monkeypatch
    ):
        setup.inventories["tt"] = _inventory(
            "tt",
            processes=("proc", "other"),
            categories_aux={"cat": {"skip_process_inst": self._skip_other}},
        )
        monkeypatch.setattr(
            merging, "default_variations", [make_variation("up")]
        )
        _write_inputs(
            tmp_path,
            {
                _key("proc", "ds1"): [1.0],
                _key("proc", "ds2"): [1.0],
                _key("proc", "ds1", variation="up"): [1.0],
                _key("proc", "ds2", variation="up"): [1.0],
            },
        )
        out = _read(_run(tmp_path))
        assert sorted(out) == [
            "c/tt/cat/proc/pt__nominal",
            "c/tt/cat/proc/pt__up",
        ]

    def test_unskipped_process_missing_input_still_raises(
        self, tmp_path, setup
    ):
        # Category defines the aux, but does not skip the process without input
        setup.inventories["tt"] = _inventory(
            "tt",
            processes=("proc", "other"),
            categories_aux={"cat": {"skip_process_inst": lambda p: False}},
        )
        _write_inputs(
            tmp_path,
            {_key("proc", "ds1"): [1.0], _key("proc", "ds2"): [2.0]},
        )
        with pytest.raises(ValueError):
            _run(tmp_path)
