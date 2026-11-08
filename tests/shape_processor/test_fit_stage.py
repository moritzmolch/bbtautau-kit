"""Unit tests for the entry point of the fit stage (`build_tasks`).

The real ``fit.yaml`` is composed with Hydra; the merged histogram file is a
fabricated ROOT file that only contains the category directories.
"""

import pickle
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from xyh import ROOT_DIR
from xyh.fit.combine import CombineConfig
from xyh.fit.mass_points import MassPoint
from xyh.shape_processor import fit as fit_stage
from xyh.workflow.hydra_utils import compose_cfg

ROOT = pytest.importorskip("ROOT")

POINTS = [
    MassPoint("y2b", "h2tau", 2000, 500),
    MassPoint("y2b", "h2tau", 3000, 100),
    MassPoint("y2tau", "h2b", 2000, 500),
]


@pytest.fixture
def merged_file(tmp_path):
    path = tmp_path / "merged.root"
    root_file = ROOT.TFile.Open(str(path), "RECREATE")
    for campaign in ("2024_nano_v15", "2025_nano_v15"):
        campaign_dir = root_file.mkdir(campaign)
        for channel in ("et", "mt", "tt"):
            directory = campaign_dir.mkdir(channel)
            for point in POINTS:
                directory.mkdir(point.category(channel, "xyh"))
                directory.mkdir(point.category(channel, "t_tt"))
            directory.mkdir(f"{channel}_regular_category")
    root_file.Write()
    root_file.Close()
    return path


@pytest.fixture
def make_cfg(tmp_path, merged_file):
    def make(*overrides):
        return compose_cfg(
            "fit",
            [
                "tags.shapes_tag=foo",
                f"merged_histograms_file={merged_file}",
                f"fit_dir={tmp_path / 'fit'}",
                *overrides,
            ],
        )

    return make


class TestFitYaml:
    def test_defaults_compose(self):
        cfg = compose_cfg("fit", ["tags.shapes_tag=foo"])
        assert cfg.merged_histograms_file == (
            "data/output/foo/histograms/merged_histograms.root"
        )
        assert cfg.fit_dir == "data/output/fit/foo"
        assert cfg.fit.data.mode == "asimov_bkg"
        assert cfg.fit.stop_after == "limits"
        assert list(cfg.inventory.channels) == ["et", "mt", "tt"]


