"""Unit tests for `xyh.fit.shapes`.

The pure helpers are tested on numpy shapes, the ROOT I/O on small merged
files fabricated in `tmp_path`.
"""

import numpy as np
import pytest

from xyh.fit.mass_points import CLASSES, MassPoint
from xyh.fit.scope import FitBin, resolve_scope
from xyh.fit.shapes import (
    DATA_OBS_NAME,
    SIGNAL_NAME,
    BinShapes,
    Shape,
    add_shapes,
    build_bin_shapes,
    build_point_shapes,
    clip_negative,
    is_signal_process,
    list_categories,
    list_keys,
    read_bin_processes,
    read_shape,
    rebin_shape,
    write_shapes_file,
)

POINT = MassPoint("y2b", "h2tau", 2000, 500)
OTHER = MassPoint("y2b", "h2tau", 3000, 100)
EDGES = np.array([0.0, 0.25, 0.5, 0.75, 1.0])


def make_shape(values, edges=EDGES, sumw2=None):
    values = np.asarray(values, dtype=float)
    sumw2 = values.copy() if sumw2 is None else np.asarray(sumw2, float)
    return Shape(np.asarray(edges, float), values, sumw2)


def processes(**overrides):
    result = {
        POINT.signal_process: make_shape([1, 1, 1, 1]),
        OTHER.signal_process: make_shape([9, 9, 9, 9]),
        "dy": make_shape([4, 3, 2, 1]),
        "tt": make_shape([1, 1, 1, 1]),
        "data": make_shape([5, 4, 3, 2]),
    }
    result.update(overrides)
    return result


class TestHelpers:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [("xyh_y2b_h2tau_mx1_my2", True), ("dy", False), ("data", False)],
    )
    def test_is_signal_process(self, name, expected):
        assert is_signal_process(name) is expected

    def test_shape_integral_sums_values(self):
        assert make_shape([1, 2, 3, 4]).integral == pytest.approx(10.0)

    def test_clip_negative_sets_negatives_to_zero_keeps_input(self):
        shape = make_shape([-1, 2, -3, 4], sumw2=[1, 2, 3, 4])
        clipped = clip_negative(shape)
        assert clipped.values.tolist() == [0, 2, 0, 4]
        assert clipped.sumw2.tolist() == [1, 2, 3, 4]
        assert shape.values.tolist() == [-1, 2, -3, 4]

    def test_add_shapes_sums_values_and_sumw2(self):
        total = add_shapes(
            [make_shape([1, 2, 3, 4]), make_shape([1, 1, 1, 1], sumw2=[2] * 4)]
        )
        assert total.values.tolist() == [2, 3, 4, 5]
        assert total.sumw2.tolist() == [3, 4, 5, 6]

    def test_add_shapes_empty_raises(self):
        with pytest.raises(ValueError, match="empty list"):
            add_shapes([])

    @pytest.mark.parametrize(
        "other_edges",
        [[0, 0.5, 1.0], [0, 0.25, 0.5, 0.75, 2.0]],
        ids=["different-length", "different-edges"],
    )
    def test_add_shapes_different_binning_raises(self, other_edges):
        other = Shape(
            np.array(other_edges, float),
            np.ones(len(other_edges) - 1),
            np.ones(len(other_edges) - 1),
        )
        with pytest.raises(ValueError, match="different binning"):
            add_shapes([make_shape([1, 1, 1, 1]), other])

    def test_rebin_shape_merges_adjacent_bins(self):
        rebinned = rebin_shape(make_shape([1, 2, 3, 4], sumw2=[1, 1, 2, 2]), 2)
        assert rebinned.values.tolist() == [3, 7]
        assert rebinned.sumw2.tolist() == [2, 4]
        assert rebinned.edges.tolist() == [0.0, 0.5, 1.0]

    def test_rebin_shape_factor_one_is_identity(self):
        rebinned = rebin_shape(make_shape([1, 2, 3, 4]), 1)
        assert rebinned.values.tolist() == [1, 2, 3, 4]
        assert rebinned.edges.tolist() == EDGES.tolist()

    @pytest.mark.parametrize("factor", [0, -1, 3])
    def test_rebin_shape_invalid_factor_raises(self, factor):
        with pytest.raises(ValueError, match="Cannot rebin 4 bins"):
            rebin_shape(make_shape([1, 2, 3, 4]), factor)


