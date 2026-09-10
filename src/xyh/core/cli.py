from collections.abc import Callable
from typing import Any

import hydra
from omegaconf import DictConfig

from xyh import ROOT_DIR


def hydra_cli(config_name: str) -> Callable[[], None]:
    """Decorate a function as a Hydra CLI entry point.

    Parameters
    ----------
    config_name : str
        Name of the entry-point-specific config group (without the ``.yaml``
        extension).

    Returns
    -------
    Callable
        A decorator that wraps `fn(cfg: DictConfig)` with `@hydra.main`.
    """

    def decorator(fn: Callable[[DictConfig], None]) -> Callable[[], None]:
        @hydra.main(
            config_path=str(ROOT_DIR / "hydra_config"),
            config_name=config_name,
            version_base=None,
        )
        def wrapper(cfg: DictConfig) -> Any:
            # The entry-point-specific group is merged into the top level of
            # the composed config, so no extra lookup is needed here.
            return fn(cfg)

        return wrapper

    return decorator
