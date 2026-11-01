import logging
import os
from collections.abc import Callable
from fnmatch import fnmatch
from time import time

import numpy as np
import ROOT

from xyh.core.graph.artifacts import Artifacts
from xyh.core.graph.node import Node

# Set up logging
logger = logging.getLogger(__name__)

# Weight prefix to prepend to the name of weight columns
WEIGHT_PREFIX = "__weight_"
TOTAL_WEIGHT_NAME = f"{WEIGHT_PREFIX}total"


def _get_single_parent(node: Node) -> Node:
    """
    Get the single parent of a node.

    The function is going to return a single parent of a node. If the node has
    more than one parent, a `ValueError` is raised.

    Parameters
    ----------
    node : Node
        The node for which the parent is to be retrieved.

    Returns
    -------
    Node
        The single parent of the node.

    Raises
    ------
    ValueError
        If the node has more than one parent.
    """

    # Check if the node has more than one parent
    if not len(node.parents) == 1:
        raise ValueError(
            f"Filter node {node.hash} must have exactly one parent, "
            f"but has {len(node.parents)} parents."
        )

    return node.parents[0]


def _parse_snapshot_column(pattern: str) -> tuple[str, frozenset[str] | None]:
    """Parse a snapshot column pattern into a (name, channels) pair.

    Column patterns follow the inventory variable convention: the 'pure'
    column name, optionally followed by a list of channels the column is
    written for, '<name>[<channel 1>,<channel 2>,...]'. `None` channels mean
    the column is written in all channels. Patterns that do not follow the
    convention are used verbatim as shell-style glob patterns without channel
    restriction.
    """
    m = re.match(r"^([^\[]+)(?:\[([^\]]+)\])?$", pattern)
    if m is None:
        return pattern, None
    name = m.group(1).strip()
    channels = m.group(2)
    if channels is None:
        return name, None
    return name, frozenset(c.strip() for c in channels.split(",") if c.strip())


def _prepare_snapshot_columns(
    all_columns: list[str],
    columns: tuple[str, ...] | None = None,
    channel: str | None = None,
) -> list[str]:
    """Map friend-qualified column names and keep the configured columns.

    Columns from friend trees are listed as "<tree>.<column>", which Snapshot
    would save as "<tree>_<column>". They can be accessed by their plain
    name, so the prefix is stripped to keep the original column names. If the
    plain name clashes with another column, the qualified name is kept.

    If `columns` is `None` or empty, all columns are kept. Otherwise only
    columns matching any entry of `columns` are written to the snapshot.
    Entries follow shell-style globbing (`fnmatch`) and are matched against
    both the final (possibly stripped) column name and the original
    friend-qualified name. Entries may restrict a column to a set of channels
    via the '<name>[<channel 1>,<channel 2>,...]' convention; a column that
    only matches a restricted entry is written solely if `channel` is in that
    set (`channel=None` ignores the restriction).
    """
    patterns = [(_parse_snapshot_column(p)) for p in columns] if columns else []

    def _matches(c: str, original: str) -> bool:
        for pattern, channels in patterns:
            if (
                channel is not None
                and channels is not None
                and channel not in channels
            ):
                continue
            if fnmatch(c, pattern) or fnmatch(original, pattern):
                return True
        return False

    plain_columns = {c for c in all_columns if "." not in c}
    selected = []
    for c in all_columns:
        original = c
        if "." in c:
            stripped = c.split(".", 1)[1]
            if stripped not in plain_columns:
                plain_columns.add(stripped)
                c = stripped
        if patterns and not _matches(c, original):
            logger.debug(f"Skipping column {original} in snapshot")
            continue
        selected.append(c)
    return selected


def input_files(
    node: Node,
    artifacts: dict[str, Artifacts],
) -> Artifacts:
    """
    Load input files into an `RDataFrame`.

    This class stores the loaded object and associated `ROOT.TChain` objects
    as artifacts. The `ROOT.TChain` objects need to persist in memory as long as
    the `RDataFrame` exists.

    Parameters
    ----------
    node : Node
        The `"input_files"` operation node that is being processed.

    artifacts: dict[str, Artifacts]
        The artifacts from parent nodes with the parent node hashes as keys.

    Returns
    -------
    Artifacts
        The artifacts containing the loaded `RDataFrame` and associated
        `ROOT.TChain` objects.
    """

    # Log current node's context and start time profiling
    logger.debug(
        "\n".join(
            [
                "Initialize data frame from input files for",
                f"    node:     {node.hash}",
                f"    campaign: {node.data.campaign}",
                f"    channel:  {node.data.channel}",
                f"    dataset:  {node.data.dataset}",
            ]
        )
    )
    start = time()

    # Create the chains of the input files
    chains = {}
    for key, files in node.data.files.items():
        chain = ROOT.TChain("ntuple")
        for file in files:
            chain.Add(file)
        chains[key] = chain

    # Add friends to main chain
    main_chain = chains.pop("main")
    for chain in chains.values():
        if chain.GetListOfFiles().GetEntries() > 0:
            main_chain.AddFriend(chain)

    # Create the RDataFrame
    data_frame = ROOT.RDataFrame(main_chain)

    # Stop time profiling and log time that has been used loading the
    # RDataFrame
    stop = time()
    delta = round(stop - start, 2)
    logger.debug(
        "\n".join(
            [
                f"Initialized data frame in {delta} s",
            ]
        )
    )

    return Artifacts(
        data_frame=data_frame,
        main_chain=main_chain,
        friend_chains=chains,
    )