class TestBuildBinShapes:
    def test_backgrounds_exclude_data_and_all_signals(self):
        shapes = build_bin_shapes(processes(), POINT, "asimov_bkg")
        assert sorted(shapes.backgrounds) == ["dy", "tt"]
        assert shapes.signal is not None
        assert shapes.signal.values.tolist() == [1, 1, 1, 1]

    def test_other_mass_point_signal_is_ignored_everywhere(self):
        shapes = build_bin_shapes(processes(), POINT, "asimov_sb")
        # dy + tt + own signal; the 9s of the other point must not enter
        assert shapes.data_obs.values.tolist() == [6, 5, 4, 3]

    def test_asimov_bkg_is_sum_of_backgrounds(self):
        shapes = build_bin_shapes(processes(), POINT, "asimov_bkg")
        assert shapes.data_obs.values.tolist() == [5, 4, 3, 2]

    def test_asimov_sb_adds_signal(self):
        shapes = build_bin_shapes(processes(), POINT, "asimov_sb")
        assert shapes.data_obs.values.tolist() == [6, 5, 4, 3]

    def test_asimov_data_sumw2_equals_values(self):
        shapes = build_bin_shapes(processes(), POINT, "asimov_sb")
        assert shapes.data_obs.sumw2.tolist() == shapes.data_obs.values.tolist()

    def test_observed_uses_data_process(self):
        shapes = build_bin_shapes(processes(), POINT, "observed")
        assert shapes.data_obs.values.tolist() == [5, 4, 3, 2]
        assert shapes.data_obs.sumw2.tolist() == [5, 4, 3, 2]

    def test_observed_without_data_raises(self):
        procs = processes()
        del procs["data"]
        with pytest.raises(ValueError, match="'data' not found"):
            build_bin_shapes(procs, POINT, "observed")

    def test_observed_data_negative_bins_are_clipped(self):
        shapes = build_bin_shapes(
            processes(data=make_shape([-2, 4, 3, 2])), POINT, "observed"
        )
        assert shapes.data_obs.values.tolist() == [0, 4, 3, 2]

    def test_unknown_data_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown data mode 'foo'"):
            build_bin_shapes(processes(), POINT, "foo")

    def test_missing_signal_raises(self):
        procs = processes()
        del procs[POINT.signal_process]
        with pytest.raises(ValueError, match="Signal process .* not found"):
            build_bin_shapes(procs, POINT, "asimov_bkg")

    def test_negative_bins_clipped_in_backgrounds_and_signal(self):
        shapes = build_bin_shapes(
            processes(
                dy=make_shape([-4, 3, 2, 1]),
                **{POINT.signal_process: make_shape([-1, 1, 1, 1])},
            ),
            POINT,
            "asimov_sb",
        )
        assert shapes.backgrounds["dy"].values.tolist() == [0, 3, 2, 1]
        assert shapes.signal.values.tolist() == [0, 1, 1, 1]
        assert shapes.data_obs.values.tolist() == [1, 5, 4, 3]

    @pytest.mark.parametrize(
        "values",
        [[0, 0, 0, 0], [-1, -2, 0, 0], [np.nan, 1, 1, 1], [np.inf, 1, 1, 1]],
        ids=["zero", "all-negative", "nan", "inf"],
    )
    def test_unusable_background_is_dropped(self, values):
        shapes = build_bin_shapes(
            processes(tt=make_shape(values)), POINT, "asimov_bkg"
        )
        assert sorted(shapes.backgrounds) == ["dy"]
        assert shapes.data_obs.values.tolist() == [4, 3, 2, 1]

    def test_zero_integral_signal_becomes_none_and_is_not_added(self):
        shapes = build_bin_shapes(
            processes(**{POINT.signal_process: make_shape([0, 0, 0, 0])}),
            POINT,
            "asimov_sb",
        )
        assert shapes.signal is None
        assert shapes.data_obs.values.tolist() == [5, 4, 3, 2]

    def test_no_background_left_raises(self):
        procs = {
            POINT.signal_process: make_shape([1, 1, 1, 1]),
            "dy": make_shape([0, 0, 0, 0]),
        }
        with pytest.raises(ValueError, match="No background"):
            build_bin_shapes(procs, POINT, "asimov_bkg")

    def test_exclude_removes_process_from_backgrounds(self):
        shapes = build_bin_shapes(
            processes(), POINT, "asimov_bkg", exclude=["dy"]
        )
        assert sorted(shapes.backgrounds) == ["tt"]
        assert shapes.data_obs.values.tolist() == [1, 1, 1, 1]

    def test_rebin_applies_to_all_components(self):
        shapes = build_bin_shapes(processes(), POINT, "asimov_sb", rebin=2)
        assert shapes.backgrounds["dy"].values.tolist() == [7, 3]
        assert shapes.signal.values.tolist() == [2, 2]
        assert shapes.data_obs.values.tolist() == [11, 7]
        assert shapes.data_obs.edges.tolist() == [0.0, 0.5, 1.0]

    @pytest.mark.parametrize("rebin", [None, 0, 1])
    def test_rebin_none_zero_or_one_keeps_binning(self, rebin):
        shapes = build_bin_shapes(processes(), POINT, "asimov_bkg", rebin=rebin)
        assert len(shapes.data_obs.values) == 4

    def test_rebin_incompatible_with_bins_raises(self):
        with pytest.raises(ValueError, match="Cannot rebin"):
            build_bin_shapes(processes(), POINT, "asimov_bkg", rebin=3)

    def test_input_shapes_are_not_modified(self):
        procs = processes(dy=make_shape([-4, 3, 2, 1]))
        build_bin_shapes(procs, POINT, "asimov_sb")
        assert procs["dy"].values.tolist() == [-4, 3, 2, 1]


