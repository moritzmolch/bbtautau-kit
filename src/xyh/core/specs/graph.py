import hashlib
import json
from collections import OrderedDict
from dataclasses import asdict, dataclass
from functools import cached_property
from pathlib import Path

import networkx

# ------------------------------------------------------------------------------
# Graph node classes
# ------------------------------------------------------------------------------

# region


@dataclass(frozen=True)
class GraphNode:
    @cached_property
    def hash(self):
        return hashlib.sha256(json.dumps(asdict(self)).encode()).hexdigest()


@dataclass(frozen=True)
class InputFilesNode(GraphNode):
    campaign: str
    channel: str
    dataset: str
    files: list[str]
    friend_files: dict[str, list[str]]


@dataclass(frozen=True)
class FilterNode(GraphNode):
    name: str
    expression: str
    depends_on: str | None


@dataclass(frozen=True)
class WeightsNode(GraphNode):
    name: str
    expression: str
    depends_on: str | None


@dataclass(frozen=True)
class SnapshotNode(GraphNode):
    campaign: str
    channel: str
    category: str
    dataset: str
    process: str
    variation: str
    output_file: str


@dataclass(frozen=True)
class HistogramNode(GraphNode):
    campaign: str
    channel: str
    category: str
    dataset: str
    process: str
    variation: str
    variable: str
    expression: str
    bin_edges: list[int | float]
    output_file: str


# endregion


def cat_weights(weights: OrderedDict[str, str]) -> str:
    # Concatenate all weights into a single expression
    return " * ".join(w for w in weights.values())


def _get_dataset_spec(
    dataset_specs,
    campaign,
    channel,
    dataset,
):
    # Return the first dataset matching the names of the campaign, channeln and
    # dataset
    dataset_spec = next(
        iter(
            (
                ds
                for ds in dataset_specs
                if (
                    ds["campaign"] == campaign
                    and ds["channel"] == channel
                    and ds["dataset"] == dataset
                )
            ),
        ),
        None,
    )

    # Raise an exception if no spec has been found
    if dataset_spec is None:
        raise ValueError(
            f"Dataset spec for campaign {campaign}, channel {channel}, "
            + f"dataset {dataset} not found"
        )

    return dataset_spec


def _get_histogram_specs(
    histogram_specs,
    campaign,
    channel,
    category,
):
    # Return all histogram specs matching the names of the campaign, channel,
    # and category
    histogram_specs = list(
        hs
        for hs in histogram_specs
        if (
            hs["campaign"] == campaign
            and hs["channel"] == channel
            and hs["category"] == category
        )
    )

    # Raise an exception if no spec has been found
    if len(histogram_specs) == 0:
        raise ValueError(
            f"Histogram specs for campaign {campaign}, channel {channel}, "
            + f"category {category} not found"
        )

    return histogram_specs


class GraphBuilder:
    def __init__(self):
        self.nodes = {}
        self.edges = set()
        self.last_node: GraphNode | None = None

    def add_node(self, node: GraphNode, last_node: GraphNode | None = None):
        node_hash = node.hash
        self.nodes[node_hash] = node

        if last_node is not None:
            last_node_hash = last_node.hash
            self.edges.add((last_node_hash, node_hash))

        self.last_node = node


def build_graph(
    dataset_specs,
    histogram_specs,
    filters_and_weights_specs,
    mode,
):
    # Check if 'mode' has valid value
    modes = ["snapshot", "histogram"]
    if mode not in modes:
        raise ValueError(f"Argument node must be from {modes}")

    # Create the graph object
    graph_builder = GraphBuilder()

    for fw_spec in filters_and_weights_specs:
        # Get spec attributes
        campaign = fw_spec["campaign"]
        channel = fw_spec["channel"]
        category = fw_spec["category"]
        dataset = fw_spec["dataset"]
        process = fw_spec["process"]
        variation = fw_spec["variation"]

        # --- Input files ------------------------------------------------------

        # Create the input file node
        # No edge is added, meaning that this node is a root node
        dataset_spec = _get_dataset_spec(
            dataset_specs,
            campaign,
            channel,
            dataset,
        )
        input_files_node = InputFilesNode(
            campaign=campaign,
            channel=channel,
            dataset=dataset,
            files=dataset_spec["files"],
            friend_files=dataset_spec["friend_files"],
        )
        graph_builder.add_node(input_files_node)

        # --- Filters ----------------------------------------------------------

        # Chain filters
        last_filter = None
        for name, expression in fw_spec["filters"].items():
            filter_node = FilterNode(
                name=name,
                expression=expression,
                depends_on=last_filter.hash if last_filter else None,
            )
            last_filter = filter_node
            graph_builder.add_node(filter_node)

        # --- Weights ----------------------------------------------------------

        # Create weights node with all weights concatenated into a single
        # expression
        weights = cat_weights(OrderedDict(fw_spec["weights"]))
        weights_node = WeightsNode(
            name="weights",
            expression=weights,
            depends_on=last_filter.hash if last_filter else None,
        )
        graph_builder.add_node(weights_node)

        # --- Output nodes (snapshot or histogram) -----------------------------

        if mode == "snapshot":
            # Define output file path for the snapshot node
            snapshot_output_file = str(
                Path(
                    campaign,
                    f"{channel}__{category}",
                    f"{process}__{dataset}__{variation}.root",
                )
            )

            # Create the snapshot node
            snapshot_node = SnapshotNode(
                campaign=campaign,
                channel=channel,
                category=category,
                dataset=dataset,
                process=process,
                variation=variation,
                output_file=snapshot_output_file,
            )
            graph_builder.add_node(snapshot_node, last_node=weights_node)

        elif mode == "histogram":
            # Create the histogram nodes for each variable; attach all
            # histograms to the last filter or weights node
            last_node = graph_builder.last_node

            for histogram_spec in _get_histogram_specs(
                histogram_specs,
                campaign,
                channel,
                category,
            ):
                # Define output file path for the histogram node
                histogram_output_file = str(
                    Path(
                        campaign,
                        f"{channel}__{category}",
                        f"{process}__{dataset}__{histogram_spec['variable']}__{variation}.root",
                    )
                )

                # Create the histogram node. Do not update the last node, as
                # all histograms shall be added to the same input node
                histogram_node = HistogramNode(
                    campaign=campaign,
                    channel=channel,
                    category=category,
                    dataset=dataset,
                    process=process,
                    variation=variation,
                    variable=histogram_spec["variable"],
                    expression=histogram_spec["expression"],
                    bin_edges=histogram_spec["bin_edges"],
                    output_file=histogram_output_file,
                )
                graph_builder.add_node(histogram_node, last_node=last_node)

    # --- Create final graph ---------------------------------------------------

    # Create the graph object
    graph = networkx.DiGraph()
    for node in graph_builder.nodes.values():
        graph.add_node(node.hash, spec=asdict(node))
    graph.add_edges_from(graph_builder.edges)

    return graph
