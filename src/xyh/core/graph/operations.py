import logging
from time import time

import numpy as np
import ROOT

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


class Artifacts(dict):
    """
    Artifacts object to store objects that persist in memory for the lifetime of
    the computation graph.
    """

    def __getattr__(self, key):
        return self[key]


class ArtifactsStore:
    def __init__(self):
        self._artifacts: dict[str, Artifacts] = {}

    def put(self, node_id: str, artifacts: Artifacts):
        self._artifacts[node_id] = artifacts

    def get(self, node_id: str) -> Artifacts:
        return self._artifacts[node_id]


class OutputFiles(dict):
    """
    Persistent output files object to store output files that are generated
    during the graph computation.
    """

    def __getattr__(self, key):
        return self[key]


def input_files(
    node: Node,
    artifacts_store: ArtifactsStore,
) -> tuple[Artifacts, OutputFiles]:
    """
    Load input files into an `RDataFrame`.

    This class stores the loaded object and associated `ROOT.TChain` objects
    as artifacts. The `ROOT.TChain` objects need to persist in memory as long as
    the `RDataFrame` exists.

    Parameters
    ----------
    node : Node
        The `"input_files"` operation node that is being processed.

    Returns
    -------
    tuple[Artifacts, OutputFiles]
        A tuple containing the artifacts and output files.
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
    ), OutputFiles()


def filter(
    node: Node,
    artifacts_store: ArtifactsStore,
) -> tuple[Artifacts, OutputFiles]:
    """
    Declare a filter on an `RDataFrame` object.

    The filter is applied to the `RDataFrame` and the modified `RDataFrame` is
    stored as an artifact.

    Parameters
    ----------
    node : Node
        The `"filter"` operation node that is being processed.

    artifacts_store : ArtifactsStore
        The store for the artifacts.

    Returns
    -------
    tuple[Artifacts, OutputFiles]
        A tuple containing the artifacts and output files.
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
    data_frame = artifacts_store.get(parent.hash).data_frame
    data_frame = data_frame.Filter(node.data.expression, node.data.name)

    return Artifacts(data_frame=data_frame), OutputFiles()


def weight(
    node: Node,
    artifacts_store: ArtifactsStore,
) -> tuple[Artifacts, OutputFiles]:
    """
    Declare a weight on an `RDataFrame` object.

    The weight is defined to the `RDataFrame` and the modified `RDataFrame` is
    stored as an artifact.

    Parameters
    ----------
    node : Node
        The `"weight"` operation node that is being processed.

    artifacts_store : ArtifactsStore
        The store for the artifacts.

    Returns
    -------
    tuple[Artifacts, OutputFiles]
        A tuple containing the artifacts and output files.
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
    data_frame = artifacts_store.get(parent.hash).data_frame
    data_frame = data_frame.Define(
        f"{WEIGHT_PREFIX}{node.data.name}",
        node.data.expression,
    )

    return Artifacts(data_frame=data_frame), OutputFiles()


def weight_product(
    node: Node,
    artifacts_store: ArtifactsStore,
) -> tuple[Artifacts, OutputFiles]:
    """
    Produce a total weight column by multiplying all weights declared in the
    node data.

    The total weight is defined on the `RDataFrame` and the modified
    `RDataFrame` is stored as an artifact.

    Parameters
    ----------
    node : Node
        The `"weight_product"` operation node that is being processed.

    artifacts_store : ArtifactsStore
        The store for the artifacts.

    Returns
    -------
    tuple[Artifacts, OutputFiles]
        A tuple containing the artifacts and output files.
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
    data_frame = artifacts_store.get(parent.hash).data_frame

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

    return Artifacts(data_frame=data_frame), OutputFiles()


def histogram(
    node: Node, artifacts_store: ArtifactsStore
) -> tuple[Artifacts, OutputFiles]:
    """
    Declare a lazy `TH1D` histogram operation on the `RDataFrame`.

    The artifacts object contains the `RDataFrame` as well as the lazy histogram
    object.

    Parameters
    ----------
    node : Node
        The `"histogram"` operation node that is being processed.

    artifacts_store : ArtifactsStore
        The store for the artifacts.

    Returns
    -------
    tuple[Artifacts, OutputFiles]
        A tuple containing the artifacts and output files.
    """
    # Log context of this node
    logger.debug(
        "\n".join(
            [
                "Declare histogram",
                f"    campaign:   {node.data.campaign}",
                f"    channel:    {node.data.channel}",
                f"    category:   {node.data.category}",
                f"    dataset:    {node.data.dataset}",
                f"    process:    {node.data.process}",
                f"    variation:  {node.data.variation}",
                f"    variable:   {node.data.variable}",
                f"    expression: {node.data.expression}",
            ]
        )
    )

    # Assert that the node has exactly one parent and get that parent node
    parent = _get_single_parent(node)

    # Get the data frame from the parent
    data_frame = artifacts_store.get(parent.hash).data_frame

    # Define custom expression as column if provided
    column = node.data.variable
    if node.data.expression is not None:
        column = f"__private__{node.data.variable}"
        data_frame = data_frame.Define(column, node.data.expression)
        logger.debug(
            f"Defined custom expression for variable '{node.data.variable}' "
            + f"as column with expression '{node.data.expression}'"
        )

    # Declare the lazy histogram operation
    lazy_hist = data_frame.Histo1D(
        (
            node.data.variable,
            node.data.variable,
            len(node.data.bin_edges) - 1,
            np.array(node.data.bin_edges),
        ),
        column,
        TOTAL_WEIGHT_NAME,
    )

    return Artifacts(
        data_frame=data_frame,
        lazy_hist=lazy_hist,
    ), OutputFiles()
