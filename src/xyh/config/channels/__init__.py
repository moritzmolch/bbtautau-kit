"""
Channels and categories the analysis is split into.
"""

import importlib
from functools import cache

from order import Channel, UniqueObjectIndex


@cache
def load_channel(channel_name: str) -> Channel:
    """
    Load a channel instance based on the provided channel name.

    Parameters
    ----------
    channel_name : str
        The name of the channel to load.

    Raises
    ------
    ValueError
        If the channel instance cannot be found or loaded.
    """
    try:
        # Import the channel module dynamically based on the provided channel name
        module = importlib.import_module(".channels", __package__)
        channel_inst = getattr(module, channel_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Channel '{channel_name}' not found.") from e
    return channel_inst


@cache
def channels() -> UniqueObjectIndex:
    """
    Return a UniqueObjectIndex containing all available channels.

    Returns
    -------
    UniqueObjectIndex
        A UniqueObjectIndex of all available `Channel` objects.
    """
    return UniqueObjectIndex(
        Channel,
        [
            load_channel(channel_name)
            for channel_name in [
                "ch_et",
                "ch_mt",
                "ch_tt",
                "ch_em",
                "ch_ee",
                "ch_mm",
            ]
        ],
    )
