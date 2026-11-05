import hashlib
import json
from types import SimpleNamespace

import pytest
import ROOT

from xyh.core.histograms import fake_factors
from xyh.core.histograms.fake_factors import run_fake_factor_histograms
from xyh.core.io import dump_json, load_json

FF = "fake_factors"


@pytest.fixture(autouse=True)
def restore_th1_directory_status():
    # `run_fake_factor_histograms` disables the ROOT directory ownership of
    # histograms globally. Restore the status to not leak into other tests.
    previous = ROOT.TH1.AddDirectoryStatus()
    ROOT.TH1.AddDirectory(False)
    yield
    ROOT.TH1.AddDirectory(previous)


def _make_inventory(
    channel,
    categories=("cat",),
    data=(("data", ("data_proc",)),),
    backgrounds=(("jetfakes", ("jetfakes",)), ("tt", ("tt_proc",))),
):
    def _sets(spec):
        return [SimpleNamespace(name=n, processes=list(p)) for n, p in spec]

    return SimpleNamespace(
        campaign=SimpleNamespace(name="c"),
        channel=SimpleNamespace(
            name=channel,
            has_category=lambda c: c in categories,
            get_category=lambda c: SimpleNamespace(name=c),
        ),
        process_set=SimpleNamespace(
            data=_sets(data), backgrounds=_sets(backgrounds)
        ),
        processes=SimpleNamespace(get=lambda n: SimpleNamespace(name=n)),
        variables=SimpleNamespace(get=lambda n: SimpleNamespace(name=n)),
    )


@pytest.fixture
def datasets():
    """Datasets per process."""
    return {
        "data_proc": ["ds_data_1", "ds_data_2"],
        "tt_proc": ["ds_tt"],
    }


@pytest.fixture
def patch_config(monkeypatch, datasets):
    """Patch the inventory loading and the dataset generation."""
    calls = []
    inventories = {}

    def _patch(inventory_for_channel):
        inventories.update(inventory_for_channel)

    def fake_load_inventory(path, campaign, channel, **kwargs):
        calls.append((path, campaign, channel, kwargs))
        return inventories[channel]

    def fake_gen_dataset_insts(inventory, process):
        return [SimpleNamespace(name=d) for d in datasets[process]]

    monkeypatch.setattr(fake_factors, "load_inventory", fake_load_inventory)
    monkeypatch.setattr(
        fake_factors, "gen_dataset_insts", fake_gen_dataset_insts
    )
    _patch.calls = calls
    return _patch


@pytest.fixture
def write_inputs(tmp_path):
    """Write the input histogram file and the keys file."""

    def _write(contents, extra_keys=None):
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
        keys = {path.name: sorted(contents)}
        keys.update(extra_keys or {})
        dump_json(keys, tmp_path / "histogram_keys.json.gz")
        return path

    return _write


def _key(channel, process, dataset, variable, variation=FF, category="cat"):
    return f"c/{channel}/{category}/{process}/{dataset}/{variable}__{variation}"


def _read_output(tmp_path):
    keys = load_json(tmp_path / "histogram_keys.json.gz")
    (output_name,) = (k for k in keys if k != "histograms_in.root")
    root_file = ROOT.TFile.Open(str(tmp_path / output_name), "READ")
    hists = {}
    for key in keys[output_name]:
        hist = root_file.Get(key)
        hists[key] = [
            hist.GetBinContent(i) for i in range(1, hist.GetNbinsX() + 1)
        ]
        assert hist.GetName() == key.rsplit("/", 1)[1]
    root_file.Close()
    return output_name, keys[output_name], hists


def _run(tmp_path, **overrides):
    kwargs = {
        "inventory_factory_fn_path": "pkg.module:fn",
        "inventory_factory_kwargs": {"opt": 1},
        "campaigns": ["c"],
        "channels": ["tt"],
        "categories": ["cat"],
        "variables": ["pt"],
        "histograms_dir": tmp_path,
    }
    kwargs.update(overrides)
    run_fake_factor_histograms(**kwargs)


