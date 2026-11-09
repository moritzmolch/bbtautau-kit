"""Unit tests for the NN score plots of the fit shapes."""

from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import ROOT  # noqa: E402

from xyh.core.plotting import nn_score_plots  # noqa: E402
from xyh.core.plotting.nn_score_plots import (  # noqa: E402
    concatenate_classes,
    find_bins,
    plot_nn_scores,
    sum_channels,
)
from xyh.fit.mass_points import CLASSES  # noqa: E402
from xyh.fit.shapes import Shape  # noqa: E402

COLORS = {"TT": "#ff0000", "DY": "#00ff00", "sig": "#0000ff"}
SIGNAL = "xyh_h2tau_mx2000_my60"
# Number of bins per class, deliberately different
N_BINS = {"xyh": 2, "t_tt": 3, "z2tau": 2, "jetfakes": 1}


@pytest.fixture(autouse=True)
def restore_th1_directory_status():
    previous = ROOT.TH1.AddDirectoryStatus()
    yield
    ROOT.TH1.AddDirectory(previous)


def _shape(n, value, error=None):
    error = value / 10 if error is None else error
    return Shape(
        np.linspace(0.0, 1.0, n + 1),
        np.full(n, float(value)),
        np.full(n, float(error) ** 2),
    )


def _class_shapes(spec):
    """Build shapes from `{cls: {process: value}}`; others are empty."""
    return {
        cls: {p: _shape(N_BINS[cls], v) for p, v in spec.get(cls, {}).items()}
        for cls in CLASSES
    }


def _full_spec():
    return {
        "xyh": {"data_obs": 1, "tt": 10, SIGNAL: 5},
        "t_tt": {"data_obs": 2, "tt": 20, "dy": 1},
        "z2tau": {"data_obs": 3, "dy": 30, SIGNAL: 4},
        "jetfakes": {"data_obs": 4, "tt": 3, "dy": 2},
    }


def _contents(hist):
    n = hist.GetNbinsX()
    return (
        np.array([hist.GetBinContent(i) for i in range(1, n + 1)]),
        np.array([hist.GetBinError(i) for i in range(1, n + 1)]),
    )


def _group(name, processes):
    return SimpleNamespace(
        name=name,
        processes=list(processes),
        color=COLORS.get(name, "gray"),
        label=f"l_{name}",
        scale_factor=None,
    )


def _inventory(backgrounds=None):
    if backgrounds is None:
        backgrounds = [_group("TT", ["tt"]), _group("DY", ["dy"])]
    return SimpleNamespace(
        campaign=SimpleNamespace(x=SimpleNamespace(lumi=100.0), ecm=13.6),
        process_set=SimpleNamespace(
            name="default",
            backgrounds=backgrounds,
            signals=[_group("sig", [SIGNAL])],
        ),
    )


class TestConcatenateClasses:
    def test_concatenate_classes_segments_follow_class_order(self):
        shapes = _class_shapes(_full_spec())

        hist = concatenate_classes(shapes, ["tt"], "h")

        values, errors = _contents(hist)
        # tt: xyh(2 bins)=10, t_tt(3)=20, z2tau(2)=missing, jetfakes(1)=3
        assert values.tolist() == [10, 10, 20, 20, 20, 0, 0, 3]
        assert errors == pytest.approx([1, 1, 2, 2, 2, 0, 0, 0.3])

    def test_concatenate_classes_axis_is_bin_index(self):
        hist = concatenate_classes(_class_shapes(_full_spec()), ["tt"], "h")

        assert hist.GetNbinsX() == sum(N_BINS.values())
        assert hist.GetXaxis().GetXmin() == 0.0
        assert hist.GetXaxis().GetXmax() == sum(N_BINS.values())

    def test_concatenate_classes_sums_processes_and_adds_errors_in_quadrature(
        self,
    ):
        shapes = _class_shapes(_full_spec())

        hist = concatenate_classes(shapes, ["tt", "dy"], "h")

        values, errors = _contents(hist)
        # t_tt segment: 20 + 1, error sqrt(2^2 + 0.1^2)
        assert values[2:5].tolist() == [21, 21, 21]
        assert errors[2] == pytest.approx(np.hypot(2, 0.1))

    def test_concatenate_classes_missing_process_gives_zeros(self):
        hist = concatenate_classes(
            _class_shapes(_full_spec()), ["nonexistent"], "h"
        )

        values, errors = _contents(hist)
        assert not values.any()
        assert not errors.any()

    def test_concatenate_classes_blind_zeroes_only_xyh_segment(self):
        shapes = _class_shapes(_full_spec())

        hist = concatenate_classes(shapes, ["data_obs"], "d", blind=True)

        values, errors = _contents(hist)
        n = N_BINS["xyh"]
        assert not values[:n].any()
        assert not errors[:n].any()
        assert values[n:].tolist() == [2, 2, 2, 3, 3, 4]
        assert (errors[n:] > 0).all()

    def test_concatenate_classes_blind_leaves_signal_untouched(self):
        shapes = _class_shapes(_full_spec())

        hist = concatenate_classes(shapes, [SIGNAL], SIGNAL)

        values, _ = _contents(hist)
        assert values.tolist() == [5, 5, 0, 0, 0, 4, 4, 0]

    def test_concatenate_classes_unblinded_keeps_xyh_data(self):
        shapes = _class_shapes(_full_spec())

        hist = concatenate_classes(shapes, ["data_obs"], "d")

        values, _ = _contents(hist)
        assert values[:2].tolist() == [1, 1]


