from networkx import DiGraph, topological_sort

from xyh.core.graph.artifacts import Artifacts, ArtifactsStore
from xyh.core.graph.operations import get_operation_fn


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


def _execute_graph(graph: DiGraph) -> list[Artifacts]:
    """
    Execute a single directed graph and store artifacts for each node.

    Parameters
    ----------
    graph : DiGraph
        The directed graph to execute.
    """

    # Artifacts of all output nodes of this graph
    artifacts_store = ArtifactsStore()

    for node_hash in topological_sort(graph):
        # Get the node object
        node = graph.nodes[node_hash]["node"]

        # Get artifacts from parent nodes
        input_artifacts = artifacts_store.get(*graph.predecessors(node_hash))

        # Get the operation function and execute it
        operation = get_operation_fn(node)
        output_artifacts = operation(node, input_artifacts)

        # Put the output artifacts into the store
        artifacts_store.put(node_hash, output_artifacts)

    # Get artifacts and output files of leaves
    leaf_hashes = [n for n in graph.nodes if graph.out_degree(n) == 0]

    return list(artifacts_store.get(*leaf_hashes).values())


def execute(
    graphs: list[DiGraph],
) -> list[Artifacts]:
    """
    Execute the given list of disjoint processing graphs.

    Parameters
    ----------
    graphs : list[DiGraph]
        List of disjoint processing graphs to execute.
    """

    # Prune graphs to remove output nodes, for which the outputs already exist
    pruned_graphs = [_prune_graph(graph) for graph in graphs]

    # Execute each graph and fetch artifacts
    artifacts = []
    for graph in pruned_graphs:
        artifacts.extend(_execute_graph(graph))

    return artifacts
