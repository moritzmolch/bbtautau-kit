"""
Helpers to access the specs of a shape production and the ntuples they refer to.

The specs (``filters_and_weights.json.gz`` and ``graphs.json.gz``) of a shapes
tag contain the selections, weights and ntuple file lists, so that scripts can
reproduce the selection of the analysis outside of the graph processing.
"""

import gzip
import json

import ROOT

from xyh import ROOT_DIR


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
            files = dict(spec["files"])
            if n_files is not None:
                files = {k: v[:n_files] for k, v in files.items()}
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
