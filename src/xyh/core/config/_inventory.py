from dataclasses import dataclass
from importlib import import_module

from order import Campaign, Channel, UniqueObjectIndex

from ._process_set import ProcessSet


@dataclass
class Inventory:
    """
    Inventory of analysis objects for a given campaign and channel.
    """

    campaign: Campaign
    channel: Channel
    processes: UniqueObjectIndex  # UniqueObjectIndex[Process]
    variables: UniqueObjectIndex  # UniqueObjectIndex[Variable]
    process_datasets_map: dict[str, list[str]]
    process_set: ProcessSet


def load_inventory(
    factory_fn_path: str,
    campaign: str,
    channel: str,
) -> Inventory:
    """
    Load the inventory of analysis objects for a given campaign and channel.

    The factory function specified by `factory_fn_path` is expected to take
    a campaign and a channel name as arguments and to return an `Inventory`
    object.

    Parameters
    ----------
    factory_fn_path : str
        Python module path to the factory function that creates the inventory.

    campaign : str
        The campaign for which to load the inventory.

    channel : str
        The channel for which to load the inventory.

    Returns
    -------
    Inventory
        The inventory of analysis objects.
    """

    # Import the factory function
    parts = factory_fn_path.split(".")
    module_str, inst_str = ".".join(parts[:-1]), parts[-1]
    module_str = import_module(module_str)
    factory_fn = getattr(module_str, inst_str)

    # Execute the inventory factory function to get the inventory
    inventory = factory_fn(campaign, channel)

    return inventory
