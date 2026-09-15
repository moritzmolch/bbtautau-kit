import logging
from itertools import chain, groupby
from pathlib import Path

import ROOT

from xyh.core.config import load_inventory
from xyh.core.config.util import gen_dataset_insts
from xyh.core.histograms.util import add_histograms

logger = logging.getLogger(__name__)


def run_fake_factor_histograms(
    inventory_factory_fn_path: str,
    graph_specs: dict,
    histograms_dir: Path,
    output_dir: Path,
):
    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    # Filter specs of all histogram nodes from graph processing
    graph_histogram_nodes = [
        node["spec"]
        for node in graph_specs["nodes"]
        if node["type"] == "HistogramNode"
    ]

    def key_fn_campaign_channel(x):
        return (x["campaign"], x["channel"])

    for (campaign, channel), nodes_campaign_channel in groupby(
        sorted(graph_histogram_nodes, key=key_fn_campaign_channel),
        key=key_fn_campaign_channel,
    ):
        # Load the analysis inventory for this campaign and channel
        inventory = load_inventory(
            inventory_factory_fn_path,
            campaign,
            channel,
        )

        # Get analysis config objects
        campaign_inst = inventory.campaign
        channel_inst = inventory.channel
        process_set = inventory.process_set

        def key_fn_category_variable(x):
            return (x["category"], x["variable"])

        for (category, variable), nodes_category_variable in groupby(
            sorted(nodes_campaign_channel, key=key_fn_category_variable),
            key=key_fn_category_variable,
        ):
            # Get the category and channel instances
            category_inst = channel_inst.get_category(category)
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

            # Make a persistent list of nodes and create a lookup table to be
            # able to conveniently find histograms for a process, dataset, and
            # variation
            nodes_lookup = {
                (n["process"], n["dataset"], n["variation"]): n
                for n in list(nodes_category_variable)
            }

            # Load histograms of data and background processes
            histograms = {}

            # Get data and background processes
            data_processes = list(
                chain.from_iterable(p.processes for p in process_set.data)
            )
            bkg_processes = list(
                chain.from_iterable(
                    p.processes
                    for p in process_set.backgrounds
                    if p.name != "jetfakes"
                )
            )

            # Get the jet fakes process
            jetfakes_processes = [
                p
                for s in process_set.backgrounds
                for p in s.processes
                if p == "jetfakes"
            ]
            if not len(jetfakes_processes) == 1:
                raise RuntimeError(
                    "Number of jet fakes processes is different from 1"
                )
            jetfakes_process_inst = inventory.processes.get(
                jetfakes_processes[0]
            )

            logger.debug(
                "\n".join(
                    [
                        "Consider process classes",
                        f"    data:       {data_processes}",
                        f"    background: {bkg_processes}",
                        f"    jet fakes:  {jetfakes_process_inst.name}",
                    ],
                ),
            )

            # Get histograms needed for the fake factor background estimation.
            # The dictionary keys in `histograms` are `True` for data processes
            # and `False` for background processes.
            histograms = {}
            for process in data_processes + bkg_processes:
                for dataset_inst in gen_dataset_insts(
                    inventory, process=process
                ):
                    # Get the node spec for this configuration
                    node_spec = nodes_lookup[
                        (process, dataset_inst.name, "fake_factors")
                    ]

                    # Construct input file path and obtain the histogram
                    input_file = histograms_dir / node_spec["output_file"]
                    rf = ROOT.TFile.Open(str(input_file), "READ")
                    histograms.setdefault(process in data_processes, []).append(
                        rf.Get(node_spec["variable"])
                    )
                    rf.Close()

            # Add data and background histograms separately, then subtract
            # backgrounds from data
            hist_data = add_histograms(histograms[True])
            hist_bkg = add_histograms(histograms[False])

            # Subtract fake factor-weighted backgrounds from fake
            # factor-weighted data in application region and rename the
            # histogram to the jet fakes process name
            name = f"{variable_inst.name}"
            hist_fake_factor = hist_data.Clone()
            hist_fake_factor.Add(hist_bkg, -1)
            hist_fake_factor.SetName(name)
            hist_fake_factor.SetTitle(name)

            # Construct output file path and create the directory if it does not
            # exist
            output_file = (
                output_dir
                / campaign
                / f"{channel_inst.name}__{category_inst.name}"
                / f"{jetfakes_process_inst.name}__{jetfakes_process_inst.name}__{variable_inst.name}__nominal.root"
            )
            if not output_file.parent.exists():
                output_file.parent.mkdir(parents=True)
                logger.debug(f"Created directory {output_file.parent}")

            # Dump the histogram to the output file
            rf = ROOT.TFile.Open(str(output_file), "RECREATE")
            hist_fake_factor.Write()
            rf.Close()
            logger.info(f"Wrote fake factor histogram to {output_file}")
