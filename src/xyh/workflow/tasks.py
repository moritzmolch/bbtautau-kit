"""Tasks covering the shape production chain (phase 1: one task per stage).

Run with, e.g.::

    law run xyh.Shapes --overrides "tags.shapes_tag=foo" --fake-factors
"""

import law
import luigi

from xyh.workflow.base import DirStageTask, FileStageTask


class CreateDatasetSpecs(FileStageTask):
    stage = "create_dataset_specs"


class CreateFiltersAndWeightsSpecs(FileStageTask):
    stage = "create_filters_and_weights_specs"


class CreateHistogramSpecs(FileStageTask):
    stage = "create_histogram_specs"


class CreateGraphSpecs(FileStageTask):
    stage = "create_graph_specs"

    def requires(self):
        kwargs = {"overrides": self.overrides}
        return {
            "datasets": CreateDatasetSpecs.req(self, **kwargs),
            "filters_and_weights": CreateFiltersAndWeightsSpecs.req(
                self, **kwargs
            ),
            "histograms": CreateHistogramSpecs.req(self, **kwargs),
        }


class RunGraphs(DirStageTask):
    stage = "run_graphs"

    def requires(self):
        return CreateGraphSpecs.req(self)


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
