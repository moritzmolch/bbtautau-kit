from dataclasses import dataclass

from order import Campaign, Channel, UniqueObjectIndex

from xyh.config.process_datasets_map import get_process_datasets_map
from xyh.config.processes import processes
from xyh.config.profiles import get_profile
from xyh.config.variables import get_variables


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


def create_inventory(
    campaign_inst: Campaign,
    channel_inst: Channel,
) -> Inventory:
    """
    Create an inventory of analysis objects for a given campaign and channel.

    Parameters
    ----------
    campaign_inst : Campaign
        The campaign for which to create the inventory.

    channel_inst : Channel
        The channel for which to create the inventory.

    Returns
    -------
    Inventory
        The inventory of analysis objects for the given campaign and channel.
    """

    # Remove signal processes that are not present in the current campaign
    process_insts = processes.copy()
    for (y_decay_mode, h_decay_mode), (
        m_x,
        m_y,
    ) in get_profile().iterate_signal_parameters(campaign=campaign_inst.name):
        process_insts.remove(
            f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}"
        )

    # Get variable index for this channel
    variable_insts = get_variables(channel_inst)

    # Create the process-datasets map for this campaign and channel
    process_datasets_map = get_process_datasets_map(
        campaign_inst,
        channel_inst,
    )

    # Create the inventory
    inventory = Inventory(
        campaign=campaign_inst,
        channel=channel_inst,
        processes=process_insts,
        variables=variable_insts,
        process_datasets_map=process_datasets_map,
    )

    return inventory
