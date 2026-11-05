import logging
from itertools import product
from pathlib import Path
from typing import Any

import ROOT

from xyh.core.config import load_inventory
from xyh.core.config.util import (
    gen_dataset_insts,
    gen_process_insts,
    skip_process_in_category,
)
from xyh.core.histograms.util import (
    add_histograms,
    filter_histograms,
    get_histogram,
    load_all,
)
from xyh.core.specs.binning import _parse_variable_name

# TODO make this more generic
from xyh.variations import default_variations

# Set up logging
logger = logging.getLogger(__name__)


def merge_histograms(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict[str, Any],
    campaigns: list[str],
    channels: list[str],
    categories: list[str],
    variables: list[str],
    histograms_dir: Path,
    output_file: Path,
):
    # Load all histograms
    histograms = load_all(
        histograms_dir / "histogram_keys.json.gz",
        histograms_dir,
    )

    # Store for the output histograms
    histograms_output = {}

    for campaign, channel in product(campaigns, channels):
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

        for category in (c for c in categories if channel_inst.has_category(c)):
            # Get the category instance for this channel and category
            category_inst = channel_inst.get_category(category)
            for variable_arg in variables:
                # Parse the variable name to extract the 'pure' name and the
                # channels the variable is restricted to (if any)
                variable, variable_channels = _parse_variable_name(variable_arg)
                if (
                    variable_channels is not None
                    and channel_inst.name not in variable_channels
                ):
                    logger.debug(
                        f"Skipping variable {variable} in channel "
                        + channel_inst.name
                    )
                    continue

                # Get the variable instance
                variable_inst = inventory.variables.get(variable)

                logger.debug(
                    "\n".join(
                        [
                            "Process histograms for",
                            f"    campaign:  {campaign_inst.name}",
                            f"    channel:   {channel_inst.name}",
                            f"    category:  {category_inst.name}",
                            f"    variable:  {variable_inst.name}",
                        ],
                    ),
                )

                # Get the input histograms for this variable
                histograms_variable = list(
                    filter_histograms(
                        histograms,
                        campaign=campaign,
                        channel=channel,
                        category=category,
                        variable=variable,
                    )
                )

                for process_inst in gen_process_insts(inventory):
                    # Skip processes that are not relevant for this category,
                    # e.g. signals of other mass points in classifier categories
                    if skip_process_in_category(category_inst, process_inst):
                        continue

                    for variation_class in ["nominal"] + default_variations:
                        # Get information from the variation
                        variation_name = "nominal"
                        if not isinstance(variation_class, str):
                            variation = variation_class(
                                campaign_inst=campaign_inst,
                                channel_inst=channel_inst,
                                category_inst=category_inst,
                                process_inst=process_inst,
                            )
                            variation_name = variation_class.name

                            # Check if this process is skipped
                            if variation.skip():
                                continue

                        # Declare variable for merged histogram
                        hist = None

                        # Handle jetfakes histograms
                        # TODO needs to be done more generic
                        if process_inst.name == "jetfakes":  # TODO more generic
                            hist = get_histogram(
                                histograms_variable,
                                campaign=campaign,
                                channel=channel,
                                category=category,
                                variable=variable,
                                process=process_inst.name,
                                dataset=process_inst.name,
                                variation=variation_name,
                            ).histogram

                        else:
                            # For usual processes, get histograms of all
                            # datasets and add them together
                            to_sum = []
                            for dataset_inst in gen_dataset_insts(
                                inventory, process=process_inst
                            ):
                                to_sum.append(
                                    get_histogram(
                                        histograms_variable,
                                        campaign=campaign,
                                        channel=channel,
                                        category=category,
                                        variable=variable,
                                        process=process_inst.name,
                                        dataset=dataset_inst.name,
                                        variation=variation_name,
                                    )
                                )

                            # Get the summed histogram
                            hist = add_histograms([h.histogram for h in to_sum])

                        # Set canonical histogram name and put output
                        # histogram into global dictionary for later use
                        key = "/".join(
                            (
                                campaign,
                                channel,
                                category,
                                process_inst.name,
                                f"{variable_inst.name}__{variation_name}",
                            )
                        )
                        histograms_output[key] = hist

    # Put all histograms into a single output file
    parent_dir = output_file.parent
    if not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory {parent_dir}")

    # Dump the histogram to the output file
    root_file = ROOT.TFile.Open(str(output_file), "RECREATE")
    for key, hist in histograms_output.items():
        # Split key into parts
        key_parts = key.split("/")

        # Set the histogram directory and move to this directory
        dir_name = "/".join(key_parts[:-1])
        directory = root_file.GetDirectory(dir_name)
        if not directory:
            directory = root_file.mkdir(dir_name)
        directory.cd()

        # Set the histogram name and title
        hist_name = key_parts[-1]
        hist.SetName(hist_name)
        hist.SetTitle(hist_name)

        # Write the histogram
        hist.Write()

    root_file.Close()
    logger.info(f"Wrote merged histograms to {output_file}")