# ROOT I/O

ROOT = pytest.importorskip("ROOT")

CAMPAIGN_A = "2024_nano_v15"
CAMPAIGN_B = "2023_nano_v12"


def _fill_hist(name, shape):
    hist = ROOT.TH1D(name, name, len(shape.values), shape.edges.astype("d"))
    for i, (v, w2) in enumerate(
        zip(shape.values, shape.sumw2, strict=True), start=1
    ):
        hist.SetBinContent(i, float(v))
        hist.SetBinError(i, float(np.sqrt(w2)))
    return hist


def write_merged_file(path, layout):
    """Write ``{(campaign, channel, category): {process: Shape}}``."""
    root_file = ROOT.TFile.Open(str(path), "RECREATE")
    try:
        for (campaign, channel, category), procs in layout.items():
            for process, shape in procs.items():
                directory = f"{campaign}/{channel}/{category}/{process}"
                parent = root_file
                for part in directory.split("/"):
                    sub = parent.GetDirectory(part)
                    parent = sub if sub else parent.mkdir(part)
                parent.cd()
                hist = _fill_hist("max_score__nominal", shape)
                # A non-nominal variation that must never be picked
                var = _fill_hist(
                    "max_score__jesUp",
                    Shape(shape.edges, shape.values * 100, shape.sumw2),
                )
                hist.Write()
                var.Write()
                root_file.cd()
    finally:
        root_file.Close()


def full_layout(campaigns=(CAMPAIGN_A,), channels=("tt",), point=POINT):
    layout = {}
    for campaign in campaigns:
        for channel in channels:
            for cls in CLASSES:
                layout[(campaign, channel, point.category(channel, cls))] = (
                    processes()
                )
    return layout


@pytest.fixture
def merged_file(tmp_path):
    path = tmp_path / "merged.root"
    write_merged_file(
        path,
        full_layout(campaigns=(CAMPAIGN_A, CAMPAIGN_B), channels=("tt", "mt")),
    )
    return path


