import logging
from collections.abc import Generator
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import Any

import ROOT

from xyh.core.config import load_inventory
from xyh.core.config.util import gen_dataset_insts, gen_process_insts
from xyh.core.io import load_json
from xyh.core.parallel import run_in_parallel

# TODO make this more generic
from xyh.variations import default_variations

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TH1Wrapper:
    campaign: str
    channel: str
    category: str
    process: str
    dataset: str
    variable: str
    variation: str
    histogram: ROOT.TH1


def load_all(
    histogram_keys_file: Path, histograms_dir: Path
) -> list[TH1Wrapper]:
    """
    Load all histograms from graph output files of a production campaign.

    The function returns `TH1Wrapper` objects which contain the `TH1` histogram
    as well as associated metadata: campaign, channel, category, process,
    dataset, variable, and variation.

    Parameters
    ----------
    histogram_keys_file : Path
        Path to the JSON file containing the mapping of output files to
        histogram keys.

    histograms_dir : Path
        Path to the directory containing the output files of the production
        campaign.

    Returns
    -------
    list[TH1Wrapper]
        A list of `TH1Wrapper` objects.
    """

    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    # Load the histogram keys and corresponding files from the JSON file
    histogram_keys = load_json(histogram_keys_file)

    histograms = []

    for output_file, hist_keys in histogram_keys.items():
        # Construct the full path of the output file
        output_file_path = histograms_dir / output_file

        # Open the ROOT file and load all histograms
        rf = ROOT.TFile.Open(str(output_file_path), "READ")
        for hist_key in hist_keys:
            # Get the analysis context from the histogram key, which has the
            # form 'campaign/channel/category/process/dataset/variable__variation'
            key_parts = hist_key.split("/")
            if len(key_parts) != 6 or "__" not in key_parts[-1]:
                raise ValueError(
                    f"Histogram key {hist_key} in {output_file_path} does not "
                    + "match the pattern 'campaign/channel/category/process/"
                    + "dataset/variable__variation'"
                )
            campaign, channel, category, process, dataset, name = key_parts
            variable, variation = name.rsplit("__", 1)

            # Get the histogram
            hist = rf.Get(hist_key)
            if not hist:
                raise ValueError(
                    f"Histogram {hist_key} not found in {output_file_path}"
                )
            histograms.append(
                TH1Wrapper(
                    campaign=campaign,
                    channel=channel,
                    category=category,
                    process=process,
                    dataset=dataset,
                    variable=variable,
                    variation=variation,
                    histogram=hist,
                )
            )

        rf.Close()

    return histograms


def filter_histograms(
    histograms: list[TH1Wrapper],
    campaign: str | None = None,
    channel: str | None = None,
    category: str | None = None,
    process: str | None = None,
    dataset: str | None = None,
    variable: str | None = None,
    variation: str | None = None,
) -> Generator[TH1Wrapper, None, None]:
    """
    Filter a list of `TH1Wrapper` objects based on the provided criteria.

    Parameters
    ----------
    histograms : list[TH1Wrapper]
        The list of `TH1Wrapper` objects to filter.

    campaign : str | None, optional
        The campaign to filter by. If `None`, do not filter by campaign.

    channel : str | None, optional
        The channel to filter by. If `None`, do not filter by channel.

    category : str | None, optional
        The category to filter by. If `None`, do not filter by category.

    process : str | None, optional
        The process to filter by. If `None`, do not filter by process.

    dataset : str | None, optional
        The dataset to filter by. If `None`, do not filter by dataset.

    variable : str | None, optional
        The variable to filter by. If `None`, do not filter by variable.

    variation : str | None, optional
        The variation to filter by. If `None`, do not filter by variation.

    Yields
    ------
    TH1Wrapper
        The filtered `TH1Wrapper` objects.
    """
    # Compile list of criteria for filtering (interpreted as AND)
    criteria = {
        "campaign": campaign,
        "channel": channel,
        "category": category,
        "process": process,
        "dataset": dataset,
        "variable": variable,
        "variation": variation,
    }
    criteria = {k: v for k, v in criteria.items() if v is not None}

    for hist in histograms:
        if all(getattr(hist, k) == v for k, v in criteria.items()):
            yield hist


def get_histogram(
    histograms: list[TH1Wrapper],
    campaign: str,
    channel: str,
    category: str,
    process: str,
    dataset: str,
    variable: str,
    variation: str,
) -> TH1Wrapper:
    """
    Get a `TH1Wrapper` object based on the provided criteria.

    Parameters
    ----------
    histograms : list[TH1Wrapper]
        The list of `TH1Wrapper` objects to filter.

    campaign : str
        The campaign to filter by.

    channel : str | None, optional
        The channel to filter by.

    category : str | None, optional
        The category to filter by.

    process : str | None, optional
        The process to filter by.

    dataset : str | None, optional
        The dataset to filter by.

    variable : str | None, optional
        The variable to filter by.

    variation : str | None, optional
        The variation to filter by.

    Returns
    ------
    TH1Wrapper
        The filtered `TH1Wrapper` object.

    Raises
    ------
    ValueError
        If no matching histogram is found.
    """

    # Compile list of criteria for filtering (interpreted as AND)
    criteria = {
        "campaign": campaign,
        "channel": channel,
        "category": category,
        "process": process,
        "dataset": dataset,
        "variable": variable,
        "variation": variation,
    }

    # Get the histogram that matches the criteria
    for hist in histograms:
        if all(getattr(hist, k) == v for k, v in criteria.items()):
            return hist

    raise ValueError("No matching histogram found for the given criteria")


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


