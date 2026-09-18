import itertools
import logging
from typing import Any

from xyh.core.config import load_inventory
from xyh.core.config.util import gen_process_and_dataset_insts
from xyh.core.specs.specs import FiltersAndWeights
from xyh.filters import default_filters_without_bjets  # TODO load dynamically
from xyh.variations import default_variations  # TODO load dynamically
from xyh.weights import (
    default_weights as default_weights,  # TODO load dynamically
)
from xyh.weights import (
    default_weights_without_bjet_weights as default_weights_without_bjet_weights,  # TODO load dynamically
)

# Set up logger for this module
logger = logging.getLogger(__name__)


def create_filters_and_weights_spec(
    campaign_inst,
    channel_inst,
    category_inst,
    dataset_inst,
    process_inst,
):
    # List of all specs for this context
    filters_and_weights_specs = []

    # Create the filter and weight classes
    filters_class = default_filters_without_bjets(
        campaign_inst=campaign_inst,
        channel_inst=channel_inst,
        category_inst=category_inst,
        dataset_inst=dataset_inst,
        process_inst=process_inst,
    )
    weights_class = default_weights(
        campaign_inst=campaign_inst,
        channel_inst=channel_inst,
        category_inst=category_inst,
        dataset_inst=dataset_inst,
        process_inst=process_inst,
    )

    # Get the nominal filter and weight expression dictionaries
    filters = filters_class.nominal()
    weights = weights_class.nominal()

    # Create the selection and weight specs and append them to the
    # global list
    logger.debug(
        "\n".join(
            [
                "Created filters and weights",
                f"    filters:    {filters}",
                f"    weights:    {weights}",
            ],
        ),
    )

    # Shared arguments between all variations
    shared_kwargs = {
        "campaign": campaign_inst.name,
        "channel": channel_inst.name,
        "category": category_inst.name,
        "process": process_inst.name,
        "dataset": dataset_inst.name,
    }

    # Add nominal specs
    filters_and_weights_specs.append(
        FiltersAndWeights(
            **shared_kwargs,
            variation="nominal",
            filters=filters,
            weights=weights,
        )
    )

    for variation_class in default_variations:
        # Create the variation object for this context
        variation = variation_class(
            campaign_inst=campaign_inst,
            channel_inst=channel_inst,
            category_inst=category_inst,
            dataset_inst=dataset_inst,
            process_inst=process_inst,
        )

        # Check if this variation is applicable for this context
        if variation.skip():
            logger.debug(
                f"Skipping variation {variation.name} for this context"
            )
            continue

        # Create varied filter and weight expressions
        varied_filters, varied_weights = variation.apply(filters, weights)

        # Add the varied specs to the global list
        filters_and_weights_specs.append(
            FiltersAndWeights(
                **shared_kwargs,
                variation=variation.name,
                filters=varied_filters,
                weights=varied_weights,
            )
        )

    return filters_and_weights_specs


def create_filters_and_weights_specs(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict[str, Any],
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
            **inventory_factory_kwargs,
        )

        # Get analysis config objects
        campaign_inst = inventory.campaign
        channel_inst = inventory.channel

        # Iterate through categories of this channel
        for category_inst in (
            channel_inst.get_category(c)
            for c in categories
            if channel_inst.has_category(c)
        ):
            # Create the selection and weight specs and append them to the
            # global list
            logger.debug(
                "\n".join(
                    [
                        "Creating selection specs for",
                        f"    campaign: {campaign_inst.name}",
                        f"    channel:  {channel_inst.name}",
                        f"    category: {category_inst.name}",
                    ],
                ),
            )

            # List of all specs for this context
            filters_and_weights_specs_category = []

            # Iterate through all processes and datasets of a process set
            for process_inst, dataset_inst in gen_process_and_dataset_insts(
                inventory
            ):
                filters_and_weights_specs_category.extend(
                    create_filters_and_weights_spec(
                        campaign_inst,
                        channel_inst,
                        category_inst,
                        dataset_inst,
                        process_inst,
                    )
                )
            filters_and_weights_specs.extend(filters_and_weights_specs_category)

        logger.info(
            f"Added {len(filters_and_weights_specs_category)} filters and "
            + "weights specs"
        )

    return filters_and_weights_specs