def filter(
    node: Node,
    artifacts: dict[str, Artifacts],
) -> Artifacts:
    """
    Declare a filter on an `RDataFrame` object.

    The filter is applied to the `RDataFrame` and the modified `RDataFrame` is
    stored as an artifact.

    Parameters
    ----------
    node : Node
        The `"filter"` operation node that is being processed.

    artifacts: dict[str, Artifacts]
        The artifacts from parent nodes with the parent node hashes as keys.

    Returns
    -------
    Artifacts
        The artifacts containing the modified `RDataFrame`.
    """

    # Log context of the node
    logger.debug(
        "\n".join(
            [
                "Declare filter on data frame",
                f"    node:       {node.hash}",
                f"    parents:    {[p.hash for p in node.parents]}",
                f"    name:       {node.data.name}",
                f"    expression: {node.data.expression}",
            ]
        )
    )

    # Assert that the node has exactly one parent and get that parent node
    parent = _get_single_parent(node)

    # Get the data frame and define the filter on it
    data_frame = artifacts[parent.hash].data_frame
    data_frame = data_frame.Filter(node.data.expression, node.data.name)

    return Artifacts(data_frame=data_frame)


def weight(
    node: Node,
    artifacts: dict[str, Artifacts],
) -> Artifacts:
    """
    Declare a weight on an `RDataFrame` object.

    The weight is defined to the `RDataFrame` and the modified `RDataFrame` is
    stored as an artifact.

    Parameters
    ----------
    node : Node
        The `"weight"` operation node that is being processed.

    artifacts: dict[str, Artifacts]
        The artifacts from parent nodes with the parent node hashes as keys.

    Returns
    -------
    Artifacts
        The artifacts containing the modified `RDataFrame`.
    """

    # Log context of the node
    logger.debug(
        "\n".join(
            [
                "Declare weight on data frame",
                f"    node:          {node.hash}",
                f"    parents:       {[p.hash for p in node.parents]}",
                f"    name:          {node.data.name}",
                f"    prefixed name: {WEIGHT_PREFIX}{node.data.name}",
                f"    expression:    {node.data.expression}",
            ]
        )
    )

    # Assert that the node has exactly one parent and get that parent node
    parent = _get_single_parent(node)

    # Get the data frame and define the weight on it. A custom weight prefix
    # reduces the risk of collisions with existing column names.
    data_frame = artifacts[parent.hash].data_frame
    data_frame = data_frame.Define(
        f"{WEIGHT_PREFIX}{node.data.name}",
        node.data.expression,
    )

    return Artifacts(data_frame=data_frame)


def weight_product(
    node: Node,
    artifacts: dict[str, Artifacts],
) -> Artifacts:
    """
    Produce a total weight column by multiplying all weights declared in the
    node data.

    The total weight is defined on the `RDataFrame` and the modified
    `RDataFrame` is stored as an artifact.

    Parameters
    ----------
    node : Node
        The `"weight_product"` operation node that is being processed.

    artifacts: dict[str, Artifacts]
        The artifacts from parent nodes with the parent node hashes as keys.

    Returns
    -------
    Artifacts
        The artifacts containing the modified `RDataFrame`.
    """

    # Log context of the node
    logger.debug(
        "\n".join(
            [
                "Declare weight on data frame",
                f"    node:       {node.hash}",
                f"    parents:    {[p.hash for p in node.parents]}",
                f"    weights:    {[f'{WEIGHT_PREFIX}{w.name}' for w in node.data.weights]}",
                f"    total name: {TOTAL_WEIGHT_NAME}",
            ]
        )
    )

    # Assert that the node has exactly one parent and get that parent node
    parent = _get_single_parent(node)

    # Get the data frame from the parent
    data_frame = artifacts[parent.hash].data_frame

    # Get the weight columns to multiply and check that they are present in the
    # data frame
    weight_columns = [
        f"{WEIGHT_PREFIX}{weight.name}" for weight in node.data.weights
    ]
    if not set(weight_columns).issubset(
        str(c) for c in data_frame.GetColumnNames()
    ):
        raise ValueError(
            "Not all weight columns are present in the data frame: "
            + ", ".join(weight_columns)
        )

    # Define the weight expression and declare the total weight calculation
    weight_expression = "1"
    if len(weight_columns) > 0:
        weight_expression = " * ".join(weight_columns)
    else:
        logger.debug("No weight columns found, setting total weight to 1")
    data_frame = data_frame.Define(TOTAL_WEIGHT_NAME, weight_expression)

    return Artifacts(data_frame=data_frame)