def _build_merge_tasks(
    graph_specs,
    inventory_factory_fn_path,
    histograms_dir,
    output_dir,
) -> list[dict[str, Any]]:
    """Split the histogram nodes into independent merge tasks.

    Each task merges the histograms of one campaign, channel, category, and
    variable combination into a single output file. All tasks are fully
    independent, so they can be processed in parallel.
    """
    # Filter specs of all histogram nodes from graph processing
    graph_histogram_nodes = [
        node["spec"]
        for node in graph_specs["nodes"]
        if node["type"] == "HistogramNode"
    ]

    def key_fn_campaign_channel(x):
        return (x["campaign"], x["channel"])

    def key_fn_category_variable(x):
        return (x["category"], x["variable"])

    tasks = []
    for (campaign, channel), nodes_campaign_channel in groupby(
        sorted(graph_histogram_nodes, key=key_fn_campaign_channel),
        key=key_fn_campaign_channel,
    ):
        for (category, variable), nodes_category_variable in groupby(
            sorted(nodes_campaign_channel, key=key_fn_category_variable),
            key=key_fn_category_variable,
        ):
            tasks.append(
                {
                    "inventory_factory_fn_path": inventory_factory_fn_path,
                    "histograms_dir": histograms_dir,
                    "output_dir": output_dir,
                    "campaign": campaign,
                    "channel": channel,
                    "category": category,
                    "variable": variable,
                    "nodes": list(nodes_category_variable),
                }
            )

    return tasks


def _merge_category_variable(task: dict[str, Any]) -> str:
    """Merge all histograms of one merge task into a single output file.

    The function is executed either in the current process or in a worker
    process of the pool. It must therefore be a picklable top-level function
    and must not depend on any state of the parent process.
    """
    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    # Load the analysis inventory for this campaign and channel
    inventory = load_inventory(
        task["inventory_factory_fn_path"],
        task["campaign"],
        task["channel"],
    )

    # Unpack the task information
    campaign = task["campaign"]
    category = task["category"]
    variable = task["variable"]
    nodes_category_variable = task["nodes"]
    histograms_dir = task["histograms_dir"]
    output_dir = task["output_dir"]

    # Get analysis config objects
    campaign_inst = inventory.campaign
    channel_inst = inventory.channel
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

    # Make a persistent list of nodes and create a lookup table to be able to
    # conveniently find histograms for a process, dataset, and variation
    nodes_lookup = {
        (n["process"], n["dataset"], n["variation"]): n
        for n in nodes_category_variable
    }

    # Load histograms of data and background processes
    histograms = {}

    # Iterate through all processes of a process set
    for process_inst in gen_process_insts(inventory):
        # TODO Skip signals that are not relevant for classifier categories
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

            # Histograms to be summed together
            hists = []

            if process_inst.name == "jetfakes":  # TODO more generic
                input_file = (
                    histograms_dir
                    / campaign
                    / f"{channel_inst.name}__{category_inst.name}"
                    / f"{process_inst.name}__{process_inst.name}__{variable}__{variation_name}.root"
                )
                rf = ROOT.TFile.Open(str(input_file), "READ")
                hists.append(rf.Get(variable))
                rf.Close()

            else:
                for dataset_inst in gen_dataset_insts(
                    inventory, process=process_inst
                ):
                    # Get the node spec for this configuration
                    node_spec = nodes_lookup[
                        (
                            process_inst.name,
                            dataset_inst.name,
                            variation_name,
                        )
                    ]

                    # Construct input file path and obtain the histogram
                    input_file = histograms_dir / node_spec["output_file"]
                    rf = ROOT.TFile.Open(str(input_file), "READ")
                    hists.append(rf.Get(node_spec.get("hist_path", variable)))
                    rf.Close()

            # Add the histograms and add them to the output dictionary
            histograms[(process_inst.name, variation_name)] = add_histograms(
                hists
            )

    # Construct output file path and create the directory if it does not exist
    output_file = (
        output_dir
        / campaign
        / f"{channel_inst.name}__{category_inst.name}"
        / f"{variable}.root"
    )
    # `exist_ok=True` is required since concurrent workers may create the same
    # parent directory at the same time
    if not output_file.parent.exists():
        output_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory {output_file.parent}")

    # Create new ROOT file and write histograms to it
    rf = ROOT.TFile(str(output_file), "RECREATE")
    for (process, variation), hist in histograms.items():
        dir_name = (
            f"{campaign}/{channel_inst.name}/{category_inst.name}/{process}"
        )
        directory = rf.GetDirectory(dir_name)
        if not directory:
            directory = rf.mkdir(dir_name)
        hist_name = f"{variable}__{variation}"
        hist.SetName(hist_name)
        hist.SetTitle(hist_name)
        directory.WriteObject(hist, hist.GetName())
    rf.Close()
    logger.info(f"Wrote merged histograms to {output_file}")

    return str(output_file)


def merge_histograms(
    inventory_factory_fn_path,
    graph_specs,
    histograms_dir,
    output_dir,
    num_workers: int = 1,
):
    # Load all histograms from the input files
    histograms = load_all(
        Path(graph_specs["histogram_keys_file"]), histograms_dir
    )

    # Split the histogram nodes into independent merge tasks
    tasks = _build_merge_tasks(
        graph_specs,
        inventory_factory_fn_path,
        histograms_dir,
        output_dir,
    )

    # Merge the histograms, optionally in parallel. The tasks are fully
    # independent since each of them writes its own output file.
    run_in_parallel(_merge_category_variable, tasks, num_workers)
