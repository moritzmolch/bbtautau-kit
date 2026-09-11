import itertools
import logging

from xyh.core.config import load_inventory
from xyh.core.specs.specs import FiltersAndWeights

# TODO Dynamically load selection
from xyh.filters import default_filters
from xyh.weights import default_weights


def create_filters_and_weights_spec(
    campaign_inst,
    channel_inst,
    category_inst,
    dataset_inst,
    process_inst,
):
    # Create the filter and weight classes
    filters_wrapper = default_filters(
        campaign_inst=campaign_inst,
        channel_inst=channel_inst,
        category_inst=category_inst,
        dataset_inst=dataset_inst,
        process_inst=process_inst,
    )
    weights_wrapper = default_weights(
        campaign_inst=campaign_inst,
        channel_inst=channel_inst,
        category_inst=category_inst,
        dataset_inst=dataset_inst,
        process_inst=process_inst,
    )

    # Get the filter and weight expression dictionaries
    filters = filters_wrapper()
    weights = weights_wrapper()

    # Create the selection and weight specs and append them to the
    # global list
    logging.info(
        "\n".join(
            [
                "Created filters and weights",
                f"    filters:    {filters}",
                f"    weights:    {weights}",
            ],
        ),
    )

    # Create the spec object
    filters_and_weights_spec = FiltersAndWeights(
        campaign=campaign_inst.name,
        channel=channel_inst.name,
        category=category_inst.name,
        process=process_inst.name,
        dataset=dataset_inst.name,
        filters=filters,
        weights=weights,
    )

    return filters_and_weights_spec


def create_filters_and_weights_specs(
    inventory_factory_fn_path: str,
    campaigns: list[str],
    channels: list[str],
    categories: list[str],
):
    # Container of  filters and weights specs for each context
    filters_and_weights_specs = []

    for campaign, channel in itertools.product(campaigns, channels):
        # Load the analysis inventory for this campaign and channel
        inventory = load_inventory(
            inventory_factory_fn_path,
            campaign,
            channel,
        )

        # Get analysis config objects
        campaign_inst = inventory.campaign
        channel_inst = inventory.channel
        process_insts = inventory.processes
        process_datasets_map = inventory.process_datasets_map

        # Iterate through categories of this channel
        for category_inst in (
            channel_inst.get_category(c)
            for c in categories
            if channel_inst.has_category(c)
        ):
            # Iterate through all processes and datasets
            for process, datasets in process_datasets_map.items():
                # Load the process instance
                process_inst = process_insts.get(process)

                # Iterate through datasets associated with the process
                for dataset in datasets:
                    # Load the dataset instance
                    dataset_inst = campaign_inst.datasets.get(dataset)

                    # Create the selection and weight specs and append them to the
                    # global list
                    logging.info(
                        "\n".join(
                            [
                                "Creating selection specs for",
                                f"    campaign: {campaign_inst.name}",
                                f"    channel:  {channel_inst.name}",
                                f"    category: {category_inst.name}",
                                f"    dataset:  {dataset_inst.name}",
                                f"    process:  {process_inst.name}",
                            ],
                        ),
                    )
                    filters_and_weights_specs.append(
                        create_filters_and_weights_spec(
                            campaign_inst,
                            channel_inst,
                            category_inst,
                            dataset_inst,
                            process_inst,
                        )
                    )

    return filters_and_weights_specs