class TestBuildTasks:
    def test_defaults_give_one_task_per_point_in_all_scope(self, make_cfg):
        tasks = fit_stage.build_tasks(make_cfg())
        assert [t.point for t in tasks] == sorted(POINTS)
        task = tasks[0]
        assert task.scope.tag == "all_all"
        assert task.data_mode == "asimov_bkg"
        assert task.variable == "max_score"
        assert task.rebin is None
        assert task.auto_mc_stats is None
        assert task.exclude == ()
        assert task.stop_after == "limits"
        assert task.output_dir.parts[-4:] == (
            "all_all",
            "asimov_bkg",
            "y2b_h2tau",
            "mx2000_my500",
        )

    def test_scope_overrides_select_campaign_and_channel(self, make_cfg):
        tasks = fit_stage.build_tasks(
            make_cfg("fit.campaigns=[2024]", "fit.channels=[tt]")
        )
        scope = tasks[0].scope
        assert scope.campaigns == ("2024_nano_v15",)
        assert scope.channels == ("tt",)
        assert scope.tag == "2024_tt"
        assert "2024_tt" in tasks[0].output_dir.parts

    def test_mass_point_and_decay_mode_selection(self, make_cfg):
        tasks = fit_stage.build_tasks(
            make_cfg("fit.mass_points=[[2000,500]]", "fit.ydm=[y2tau]")
        )
        assert [t.point for t in tasks] == [POINTS[2]]

    def test_string_mass_point_is_accepted(self, make_cfg):
        tasks = fit_stage.build_tasks(make_cfg("fit.mass_points=['3000_100']"))
        assert [t.point for t in tasks] == [POINTS[1]]

    def test_unavailable_mass_point_raises(self, make_cfg):
        with pytest.raises(ValueError, match="not available"):
            fit_stage.build_tasks(make_cfg("fit.mass_points=[[1,1]]"))

    def test_unknown_data_mode_raises(self, make_cfg):
        with pytest.raises(ValueError, match="fit.data.mode must be one of"):
            fit_stage.build_tasks(make_cfg("fit.data.mode=foo"))

    @pytest.mark.parametrize("mode", ["asimov_bkg", "asimov_sb", "observed"])
    def test_data_mode_is_part_of_output_dir(self, make_cfg, mode):
        tasks = fit_stage.build_tasks(make_cfg(f"fit.data.mode={mode}"))
        assert mode in tasks[0].output_dir.parts
        assert tasks[0].data_mode == mode

    def test_unknown_campaign_raises(self, make_cfg):
        with pytest.raises(ValueError, match="not available"):
            fit_stage.build_tasks(make_cfg("fit.campaigns=[2018]"))

    def test_processing_options_are_forwarded(self, make_cfg):
        tasks = fit_stage.build_tasks(
            make_cfg(
                "fit.rebin=2",
                "fit.automcstats=10",
                "fit.exclude_processes=[dy,tt]",
                "fit.stop_after=datacard",
                "fit.variable=other",
            )
        )
        task = tasks[0]
        assert task.rebin == 2
        assert task.auto_mc_stats == 10
        assert task.exclude == ("dy", "tt")
        assert task.stop_after == "datacard"
        assert task.variable == "other"

    def test_default_combine_config_resolves_relative_cmssw_dir(self, make_cfg):
        combine = fit_stage.build_tasks(make_cfg())[0].combine
        assert combine.cmssw_dir == str(
            ROOT_DIR / "external/combine/CMSSW_16_0_0"
        )
        assert combine.scram_arch == "el9_amd64_gcc13"
        assert combine.setup_cmd == ""
        assert combine.r_range is None
        assert combine.extra_args == ()

    def test_combine_overrides(self, make_cfg):
        combine = fit_stage.build_tasks(
            make_cfg(
                "fit.combine.cmssw_dir=/abs/CMSSW",
                "fit.combine.setup_cmd='source x'",
                "fit.combine.r_range=[0,5]",
                "fit.combine.extra_args=[--verbose,foo]",
            )
        )[0].combine
        assert combine == CombineConfig(
            cmssw_dir="/abs/CMSSW",
            scram_arch="el9_amd64_gcc13",
            setup_cmd="source x",
            r_range=(0.0, 5.0),
            extra_args=("--verbose", "foo"),
        )

    def test_numeric_extra_args_are_strings(self, make_cfg):
        combine = fit_stage.build_tasks(
            make_cfg("fit.combine.extra_args=[-v,2]")
        )[0].combine
        assert combine.extra_args == ("-v", "2")

    def test_empty_cmssw_dir_gives_empty_string(self, make_cfg):
        combine = fit_stage.build_tasks(make_cfg("fit.combine.cmssw_dir=null"))[
            0
        ].combine
        assert combine.cmssw_dir == ""

    def test_relative_paths_are_resolved_against_repository_root(
        self, merged_file
    ):
        cfg = compose_cfg("fit", ["tags.shapes_tag=foo"])
        cfg = OmegaConf.merge(cfg, {"merged_histograms_file": str(merged_file)})
        tasks = fit_stage.build_tasks(cfg)
        assert tasks[0].merged_file == Path(merged_file)
        assert tasks[0].output_dir.is_relative_to(
            ROOT_DIR / "data/output/fit/foo"
        )

    def test_tasks_are_picklable(self, make_cfg):
        tasks = fit_stage.build_tasks(make_cfg())
        assert pickle.loads(pickle.dumps(tasks)) == tasks

    def test_missing_merged_file_raises(self, make_cfg, tmp_path):
        cfg = make_cfg(f"merged_histograms_file={tmp_path / 'nope.root'}")
        # PyROOT raises a plain OSError itself for files that do not exist
        with pytest.raises(OSError, match="Failed to open"):
            fit_stage.build_tasks(cfg)


class TestMain:
    def test_main_runs_fit_with_tasks_and_num_workers(self, make_cfg, mocker):
        run = mocker.patch.object(fit_stage, "run_fit")
        fit_stage.main.__wrapped__(make_cfg("fit.num_workers=3"))
        tasks = run.call_args.args[0]
        assert len(tasks) == len(POINTS)
        assert run.call_args.kwargs == {"num_workers": 3}