class TestRootReading:
    def test_read_shape_returns_edges_values_and_sumw2(self, tmp_path):
        path = tmp_path / "f.root"
        shape = make_shape([1, 2, 3, 4], sumw2=[4, 4, 9, 9])
        write_merged_file(path, {("c", "tt", "cat"): {"dy": shape}})
        root_file = ROOT.TFile.Open(str(path))
        try:
            read = read_shape(root_file, "c/tt/cat/dy/max_score__nominal")
        finally:
            root_file.Close()
        assert read.edges.tolist() == pytest.approx(EDGES.tolist())
        assert read.values.tolist() == pytest.approx([1, 2, 3, 4])
        assert read.sumw2.tolist() == pytest.approx([4, 4, 9, 9])

    def test_read_shape_missing_histogram_raises(self, merged_file):
        root_file = ROOT.TFile.Open(str(merged_file))
        try:
            with pytest.raises(KeyError, match="not found"):
                read_shape(root_file, "nope/hist")
        finally:
            root_file.Close()

    def test_list_keys_and_categories(self, merged_file):
        root_file = ROOT.TFile.Open(str(merged_file))
        try:
            keys = list_keys(root_file, f"{CAMPAIGN_A}/tt")
            categories = list_categories(root_file, CAMPAIGN_A, "mt")
        finally:
            root_file.Close()
        expected = sorted(POINT.category("tt", c) for c in CLASSES)
        assert sorted(keys) == expected
        assert len(categories) == len(CLASSES)

    def test_list_keys_missing_directory_raises(self, merged_file):
        root_file = ROOT.TFile.Open(str(merged_file))
        try:
            with pytest.raises(KeyError, match="Directory .* not found"):
                list_keys(root_file, "nope")
        finally:
            root_file.Close()

    def test_read_bin_processes_reads_nominal_of_all_processes(
        self, merged_file
    ):
        root_file = ROOT.TFile.Open(str(merged_file))
        try:
            procs = read_bin_processes(
                root_file,
                CAMPAIGN_A,
                "tt",
                POINT.category("tt", "xyh"),
                "max_score",
            )
        finally:
            root_file.Close()
        assert sorted(procs) == sorted(processes())
        assert procs["dy"].values.tolist() == pytest.approx([4, 3, 2, 1])


class TestBuildPointShapes:
    def test_all_scope_returns_every_bin(self, merged_file):
        scope = resolve_scope(
            "all", "all", [CAMPAIGN_A, CAMPAIGN_B], ["tt", "mt"]
        )
        bins = build_point_shapes(
            merged_file, POINT, scope, "max_score", "asimov_bkg"
        )
        assert len(bins) == 2 * 2 * len(CLASSES)
        assert {b.name for b in bins} == {b.name for b in scope.bins()}

    def test_single_channel_scope_restricts_bins(self, merged_file):
        scope = resolve_scope(
            "all", "tt", [CAMPAIGN_A, CAMPAIGN_B], ["tt", "mt"]
        )
        bins = build_point_shapes(
            merged_file, POINT, scope, "max_score", "asimov_bkg"
        )
        assert {b.channel for b in bins} == {"tt"}
        assert len(bins) == 2 * len(CLASSES)

    def test_single_campaign_scope_restricts_bins(self, merged_file):
        scope = resolve_scope(
            "2024", "all", [CAMPAIGN_A, CAMPAIGN_B], ["tt", "mt"]
        )
        bins = build_point_shapes(
            merged_file, POINT, scope, "max_score", "asimov_bkg"
        )
        assert {b.campaign for b in bins} == {CAMPAIGN_A}
        assert len(bins) == 2 * len(CLASSES)

    def test_bin_content_uses_own_signal_and_nominal_only(self, merged_file):
        scope = resolve_scope("2024", "tt", [CAMPAIGN_A], ["tt"])
        bins = build_point_shapes(
            merged_file, POINT, scope, "max_score", "asimov_sb"
        )
        shapes = next(iter(bins.values()))
        assert shapes.signal.values.tolist() == pytest.approx([1, 1, 1, 1])
        assert shapes.data_obs.values.tolist() == pytest.approx([6, 5, 4, 3])

    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            ("asimov_bkg", [5, 4, 3, 2]),
            ("asimov_sb", [6, 5, 4, 3]),
            ("observed", [5, 4, 3, 2]),
        ],
    )
    def test_data_modes(self, merged_file, mode, expected):
        scope = resolve_scope("2024", "tt", [CAMPAIGN_A], ["tt"])
        bins = build_point_shapes(merged_file, POINT, scope, "max_score", mode)
        for shapes in bins.values():
            assert shapes.data_obs.values.tolist() == pytest.approx(expected)

    def test_rebin_and_exclude_are_forwarded(self, merged_file):
        scope = resolve_scope("2024", "tt", [CAMPAIGN_A], ["tt"])
        bins = build_point_shapes(
            merged_file,
            POINT,
            scope,
            "max_score",
            "asimov_bkg",
            exclude=["tt"],
            rebin=2,
        )
        shapes = next(iter(bins.values()))
        assert sorted(shapes.backgrounds) == ["dy"]
        assert shapes.data_obs.values.tolist() == pytest.approx([7, 3])

    def test_empty_bin_is_skipped_with_warning(self, tmp_path, caplog):
        layout = full_layout()
        key = ("2024_nano_v15", "tt", POINT.category("tt", "t_tt"))
        layout[key] = {
            POINT.signal_process: make_shape([1, 1, 1, 1]),
            "dy": make_shape([0, 0, 0, 0]),
        }
        path = tmp_path / "m.root"
        write_merged_file(path, layout)
        scope = resolve_scope("2024", "tt", [CAMPAIGN_A], ["tt"])
        with caplog.at_level("WARNING"):
            bins = build_point_shapes(
                path, POINT, scope, "max_score", "asimov_bkg"
            )
        assert len(bins) == len(CLASSES) - 1
        assert "2024_nano_v15_tt_t_tt" in caplog.text

    def test_no_usable_bin_raises(self, tmp_path):
        layout = {
            (CAMPAIGN_A, "tt", POINT.category("tt", cls)): {
                POINT.signal_process: make_shape([1, 1, 1, 1]),
                "dy": make_shape([0, 0, 0, 0]),
            }
            for cls in CLASSES
        }
        path = tmp_path / "m.root"
        write_merged_file(path, layout)
        scope = resolve_scope("2024", "tt", [CAMPAIGN_A], ["tt"])
        with pytest.raises(ValueError, match="No usable bins"):
            build_point_shapes(path, POINT, scope, "max_score", "asimov_bkg")

    def test_missing_category_raises_key_error(self, merged_file):
        scope = resolve_scope("2024", "tt", [CAMPAIGN_A], ["tt"])
        missing = MassPoint("y2b", "h2tau", 1, 1)
        with pytest.raises(KeyError, match="not found"):
            build_point_shapes(
                merged_file, missing, scope, "max_score", "asimov_bkg"
            )

    def test_missing_file_raises(self, tmp_path):
        scope = resolve_scope("2024", "tt", [CAMPAIGN_A], ["tt"])
        # PyROOT raises a plain OSError itself, before the FileNotFoundError
        # branch of the production code can be reached
        with pytest.raises(OSError, match="Failed to open"):
            build_point_shapes(
                tmp_path / "nope.root", POINT, scope, "max_score", "asimov_bkg"
            )


