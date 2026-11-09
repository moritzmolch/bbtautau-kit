"""Orchestration of the fit: one independent task per mass point."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from xyh.core.parallel import run_in_parallel
from xyh.fit import combine as cmb
from xyh.fit.combine_config import CombineConfig
from xyh.fit.datacard import (
    DatacardSpec,
    build_datacard_spec,
    run_datacard_script,
    write_spec,
)
from xyh.fit.limits import (
    LIMITS_CSV,
    LIMITS_JSON,
    LimitResult,
    collect_limits,
    read_limits_json,
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
    # Recreate files that are already on disk
    overwrite: bool = False


WORKSPACE_FILE = "workspace.root"
SHAPES_IN_FILE = "shapes_in.root"
SPEC_FILE = "datacard_spec.json"


def _done(task: PointTask, *files: Path) -> bool:
    """Whether all `files` exist and may be reused."""
    return not task.overwrite and all(f.exists() for f in files)


def _check_step(task: PointTask) -> None:
    if task.stop_after not in STEPS:
        raise ValueError(f"Unknown step {task.stop_after!r}, use {STEPS}")


def prepare_point(task: PointTask) -> None:
    """Stage 1: shapes, datacard and workspace of one point.

    Steps whose output files are already on disk are skipped (unless
    `task.overwrite` is set). Stops after `task.stop_after`.
    """
    _check_step(task)
    out = task.output_dir
    out.mkdir(parents=True, exist_ok=True)
    defaults = DatacardSpec(analysis="", mass=0, bins=())
    datacard = out / defaults.datacard_file
    datacard_files = (datacard, out / defaults.shapes_out_file)

    # Shapes and datacard specification
    if not _done(task, out / SHAPES_IN_FILE, out / SPEC_FILE) and not (
        _done(task, *datacard_files) and task.stop_after != "shapes"
    ):
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
        write_shapes_file(out / SHAPES_IN_FILE, bins, task.point.signal_process)
        spec = build_datacard_spec(task.point, bins, task.auto_mc_stats)
        write_spec(spec, out / SPEC_FILE)
    else:
        logger.info(f"Reuse shapes of {task.point.signal_process}")
    if task.stop_after == "shapes":
        return

    # Datacard and workspace need the CMSSW environment
    prefix = cmb.environment_prefix(task.combine.environment)

    if not _done(task, *datacard_files):
        run_datacard_script(prefix, out / SPEC_FILE, out)
    else:
        logger.info(f"Reuse datacard of {task.point.signal_process}")
    if task.stop_after == "datacard":
        return

    if not _done(task, out / WORKSPACE_FILE):
        cmb.run_in_env(
            prefix,
            cmb.text2workspace_command(defaults.datacard_file, WORKSPACE_FILE),
            out,
            out / "text2workspace.log",
        )
    else:
        logger.info(f"Reuse workspace of {task.point.signal_process}")


def limit_point(task: PointTask) -> LimitResult | None:
    """Stage 2: asymptotic limits of one point from its workspace.

    Reuses an existing ``limits.json`` (unless `task.overwrite` is set).
    """
    out = task.output_dir
    limits_file = out / LIMITS_JSON
    if _done(task, limits_file):
        logger.info(f"Reuse limits of {task.point.signal_process}")
        return read_limits_json(limits_file)

    # Name of the combine output
    datacard_name = task.point.signal_process
    prefix = cmb.environment_prefix(task.combine.environment)
    cmb_cfg = task.combine
    cmb.run_in_env(
        prefix,
        cmb.asymptotic_limits_command(
            WORKSPACE_FILE,
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
    write_limits_json(result, limits_file)
    return result


def run_point(task: PointTask) -> LimitResult | None:
    """Run both stages for one point; returns `None` if stopped early."""
    prepare_point(task)
    if task.stop_after != "limits":
        return None
    return limit_point(task)


def _run_safe(fn, task: PointTask) -> tuple[MassPoint, str | None]:
    try:
        fn(task)
    except Exception as err:  # noqa: BLE001 - reported at the end
        logger.exception(f"{fn.__name__} of {task.point} failed")
        return task.point, f"{type(err).__name__}: {err}"
    return task.point, None


# Module-level so that they can be pickled for the process pool
def _prepare_point_safe(task: PointTask) -> tuple[MassPoint, str | None]:
    return _run_safe(prepare_point, task)


def _limit_point_safe(task: PointTask) -> tuple[MassPoint, str | None]:
    return _run_safe(limit_point, task)


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

    # Stage 1: datacards and workspaces of all points
    for task in tasks:
        _check_step(task)
    failed: dict[MassPoint, str] = {}
    outcomes = run_in_parallel(_prepare_point_safe, tasks, num_workers)
    failed.update({p: e for p, e in outcomes if e is not None})

    # Stage 2: limits of all points with a workspace
    if first.stop_after == "limits":
        ready = [t for t in tasks if t.point not in failed]
        outcomes = run_in_parallel(_limit_point_safe, ready, num_workers)
        failed.update({p: e for p, e in outcomes if e is not None})

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
