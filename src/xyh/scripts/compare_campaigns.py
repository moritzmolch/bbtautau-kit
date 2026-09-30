#!/usr/bin/env python
"""
Overlay a process histogram for multiple campaigns (eras).

Loads the ``<variable>__nominal`` histograms of a process group for an
arbitrary number of campaigns from the merged-histogram output and produces a
two-panel figure:

* **Top panel**: absolute histograms of every campaign overlaid as step lines.
* **Bottom panel**: ratio of each campaign's histogram to the first campaign
  (reference).

Before plotting, all histograms are normalized to a unit integral, so the
overlaid shapes are compared independent of their overall normalization.

The reference for the ratio panel is the first campaign passed with
``--campaigns``, so at least two campaigns must be given.

Data are read from the per-campaign directories inside a merged-histograms
output tree (``<merged_histograms_dir>/<campaign>/<channel>__<category>/
<variable>.root``), using the inventory factory to resolve campaign, channel,
category, and variable instances for labels. A process group is resolved from
the process set and the histograms of all of its member processes are summed.

Usage
-----
    # Default merged-histograms dir (from config) for 2024 vs 2025
    python -m xyh.scripts.compare_campaigns \
        --campaigns 2024_nano_v15 2025_nano_v15 \
        --process-group tt \
        --channel mm --category mm_eq2j --variable m_vis \
        --output tt_mvis.png

    # Arbitrary shapes tag, a single-process group, and the 'mc' process set
    python -m xyh.scripts.compare_campaigns \
        --shapes-tag shapes-2026-09-21-ntuples-2026-06-10 \
        --process-set mc \
        --campaigns 2024_nano_v15 2025_nano_v15 \
        --process-group tt_jetfakes --channel mm --category mm_eq2j \
        --variable yield --output tt_jetfakes_yield.pdf

Note
----

The code in this script has been generated with DeepSeek V4 Flash.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import mplhep
import numpy as np
import ROOT

from xyh import ROOT_DIR
from xyh.core.config import load_inventory
from xyh.core.histograms.util import add_histograms
from xyh.core.plotting.util import (
    plot_distribution,
    set_axes_limits_distributions,
    set_axes_limits_ratio,
)

DEFAULT_FACTORY_FN = "xyh.config.inventory.create_inventory"

DEFAULT_MERGED_HISTOGRAMS_DIR = ROOT_DIR / "data" / "output"

CAMPAIGN_COLORS = [
    "#1f77b4",
    "#d62728",
    "#2ca02c",
    "#ff7f0e",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


def _plot(campaigns, hists, x_label, y_label, output_file: Path) -> None:
    """Create the top/ratio figure and save it to ``output_file``."""
    fig, (ax_top, ax_bottom) = plt.subplots(
        ncols=1,
        nrows=2,
        sharex=True,
        height_ratios=[0.7, 0.3],
        gridspec_kw={"hspace": 0.0},
    )

    # --- top panel: absolute histograms of every campaign -------------------
    for i, (campaign_inst, hist) in enumerate(
        zip(campaigns, hists, strict=True)
    ):
        lumi = campaign_inst.x.lumi
        label = f"{campaign_inst.name}"
        if lumi is not None:
            label += rf" ($L={lumi:.1f}~fb^{{-1}}$)"
        plot_distribution(
            ax_top,
            hist,
            histtype="step",
            linewidth=2,
            color=CAMPAIGN_COLORS[i % len(CAMPAIGN_COLORS)],
            label=label,
        )

    # --- bottom panel: ratios to the first campaign -------------------------
    hist_ref = hists[0]
    ratio_hists = []
    for hist in hists:
        hist_ratio = hist_ref.Clone()
        hist_ratio.Divide(hist)
        ratio_hists.append(hist_ratio)

    for histogram, color in zip(
        ratio_hists, CAMPAIGN_COLORS[: len(ratio_hists)], strict=True
    ):
        ax_bottom.errorbar(
            np.array(
                [
                    histogram.GetXaxis().GetBinCenter(i)
                    for i in range(1, histogram.GetNbinsX() + 1)
                ]
            ),
            np.array(
                [
                    histogram.GetBinContent(i)
                    for i in range(1, histogram.GetNbinsX() + 1)
                ]
            ),
            yerr=np.array(
                [
                    histogram.GetBinError(i)
                    for i in range(1, histogram.GetNbinsX() + 1)
                ]
            ),
            fmt="o",
            markersize=5,
            elinewidth=2,
            color=color,
        )
    ax_bottom.axhline(1, color="black", linestyle="dashed")

    # --- plot style ---------------------------------------------------------
    ax_top.set_ylabel(y_label)
    ax_bottom.set_xlabel(x_label)
    ax_bottom.set_ylabel(r"Ratio to " + campaigns[0].name)

    set_axes_limits_distributions(ax_top, hists, None)
    set_axes_limits_ratio(ax_bottom, ratio_hists, (0.7, 1.3))

    mplhep.cms.label(
        ax=ax_top,
        text="Work in progress",
        com=campaigns[0].ecm,
        lumi=None,
        year=None,
        fontsize=20,
    )

    ax_top.legend(
        fontsize="small",
        loc="upper right",
        ncols=1,
    )

    fig.savefig(output_file)
    plt.close(fig)


def get_process_hist(
    rf: ROOT.TFile,
    campaign_inst,
    channel_inst,
    category_inst,
    process: str,
    variable_inst,
) -> ROOT.TH1:
    """Read the ``__nominal`` histogram of a single process from a ROOT file."""
    hist_name = "/".join(
        (
            campaign_inst.name,
            channel_inst.name,
            category_inst.name,
            process,
            f"{variable_inst.name}__nominal",
        )
    )
    hist = rf.Get(hist_name)
    if hist is None:
        raise ValueError(f"Histogram '{hist_name}' not found in {rf.GetName()}")
    hist.Sumw2()  # Ensure sum of squares of weights is computed for error bars
    return hist


def get_process_group_hist(
    rf: ROOT.TFile,
    inventory,
    process_group: str,
    category_inst,
    variable_inst,
) -> ROOT.TH1:
    """Resolve a process group and sum the histograms of its members."""
    process_group_inst = next(
        (
            g
            for g in inventory.process_set.process_groups
            if g.name == process_group
        ),
        None,
    )
    if process_group_inst is None:
        available = ", ".join(
            g.name for g in inventory.process_set.process_groups
        )
        raise ValueError(
            f"Process group '{process_group}' not found in process set "
            f"'{inventory.process_set.name}'. Available groups: {available}"
        )

    campaign_inst = inventory.campaign
    channel_inst = inventory.channel

    return add_histograms(
        [
            get_process_hist(
                rf,
                campaign_inst,
                channel_inst,
                category_inst,
                process,
                variable_inst,
            )
            for process in process_group_inst.processes
        ]
    )


def normalize_histograms(hists: list[ROOT.TH1]) -> list[ROOT.TH1]:
    """Normalize all histograms to a unit integral.

    Every histogram is rescaled so that its total integral equals 1, enabling
    a comparison of the shapes independent of their overall normalization.
    """
    normalized = []
    for hist in hists:
        integral = hist.Integral()
        if integral == 0:
            raise ValueError(
                f"Histogram '{hist.GetName()}' has zero integral; "
                "cannot normalize."
            )
        scaled = hist.Clone()
        scaled.Scale(1.0 / integral)
        normalized.append(scaled)

    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--merged-histograms-dir",
        type=Path,
        default=DEFAULT_MERGED_HISTOGRAMS_DIR,
        help="Base directory containing the merged-histogram output trees "
        "(e.g. data/output).",
    )
    parser.add_argument(
        "--shapes-tag",
        type=str,
        default=None,
        help="Name of the shapes output directory under --merged-histograms-dir "
        "that contains the 'merged_histograms' subdirectory.",
    )
    parser.add_argument(
        "--campaigns",
        type=str,
        nargs="+",
        required=True,
        help="Campaign (era) names to compare. The first campaign is used as "
        "the reference in the ratio panel; at least two campaigns are required.",
    )
    parser.add_argument(
        "--process-group",
        type=str,
        required=True,
        help="Name of the process group to plot (e.g. tt, z_2l, vv, "
        "jetfakes). The histograms of all member processes are summed.",
    )
    parser.add_argument(
        "--process-set",
        type=str,
        default="default",
        help="Name of the process set from which the process group is taken "
        "(e.g. default, mc).",
    )
    parser.add_argument(
        "--channel",
        type=str,
        required=True,
        help="Name of the channel (e.g. mm, ee, em).",
    )
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        help="Name of the category (e.g. mm_eq2j).",
    )
    parser.add_argument(
        "--variable",
        type=str,
        required=True,
        help="Name of the variable (e.g. m_vis, yield).",
    )
    parser.add_argument(
        "--inventory-factory",
        type=str,
        default=DEFAULT_FACTORY_FN,
        help="Path to the inventory factory function.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("compare_campaigns.png"),
        help="Output image file. Format is inferred from the extension.",
    )
    args = parser.parse_args()

    if len(args.campaigns) < 2:
        raise SystemExit("At least two campaigns are required for a ratio.")

    # Resolve the merged-histograms directory holding per-campaign subdirs
    if args.shapes_tag is not None:
        merged_histograms_dir = (
            args.merged_histograms_dir / args.shapes_tag / "merged_histograms"
        )
    else:
        merged_histograms_dir = args.merged_histograms_dir

    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    campaigns = []
    hists = []
    variable_inst = None

    for campaign in args.campaigns:
        # Load the analysis inventory for this campaign and channel
        inventory = load_inventory(
            args.inventory_factory,
            campaign,
            args.channel,
            process_set=args.process_set,
        )
        campaign_inst = inventory.campaign
        channel_inst = inventory.channel

        category_inst = channel_inst.get_category(args.category)
        variable_inst = inventory.variables.get(args.variable)

        # Open the merged histogram file and read the process-group histogram
        input_file = (
            merged_histograms_dir
            / campaign_inst.name
            / f"{channel_inst.name}__{category_inst.name}"
            / f"{variable_inst.name}.root"
        )
        rf = ROOT.TFile.Open(str(input_file), "READ")
        hist = get_process_group_hist(
            rf,
            inventory,
            args.process_group,
            category_inst,
            variable_inst,
        )
        campaigns.append(campaign_inst)
        hists.append(hist.Clone())
        rf.Close()

    # Normalize all histograms to unit integral so that the shapes can be
    # compared independent of their overall normalization
    hists = normalize_histograms(hists)

    # Create the output directory if it does not exist
    if not args.output.parent.exists():
        args.output.parent.mkdir(parents=True)

    _plot(
        campaigns,
        hists,
        x_label=variable_inst.get_full_x_title(),
        y_label="Arbitrary units (normalized)",
        output_file=args.output,
    )

    print(f"Wrote comparison plot to {args.output}")


if __name__ == "__main__":
    main()
