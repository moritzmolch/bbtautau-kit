"""Base class for workflow tasks that wrap shape_processor stages.

Tasks have no parameters of their own beyond ``overrides``. All configuration
(tags, campaigns, paths, ...) lives in the Hydra config, which the task
composes to derive its outputs.
"""

import shlex
from functools import cached_property
from pathlib import Path
from typing import Any

import law
import luigi
from omegaconf import DictConfig, OmegaConf

from xyh import ROOT_DIR
from xyh.workflow.hydra_utils import compose_cfg, run_stage


class HydraTask(law.Task):
    """A task wrapping one shape_processor stage.

    Subclasses set `stage` (the stage module, which is also the name of its
    Hydra config) and implement `output`.
    """

    stage: str

    overrides = luigi.Parameter(
        default="",
        description="Whitespace-separated Hydra overrides, as passed to the "
        "stage CLI, e.g. 'tags.shapes_tag=foo inventory.campaigns=[2024_nano_v15]'",
    )

    # `overrides` determines the composed config and therefore all outputs
    task_namespace = "xyh"

    @property
    def override_list(self) -> list[str]:
        return shlex.split(self.overrides)

    @cached_property
    def cfg(self) -> DictConfig:
        return compose_cfg(self.stage, self.override_list)

    def cfg_value(self, key: str) -> Any:
        """Resolve a single (dotted) key of the composed config.

        Resolving lazily avoids failing on unrelated keys with unresolvable
        interpolations, which Hydra itself only evaluates on access.
        """
        return OmegaConf.select(self.cfg, key, throw_on_missing=True)

    def path_target(self, key: str) -> law.LocalFileTarget:
        """Target for a path-valued key of the composed stage config."""
        return law.LocalFileTarget(str(ROOT_DIR / self.cfg_value(key)))

    def marker_target(self) -> law.LocalFileTarget:
        """Completion marker for stages that write a directory of files."""
        specs_dir = Path(self.cfg_value("artifacts.graph_specs_file")).parent
        return law.LocalFileTarget(
            str(
                ROOT_DIR / specs_dir.parent / ".workflow" / f"{self.stage}.done"
            )
        )

    def run_stage(self, extra_overrides: list[str] = ()) -> None:  # pyright: ignore[reportAssignmentType]
        run_stage(self.stage, [*self.override_list, *extra_overrides])


class DirStageTask(HydraTask):
    """A stage writing many files; completion is tracked by a marker file."""

    def output(self):
        return self.marker_target()

    def run(self):
        self.run_stage()
        self.output().dump("done\n", formatter="text")
