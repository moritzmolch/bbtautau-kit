import itertools
import logging

from xyh.core.analysis_config import load_analysis_inst
from xyh.core.specs.specs import FiltersAndWeights

# TODO Dynamically load selection
from xyh.filters import default as default_filters
from xyh.weights import default as default_weights


def create_filters_and_weights_spec(
    analysis_inst,
    config_inst,
    campaign_inst,
    channel_inst,
    category_inst,
    dataset_inst,
    process_inst,
):
    # Create the filter and weight classes
    filters_wrapper = default_filters(
        analysis_inst=analysis_inst,
        config_inst=config_inst,
        campaign_inst=campaign_inst,
        channel_inst=channel_inst,
        category_inst=category_inst,
        dataset_inst=dataset_inst,
        process_inst=process_inst,
    )
    weights_wrapper = default_weights(
        analysis_inst=analysis_inst,
        config_inst=config_inst,
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
    campaigns: list[str],
    categories: list[str],
):
    # Load the analysis instance
    analysis_inst = load_analysis_inst(analysis)

    # Container of  filters and weights specs for each context
    filters_and_weights_specs = []

    for campaign, category in itertools.product(campaigns, categories):
        # Get the configuration, category and channel instances
        config_inst = analysis_inst.get_config(campaign)
        category_inst = config_inst.get_category(category)
        channel_inst = category_inst.channel

        # Get the process-datasets map from the analysis configuration for the
        # given channel
        process_datasets_map = config_inst.x.get_process_datasets_map(
            channel_inst
        )

        # Iterate through all processes and datasets
        for process, datasets in process_datasets_map.items():
            # Load the process instance
            process_inst = config_inst.get_process(process)

            # Iterate through datasets associated with the process
            for dataset in datasets:
                # Load the dataset instance
                dataset_inst = config_inst.get_dataset(dataset)

                # Create the selection and weight specs and append them to the
                # global list
                logging.info(
                    "\n".join(
                        [
                            "Creating selection specs for",
                            f"    campaign: {config_inst.campaign.name}",
                            f"    channel:  {channel_inst.name}",
                            f"    category: {category_inst.name}",
                            f"    dataset:  {dataset_inst.name}",
                            f"    process:  {process_inst.name}",
                        ],
                    ),
                )
                filters_and_weights_specs.append(
                    create_filters_and_weights_spec(
                        analysis_inst,
                        config_inst,
                        config_inst.campaign,
                        channel_inst,
                        category_inst,
                        dataset_inst,
                        process_inst,
                    )
                )

    return filters_and_weights_specs
