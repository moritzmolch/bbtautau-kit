from dataclasses import dataclass

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
