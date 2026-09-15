import logging
from itertools import groupby

import ROOT

from xyh.core.config import load_inventory

logger = logging.getLogger(__name__)


def add_histograms(histograms: list[ROOT.TH1]) -> ROOT.TH1:
    # Raise exception if no histograms are provided
    if len(histograms) == 0:
        raise ValueError("No histograms to add")

    # Iterate over the histograms, take the first one as the base to clone
    hist_iter = iter(histograms)
    hist_added = next(hist_iter).Clone()
    for hist in hist_iter:
        hist_added.Add(hist)

    return hist_added


def merge_histograms(
    inventory_factory_fn_path,
    graph_specs,
    histograms_dir,
    output_dir,
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
        process_insts = inventory.processes
        process_datasets_map = inventory.process_datasets_map

        def key_fn_category_variable(x):
            return (x["category"], x["variable"])

        for (category, variable), nodes_category_variable in groupby(
            sorted(nodes_campaign_channel, key=key_fn_category_variable),
            key=key_fn_category_variable,
        ):
            # Get the category and channel instances
            category_inst = channel_inst.get_category(category)
            variable_inst = inventory.variables.get(variable)
            logger.info(
                "\n".join(
                    [
                        "Merge histograms for",
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

            # Go through processes in the process-dataset map and merge
            # histograms with the same process
            for process, datasets in process_datasets_map.items():
                # Skip processes without any datasets (e.g., data-driven
                # background processes)
                if len(datasets) == 0:
                    continue

                # Get the process instance
                process_inst = process_insts.get(process)
                logging.info(f"Handle process {process_inst.name}")

                # Skip signals that are not relevant for classifier categories
                # if (
                #     category_inst.has_tag("clf")
                #     and process_inst.get_aux("is_signal", False)
                #     and not (
                #         process_inst.x.y_decay_mode
                #         == category_inst.x.y_decay_mode
                #         and process_inst.x.h_decay_mode
                #         == category_inst.x.h_decay_mode
                #         and process_inst.x.m_x == category_inst.x.m_x
                #         and process_inst.x.m_y == category_inst.x.m_y
                #     )
                # ):
                #     continue
                # else:
                #     if process_inst.get_aux("is_signal", False):
                #         continue

                for variation in ["nominal"]:  # TODO extend
                    # Histograms to be summed together
                    hists = []

                    # if process_inst.name == "jetfakes":  # TODO more generic
                    #     input_file = (
                    #         histograms_dir
                    #         / campaign
                    #         / f"{channel_inst.name}__{category}"
                    #         / f"{process_inst.name}__{process_inst.name}__{name}__{variation}.root"
                    #     )
                    #     rf = ROOT.TFile.Open(str(input_file), "READ")
                    #     hists.append(rf.Get(name))
                    #     rf.Close()

                    # else:

                    for dataset in datasets:
                        # Get the node spec for this configuration
                        node_spec = nodes_lookup[
                            (
                                process,
                                dataset,
                                variation,
                            )
                        ]

                        # Construct input file path and obtain the histogram
                        input_file = histograms_dir / node_spec["output_file"]
                        rf = ROOT.TFile.Open(str(input_file), "READ")
                        hists.append(rf.Get(variable))
                        rf.Close()

                    # Add the histograms and add them to the output dictionary
                    histograms[(process, variation)] = add_histograms(hists)

            # Construct output file path and create the directory if it does not
            # exist
            output_file = (
                output_dir
                / campaign
                / f"{channel_inst.name}__{category}"
                / f"{variable}.root"
            )
            if not output_file.parent.exists():
                output_file.parent.mkdir(parents=True)
                logging.info(f"Created directory {output_file.parent}")

            # Create new ROOT file and write histograms to it
            rf = ROOT.TFile(str(output_file), "RECREATE")
            for (process, variation), hist in histograms.items():
                dir_name = (
                    f"{campaign}/{channel_inst.name}/{category}/{process}"
                )
                directory = rf.GetDirectory(dir_name)
                if not directory:
                    directory = rf.mkdir(dir_name)
                hist_name = f"{variable}__{variation}"
                hist.SetName(hist_name)
                hist.SetTitle(hist_name)
                directory.WriteObject(hist, hist.GetName())
            rf.Close()
            logging.info(f"Wrote merged histograms to {output_file}")
