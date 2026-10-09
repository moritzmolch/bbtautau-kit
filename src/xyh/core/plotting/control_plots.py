import logging
from itertools import groupby
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import ROOT

from xyh.core.config import load_inventory
from xyh.core.histograms.util import add_histograms
from xyh.core.parallel import run_in_parallel

from .util import plot

logger = logging.getLogger(__name__)


def _build_plot_tasks(
    graph_specs,
    inventory_factory_fn_path,
    merged_histograms_dir,
    output_dir,
    extensions,
) -> list[dict[str, Any]]:
    """Split the histogram nodes into independent plot tasks.

    Each task produces the control plots of one campaign, channel, category,
    and variable combination. All tasks are fully independent, so they can be
    processed in parallel.
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
        for (category, variable), _ in groupby(
            sorted(nodes_campaign_channel, key=key_fn_category_variable),
            key=key_fn_category_variable,
        ):
            tasks.append(
                {
                    "inventory_factory_fn_path": inventory_factory_fn_path,
                    "merged_histograms_dir": merged_histograms_dir,
                    "output_dir": output_dir,
                    "extensions": extensions,
                    "campaign": campaign,
                    "channel": channel,
                    "category": category,
                    "variable": variable,
                }
            )

    return tasks


def _plot_category_variable(task: dict[str, Any]) -> list[str]:
    """Produce the control plots of one plot task.

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
    merged_histograms_dir = task["merged_histograms_dir"]
    output_dir = task["output_dir"]
    extensions = task["extensions"]

    # Get analysis config objects
    campaign_inst = inventory.campaign
    channel_inst = inventory.channel
    process_set = inventory.process_set
    category_inst = channel_inst.get_category(category)
    variable_inst = inventory.variables.get(variable)
    logger.info(
        "\n".join(
            [
                "Producing control plots for",
                f"    campaign:  {campaign_inst.name}",
                f"    channel:   {channel_inst.name}",
                f"    category:  {category_inst.name}",
                f"    variable:  {variable_inst.name}",
            ],
        ),
    )

    # Open input file with histograms for this variable
    input_file = (
        merged_histograms_dir
        / campaign
        / f"{channel_inst.name}__{category}"
        / f"{variable_inst.name}.root"
    )
    rf = ROOT.TFile.Open(str(input_file), "READ")

    # Load histograms from file and prepare histograms for plotting
    histograms = {}
    for hist_type, process_groups in [
        ("data", process_set.data),
        ("signals", process_set.signals),
        ("backgrounds", process_set.backgrounds),
    ]:
        histograms[hist_type] = {}

        for process_group in process_groups:
            process_group_name = process_group.name

            # Collect histograms of this group and add them up
            hists_group = []
            for process in process_group.processes:
                # if process_inst.get_aux("is_signal", False):
                #     if not category_inst.has_tag("clf"):
                #         continue
                #     if not (
                #         process_inst.x.y_decay_mode
                #         == category_inst.x.y_decay_mode
                #         and process_inst.x.h_decay_mode
                #         == category_inst.x.h_decay_mode
                #         and process_inst.x.m_x == category_inst.x.m_x
                #         and process_inst.x.m_y == category_inst.x.m_y
                #     ):
                #         continue
                hist_name = (
                    f"{campaign}/{channel_inst.name}/{category_inst.name}/"
                    f"{process}/{variable_inst.name}__nominal"
                )
                h = rf.Get(hist_name)
                hists_group.append(h)
            if len(hists_group) == 0:
                continue

            # Add histograms of this process group
            h = add_histograms(hists_group)

            histograms[hist_type][process_group_name] = {
                "histogram": h,
                "mpl_kwargs": {
                    "color": process_group.color,
                    "label": process_group.label,
                },
            }
            if process_group.scale_factor is not None:
                histograms[hist_type][process_group_name]["mpl_kwargs"][
                    "scale_factor"
                ] = process_group.scale_factor.get(channel_inst.name, 1.0)

    rf.Close()

    # Prepare data, signal, and background histograms
    hist_data = None
    kwargs_data = {}
    for h in histograms["data"].values():
        if hist_data is None:
            hist_data = h["histogram"].Clone()
            kwargs_data = h["mpl_kwargs"]
        else:
            hist_data.Add(h["histogram"])
    histogram_data = (hist_data, kwargs_data)

    histograms_signal = [
        (h["histogram"], h["mpl_kwargs"])
        for h in histograms["signals"].values()
    ]

    histograms_background = [
        (h["histogram"], h["mpl_kwargs"])
        for h in histograms["backgrounds"].values()
    ]

    fig, ax = plot(
        hist_data=(
            histogram_data if not category_inst.has_tag("blinded") else None
        ),
        hist_backgrounds=histograms_background,
        hist_signals=histograms_signal,
        stack_kwargs=None,
        x_label_top=None,
        y_label_top="Events",
        x_label_bottom=variable_inst.get_full_x_title(),
        y_label_bottom=r"Ratio to background",
        y_limits_top=None,
        y_limits_bottom=(0.7, 1.3),
        category_label=category_inst.label,
        lumi=campaign_inst.x.lumi,
        era=None,
        sqrt_s=campaign_inst.ecm,
        fit_ratio=True,
    )

    # Save the file
    output_files = []
    for ext in extensions:
        output_file = (
            output_dir
            / campaign
            / f"{channel_inst.name}__{category_inst.name}"
            / f"{variable_inst.name}.{ext}"
        )
        # `exist_ok=True` is required since concurrent workers may create the
        # same parent directory at the same time
        if not output_file.parent.exists():
            output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_file)
        output_files.append(str(output_file))
        logger.info(f"Wrote control plot to {output_file}")

    # Clear figure to release memory
    plt.clf()

    return output_files


def plot_shapes(
    inventory_factory_fn_path: str,
    graph_specs: dict,
    merged_histograms_dir: Path,
    output_dir: Path,
    extensions: list[str],
    num_workers: int = 1,
):
    # Split the histogram nodes into independent plot tasks
    tasks = _build_plot_tasks(
        graph_specs,
        inventory_factory_fn_path,
        merged_histograms_dir,
        output_dir,
        extensions,
    )

    # Produce the control plots, optionally in parallel. The tasks are fully
    # independent since each of them writes its own output files.
    run_in_parallel(_plot_category_variable, tasks, num_workers)
