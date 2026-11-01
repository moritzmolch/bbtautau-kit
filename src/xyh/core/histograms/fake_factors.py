import hashlib
import json
import logging
from itertools import chain, product
from pathlib import Path
from typing import Any

import ROOT

from xyh.core.config import load_inventory
from xyh.core.config.util import gen_dataset_insts
from xyh.core.histograms.util import (
    add_histograms,
    filter_histograms,
    get_histogram,
    load_all,
)
from xyh.core.io import dump_json, load_json

logger = logging.getLogger(__name__)


def run_fake_factor_histograms(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict[str, Any],
    campaigns: list[str],
    channels: list[str],
    categories: list[str],
    variables: list[str],
    histograms_dir: Path,
):
    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

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
        process_set = inventory.process_set

        # Get the jet fakes process
        jetfakes_processes = [
            p
            for s in process_set.backgrounds
            for p in s.processes
            if p == "jetfakes"
        ]
        if len(jetfakes_processes) == 0:
            logger.info(
                f"Skip campaign {campaign}, channel {channel} because no jet "
                + "fakes process is defined"
            )
            continue
        elif len(jetfakes_processes) >= 2:
            raise RuntimeError(
                "More than one jet fakes process is defined in the inventory"
            )
        jetfakes_process_inst = inventory.processes.get(jetfakes_processes[0])

        # Get data and non-jet fake background processes to subtract
        data_processes = list(
            chain.from_iterable(p.processes for p in process_set.data)
        )
        non_jetfakes_processes = list(
            chain.from_iterable(
                p.processes
                for p in process_set.backgrounds
                if p.name != "jetfakes"
            )
        )

        # Log message with the processes used for fake factor histogram
        # production
        logger.debug(
            "\n".join(
                [
                    "Consider process classes for fake factor histogram production:",
                    f"    data:                     {data_processes}",
                    f"    non-jet fakes background: {non_jetfakes_processes}",
                    f"    jet fakes:                {jetfakes_process_inst.name}",
                ],
            ),
        )

        for category in (c for c in categories if channel_inst.has_category(c)):
            # Get the category instance for this channel and category
            category_inst = channel_inst.get_category(category)
            for variable in variables:
                # Get the variable instance
                variable_inst = inventory.variables.get(variable)

                logger.debug(
                    "\n".join(
                        [
                            "Produce fake factor histogram for",
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
                        variation="fake_factors",
                    )
                )

                # Sum the histograms for the data and the non-jet fakes backgrounds separately
                fake_factor_histograms = {}
                for domain, process_list in [
                    ("data", data_processes),
                    ("non_jetfakes", non_jetfakes_processes),
                ]:
                    # Get the histograms for the processes in this domain
                    to_sum = []
                    for process in process_list:
                        for dataset_inst in gen_dataset_insts(
                            inventory, process=process
                        ):
                            to_sum.append(
                                get_histogram(
                                    histograms_variable,
                                    campaign=campaign,
                                    channel=channel,
                                    category=category,
                                    variable=variable,
                                    process=process,
                                    dataset=dataset_inst.name,
                                    variation="fake_factors",
                                )
                            )

                    # Sum the histograms for this domain
                    fake_factor_histograms[domain] = add_histograms(
                        [h.histogram for h in to_sum]
                    )

                # Subtract fake factor-weighted backgrounds from fake
                # factor-weighted data in application region and rename the
                # histogram to the jet fakes process name
                hist_fake_factor = fake_factor_histograms["data"].Clone()
                hist_fake_factor.Add(fake_factor_histograms["non_jetfakes"], -1)

                # Set canonical histogram name and put output histogram into
                # global dictionary for later use
                key = "/".join(
                    (
                        campaign,
                        channel,
                        category,
                        jetfakes_process_inst.name,
                        jetfakes_process_inst.name,
                        f"{variable_inst.name}__nominal",
                    )
                )
                histograms_output[key] = hist_fake_factor

    # Construct output file path with a "pseudo-hash" based on the input
    # parameters
    jetfakes_hash = hashlib.sha256(
        json.dumps(sorted(histograms_output.keys())).encode()
    ).hexdigest()
    output_file = histograms_dir / f"histograms_{jetfakes_hash}.root"

    # Put all histograms into a single output file
    if not output_file.parent.exists():
        output_file.parent.mkdir(parents=True)
        logger.debug(f"Created directory {output_file.parent}")

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

        # Set the histogram name and title
        hist.Write()

    root_file.Close()
    logger.info(f"Wrote fake factor histogram to {output_file}")

    # Update histogram keys file
    histogram_keys_file = histograms_dir / "histogram_keys.json.gz"
    histogram_keys = load_json(histogram_keys_file)
    histogram_keys.update({output_file.name: sorted(histograms_output.keys())})
    dump_json(histogram_keys, histogram_keys_file)
    logger.info(f"Updated histogram keys file {histogram_keys_file}")
