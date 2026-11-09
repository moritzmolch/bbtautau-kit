"""Fit stage: Combine datacards, workspaces and asymptotic limits."""

import logging
from pathlib import Path

from omegaconf import DictConfig

from xyh import ROOT_DIR
from xyh.core.cli import hydra_cli
from xyh.fit.combine_config import (
    AsymptoticLimits,
    CombineConfig,
    DefaultArguments,
    Environment,
)
from xyh.fit.config import as_list
from xyh.fit.mass_points import discover_mass_points, select_mass_points
from xyh.fit.pipeline import PointTask, point_dir, run_fit
from xyh.fit.scope import resolve_scope
from xyh.fit.shapes import DATA_MODES, list_categories

logger = logging.getLogger(__name__)


def _resolve_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT_DIR / p


def build_tasks(cfg: DictConfig) -> list[PointTask]:
    """Translate the Hydra config into one task per mass point."""
    import ROOT

    fit = cfg["fit"]
    data_mode = fit["data"]["mode"]
    if data_mode not in DATA_MODES:
        raise ValueError(f"fit.data.mode must be one of {DATA_MODES}")

    scope = resolve_scope(
        as_list(fit["campaigns"]) or [],
        as_list(fit["channels"]) or [],
        list(cfg["inventory"]["campaigns"]),
        list(cfg["inventory"]["channels"]),
    )
    merged_file = _resolve_path(cfg["merged_histograms_file"])
    fit_dir = _resolve_path(cfg["fit_dir"])

    # Discover the available points from the first bin of the scope
    root_file = ROOT.TFile.Open(str(merged_file), "READ")
    if not root_file or root_file.IsZombie():
        raise FileNotFoundError(f"Cannot open {merged_file}")
    try:
        categories = list_categories(
            root_file, scope.campaigns[0], scope.channels[0]
        )
    finally:
        root_file.Close()
    points = select_mass_points(
        discover_mass_points(categories),
        as_list(fit["mass_points"]),
        as_list(fit["decay_modes"]),
    )

    comb = fit["combine"]
    combine = CombineConfig(
        environment=Environment(**comb["environment"]),
        default_arguments=DefaultArguments(**comb["default_arguments"]),
        asymptotic_limits=AsymptoticLimits(**comb["asymptotic_limits"]),
    )
    return [
        PointTask(
            point=point,
            scope=scope,
            merged_file=merged_file,
            output_dir=point_dir(fit_dir, scope, data_mode, point),
            variable=fit["variable"],
            data_mode=data_mode,
            combine=combine,
            rebin=fit["rebin"],
            min_real_events=fit["min_real_events"],
            auto_mc_stats=fit["automcstats"],
            exclude=tuple(as_list(fit.get("exclude_processes")) or ()),
            stop_after=fit["stop_after"],
            overwrite=fit.get("overwrite", False),
        )
        for point in points
    ]


@hydra_cli("fit")
def main(cfg: DictConfig):
    tasks = build_tasks(cfg)
    logger.info(f"Fit {len(tasks)} mass points in scope {tasks[0].scope.tag}")
    run_fit(tasks, num_workers=cfg["fit"]["num_workers"])


if __name__ == "__main__":
    main()
