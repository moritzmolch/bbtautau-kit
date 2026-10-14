"""Base class for workflow tasks that wrap shape_processor stages.

Tasks have no parameters of their own beyond ``overrides``. All configuration
(tags, campaigns, paths, ...) lives in the Hydra config, which the task
composes to derive its outputs.
"""

import shlex
from collections.abc import Sequence
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar

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

    # Overrides forced by the task, e.g. `graph_processing.mode=snapshot`.
    # They take precedence over user overrides of the same key.
    forced_overrides: ClassVar[dict[str, str]] = {}

    # Name of the completion marker, defaults to the stage name
    marker_name: ClassVar[str | None] = None

    # Whether the task derives the data-driven Z corrections. Such a task
    # always runs in the production the corrections are derived from.
    derives_z_corrections: ClassVar[bool] = False

    @staticmethod
    def _merge_overrides(
        overrides: Sequence[str], forced: Sequence[str]
    ) -> list[str]:
        """Append forced overrides, which replace overrides of the same key."""
        keys = {o.split("=", 1)[0] for o in forced}
        return [
            *(o for o in overrides if o.split("=", 1)[0] not in keys),
            *forced,
        ]

    @cached_property
    def user_cfg(self) -> DictConfig:
        """The stage config composed from the user overrides only."""
        return compose_cfg(self.stage, shlex.split(self.overrides))

    @cached_property
    def z_corrections_tag(self) -> str:
        """Tag of the production the Z corrections are taken from."""
        tag = OmegaConf.select(self.user_cfg, "z_pt_weights.tag")
        return tag or OmegaConf.select(
            self.user_cfg, "tags.shapes_tag", throw_on_missing=True
        )

    @property
    def applies_z_corrections(self) -> bool:
        """Whether the task's production uses corrections from another one."""
        return (
            not self.derives_z_corrections
            and self.z_corrections_tag
            != OmegaConf.select(self.user_cfg, "tags.shapes_tag")
        )

    @cached_property
    def derivation_overrides(self) -> list[str]:
        """Overrides of the production the Z corrections are derived from.

        These are the user overrides, replaced by the overrides configured in
        `z_pt_weights.overrides` and by the tag of the derivation production.
        No corrections are applied in the derivation production.
        """
        configured = list(
            OmegaConf.select(self.user_cfg, "z_pt_weights.overrides") or []
        )
        tag = self.z_corrections_tag
        return self._merge_overrides(
            self._merge_overrides(
                [
                    o
                    for o in shlex.split(self.overrides)
                    if o.split("=", 1)[0] != "z_pt_weights.input_dir"
                ],
                configured,
            ),
            [f"tags.shapes_tag={tag}", f"z_pt_weights.tag={tag}"],
        )

    @cached_property
    def z_corrections_dir(self) -> str:
        """Directory with the correctionlib files of the Z corrections."""
        cfg = compose_cfg("derive_z_pt_weights", self.derivation_overrides)
        return str(
            ROOT_DIR / OmegaConf.select(cfg, "artifacts.z_pt_weights_dir")
        )

    @property
    def override_list(self) -> list[str]:
        """User overrides followed by the overrides forced by the task."""
        forced = [f"{k}={v}" for k, v in self.forced_overrides.items()]
        if self.derives_z_corrections:
            # Always run in the derivation production
            return self._merge_overrides(self.derivation_overrides, forced)
        if self.applies_z_corrections:
            forced.append(f"z_pt_weights.input_dir={self.z_corrections_dir}")
        return self._merge_overrides(shlex.split(self.overrides), forced)

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
                ROOT_DIR
                / specs_dir.parent
                / ".workflow"
                / f"{self.marker_name or self.stage}.done"
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
