from networkx import DiGraph, topological_sort

from xyh.core.graph.artifacts import Artifacts, ArtifactsStore
from xyh.core.graph.operations import get_operation_fn


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
):
    """
    Execute the given list of disjoint processing graphs.

    Parameters
    ----------
    graphs : list[DiGraph]
        List of disjoint processing graphs to execute.
    """

    for graph in graphs:
        # Execute the graph and store artifacts for each node
        _execute_graph(graph)
