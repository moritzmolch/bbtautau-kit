import logging
import multiprocessing
from concurrent.futures import as_completed

import ROOT
from networkx import DiGraph, topological_sort

from xyh.core.graph.artifacts import Artifacts, ArtifactsStore
from xyh.core.graph.operations import get_operation_fn
from xyh.core.parallel import (
    _process_pool,
)

# Set up logging
logger = logging.getLogger(__name__)


def _subgraph_label(graph: DiGraph) -> str:
    """
    Return a human-readable label for a subgraph.

    The label is built from the campaign, channel, and dataset of the
    `input_files` nodes of the subgraph.

    Parameters
    ----------
    graph : DiGraph
        The subgraph to label.

    Returns
    -------
    str
        The label of the subgraph.
    """

    labels = sorted(
        {
            f"campaign='{n.data.campaign}', channel='{n.data.channel}', "
            f"dataset='{n.data.dataset}'"
            for n in (d["node"] for _, d in graph.nodes(data=True))
            if n.operation == "input_files"
        }
    )
    if not labels:
        return "subgraph without input files"
    return "; ".join(labels)


def _prune_graph(graph: DiGraph) -> DiGraph:
    """
    Prune the graph by removing nodes that do not contribute to the output.

    Parameters
    ----------
    graph : DiGraph
        The directed graph to prune.

    Returns
    -------
    DiGraph
        The pruned directed graph.
    """

    # Required nodes: missing outputs
    required = set()

    for node_hash in reversed(list(topological_sort(graph))):
        # Get the node
        node = graph.nodes[node_hash]["node"]

        # Check if node has missing outputs
        missing_outputs = any(not o.exists() for o in node.outputs.values())

        # Check if this is a leaf node
        is_leaf = graph.out_degree(node_hash) == 0

        # Check if this node is required by any other successor nodes
        is_required_by_successors = any(
            s in required for s in graph.successors(node_hash)
        )

        if (
            missing_outputs
            or (is_leaf and not node.outputs)
            or is_required_by_successors
        ):
            required.add(node_hash)

    return graph.subgraph(required).copy()


def _execute_graph(graph: DiGraph, num_threads: int = 1) -> list[Artifacts]:
    """
    Execute a single directed graph and store artifacts for each node.

    Parameters
    ----------
    graph : DiGraph
        The directed graph to execute.

    num_threads : int, optional
        The number of threads to use for parallel `ROOT` processing. (default:
        1)
    """

    # Enable multi-threading in ROOT if num_threads > 1
    if num_threads > 1:
        ROOT.EnableImplicitMT(num_threads)

    try:
        # Artifacts of all output nodes of this graph
        artifacts_store = ArtifactsStore()

        for node_hash in topological_sort(graph):
            # Get the node object
            node = graph.nodes[node_hash]["node"]

            # Get artifacts from parent nodes
            input_artifacts = artifacts_store.get(
                *graph.predecessors(node_hash)
            )

            # Get the operation function and execute it
            operation = get_operation_fn(node)
            output_artifacts = operation(node, input_artifacts)

            # Put the output artifacts into the store
            artifacts_store.put(node_hash, output_artifacts)

        # Get artifacts and output files of leaves
        leaf_hashes = [n for n in graph.nodes if graph.out_degree(n) == 0]

    finally:
        # Disable multi-threading in ROOT after execution
        if num_threads > 1:
            ROOT.DisableImplicitMT()

    return list(artifacts_store.get(*leaf_hashes).values())


def execute(
    graphs: list[DiGraph],
    num_workers: int = 1,
    num_threads: int = 1,
) -> list[Artifacts]:
    """
    Execute the given list of disjoint processing graphs.

    Parameters
    ----------
    graphs : list[DiGraph]
        List of disjoint processing graphs to execute.

    num_workers : int, optional
        The number of workers to use for parallel execution. (default: 1)

    num_threads : int, optional
        The number of threads to use for each worker. (default: 1)
    """

    # Prune graphs to remove output nodes, for which the outputs already exist
    pruned_graphs = [
        g
        for g in (_prune_graph(graph) for graph in graphs)
        if g.number_of_nodes() > 0
    ]
    n_graphs = len(pruned_graphs)

    # Processing artifacts of all output nodes of all graphs
    artifacts = []

    if num_workers == 1:
        # For a single worker, execute graphs sequentially
        for i, graph in enumerate(pruned_graphs):
            artifacts.extend(_execute_graph(graph, num_threads=num_threads))
            label = _subgraph_label(graph)
            logger.info(
                f"Completed execution of subgraph {i + 1}/{n_graphs}: {label}"
            )

    else:
        # For multiple workers, set up a multiprocessing pool
        with _process_pool(
            max_workers=num_workers,
            mp_context=multiprocessing.get_context("spawn"),
        ) as pool:
            # Submit all graphs to the pool for execution
            futures = {
                pool.submit(
                    _execute_graph,
                    graph,
                    num_threads=num_threads,
                ): graph
                for graph in pruned_graphs
            }

            # Collect results as they complete
            for i, future in enumerate(as_completed(futures)):
                artifacts.extend(future.result())
                label = _subgraph_label(futures[future])
                logger.info(
                    f"Completed execution of subgraph {i + 1}/{n_graphs}: {label}"
                )

    return artifacts