def histogram(
    node: Node,
    artifacts: dict[str, Artifacts],
) -> Artifacts:
    """
    Declare a lazy `TH1D` histogram operation on the `RDataFrame`.

    The artifacts object contains the `RDataFrame` as well as the lazy histogram
    object.

    Parameters
    ----------
    node : Node
        The `"histogram"` operation node that is being processed.

    artifacts: dict[str, Artifacts]
        The artifacts from parent nodes with the parent node hashes as keys.

    Returns
    -------
    Artifacts
        The artifacts containing the `RDataFrame` and the lazy histogram.
    """
    # Log context of this node
    logger.debug(
        "\n".join(
            [
                "Declare histogram",
                f"    campaign:   {node.data.binning.campaign}",
                f"    channel:    {node.data.binning.channel}",
                f"    category:   {node.data.binning.category}",
                f"    dataset:    {node.data.dataset}",
                f"    process:    {node.data.process}",
                f"    variation:  {node.data.variation}",
                f"    variable:   {node.data.binning.variable}",
                f"    expression: {node.data.binning.expression}",
            ]
        )
    )

    # Assert that the node has exactly one parent and get that parent node
    parent = _get_single_parent(node)

    # Get the data frame from the parent
    data_frame = artifacts[parent.hash].data_frame

    # Define custom expression as column if provided
    column = node.data.binning.variable
    if node.data.binning.expression is not None:
        column = f"__private__{node.data.binning.variable}"
        data_frame = data_frame.Define(column, node.data.binning.expression)
        logger.debug(
            f"Defined custom expression for variable '{node.data.binning.variable}' "
            + f"as column with expression '{node.data.binning.expression}'"
        )

    # Declare the lazy histogram operation
    lazy_hist = data_frame.Histo1D(
        (
            node.data.binning.variable,
            node.data.binning.variable,
            len(node.data.binning.bin_edges) - 1,
            np.array(node.data.binning.bin_edges),
        ),
        column,
        TOTAL_WEIGHT_NAME,
    )

    return Artifacts(
        data_frame=data_frame,
        lazy_hist=lazy_hist,
    )


def snapshot(
    node: Node,
    artifacts: dict[str, Artifacts],
) -> Artifacts:
    """
    Declare a lazy snapshot operation on the `RDataFrame`.

    The artifacts object contains the `RDataFrame` as well as the lazy snapshot
    object.

    Parameters
    ----------
    node : Node
        The `"histogram"` operation node that is being processed.

    artifacts: dict[str, Artifacts]
        The artifacts from parent nodes with the parent node hashes as keys.

    Returns
    -------
    Artifacts
        The artifacts containing the `RDataFrame` and the lazy snapshot.
    """

    # Log context of this node
    logger.debug(
        "\n".join(
            [
                "Declare snapshot",
                f"    campaign:   {node.data.campaign}",
                f"    channel:    {node.data.channel}",
                f"    category:   {node.data.category}",
                f"    dataset:    {node.data.dataset}",
                f"    process:    {node.data.process}",
                f"    variation:  {node.data.variation}",
                f"    columns:    {','.join(c for c in node.data.columns)}",
            ]
        )
    )

    # Assert that the node has exactly one parent and get that parent node
    parent = _get_single_parent(node)

    # Get the data frame from the parent
    data_frame = artifacts[parent.hash].data_frame

    # Create the snapshot's output directory if it does not exist
    snapshot_file = node.outputs["snapshot_file"].path
    parent_dir = os.path.dirname(snapshot_file)
    if not os.path.exists(parent_dir):
        os.makedirs(os.path.dirname(parent_dir), exist_ok=True)
        logger.debug(f"Created directory {parent_dir}")

    # Columns from friend trees are listed as "<tree>.<column>", which
    # Snapshot would save as "<tree>_<column>". They can be accessed by their
    # plain name, so strip the prefix to keep the original column names. If
    # the plain name clashes with another column, keep the qualified name.
    # `node.columns` restricts the snapshot to explicitly listed columns;
    # entries may further restrict columns to a subset of channels.
    columns = _prepare_snapshot_columns(
        [str(c) for c in data_frame.GetColumnNames()],
        node.data.columns,
        node.data.channel,
    )

    # Columns that are not available for this particular sample (e.g. a
    # missing friend or branch) are ignored instead of failing the snapshot.
    available_columns = [c for c in columns if data_frame.HasColumn(c)]
    for column in set(columns) - set(available_columns):
        logger.debug(f"Ignoring column {column} not available for this sample")
    columns = available_columns

    # Trigger lazy snapshot creation
    options = ROOT.RDF.RSnapshotOptions()
    options.fLazy = True
    lazy_snapshot = data_frame.Snapshot(
        "ntuple",
        snapshot_file,
        columns,
        options,
    )

    return Artifacts(
        data_frame=data_frame,
        lazy_snapshot=lazy_snapshot,
    )


