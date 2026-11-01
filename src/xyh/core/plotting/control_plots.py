import logging
from itertools import product
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import ROOT

from xyh.core.config import load_inventory
from xyh.core.histograms.util import add_histograms
from xyh.core.parallel import run_in_parallel
from xyh.core.specs.binning import _parse_variable_name

from .util import plot

logger = logging.getLogger(__name__)


def _build_plot_tasks(
    inventory_factory_fn_path,
    inventory_factory_kwargs,
    campaigns,
    channels,
    categories,
    variables,
    histograms,
    output_dir,
    extensions,
) -> list[dict[str, Any]]:
    """Split the histogram nodes into independent plot tasks.

    Each task produces the control plots of one campaign, channel, category,
    and variable combination. All tasks are fully independent, so they can be
    processed in parallel.
    """

    # List of tasks to be processed in parallel
    tasks = []

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

                # Get variable instance object
                variable_inst = inventory.variables.get(variable)

                # Build the task dictionary
                tasks.append(
                    {
                        "inventory_factory_fn_path": inventory_factory_fn_path,
                        "inventory_factory_kwargs": inventory_factory_kwargs,
                        "campaign_inst": campaign_inst,
                        "channel_inst": channel_inst,
                        "category_inst": category_inst,
                        "variable_inst": variable_inst,
                        "process_set": inventory.process_set,
                        "histograms": histograms,
                        "output_dir": output_dir,
                        "extensions": extensions,
                    }
                )

    return tasks


def _plot_category_variable(task: dict[str, Any]) -> list[str]:
    """Produce the control plots of one plot task.

    The function is executed either in the current process or in a worker
    process of the pool. It must therefore be a picklable top-level function
    and must not depend on any state of the parent process.
    """

    # Unpack the task information
    campaign_inst = task["campaign_inst"]
    channel_inst = task["channel_inst"]
    category_inst = task["category_inst"]
    variable_inst = task["variable_inst"]
    process_set = task["process_set"]
    histograms = task["histograms"]
    output_dir = task["output_dir"]
    extensions = task["extensions"]

    # Get analysis config objects
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

    # Load histograms from file and prepare histograms for plotting
    histograms_variable = {}
    for hist_type, process_groups in [
        ("data", process_set.data),
        ("signals", process_set.signals),
        ("backgrounds", process_set.backgrounds),
    ]:
        histograms_variable[hist_type] = {}

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
                    f"{campaign_inst.name}/{channel_inst.name}/{category_inst.name}/"
                    f"{process}/{variable_inst.name}__nominal"
                )
                h = histograms[hist_name]
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
            / campaign_inst.name
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
    inventory_factory_kwargs: dict[str, Any],
    campaigns: list[str],
    channels: list[str],
    categories: list[str],
    variables: list[str],
    merged_histograms_file: Path,
    output_dir: Path,
    extensions: list[str],
    num_workers: int = 1,
):
    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    # Load all histograms from the input file
    root_file = ROOT.TFile.Open(str(merged_histograms_file), "READ")
    histograms = {}
    for key in root_file.GetListOfKeys():
        histograms[key.GetTitle()] = root_file.Get(key)
    root_file.Close()

    # Split the histogram nodes into independent plot tasks
    tasks = _build_plot_tasks(
        inventory_factory_fn_path,
        inventory_factory_kwargs,
        campaigns,
        channels,
        categories,
        variables,
        merged_histograms_file,
        output_dir,
        extensions,
    )

    # Produce the control plots, optionally in parallel. The tasks are fully
    # independent since each of them writes its own output files.
    run_in_parallel(_plot_category_variable, tasks, num_workers)
