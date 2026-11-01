import os
from dataclasses import asdict

from networkx import DiGraph, compose_all
from networkx.readwrite import json_graph

from xyh.core.graph.node import Node

# Node type names written to the graph specs for each operation
_TYPE_NAMES = {
    "input_files": "InputFilesNode",
    "filter": "FilterNode",
    "weight": "WeightNode",
    "weight_product": "WeightProductNode",
    "histogram": "HistogramNode",
    "snapshot": "SnapshotNode",
    "binning": "BinningNode",
    "write_histograms": "WriteHistogramsNode",
    "write_snapshots": "WriteSnapshotsNode",
    "write_binning": "WriteBinningNode",
}


def _node_spec(node: Node, graph: DiGraph) -> dict:
    """
    Create a JSON-serializable description of a node.

    The attributes of the description are the ones the downstream stages (merge
    of histograms, plotting, inspection scripts) rely on. For histogram nodes,
    `output_file` is the path of the file holding the histogram relative to the
    histograms directory and `hist_path` is the path of the histogram inside
    this file.

    Parameters
    ----------
    node : Node
        The node to describe.

    graph : DiGraph
        The graph containing the node.

    Returns
    -------
    dict
        The description of the node.
    """

    data = node.data
    match node.operation:
        case "input_files":
            return asdict(data)
        case "filter" | "weight":
            return {"name": data.name, "expression": data.expression}
        case "weight_product":
            return {"weights": [w.name for w in data.weights]}
        case "histogram" | "binning":
            spec = {
                "campaign": data.binning.campaign,
                "channel": data.binning.channel,
                "category": data.binning.category,
                "dataset": data.dataset,
                "process": data.process,
                "variation": data.variation,
                "variable": data.binning.variable,
                "expression": data.binning.expression,
                "bin_edges": list(data.binning.bin_edges),
            }
            if node.operation == "binning":
                spec["output_file"] = node.outputs["binning_file"].path
                return spec

            # The histograms are written by the write node following this node
            (write_hash,) = graph.successors(node.hash)
            write_node: Node = graph.nodes[write_hash]["node"]
            spec["output_file"] = os.path.relpath(
                write_node.outputs["hists_file"].path,
                write_node.data.output_dir,
            )
            spec["hist_path"] = "/".join(
                [
                    data.binning.campaign,
                    data.binning.channel,
                    data.binning.category,
                    data.dataset,
                    data.process,
                    f"{data.binning.variable}__{data.variation}",
                ]
            )
            return spec
        case "snapshot":
            spec = asdict(data)
            spec["output_file"] = node.outputs["snapshot_file"].path
            return spec
        case _:
            return {"outputs": {k: v.path for k, v in node.outputs.items()}}


def graphs_to_specs(graphs: list[DiGraph]) -> dict:
    """
    Convert processing graphs into a JSON-serializable node-link dictionary.

    Parameters
    ----------
    graphs : list[DiGraph]
        The disjoint processing graphs created by the graph builders.

    Returns
    -------
    dict
        The node-link data of the combined graph. Each node has the attributes
        `type` and `spec`.
    """

    if len(graphs) == 0:
        return json_graph.node_link_data(DiGraph())

    combined = compose_all(graphs)
    specs_graph = DiGraph()
    for node_hash, attributes in combined.nodes(data=True):
        node: Node = attributes["node"]
        specs_graph.add_node(
            node_hash,
            type=_TYPE_NAMES[node.operation],
            spec=_node_spec(node, combined),
        )
    specs_graph.add_edges_from(combined.edges)

    return json_graph.node_link_data(specs_graph)
