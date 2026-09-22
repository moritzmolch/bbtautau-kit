#!/usr/bin/env python
"""
Inspect the distribution of a single weight for a process group after the
selection of a category.

The main shape-production pipeline computes the ``filters`` (selections) and
``weights`` (event-weight expressions) for every combination of campaign,
channel, category, process group member, and dataset, stores them in the
``filters_and_weights.json.gz`` spec file, and embeds the ntuple file lists in
the ``graphs.json.gz`` spec file. This script reuses these artifacts in order
to

* apply exactly the same selection as the ordinary analysis (the filter
  expressions of the requested category),
* evaluate only the requested *single* weight (rather than the product of all
  weights),
* fill a histogram of that weight's per-event values, and
* plot the resulting histogram in the style used by the other tools of this
  repository.

Unlike the ordinary variable histograms, the x axis of the produced histogram
*is* the weight value, so every event contributes with weight 1 (the bin
content is the number of events with a given weight). This makes the plot a
direct view of the spread of the weight.

Parameters are read from a single configuration file (``--config``), so the
script can be run for many configurations without repeating command-line
arguments.

Usage
-----
    python -m xyh.scripts.inspect_weights --config inspect_weights.yaml

A minimal configuration file looks like::

    campaign: "2024_nano_v15"
    channel: "mm"
    category: "mm_eq2j"
    process_group: "tt"
    weight: "pileup_weight"
    bins: 10
    start: 0.5
    stop: 3.0
    output: "data/inspect_weights/mm__mm_eq2j/tt/pileup_weight.png"
    shapes_tag: "shapes-2026-09-21-ntuples-2026-06-10-no-bjet-filters-with-bjet-weights"

The ``shapes_tag`` selects the shapes output tree under ``data/output/`` from
which the ``filters_and_weights.json.gz`` and ``graphs.json.gz`` spec files are
read. All other keys are optional and fall back to reasonable defaults (see
``main``). The ``process_group`` key must name a process group of the process
set (e.g. ``tt``, ``z_2l``, ``vv``); all of its member processes and datasets
are summed. The ``weight`` key must be one of the weight names defined for the
process group (e.g. ``pileup_weight``, ``gen_weight``, ``trigger_weight``,
``id_wgt_bjet_shape``, ...). If it is not present, the script raises an error
that lists the available weights.

Several configurations can be inspected in a single run by providing the
configs as a top-level list or under a ``configs`` key::

    # Shared defaults may be placed at the top level (form 3 below)
    shapes_tag: "shapes-2026-09-21-ntuples-2026-06-10-no-bjet-filters-with-bjet-weights"
    configs:
      - campaign: "2024_nano_v15"
        channel: "mm"
        category: "mm_eq2j"
        process_group: "tt"
        weight: "pileup_weight"
        bins: 10
        start: 0.5
        stop: 3.0
        output: "data/inspect_weights/tt_pileup.png"
      - campaign: "2024_nano_v15"
        channel: "ee"
        category: "ee_eq2j"
        process_group: "z_2l"
        weight: "gen_weight"
        bins: 10
        start: -1.0
        stop: 1.0
        output: "data/inspect_weights/z_2l_gen.png"

Note
----

The code in this script has been generated with DeepSeek V4 Flash.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import matplotlib.pyplot as plt
import mplhep
import ROOT
import yaml

from xyh import ROOT_DIR
from xyh.core.config import load_inventory
from xyh.core.histograms.util import add_histograms
from xyh.core.plotting.util import plot_distribution

DEFAULT_FACTORY_FN = "xyh.config.inventory.create_inventory"
DEFAULT_PROCESS_SET = "default"
DEFAULT_SHAPES_TAG = (
    "shapes-2026-09-21-ntuples-2026-06-10-no-bjet-filters-with-bjet-weights"
)


def load_config(config_file: Path) -> dict:
    """Load the inspection configuration from a JSON or YAML file.

    The ``.json.gz``/``.json`` and the ``.yaml``/``.yml`` extensions are
    supported.
    """
    if config_file.name.endswith(".gz"):
        with gzip.open(config_file, "rt") as f:
            return json.load(f)

    if config_file.suffix in (".yaml", ".yml"):
        with config_file.open("r") as f:
            return yaml.safe_load(f)

    if config_file.suffix == ".json":
        with config_file.open("r") as f:
            return json.load(f)

    raise ValueError(
        f"Unsupported config file extension '{config_file.suffix}' of "
        f"'{config_file}'. Expected .json, .json.gz, .yaml, or .yml."
    )


def get_configurations(cfg) -> list[dict]:
    """Normalize the config content into a list of single-run configurations.

    The content of the config file can be provided in three forms:

    1. A single dictionary (a single configuration run).
    2. A YAML/JSON list of dictionaries (multiple runs).
    3. A dictionary with a ``configs`` key holding a list of dictionaries.
       All other top-level keys are treated as shared defaults and are merged
       into every configuration (a per-configuration value takes precedence).

    Returns
    -------
    list[dict]
        A list of individual configuration dictionaries.
    """
    if isinstance(cfg, list):
        return cfg

    if isinstance(cfg, dict) and isinstance(cfg.get("configs"), list):
        defaults = {k: v for k, v in cfg.items() if k != "configs"}
        configurations = [defaults | conf for conf in cfg["configs"]]
    else:
        configurations = [cfg]

    if len(configurations) == 0:
        raise ValueError("No configuration provided.")

    return configurations


def load_specs(shapes_tag: str, name: str) -> list[dict]:
    """Load one spec file (``filters_and_weights`` or ``graphs``) from the
    shapes output tree.

    The files are stored as gzipped JSON under ``data/output/<shapes_tag>/specs``.
    """
    spec_file = (
        ROOT_DIR / "data" / "output" / shapes_tag / "specs" / f"{name}.json.gz"
    )
    if not spec_file.exists():
        raise ValueError(f"Spec file '{spec_file}' does not exist.")
    with gzip.open(spec_file, "rt") as f:
        return json.load(f)


def get_filters_and_weights(
    weights_specs: list[dict],
    campaign: str,
    channel: str,
    category: str,
    processes: list[str],
) -> list[dict]:
    """Return the ``nominal`` filters-and-weights specs (one per dataset and
    member process) that match the requested campaign, channel, category, and
    any of the given processes.
    """
    specs = [
        spec
        for spec in weights_specs
        if (
            spec["variation"] == "nominal"
            and spec["campaign"] == campaign
            and spec["channel"] == channel
            and spec["category"] == category
            and spec["process"] in processes
        )
    ]
    if len(specs) == 0:
        raise ValueError(
            f"No filters/weights spec found for campaign '{campaign}', "
            f"channel '{channel}', category '{category}', processes "
            f"{processes}. Check that these names match an entry in "
            "filters_and_weights.json.gz."
        )
    return specs


def resolve_processes(inventory, process_group: str) -> list[str]:
    """Resolve a process group of the process set to its member process names.

    The ``process_group`` must match the name of a process group in the
    inventory's process set (e.g. ``tt``). The names of all of its member
    processes are returned.
    """
    process_set = inventory.process_set
    for group in process_set.process_groups:
        if group.name == process_group:
            return list(group.processes)

    available = ", ".join(g.name for g in process_set.process_groups)
    raise ValueError(
        f"Process group '{process_group}' not found in the process set "
        f"'{process_set.name}'. Available process groups: {available}"
    )


def get_input_files(
    graph_specs: dict,
    campaign: str,
    channel: str,
    dataset: str,
    n_files: int | None = None,
) -> dict[str, list[str]]:
    """Look up the ntuple file lists of an ``InputFilesNode``.

    The files (main ntuple and friends) are matched by campaign, channel, and
    dataset.
    """
    for node in graph_specs["nodes"]:
        if node["type"] != "InputFilesNode":
            continue
        spec = node["spec"]
        if (
            spec["campaign"] == campaign
            and spec["channel"] == channel
            and spec["dataset"] == dataset
        ):
            files = spec["files"]
            if n_files is not None:
                for key, value in spec["files"].items():
                    files[key] = value[: min(n_files, len(value))]
            return files
    raise ValueError(
        f"No input files found for campaign '{campaign}', channel '{channel}', "
        f"dataset '{dataset}' in graphs.json.gz."
    )


def make_data_frame(files: dict[str, list[str]]) -> ROOT.RDataFrame:
    """Create an RDataFrame from the main ntuple files and attach friends.

    Mirrors ``_input_files`` in ``xyh.core.specs.graph``.
    """
    chains = {}
    for key, file_list in files.items():
        chain = ROOT.TChain("ntuple")
        for file_name in file_list:
            chain.Add(file_name)
        chains[key] = chain

    main_chain = chains.pop("main")
    for chain in chains.values():
        if chain.GetListOfFiles().GetEntries() > 0:
            main_chain.AddFriend(chain)

    return ROOT.RDataFrame(main_chain)


def fill_weight_histogram(
    data_frame: ROOT.RDataFrame,
    filters: dict[str, str],
    weight_expression: str,
    bins: int,
    start: float,
    stop: float,
    name: str,
) -> ROOT.TH1:
    """Apply the filters, define the requested weight, and fill its histogram.

    The histogram is filled unweighted, i.e. every event that passes the
    selection contributes 1, so that the x axis directly shows the value of
    the weight.
    """
    for filter_name, expression in filters.items():
        data_frame = data_frame.Filter(expression, filter_name)

    data_frame = data_frame.Define(name, weight_expression)
    data_frame = data_frame.Define("__weight_unit", "1.0f")

    hist = data_frame.Histo1D(
        (
            name,
            name,
            bins,
            start,
            stop,
        ),
        name,
        "__weight_unit",
    )

    # Force the computation of the histogram and detach it from the RDataFrame.
    # The RDataFrame is only alive inside this function, so the result must be
    # cloned before it goes out of scope.
    ROOT.RDF.RunGraphs([hist])
    hist = hist.Clone()
    hist.SetDirectory(0)
    return hist


def plot_weights(
    hist: ROOT.TH1,
    weight_name: str,
    category_label: str,
    x_label: str,
    campaign_inst,
    output_file: Path,
) -> None:
    """Plot the weight histogram and save it to ``output_file``."""
    fig, ax = plt.subplots(
        ncols=1,
        nrows=1,
    )

    plot_distribution(
        ax,
        hist,
        histtype="step",
        linewidth=2,
        color="#1f77b4",
    )

    ax.set_yscale("log")
    ax.set_xlabel(x_label)
    ax.set_ylabel("Events")
    ax.set_xlim(
        hist.GetXaxis().GetBinLowEdge(1),
        hist.GetXaxis().GetBinUpEdge(hist.GetNbinsX()),
    )

    mplhep.cms.label(
        ax=ax,
        text="Work in progress",
        com=campaign_inst.ecm,
        lumi=campaign_inst.x.lumi,
        year=None,
        fontsize=20,
    )

    ax.text(
        0.02,
        0.95,
        f"{category_label}\n{weight_name}",
        fontsize="x-small",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax.transAxes,
    )

    fig.savefig(output_file)
    plt.close(fig)


def run_configuration(cfg: dict) -> None:
    """Inspect the weight of one configuration and write the plot.

    A configuration must contain the ``campaign``, ``channel``, ``category``,
    ``process_group``, ``weight``, ``bins``, ``start``, ``stop``, and ``output``
    entries. The ``shapes_tag``, ``inventory_factory``, and ``process_set``
    entries are optional.
    """
    # Required configuration entries
    campaign = cfg["campaign"]
    channel = cfg["channel"]
    category = cfg["category"]
    process_group = cfg["process_group"]
    weight = cfg["weight"]
    bins = cfg["bins"]
    start = cfg["start"]
    stop = cfg["stop"]
    n_files = cfg.get("n_files", 2)
    output_file = Path(cfg["output"])

    # Continue if output file already exists
    if output_file.exists():
        print(f"Output file '{output_file}' already exists. Skipping.")
        return

    # Optional configuration entries
    shapes_tag = cfg.get("shapes_tag", DEFAULT_SHAPES_TAG)
    inventory_factory = cfg.get("inventory_factory", DEFAULT_FACTORY_FN)
    process_set = cfg.get("process_set", DEFAULT_PROCESS_SET)

    # Load the inventory for metadata (labels, luminosity, ...)
    inventory = load_inventory(
        inventory_factory,
        campaign,
        channel,
        process_set=process_set,
    )
    campaign_inst = inventory.campaign
    channel_inst = inventory.channel

    if not channel_inst.has_category(category):
        raise ValueError(
            f"Category '{category}' not found in channel '{channel}'."
        )
    category_inst = channel_inst.get_category(category)

    # Load the specs produced by the shape pipeline
    weights_specs = load_specs(shapes_tag, "filters_and_weights")
    graph_specs = load_specs(shapes_tag, "graphs")

    # Resolve the process group of the process set to its member processes and
    # select the filters/weights specs of those processes.
    processes = resolve_processes(inventory, process_group)
    specs = get_filters_and_weights(
        weights_specs,
        campaign,
        channel,
        category,
        processes,
    )

    # Make sure the requested weight is defined for this process. All
    # datasets and member processes share the same weight names.
    available_weights = list(specs[0]["weights"].keys())
    if weight not in available_weights:
        raise ValueError(
            f"Weight '{weight}' not found for process group '{process_group}' "
            f"(processes {processes}) in category '{category}'. Available "
            f"weights: {available_weights}"
        )

    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    # Fill a weight histogram per dataset and sum them up
    hists = []
    for spec in specs:
        dataset = spec["dataset"]
        files = get_input_files(
            graph_specs, campaign, channel, dataset, n_files=n_files
        )

        data_frame = make_data_frame(files)
        hist = fill_weight_histogram(
            data_frame,
            spec["filters"],
            spec["weights"][weight],
            bins,
            start,
            stop,
            f"{weight}__{dataset}",
        )
        hists.append(hist)
        print(f"Filled weight histogram for dataset '{dataset}'")

    hist = add_histograms(hists)
    hist.SetName(weight)
    hist.SetTitle(weight)

    # Create the output directory if it does not exist
    if not output_file.parent.exists():
        output_file.parent.mkdir(parents=True)

    plot_weights(
        hist,
        weight_name=weight,
        category_label=category_inst.label,
        x_label=weight,
        campaign_inst=campaign_inst,
        output_file=output_file,
    )

    print(f"Wrote weight histogram plot to {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        required=True,
        help="Path to the configuration file describing the weights to "
        "inspect. The file may contain a single configuration or a list of "
        "configurations.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    # The config can hold one or several individual configurations
    for configuration in get_configurations(cfg):
        run_configuration(configuration)


if __name__ == "__main__":
    main()