class TestSumChannels:
    def test_sum_channels_adds_values_and_sumw2(self):
        a = _class_shapes(_full_spec())
        b = _class_shapes(_full_spec())

        total = sum_channels([a, b])

        shape = total["t_tt"]["tt"]
        assert shape.values.tolist() == [40, 40, 40]
        assert shape.sumw2 == pytest.approx([8, 8, 8])

    def test_sum_channels_does_not_modify_inputs(self):
        a = _class_shapes(_full_spec())
        b = _class_shapes(_full_spec())

        sum_channels([a, b])

        assert a["t_tt"]["tt"].values.tolist() == [20, 20, 20]

    def test_sum_channels_process_in_one_channel_only_is_kept(self):
        a = _class_shapes({"xyh": {"tt": 1}})
        b = _class_shapes({"xyh": {"tt": 1, "dy": 7}})

        total = sum_channels([a, b])

        assert total["xyh"]["dy"].values.tolist() == [7, 7]
        assert total["xyh"]["tt"].values.tolist() == [2, 2]

    def test_sum_channels_differing_binning_raises(self):
        a = _class_shapes({"xyh": {"tt": 1}})
        b = _class_shapes({"xyh": {"tt": 1}})
        b["xyh"]["tt"] = Shape(
            np.array([0.0, 0.3, 1.0]), np.ones(2), np.ones(2)
        )

        with pytest.raises(ValueError, match="binning of class xyh differs"):
            sum_channels([a, b])


def _write_shapes_file(path, bins):
    """`bins`: {directory: {process: [contents]}}, errors are sqrt(content)."""
    root_file = ROOT.TFile.Open(str(path), "RECREATE")
    for directory, processes in bins.items():
        root_file.mkdir(directory).cd()
        for process, contents in processes.items():
            n = len(contents)
            hist = ROOT.TH1D(process, process, n, 0.0, 1.0)
            hist.Sumw2()
            for i, c in enumerate(contents, start=1):
                hist.SetBinContent(i, c)
                hist.SetBinError(i, np.sqrt(c))
            hist.Write()
        root_file.cd()
    root_file.Close()


def _bins_for(channel, campaign="2024", skip=(), binning=None):
    out = {}
    for cls, n in N_BINS.items():
        if cls in skip:
            continue
        n = (binning or N_BINS)[cls]
        processes = {
            "data_obs": [4.0] * n,
            "tt": [9.0] * n,
            "dy": [4.0] * n,
            "ttUp": [1.0] * n,
        }
        if cls in ("xyh", "z2tau"):
            processes[SIGNAL] = [1.0] * n
        out[f"{channel}_{cls}_{campaign}"] = processes
    return out


class TestFindBins:
    def test_find_bins_groups_classes_by_campaign_and_channel(self, tmp_path):
        path = tmp_path / "shapes.root"
        _write_shapes_file(
            path, {**_bins_for("et"), **_bins_for("mt", "2023"), "other": {}}
        )

        bins = find_bins(path)

        assert set(bins) == {("2024", "et"), ("2023", "mt")}
        assert bins[("2024", "et")] == {c: f"et_{c}_2024" for c in CLASSES}

    def test_find_bins_missing_class_raises(self, tmp_path):
        path = tmp_path / "shapes.root"
        _write_shapes_file(path, _bins_for("et", skip=("jetfakes",)))

        with pytest.raises(ValueError, match="jetfakes"):
            find_bins(path)

    def test_find_bins_missing_file_raises(self, tmp_path):
        # PyROOT raises OSError itself, FileNotFoundError is its subclass
        with pytest.raises(OSError):
            find_bins(tmp_path / "nope.root")


