"""Tasks of the fit: one task per mass point and the collection of limits.

Run with, e.g.::

    law run xyh.CollectLimits --overrides \\
        "tags.shapes_tag=foo fit.campaigns=[2024] fit.channels=[tt]"

All configuration stays in the Hydra config (``fit.*`` overrides). The point
tasks select their single point through ``fit.mass_points``, ``fit.ydm`` and
``fit.hdm``.
"""

import shlex
from collections.abc import Sequence
from pathlib import Path

import law

from xyh import ROOT_DIR
from xyh.fit.config import as_list
from xyh.fit.limits import (
    LIMITS_CSV,
    LIMITS_JSON,
    collect_limits,
    write_limits_csv,
)
from xyh.fit.mass_points import (
    MassPoint,
    discover_mass_points,
    parse_mass_pair,
    select_mass_points,
)
from xyh.fit.pipeline import data_mode_dir, point_dir
from xyh.fit.plotting import plot_all_limits
from xyh.fit.scope import resolve_scope
from xyh.fit.shapes import list_categories
from xyh.workflow.base import HydraTask
from xyh.workflow.shapes_and_snapshots import MergeHistograms


def strip_fit_overrides(overrides: Sequence[str]) -> list[str]:
    """Drop ``fit.*`` overrides, which upstream stages do not know."""
    return [o for o in overrides if not o.startswith("fit.")]


def point_overrides(overrides: Sequence[str], point: MassPoint) -> str:
    """Overrides that restrict a fit configuration to a single point."""
    forced = [
        f"fit.mass_points=[[{point.mx},{point.my}]]",
        f"fit.ydm=[{point.ydm}]",
        f"fit.hdm=[{point.hdm}]",
    ]
    return shlex.join(HydraTask._merge_overrides(overrides, forced))


class FitBase(HydraTask):
    """Common config access of the fit tasks."""

    stage = "fit"

    @property
    def merge_overrides(self) -> str:
        return shlex.join(strip_fit_overrides(shlex.split(self.overrides)))

    def requires(self):
        return MergeHistograms.req(
            self, overrides=self.merge_overrides, fake_factors=True
        )

    @property
    def scope(self):
        return resolve_scope(
            as_list(self.cfg.fit.campaigns) or [],
            as_list(self.cfg.fit.channels) or [],
            list(self.cfg.inventory.campaigns),
            list(self.cfg.inventory.channels),
        )

    @property
    def fit_dir(self) -> Path:
        return ROOT_DIR / self.cfg_value("fit_dir")

    @property
    def data_mode(self) -> str:
        return self.cfg_value("fit.data.mode")


class FitMassPoint(FitBase):
    """Fit of one mass point; the output is its ``limits.json``."""

    def point(self) -> MassPoint:
        fit = self.cfg.fit
        pairs = fit.mass_points
        if pairs is None or len(pairs) != 1 or not fit.ydm or not fit.hdm:
            raise ValueError(
                "FitMassPoint needs exactly one fit.mass_points entry and "
                "one fit.ydm / fit.hdm each"
            )
        mx, my = parse_mass_pair((as_list(pairs) or [])[0])
        return MassPoint(ydm=fit.ydm[0], hdm=fit.hdm[0], mx=mx, my=my)

    def output(self):
        directory = point_dir(
            self.fit_dir, self.scope, self.data_mode, self.point()
        )
        return law.LocalFileTarget(str(directory / LIMITS_JSON))

    def run(self):
        self.run_stage()


class CollectLimits(FitBase):
    """Run all points of the selection and collect ``limits.csv`` + plots."""

    def output(self):
        directory = data_mode_dir(self.fit_dir, self.scope, self.data_mode)
        return law.LocalFileTarget(str(directory / LIMITS_CSV))

    def points(self) -> list[MassPoint]:
        """Selected points; discovered from the merged file if needed."""
        import ROOT

        fit = self.cfg.fit
        merged = ROOT_DIR / self.cfg_value("merged_histograms_file")
        scope = self.scope
        root_file = ROOT.TFile.Open(str(merged), "READ")
        try:
            categories = list_categories(
                root_file, scope.campaigns[0], scope.channels[0]
            )
        finally:
            root_file.Close()

        return select_mass_points(
            discover_mass_points(categories),
            as_list(fit.mass_points),
            as_list(fit.ydm),
            as_list(fit.hdm),
        )

    def run(self):
        # The points can only be discovered once the histograms are merged
        base = shlex.split(self.overrides)
        yield [
            FitMassPoint.req(self, overrides=point_overrides(base, point))
            for point in self.points()
        ]

        directory = Path(str(self.output().path)).parent
        results = collect_limits(directory)
        write_limits_csv(results, directory / LIMITS_CSV)
        plot_all_limits(results, directory / "plots")
