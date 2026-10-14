"""Tasks covering the shape production chain (one task per stage).

Run with, e.g.::

    law run xyh.Shapes --overrides "tags.shapes_tag=foo" --fake-factors

To apply the data-driven Z corrections, set the production they are derived
from (`z_pt_weights.tag`, see `base/global.yaml`). The workflow then first
produces and merges that production, derives the corrections from it and
applies them in the production `tags.shapes_tag`::

    law run xyh.Shapes --overrides \\
        "tags.shapes_tag=foo z_pt_weights.tag=foo-z-pt-derivation"
"""

import shlex

import law
import luigi

from xyh.workflow.base import DirStageTask


class RunGraphs(DirStageTask):
    """Create all specs and process the graphs.

    The dataset, histogram, filter/weight and graph specs are created inside
    this stage and dumped to ``artifacts.*_specs_file``.
    """

    stage = "run_graphs"

    def requires(self):
        # Corrections that are applied in this production must exist first
        if self.applies_z_corrections:
            return DeriveZPtWeights.req(self)
        return super().requires()


class RunGraphsSnapshots(RunGraphs):
    """Produce snapshots instead of histograms.

    Runs the same stage as `RunGraphs` with ``graph_processing.mode=snapshot``,
    so the output goes to ``artifacts.snapshots_dir``. It is independent of
    `RunGraphs`, and the downstream histogram tasks do not require it.
    """

    forced_overrides = {"graph_processing.mode": "snapshot"}
    marker_name = "run_graphs_snapshots"


class RunFakeFactorHistograms(DirStageTask):
    stage = "run_fake_factor_histograms"

    def requires(self):
        return RunGraphs.req(self)


class MergeHistograms(DirStageTask):
    stage = "merge_histograms"

    fake_factors = luigi.BoolParameter(
        default=False,
        description="run the fake factor histograms before merging",
    )

    def requires(self):
        if self.fake_factors:
            return RunFakeFactorHistograms.req(self)
        return RunGraphs.req(self)


class PlotShapes(DirStageTask):
    stage = "plot_shapes"

    fake_factors = luigi.BoolParameter(default=False)

    def requires(self):
        return MergeHistograms.req(self, fake_factors=self.fake_factors)


class DeriveZPtWeights(DirStageTask):
    """Derive the Z normalization and pt corrections.

    The corrections are derived from the production `z_pt_weights.tag` with
    the overrides `z_pt_weights.overrides` on top of the user overrides. This
    production is run and merged without any Z corrections.
    """

    stage = "derive_z_pt_weights"
    derives_z_corrections = True

    def requires(self):
        return MergeHistograms.req(
            self, overrides=shlex.join(self.derivation_overrides)
        )


class Shapes(law.WrapperTask):
    """Full shape production, replacing ``bin/shapes_ff`` and ``bin/shapes_no_ff``."""

    overrides = luigi.Parameter(default="")
    fake_factors = luigi.BoolParameter(default=False)

    task_namespace = "xyh"

    def requires(self):
        return PlotShapes.req(self)
