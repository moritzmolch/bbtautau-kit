"""Unit tests for `xyh.fit.pipeline` with all heavy steps mocked."""

import logging
from pathlib import Path

import pytest

from xyh.fit import pipeline
from xyh.fit.combine import CombineConfig
from xyh.fit.limits import (
    LIMITS_CSV,
    LIMITS_JSON,
    LimitResult,
    write_limits_json,
)
from xyh.fit.mass_points import MassPoint
from xyh.fit.pipeline import (
    PointTask,
    data_mode_dir,
    point_dir,
    run_fit,
    run_point,
)
from xyh.fit.scope import FitScope

SCOPE = FitScope(("2024_nano_v15",), ("tt",))
ENTRIES = [
    (1.0, 0.025),
    (2.0, 0.16),
    (3.0, 0.5),
    (4.0, 0.84),
    (5.0, 0.975),
    (3.5, -1.0),
]


def _point(mx=2000, my=500):
    return MassPoint("y2b", "h2tau", mx, my)


def _task(tmp_path, point=None, **kwargs):
    point = point or _point()
    defaults = {
        "point": point,
        "scope": SCOPE,
        "merged_file": tmp_path / "merged.root",
        "output_dir": point_dir(tmp_path, SCOPE, "asimov_bkg", point),
        "variable": "max_score",
        "data_mode": "asimov_bkg",
        "combine": CombineConfig(
            setup_cmd="setup", r_range=(0.0, 10.0), extra_args=("-v", "1")
        ),
    }
    return PointTask(**{**defaults, **kwargs})


def test_directory_layout(tmp_path):
    assert data_mode_dir(tmp_path, SCOPE, "asimov_sb") == (
        tmp_path / "2024_tt" / "asimov_sb"
    )
    assert point_dir(tmp_path, SCOPE, "asimov_sb", _point()) == (
        tmp_path / "2024_tt" / "asimov_sb" / "y2b_h2tau" / "mx2000_my500"
    )


@pytest.fixture
def steps(mocker):
    """Mock everything that touches ROOT, CH or Combine."""
    mocks = mocker.MagicMock()
    # No bins: the real `build_datacard_spec` then yields an empty spec
    mocks.build_shapes.return_value = {}
    mocker.patch.object(
        pipeline, "build_point_shapes", side_effect=mocks.build_shapes
    )
    mocker.patch.object(
        pipeline, "write_shapes_file", side_effect=mocks.write_shapes
    )
    mocker.patch.object(
        pipeline.cmb, "run_in_env", side_effect=mocks.run_in_env
    )
    mocker.patch.object(
        pipeline, "run_datacard_script", side_effect=mocks.run_datacard
    )
    mocker.patch.object(
        pipeline.cmb, "read_limit_entries", return_value=ENTRIES
    )
    return mocks


class TestRunPoint:
    def test_full_chain_runs_all_steps_and_writes_limits(self, tmp_path, steps):
        task = _task(tmp_path, rebin=2, auto_mc_stats=5.0, exclude=("dy",))
        result = run_point(task)

        steps.build_shapes.assert_called_once_with(
            task.merged_file,
            task.point,
            SCOPE,
            "max_score",
            "asimov_bkg",
            ("dy",),
            2,
        )
        steps.write_shapes.assert_called_once()
        assert steps.write_shapes.call_args.args[0] == (
            task.output_dir / "shapes_in.root"
        )
        assert (task.output_dir / "datacard_spec.json").exists()
        steps.run_datacard.assert_called_once_with(
            "setup", task.output_dir / "datacard_spec.json", task.output_dir
        )
        commands = [c.args[1] for c in steps.run_in_env.call_args_list]
        assert commands[0][0] == "text2workspace.py"
        assert commands[1][:3] == ["combine", "-M", "AsymptoticLimits"]
        assert "--rMax" in commands[1] and commands[1][-2:] == ["-v", "1"]
        assert result.exp == 3.0
        assert result.obs == 3.5
        assert (task.output_dir / LIMITS_JSON).exists()

    @pytest.mark.parametrize(
        ("stop_after", "datacard", "env_calls"),
        [
            ("shapes", 0, 0),
            ("datacard", 1, 0),
            ("workspace", 1, 1),
            ("limits", 1, 2),
        ],
    )
    def test_stop_after_limits_the_executed_steps(
        self, tmp_path, steps, stop_after, datacard, env_calls
    ):
        result = run_point(_task(tmp_path, stop_after=stop_after))
        assert steps.run_datacard.call_count == datacard
        assert steps.run_in_env.call_count == env_calls
        assert (result is None) == (stop_after != "limits")

    def test_stop_after_shapes_needs_no_environment(self, tmp_path, steps):
        task = _task(tmp_path, combine=CombineConfig(), stop_after="shapes")
        assert run_point(task) is None

    def test_missing_environment_config_raises_after_shapes(
        self, tmp_path, steps
    ):
        task = _task(tmp_path, combine=CombineConfig())
        with pytest.raises(ValueError, match="cmssw_dir"):
            run_point(task)
        steps.write_shapes.assert_called_once()

    def test_unknown_stop_after_raises_before_any_work(self, tmp_path, steps):
        with pytest.raises(ValueError, match="Unknown step 'foo'"):
            run_point(_task(tmp_path, stop_after="foo"))
        steps.build_shapes.assert_not_called()


