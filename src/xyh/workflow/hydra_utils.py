"""Helpers to use the Hydra configuration from outside of a Hydra application.

The workflow tasks do not define their own parameters. Instead, they compose
the same config that the shape_processor CLI would see and derive output paths
and branch maps from it.
"""

import subprocess
import sys
from collections.abc import Sequence
from typing import Any

from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf

from xyh import ROOT_DIR

CONFIG_DIR = ROOT_DIR / "hydra_config"


def compose_cfg(config_name: str, overrides: Sequence[str] = ()) -> DictConfig:
    """Compose a stage config with the given Hydra overrides.

    Parameters
    ----------
    config_name : str
        Name of the stage config (without the ``.yaml`` extension).
    overrides : Sequence[str]
        Hydra override strings, as they would be passed on the command line.

    Returns
    -------
    DictConfig
        The composed config without the ``hydra`` node.
    """
    # `compose` needs a clean global state, e.g. when called repeatedly or
    # after a `hydra.main` run in the same process.
    GlobalHydra.instance().clear()
    with initialize_config_dir(
        config_dir=str(CONFIG_DIR), version_base=None, job_name="workflow"
    ):
        return compose(config_name=config_name, overrides=list(overrides))


def resolve_cfg(cfg: DictConfig) -> dict[str, Any]:
    """Resolve all interpolations of a composed config into a plain dict."""
    container = OmegaConf.to_container(cfg, resolve=True)
    assert isinstance(container, dict)
    return container  # pyright: ignore[reportReturnType]


def stage_command(module: str, overrides: Sequence[str] = ()) -> list[str]:
    """Build the command line that runs a shape_processor stage."""
    return [sys.executable, "-m", f"xyh.shape_processor.{module}", *overrides]


def run_stage(module: str, overrides: Sequence[str] = ()) -> None:
    """Run a shape_processor stage as a subprocess from the repository root.

    Running the stage as a normal Hydra application keeps all Hydra features
    (run directory, ``env_set``, config snapshot) identical to a manual run.
    """
    subprocess.run(stage_command(module, overrides), cwd=ROOT_DIR, check=True)