class TestWriteShapesFile:
    def test_roundtrip_writes_bin_directories_with_named_histograms(
        self, tmp_path
    ):
        fit_bin = FitBin(CAMPAIGN_A, "tt", "xyh")
        shapes = BinShapes(
            signal=make_shape([1, 1, 1, 1], sumw2=[4, 4, 4, 4]),
            backgrounds={"dy": make_shape([4, 3, 2, 1])},
            data_obs=make_shape([5, 4, 3, 2]),
        )
        path = tmp_path / "out" / "shapes_in.root"
        write_shapes_file(path, {fit_bin: shapes})

        root_file = ROOT.TFile.Open(str(path))
        try:
            names = list_keys(root_file, fit_bin.name)
            signal = read_shape(root_file, f"{fit_bin.name}/{SIGNAL_NAME}")
            data = read_shape(root_file, f"{fit_bin.name}/{DATA_OBS_NAME}")
        finally:
            root_file.Close()
        assert sorted(names) == ["data_obs", "dy", "signal"]
        assert signal.sumw2.tolist() == pytest.approx([4, 4, 4, 4])
        assert data.values.tolist() == pytest.approx([5, 4, 3, 2])
        assert data.edges.tolist() == pytest.approx(EDGES.tolist())

    def test_signal_none_is_not_written(self, tmp_path):
        fit_bin = FitBin(CAMPAIGN_A, "tt", "xyh")
        shapes = BinShapes(
            None, {"dy": make_shape([4, 3, 2, 1])}, make_shape([4, 3, 2, 1])
        )
        path = tmp_path / "s.root"
        write_shapes_file(path, {fit_bin: shapes})
        root_file = ROOT.TFile.Open(str(path))
        try:
            names = list_keys(root_file, fit_bin.name)
        finally:
            root_file.Close()
        assert sorted(names) == ["data_obs", "dy"]

    def test_pipeline_roundtrip_from_merged_file(self, merged_file, tmp_path):
        scope = resolve_scope("2024", "tt", [CAMPAIGN_A], ["tt"])
        bins = build_point_shapes(
            merged_file, POINT, scope, "max_score", "asimov_sb"
        )
        path = tmp_path / "shapes_in.root"
        write_shapes_file(path, bins)
        root_file = ROOT.TFile.Open(str(path))
        try:
            keys = root_file.GetListOfKeys()
            assert {k.GetName() for k in keys} == {b.name for b in bins}
        finally:
            root_file.Close()