class TestRunFit:
    @pytest.fixture
    def fake_point_run(self, mocker, tmp_path):
        """Replace `run_point` by a function writing a limits.json."""
        calls = []

        def fake(task):
            calls.append(task.point)
            if task.point.mx == 666:
                raise RuntimeError("combine exploded")
            values = {
                k: float(task.point.mx)
                for k in ("exp_m2", "exp_m1", "exp", "exp_p1", "exp_p2", "obs")
            }
            write_limits_json(
                LimitResult.from_values(task.point, values),
                task.output_dir / LIMITS_JSON,
            )

        mocker.patch.object(pipeline, "run_point", side_effect=fake)
        return calls

    def test_empty_task_list_raises(self):
        with pytest.raises(ValueError, match="No fit tasks"):
            run_fit([])

    def test_success_collects_results_and_writes_csv(
        self, tmp_path, fake_point_run, mocker
    ):
        check = mocker.patch.object(pipeline.cmb, "check_environment")
        tasks = [_task(tmp_path, _point(m)) for m in (3000, 2000)]
        results = run_fit(tasks)
        assert [r.mx for r in results] == [2000, 3000]
        csv_file = data_mode_dir(tmp_path, SCOPE, "asimov_bkg") / LIMITS_CSV
        assert csv_file.exists()
        check.assert_called_once()
        assert check.call_args.args[0] == "setup"

    def test_failing_point_is_logged_others_continue_then_runtime_error(
        self, tmp_path, fake_point_run, mocker, caplog
    ):
        mocker.patch.object(pipeline.cmb, "check_environment")
        tasks = [_task(tmp_path, _point(m)) for m in (2000, 666, 3000)]
        with (
            caplog.at_level(logging.ERROR),
            pytest.raises(RuntimeError, match="Fit failed for") as exc,
        ):
            run_fit(tasks)
        assert fake_point_run == [t.point for t in tasks]
        assert "xyh_y2b_h2tau_mx666_my500: RuntimeError: combine exploded" in (
            str(exc.value)
        )
        assert "mx2000" not in str(exc.value)
        assert "Fit of" in caplog.text
        # The CSV of the successful points is still written
        csv_file = data_mode_dir(tmp_path, SCOPE, "asimov_bkg") / LIMITS_CSV
        assert csv_file.read_text().count("\n") == 3

    def test_check_env_false_skips_environment_check(
        self, tmp_path, fake_point_run, mocker
    ):
        check = mocker.patch.object(pipeline.cmb, "check_environment")
        run_fit([_task(tmp_path)], check_env=False)
        check.assert_not_called()

    def test_stop_after_shapes_skips_check_and_collection(
        self, tmp_path, mocker
    ):
        check = mocker.patch.object(pipeline.cmb, "check_environment")
        mocker.patch.object(pipeline, "run_point")
        collect = mocker.patch.object(pipeline, "collect_limits")
        assert run_fit([_task(tmp_path, stop_after="shapes")]) == []
        check.assert_not_called()
        collect.assert_not_called()

    def test_stop_after_workspace_checks_env_but_does_not_collect(
        self, tmp_path, mocker
    ):
        check = mocker.patch.object(pipeline.cmb, "check_environment")
        mocker.patch.object(pipeline, "run_point")
        collect = mocker.patch.object(pipeline, "collect_limits")
        assert run_fit([_task(tmp_path, stop_after="workspace")]) == []
        check.assert_called_once()
        collect.assert_not_called()

    def test_missing_env_config_with_check_raises_before_running(
        self, tmp_path, mocker
    ):
        run = mocker.patch.object(pipeline, "run_point")
        with pytest.raises(ValueError, match="cmssw_dir"):
            run_fit([_task(tmp_path, combine=CombineConfig())])
        run.assert_not_called()


def test_point_task_is_picklable(tmp_path):
    import pickle

    task = _task(tmp_path)
    assert pickle.loads(pickle.dumps(task)) == task
    assert isinstance(task.output_dir, Path)
