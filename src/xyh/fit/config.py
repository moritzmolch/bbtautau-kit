"""Helpers to read the ``fit`` section of the Hydra config."""

from typing import Any

from omegaconf import OmegaConf


def as_list(value: Any) -> list[Any] | None:
    """Convert an OmegaConf list or a scalar to a list (`None` stays)."""
    if value is None:
        return None
    if OmegaConf.is_config(value):
        value = OmegaConf.to_container(value)
    return value if isinstance(value, list) else [value]
