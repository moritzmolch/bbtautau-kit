"""Tasks covering the shape production chain (one task per stage).

Run with, e.g.::

    law run xyh.Shapes --overrides "tags.shapes_tag=foo" --fake-factors
"""

import law
import luigi

from xyh.workflow.base import DirStageTask


class RunGraphs(DirStageTask):
    """Create all specs and process the graphs.

    The dataset, histogram, filter/weight and graph specs are created inside
    this stage and dumped to ``artifacts.*_specs_file``.
    """

    stage = "run_graphs"


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


class Shapes(law.WrapperTask):
    """Full shape production, replacing ``bin/shapes_ff`` and ``bin/shapes_no_ff``."""

    overrides = luigi.Parameter(default="")
    fake_factors = luigi.BoolParameter(default=False)

    task_namespace = "xyh"

    def requires(self):
        return PlotShapes.req(self)
