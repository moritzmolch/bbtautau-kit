"""Orchestration of the fit: one independent task per mass point."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from xyh.core.parallel import run_in_parallel
from xyh.fit import combine as cmb
from xyh.fit.combine_config import CombineConfig
from xyh.fit.datacard import (
    build_datacard_spec,
    run_datacard_script,
    write_spec,
)
from xyh.fit.limits import (
    LIMITS_CSV,
    LIMITS_JSON,
    LimitResult,
    collect_limits,
    write_limits_csv,
    write_limits_json,
)
from xyh.fit.mass_points import MassPoint
from xyh.fit.scope import FitScope
from xyh.fit.shapes import build_point_shapes, write_shapes_file

logger = logging.getLogger(__name__)

STEPS = ("shapes", "datacard", "workspace", "limits")


def data_mode_dir(fit_dir: Path, scope: FitScope, data_mode: str) -> Path:
    """Directory of all points of a scope and data mode."""
    return fit_dir / scope.tag / data_mode


def point_dir(
    fit_dir: Path, scope: FitScope, data_mode: str, point: MassPoint
) -> Path:
    """Output directory of one mass point."""
    return (
        data_mode_dir(fit_dir, scope, data_mode)
        / point.decay_mode
        / point.mass_label
    )


@dataclass(frozen=True)
class PointTask:
    """All inputs of the fit of one mass point (picklable)."""

    point: MassPoint
    scope: FitScope
    merged_file: Path
    output_dir: Path
    variable: str
    data_mode: str
    combine: CombineConfig
    rebin: int | None = None
    min_real_events: float | None = None
    auto_mc_stats: float | None = None
    exclude: tuple[str, ...] = ()
    stop_after: str = "limits"


def run_point(task: PointTask) -> LimitResult | None:
    """Run the chain for one point; returns `None` if stopped early."""
    if task.stop_after not in STEPS:
        raise ValueError(f"Unknown step {task.stop_after!r}, use {STEPS}")
    out = task.output_dir
    out.mkdir(parents=True, exist_ok=True)

    # Shapes and datacard specification
    bins = build_point_shapes(
        task.merged_file,
        task.point,
        task.scope,
        task.variable,
        task.data_mode,
        task.exclude,
        task.rebin,
        task.min_real_events,
    )
    write_shapes_file(out / "shapes_in.root", bins, task.point.signal_process)
    spec = build_datacard_spec(task.point, bins, task.auto_mc_stats)
    write_spec(spec, out / "datacard_spec.json")
    if task.stop_after == "shapes":
        return None

    # Datacard, workspace and limits need the CMSSW environment
    cmb_cfg = task.combine
    prefix = cmb.environment_prefix(cmb_cfg.environment)

    # default_arguments = DefaultArguments(**cmb_cfg.default_arguments)
    # asymptotic_limits = AsymptoticLimits(**cmb_cfg.asymptotic_limits)
    run_datacard_script(prefix, out / "datacard_spec.json", out)
    if task.stop_after == "datacard":
        return None

    cmb.run_in_env(
        prefix,
        cmb.text2workspace_command(spec.datacard_file, "workspace.root"),
        out,
        out / "text2workspace.log",
    )
    if task.stop_after == "workspace":
        return None

    # Define datacard name
    datacard_name = task.point.signal_process

    cmb.run_in_env(
        prefix,
        cmb.asymptotic_limits_command(
            "workspace.root",
            datacard_name,
            cmb_cfg.default_arguments,
            cmb_cfg.asymptotic_limits,
        ),
        out,
        out / "combine.log",
    )
    entries = cmb.read_limit_entries(out / cmb.limit_file_name(datacard_name))
    result = LimitResult.from_values(
        task.point, cmb.limits_from_entries(entries)
    )
    write_limits_json(result, out / LIMITS_JSON)
    return result


def _run_point_safe(task: PointTask) -> tuple[MassPoint, str | None]:
    try:
        run_point(task)
    except Exception as err:  # noqa: BLE001 - reported at the end
        logger.exception(f"Fit of {task.point} failed")
        return task.point, f"{type(err).__name__}: {err}"
    return task.point, None


def run_fit(
    tasks: Sequence[PointTask],
    num_workers: int = 1,
    check_env: bool = True,
) -> list[LimitResult]:
    """Run all points, then collect the results into ``limits.csv``.

    Raises
    ------
    RuntimeError
        If any point failed (after all others have been processed).
    """
    if not tasks:
        raise ValueError("No fit tasks")
    first = tasks[0]
    if check_env and first.stop_after != "shapes":
        prefix = cmb.environment_prefix(first.combine.environment)
        first.output_dir.mkdir(parents=True, exist_ok=True)
        cmb.check_environment(prefix, first.output_dir)

    outcomes = run_in_parallel(_run_point_safe, tasks, num_workers)
    failed = {p: e for p, e in outcomes if e is not None}

    results: list[LimitResult] = []
    if first.stop_after == "limits":
        directory = first.output_dir.parents[1]
        results = collect_limits(directory)
        write_limits_csv(results, directory / LIMITS_CSV)
        logger.info(f"Wrote {directory / LIMITS_CSV}")

    if failed:
        lines = [f"  {p.signal_process}: {e}" for p, e in failed.items()]
        raise RuntimeError("Fit failed for:\n" + "\n".join(lines))
    return results
