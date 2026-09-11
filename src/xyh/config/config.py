from functools import partial

from order import Analysis, Campaign

from xyh.config.channels import channels
from xyh.config.process_datasets_map import get_process_datasets_map
from xyh.config.variables import get_variables


def create_xyh_bbtautau_config(
    analysis_inst: Analysis,
    campaign_inst: Campaign,
):
    # Create the config
    config_inst = analysis_inst.add_config(campaign_inst)

    # Add channels and categories to the config
    for channel_inst in channels.values():
        config_inst.add_channel(channel_inst)
        for category_inst in channel_inst.categories.values():
            config_inst.add_category(category_inst)

    # Add datasets to the config
    for dataset_inst in campaign_inst.datasets.values():
        config_inst.add_dataset(dataset_inst)

    # Functions to get a list of variables for a given category
    config_inst.set_aux("get_variables", get_variables)

    # Function to create the process-datasets map for a single campaign and
    # channel
    config_inst.set_aux(
        "get_process_datasets_map",
        partial(get_process_datasets_map, campaign_inst),
    )