def write_histograms(
    node: Node,
    artifacts: dict[str, Artifacts],
) -> Artifacts:
    """
    Materialize lazy `TH1D` histograms and write them to an output file.

    Parameters
    ----------
    node : Node
        The `"write_histograms"` operation node that is being processed.

    artifacts: dict[str, Artifacts]
        The artifacts from parent nodes with the parent node hashes as keys.

    Returns
    -------
    Artifacts
        The artifacts containing the evaluated histograms.
    """

    # Get the output file and create output directory
    output_file = node.outputs["hists_file"].path
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Log context of this node
    logger.debug(
        "\n".join(
            [
                "Write histograms to output file",
                f"    output_file: {output_file}",
            ]
        )
    )

    # Get data frame and lazy histogram artifacts from all parents
    hists_data = []
    lazy_hists = []
    for parent in node.parents:
        hists_data.append(parent.data)
        lazy_hists.append(artifacts[parent.hash].lazy_hist)

    # Run the computations for all lazy histograms
    ROOT.RDF.RunGraphs(lazy_hists)

    # Write histograms to output file
    hists = []
    root_file = ROOT.TFile.Open(
        output_file,
        "RECREATE",
    )
    for hist_spec, lazy_hist in zip(hists_data, lazy_hists, strict=True):
        # Get the histogram
        hist = lazy_hist.GetValue()

        # Set the histogram directory and move to this directory
        dir_name = "/".join(
            [
                hist_spec.binning.campaign,
                hist_spec.binning.channel,
                hist_spec.binning.category,
                hist_spec.dataset,
                hist_spec.process,
            ]
        )
        directory = root_file.GetDirectory(dir_name)
        if not directory:
            directory = root_file.mkdir(dir_name)
        directory.cd()

        # Set the histogram name and title
        hist_name = f"{hist_spec.binning.variable}__{hist_spec.variation}"
        hist_title = hist_name
        hist.SetName(hist_name)
        hist.SetTitle(hist_title)
        hist.Write()
        hists.append((hist_spec, hist))

    # Safely close the output file
    root_file.Close()

    return Artifacts(hists=hists)


def write_snapshots(
    node: Node,
    artifacts: dict[str, Artifacts],
) -> Artifacts:
    """
    Materialize lazy snapshots and write them to an output file.

    Parameters
    ----------
    node : Node
        The `"write_histograms"` operation node that is being processed.

    artifacts: dict[str, Artifacts]
        The artifacts from parent nodes with the parent node hashes as keys.

    Returns
    -------
    Artifacts
        The artifacts containing the evaluated snapshots.
    """

    # Log context of this node
    logger.debug(
        "\n".join(
            [
                "Write snapshots to output file",
            ]
        )
    )

    # Get lazy snapshot artifacts from all parents
    lazy_snapshots = []
    for parent in node.parents:
        lazy_snapshots.append(artifacts[parent.hash].lazy_snapshot)

    # Run the computations for all lazy snapshots
    ROOT.RDF.RunGraphs(lazy_snapshots)

    return Artifacts()


# Dictionary mapping an operation name to its corresponding function
_operations: dict[str, Callable[[Node, dict[str, Artifacts]], Artifacts]] = {
    "input_files": input_files,
    "filter": filter,
    "weight": weight,
    "weight_product": weight_product,
    "histogram": histogram,
    "write_histograms": write_histograms,
}


def get_operation_fn(
    node: Node,
) -> Callable[[Node, dict[str, Artifacts]], Artifacts]:
    """
    Get the operation function for the given node;

    Parameters
    ----------
    node: Node
        The node for which the operation function is to be retrieved.

    Returns
    -------
    Callable[[Node, Artifacts], Artifacts]

    """
    # Validate operation name
    if node.operation not in _operations:
        raise ValueError(f"Unknown operation: {node.operation}")

    return _operations[node.operation]