class TestPlotInputs:
    def test_plot_inputs_groups_processes_into_process_set_groups(self):
        shapes = _class_shapes(_full_spec())
        process_set = _inventory().process_set

        data, signals, backgrounds = nn_score_plots._plot_inputs(
            shapes, process_set, [SIGNAL], "et"
        )

        assert [kw["label"] for _, kw in backgrounds] == ["l_TT", "l_DY"]
        assert [kw["color"] for _, kw in backgrounds] == ["#ff0000", "#00ff00"]
        assert _contents(backgrounds[0][0])[0][2] == 20
        assert _contents(data)[0][:2].tolist() == [0, 0]
        assert signals[0][1] == {"color": "#0000ff", "label": "l_sig"}

    def test_plot_inputs_group_without_present_process_is_skipped(self):
        shapes = _class_shapes(_full_spec())
        groups = [
            _group("TT", ["tt"]),
            _group("DY", ["dy"]),
            _group("absent", ["zzz"]),
        ]

        _, _, backgrounds = nn_score_plots._plot_inputs(
            shapes, _inventory(groups).process_set, [SIGNAL], "et"
        )

        assert len(backgrounds) == 2

    def test_plot_inputs_uncovered_background_raises(self):
        shapes = _class_shapes(_full_spec())
        process_set = _inventory([_group("TT", ["tt"])]).process_set

        with pytest.raises(ValueError, match=r"\['dy'\]"):
            nn_score_plots._plot_inputs(shapes, process_set, [SIGNAL], "et")

    def test_plot_inputs_scale_factor_selected_by_channel(self):
        shapes = _class_shapes(_full_spec())
        tt = _group("TT", ["tt"])
        tt.scale_factor = {"et": 2.0}
        groups = [tt, _group("DY", ["dy"])]

        _, _, bkgs = nn_score_plots._plot_inputs(
            shapes, _inventory(groups).process_set, [], "et"
        )
        _, _, bkgs_mt = nn_score_plots._plot_inputs(
            shapes, _inventory(groups).process_set, [], "mt"
        )

        assert bkgs[0][1]["scale_factor"] == 2.0
        assert bkgs_mt[0][1]["scale_factor"] == 1.0

    def test_plot_inputs_signal_outside_process_set_uses_fallback_style(self):
        shapes = _class_shapes(_full_spec())
        process_set = _inventory().process_set
        process_set.signals = []

        _, signals, _ = nn_score_plots._plot_inputs(
            shapes, process_set, [SIGNAL], "et"
        )

        assert signals[0][1] == nn_score_plots._SIGNAL_STYLE


class TestPlotChannel:
    def test_plot_channel_asimov_mode_labels_data_as_asimov(
        self, mocker, tmp_path
    ):
        plot = mocker.patch.object(
            nn_score_plots,
            "plot",
            return_value=(mocker.MagicMock(), (mocker.MagicMock(),) * 2),
        )
        mocker.patch.object(nn_score_plots, "_decorate")

        nn_score_plots.plot_channel(
            _class_shapes(_full_spec()),
            _inventory(),
            "et",
            ["a", "b", "c", "d"],
            "asimov_bkg",
            [],
        )

        assert plot.call_args.kwargs["hist_data"][1] == {
            "label": "Asimov data"
        }

    def test_plot_channel_real_data_mode_labels_data_as_data(self, mocker):
        plot = mocker.patch.object(
            nn_score_plots,
            "plot",
            return_value=(mocker.MagicMock(), (mocker.MagicMock(),) * 2),
        )
        mocker.patch.object(nn_score_plots, "_decorate")

        nn_score_plots.plot_channel(
            _class_shapes(_full_spec()),
            _inventory(),
            "et",
            ["a", "b", "c", "d"],
            "data",
            [],
        )

        assert plot.call_args.kwargs["hist_data"][1] == {"label": "Data"}


