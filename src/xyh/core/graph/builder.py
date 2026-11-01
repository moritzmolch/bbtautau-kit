import hashlib
import json
import os
from pathlib import Path

from networkx import (
    DiGraph,
    weakly_connected_components,
)

from xyh.core.graph.node import Node, Output
from xyh.core.specs.specs import Context, HistogramsOutput, WeightProduct
from xyh.core.specs.storage import SpecsStorage


def build_graph_from_leaf_nodes(
    leaf_nodes: list[Node],
) -> DiGraph:
    """
    Build a `DiGraph` from a list of nodes.

    The connections between nodes are established based on the parent-child
    relationships. These are defined by the `parents` attribute of each node.
    The list `nodes` only needs to contain the leaf nodes of the graph.

    Parameters
    ----------
    leaf_nodes : list[Node]
        The leaf nodes of the graph.

    Returns
    -------
    DiGraph
        A directed graph representing the relationships between computation
        nodes.
    """

    # Create an empty directed grapb
    graph = DiGraph()

    # Function to recursively add nodes and edges starting from the leaves
    def _add_nodes_and_edges(node: Node):
        # Terminate if node has already been added to the graph
        if node.hash in graph:
            return

        # Add the current node to the graph
        graph.add_node(node.hash, node=node)

        # Take care of parent nodes: add the nodes (with recursive function
        # call) and add parent -> node edges when both nodes are present
        for parent in node.parents:
            _add_nodes_and_edges(parent)
            graph.add_edge(parent.hash, node.hash)

    # Fill the graph with the nodes and edges starting from the lead nodes
    for leaf_node in leaf_nodes:
        _add_nodes_and_edges(leaf_node)

    return graph


def _build_context_nodes_for_filters_and_weights_operations(
    context: Context,
    specs_storage: SpecsStorage,
) -> Node:
    """
    Build chain of nodes from input file loading, filter operations, and weight
    calculations for a given `context`.

    The function returns the last node of the constructed chain, which can be
    used as parent for subsequent steps.

    Parameters
    ----------
    context : Context
        The context of the graph, including campaign, channel, category,
        dataset, process, and variation.

    specs_storage : SpecsStorage
        The storage containing specifications for datasets, filters, weights,
        and histograms.

    Returns
    -------
    Node
        The last node in the chain of operations, which can be used as a parent
        for subsequent nodes in the graph.
    """

    # Create the input file node
    dataset_spec = specs_storage.get_dataset_spec(context)
    n = Node(
        operation="input_files",
        data=dataset_spec,
    )

    # Create filter nodes
    for filter_spec in specs_storage.get_filters_specs(context):
        n = Node(
            operation="filter",
            data=filter_spec,
            parents=(n,),
        )

    # Create the weight nodes
    weights_spec = specs_storage.get_weights_specs(context)
    for weight_spec in weights_spec:
        n = Node(
            operation="weight",
            data=weight_spec,
            parents=(n,),
        )

    # Create the total weight multiplication node
    n = Node(
        operation="weight_product",
        data=WeightProduct(weights=weights_spec),
        parents=(n,),
    )

    return n


def _build_context_nodes_for_histograms(
    context: Context,
    spec_storage: SpecsStorage,
    variables: list[str],
) -> list[Node]:
    """
    Build chain of nodes from input file loading, filter operations, weight
    calculations, and histogram creation for a given `context`.

    The function returns the leaf nodes of the constructed chain, which can be
    used as parent for subsequent steps.

    Parameters
    ----------
    context : Context
        The context of the graph, including campaign, channel, category,
        dataset, process, and variation.

    specs_storage : SpecsStorage
        The storage containing specifications for datasets, filters, weights,
        and histograms.

    Returns
    -------
    list[Node]
        The leaf nodes in the chain of operations, which can be used as parents
        for subsequent nodes in the graph.
    """

    # Construct the chain of nodes for input files, filters, and weights
    n = _build_context_nodes_for_filters_and_weights_operations(
        context=context,
        specs_storage=spec_storage,
    )

    # Create the histogram nodes
    leaf_nodes = []
    for variable in variables:
        histogram_spec = spec_storage.get_histogram_specs(context, variable)
        leaf_nodes.append(
            Node(
                operation="histogram",
                data=histogram_spec,
                parents=(n,),
            )
        )

    return leaf_nodes


def build_histograms_graph(
    contexts: list[Context],
    variables: list[str],
    spec_storage: SpecsStorage,
    output_dir: Path,
) -> list[DiGraph]:
    """
    Build a directed graph of nodes for histogram creation.

    The result is returned as a list of graphs, which are disjoint from each
    other and which can be processed independently.

    Parameters
    ----------
    contexts : list[Context]
        A list of analysis contexts, each containing campaign, channel,
        category, dataset, process, and variation information.

    variables : list[str]
        List of variables for which histograms will be created.

    specs_storage : SpecsStorage
        The storage containing specifications for datasets, filters, weights,
        and histograms.

    output_dir : Path
        The directory where the generated histograms will be saved.

    Returns
    -------
    list[DiGraph]
        List of disjoint processing graphs for histogram creation.
    """

    # Create a list to hold all leaf nodes for the graph
    all_leaf_nodes = []

    # Iterate over each context to build the corresponding nodes
    for context in contexts:
        # Build the chain of nodes for the current context
        leaf_nodes = _build_context_nodes_for_histograms(
            context=context,
            spec_storage=spec_storage,
            variables=variables,
        )

        # Add the leaf nodes to the overall list
        all_leaf_nodes.extend(leaf_nodes)

    # Build the directed graph from all leaf nodes for histogram creation
    graph = build_graph_from_leaf_nodes(all_leaf_nodes)

    # Find disjoint subgraphs
    subgraphs = [
        graph.subgraph(c).copy() for c in weakly_connected_components(graph)
    ]

    # Append a "write_histograms" node to each subgraph
    for subgraph in subgraphs:
        # Get the subgraph's hash for output file naming
        subgraph_hash = hashlib.sha256(
            json.dumps(
                {
                    "nodes": sorted(subgraph.nodes),
                    "edges": sorted(subgraph.edges),
                },
            ).encode()
        ).hexdigest()

        # Get the leaf nodes of the subgraph
        leaf_nodes = [
            subgraph.nodes[h]["node"]
            for h in subgraph.nodes
            if subgraph.out_degree(h) == 0
        ]

        # Append a "write_histograms" node with all leaf nodes as parents
        n = Node(
            operation="write_histograms",
            data=HistogramsOutput(
                output_dir=str(output_dir),
                subgraph_hash=subgraph_hash,
            ),
            parents=tuple(leaf_nodes),
            outputs={
                "hists_file": Output(
                    path=os.path.join(
                        str(output_dir),
                        f"histograms_{subgraph_hash}.root",
                    ),
                ),
            },
        )
        subgraph.add_node(n.hash, node=n)
        subgraph.add_edges_from((leaf.hash, n.hash) for leaf in leaf_nodes)

    return subgraphs