class TestRunFakeFactorHistograms:
    def test_run_result_is_data_minus_non_jetfakes_with_fake_factor_variation(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config({"tt": _make_inventory("tt")})
        write_inputs(
            {
                _key("tt", "data_proc", "ds_data_1", "pt"): (10.0, 20.0),
                _key("tt", "data_proc", "ds_data_2", "pt"): (5.0, 5.0),
                _key("tt", "tt_proc", "ds_tt", "pt"): (1.0, 2.0),
                # Other variations must not enter the result
                _key("tt", "data_proc", "ds_data_1", "pt", "nominal"): (
                    1000.0,
                    1000.0,
                ),
                _key("tt", "tt_proc", "ds_tt", "pt", "nominal"): (
                    500.0,
                    500.0,
                ),
            }
        )
        _run(tmp_path)
        _, keys, hists = _read_output(tmp_path)
        expected_key = "c/tt/cat/jetfakes/jetfakes/pt__nominal"
        assert keys == [expected_key]
        assert hists[expected_key] == [14.0, 23.0]

    def test_run_passes_inventory_arguments_to_load_inventory(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config({"tt": _make_inventory("tt")})
        write_inputs(
            {
                _key("tt", "data_proc", "ds_data_1", "pt"): (1.0,),
                _key("tt", "data_proc", "ds_data_2", "pt"): (1.0,),
                _key("tt", "tt_proc", "ds_tt", "pt"): (1.0,),
            }
        )
        _run(tmp_path)
        assert patch_config.calls == [("pkg.module:fn", "c", "tt", {"opt": 1})]

    def test_run_output_file_name_uses_hash_of_sorted_keys(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config({"tt": _make_inventory("tt")})
        write_inputs(
            {
                _key("tt", "data_proc", "ds_data_1", "pt"): (1.0,),
                _key("tt", "data_proc", "ds_data_2", "pt"): (1.0,),
                _key("tt", "tt_proc", "ds_tt", "pt"): (1.0,),
            }
        )
        _run(tmp_path)
        expected_hash = hashlib.sha256(
            json.dumps(["c/tt/cat/jetfakes/jetfakes/pt__nominal"]).encode()
        ).hexdigest()
        assert (tmp_path / f"histograms_{expected_hash}.root").is_file()

    def test_run_updates_keys_file_keeping_existing_entries(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config({"tt": _make_inventory("tt")})
        other_key = "c/tt/cat/p/ds/z__nominal"
        other = ROOT.TFile.Open(str(tmp_path / "other.root"), "RECREATE")
        other.mkdir("c/tt/cat/p/ds").cd()
        ROOT.TH1D("z__nominal", "z", 1, 0.0, 1.0).Write()
        other.Close()
        write_inputs(
            {
                _key("tt", "data_proc", "ds_data_1", "pt"): (1.0,),
                _key("tt", "data_proc", "ds_data_2", "pt"): (1.0,),
                _key("tt", "tt_proc", "ds_tt", "pt"): (1.0,),
            },
            extra_keys={"other.root": [other_key]},
        )
        _run(tmp_path)
        keys = load_json(tmp_path / "histogram_keys.json.gz")
        new = [k for k in keys if k not in ("histograms_in.root", "other.root")]
        assert len(new) == 1
        assert new[0].startswith("histograms_") and new[0].endswith(".root")
        assert keys[new[0]] == ["c/tt/cat/jetfakes/jetfakes/pt__nominal"]
        assert keys["other.root"] == [other_key]
        assert (tmp_path / new[0]).is_file()

    def test_run_skips_variable_restricted_to_other_channel(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config({"tt": _make_inventory("tt"), "mt": _make_inventory("mt")})
        contents = {}
        for channel in ("tt", "mt"):
            for var in ("pt", "mass_1"):
                for proc, ds in (
                    ("data_proc", "ds_data_1"),
                    ("data_proc", "ds_data_2"),
                    ("tt_proc", "ds_tt"),
                ):
                    contents[_key(channel, proc, ds, var)] = (4.0,)
        write_inputs(contents)
        _run(
            tmp_path,
            channels=["tt", "mt"],
            variables=["pt", "mass_1[tt]"],
        )
        _, keys, _ = _read_output(tmp_path)
        assert keys == sorted(
            [
                "c/tt/cat/jetfakes/jetfakes/pt__nominal",
                "c/tt/cat/jetfakes/jetfakes/mass_1__nominal",
                "c/mt/cat/jetfakes/jetfakes/pt__nominal",
            ]
        )

    def test_run_skips_categories_not_in_channel(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config({"tt": _make_inventory("tt", categories=("cat",))})
        write_inputs(
            {
                _key("tt", "data_proc", "ds_data_1", "pt"): (1.0,),
                _key("tt", "data_proc", "ds_data_2", "pt"): (1.0,),
                _key("tt", "tt_proc", "ds_tt", "pt"): (1.0,),
            }
        )
        # "missing" is not a category of the channel and has no histograms
        _run(tmp_path, categories=["missing", "cat"])
        _, keys, _ = _read_output(tmp_path)
        assert keys == ["c/tt/cat/jetfakes/jetfakes/pt__nominal"]

    def test_run_channel_without_jetfakes_is_skipped(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config(
            {
                "tt": _make_inventory("tt"),
                "mt": _make_inventory(
                    "mt", backgrounds=(("tt", ("tt_proc",)),)
                ),
            }
        )
        contents = {
            _key("tt", p, d, "pt"): (1.0,)
            for p, d in (
                ("data_proc", "ds_data_1"),
                ("data_proc", "ds_data_2"),
                ("tt_proc", "ds_tt"),
            )
        }
        write_inputs(contents)
        _run(tmp_path, channels=["mt", "tt"])
        _, keys, _ = _read_output(tmp_path)
        assert keys == ["c/tt/cat/jetfakes/jetfakes/pt__nominal"]

    def test_run_more_than_one_jetfakes_process_raises(
        self, tmp_path, patch_config, write_inputs
    ):
        inventory = _make_inventory(
            "tt",
            backgrounds=(
                ("jetfakes", ("jetfakes",)),
                ("jetfakes2", ("jetfakes",)),
            ),
        )
        patch_config({"tt": inventory})
        write_inputs({_key("tt", "data_proc", "ds_data_1", "pt"): (1.0,)})
        with pytest.raises(RuntimeError, match="More than one jet fakes"):
            _run(tmp_path)

    def test_run_missing_input_histogram_raises(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config({"tt": _make_inventory("tt")})
        # ds_data_2 is missing
        write_inputs(
            {
                _key("tt", "data_proc", "ds_data_1", "pt"): (1.0,),
                _key("tt", "tt_proc", "ds_tt", "pt"): (1.0,),
            }
        )
        with pytest.raises(ValueError, match="No matching histogram"):
            _run(tmp_path)

    def test_run_inputs_are_not_modified_by_subtraction(
        self, tmp_path, patch_config, write_inputs
    ):
        patch_config({"tt": _make_inventory("tt")})
        in_path = write_inputs(
            {
                _key("tt", "data_proc", "ds_data_1", "pt"): (10.0,),
                _key("tt", "data_proc", "ds_data_2", "pt"): (10.0,),
                _key("tt", "tt_proc", "ds_tt", "pt"): (5.0,),
            }
        )
        _run(tmp_path)
        root_file = ROOT.TFile.Open(str(in_path), "READ")
        hist = root_file.Get("c/tt/cat/data_proc/ds_data_1/pt__fake_factors")
        assert hist.GetBinContent(1) == 10.0
        root_file.Close()