class TestPlotNnScores:
    @staticmethod
    def _run(point_dir, mocker, **kwargs):
        factory = mocker.patch.object(
            nn_score_plots, "load_inventory", return_value=_inventory()
        )
        files = plot_nn_scores(
            point_dir=point_dir,
            output_dir=point_dir / "plots" / "nn_scores",
            extensions=["png"],
            inventory_factory_fn_path="some.module.create",
            inventory_factory_kwargs={"process_set": "default"},
            data_mode="asimov_bkg",
            **kwargs,
        )
        return files, factory

    def test_plot_nn_scores_writes_file_per_campaign_and_channel(
        self, tmp_path, mocker
    ):
        _write_shapes_file(
            tmp_path / "shapes.root",
            {**_bins_for("et"), **_bins_for("mt")},
        )

        files, factory = self._run(tmp_path, mocker)

        base = tmp_path / "plots" / "nn_scores" / "2024"
        assert files == [base / "et.png", base / "mt.png"]
        assert all(f.is_file() and f.stat().st_size > 0 for f in files)
        factory.assert_any_call(
            "some.module.create", "2024", "et", process_set="default"
        )

    def test_plot_nn_scores_combine_channels_adds_combined_plot(
        self, tmp_path, mocker
    ):
        _write_shapes_file(
            tmp_path / "shapes.root",
            {**_bins_for("et"), **_bins_for("mt")},
        )

        files, factory = self._run(tmp_path, mocker, combine_channels=True)

        combined = tmp_path / "plots" / "nn_scores" / "2024" / "combined.png"
        assert combined in files
        assert combined.is_file()
        # The combined plot uses the inventory of the first channel
        assert factory.call_args.args[2] == "et"

    def test_plot_nn_scores_combine_channels_differing_binning_raises(
        self, tmp_path, mocker
    ):
        other = {**N_BINS, "t_tt": 5}
        _write_shapes_file(
            tmp_path / "shapes.root",
            {**_bins_for("et"), **_bins_for("mt", binning=other)},
        )

        with pytest.raises(ValueError, match="binning of class t_tt differs"):
            self._run(tmp_path, mocker, combine_channels=True)

    def test_plot_nn_scores_without_combine_accepts_differing_binning(
        self, tmp_path, mocker
    ):
        other = {**N_BINS, "t_tt": 5}
        _write_shapes_file(
            tmp_path / "shapes.root",
            {**_bins_for("et"), **_bins_for("mt", binning=other)},
        )

        files, _ = self._run(tmp_path, mocker)

        assert len(files) == 2

    def test_plot_nn_scores_no_bins_raises(self, tmp_path, mocker):
        _write_shapes_file(tmp_path / "shapes.root", {"unrelated": {}})

        with pytest.raises(ValueError, match="No Combine bins"):
            self._run(tmp_path, mocker)

    def test_plot_nn_scores_uncovered_background_raises(
        self, tmp_path, mocker
    ):
        _write_shapes_file(tmp_path / "shapes.root", _bins_for("et"))
        mocker.patch.object(
            nn_score_plots,
            "load_inventory",
            return_value=_inventory([_group("TT", ["tt"])]),
        )

        with pytest.raises(ValueError, match="not in the background groups"):
            plot_nn_scores(
                tmp_path,
                tmp_path / "out",
                ["png"],
                "f",
                {},
                "asimov_bkg",
            )


def test_read_class_shapes_skips_systematic_variations(tmp_path):
    path = tmp_path / "shapes.root"
    _write_shapes_file(path, _bins_for("et"))
    root_file = ROOT.TFile.Open(str(path))
    try:
        shapes = nn_score_plots.read_class_shapes(
            root_file, {c: f"et_{c}_2024" for c in CLASSES}
        )
    finally:
        root_file.Close()

    assert "ttUp" not in shapes["xyh"]
    assert set(shapes["xyh"]) == {"data_obs", "tt", "dy", SIGNAL}
    assert set(shapes["t_tt"]) == {"data_obs", "tt", "dy"}
    assert shapes["xyh"]["tt"].sumw2.tolist() == pytest.approx([9, 9])


def test_main_default_output_dir_and_data_mode(tmp_path, mocker, monkeypatch):
    from xyh.scripts import plot_nn_scores as script

    point = tmp_path / "asimov_bkg" / "y2b_h2tau" / "mx2000_my60"
    point.mkdir(parents=True)
    run = mocker.patch.object(nn_score_plots, "plot_nn_scores")
    monkeypatch.setattr(
        "sys.argv", ["plot_nn_scores", "--point-dir", str(point)]
    )

    script.main()

    kwargs = run.call_args.kwargs
    assert kwargs["data_mode"] == "asimov_bkg"
    assert kwargs["output_dir"] == Path(point.resolve()) / "plots/nn_scores"
    assert kwargs["log_y"] is True
