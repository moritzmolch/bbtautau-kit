import hashlib
import json
import logging
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from functools import cached_property
from pathlib import Path
from time import time
from typing import Any

import networkx
import numpy as np
import ROOT

from .specs import Dataset, FiltersAndWeights, Histogram

# Set up logger
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Graph node classes
# ------------------------------------------------------------------------------

# region


class GraphNodeMeta(type):
    _node_types = {}

    def __new__(cls, name, bases, cls_dict) -> type:
        # Explicitly set the type attribute of the class to its name.
        cls_dict.update({"type": name})

        # Create the new class
        new_cls = super().__new__(cls, name, bases, cls_dict)

        # Add the new type to the _node_types dictionary
        cls._node_types[name] = new_cls

        return new_cls

    @classmethod
    def create_instance(cls, class_name, *args, **kwargs) -> "GraphNode":
        # Create a new instance of the class with the given name
        if class_name not in cls._node_types:
            raise ValueError(f"Unknown class name: {class_name}")
        return cls._node_types[class_name](*args, **kwargs)


@dataclass(frozen=True)
class GraphNode(metaclass=GraphNodeMeta):
    @cached_property
    def hash(self):
        return hashlib.sha256(json.dumps(asdict(self)).encode()).hexdigest()


@dataclass(frozen=True)
class InputFilesNode(GraphNode):
    campaign: str
    channel: str
    dataset: str
    files: dict[str, list[str]]


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
    if len(weights) == 0:
        return "1.0"
    return " * ".join(f"({w})" for w in weights.values())


def _get_dataset_spec(
    dataset_specs: list[Dataset],
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
                    ds.campaign == campaign
                    and ds.channel == channel
                    and ds.dataset == dataset
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
) -> list[Histogram]:
    # Return all histogram specs matching the names of the campaign, channel,
    # and category
    histogram_specs = [
        hs
        for hs in histogram_specs
        if (
            hs.campaign == campaign
            and hs.channel == channel
            and hs.category == category
        )
    ]

    # Raise an exception if no spec has been found
    if len(histogram_specs) == 0:
        raise ValueError(
            f"Histogram specs for campaign {campaign}, channel {channel}, "
            + f"category {category} not found"
        )

    return histogram_specs


# ------------------------------------------------------------------------------
# Graph building
# ------------------------------------------------------------------------------


class GraphBuilder:
    def __init__(self):
        self.nodes = {}
        self.edges = set()
        self.last_node: GraphNode | None = None

    def add_node(self, node: GraphNode, last_node: GraphNode | None = None):
        # Get node hash and add it to the nodes dictionary
        node_hash = node.hash
        self.nodes[node_hash] = node

        # Set the last node to the provided last_node argument if it is not None
        if last_node is not None:
            self.last_node = last_node

        # Add edge from last node to the current node if self.last_node is not None
        if self.last_node is not None:
            self.edges.add((self.last_node.hash, node_hash))

        # Set new last node to the current one
        self.last_node = node

    def clear_last_node(self):
        self.last_node = None


def create_graph_specs(
    dataset_specs: list[Dataset],
    histogram_specs: list[Histogram],
    filters_and_weights_specs: list[FiltersAndWeights],
    mode,
) -> dict[str, Any]:
    # Check if 'mode' has valid value
    modes = ["snapshot", "histogram"]
    if mode not in modes:
        raise ValueError(f"Argument node must be from {modes}")

    # Create the graph object
    graph_builder = GraphBuilder()

    for fw_spec in filters_and_weights_specs:
        # Clear the last node in the graph builder to start with a new
        # independent subgraph
        graph_builder.clear_last_node()

        # Get spec attributes
        campaign = fw_spec.campaign
        channel = fw_spec.channel
        category = fw_spec.category
        dataset = fw_spec.dataset
        process = fw_spec.process
        variation = fw_spec.variation

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
            files=dataset_spec.files,
        )
        graph_builder.add_node(input_files_node)

        # --- Filters ----------------------------------------------------------

        # Chain filters
        for name, expression in fw_spec.filters.items():
            filter_node = FilterNode(
                name=name,
                expression=expression,
                depends_on=graph_builder.last_node.hash,
            )
            graph_builder.add_node(filter_node)

        # --- Weights ----------------------------------------------------------

        # Create weights node with all weights concatenated into a single
        # expression
        weights = cat_weights(OrderedDict(fw_spec.weights))
        weights_node = WeightsNode(
            name="weights",
            expression=weights,
            depends_on=graph_builder.last_node.hash,
        )
        graph_builder.add_node(weights_node)

        # --- Output nodes (snapshot or histogram) -----------------------------

        # Set input node for output nodes to the current last node of the graph
        last_node = graph_builder.last_node

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
            graph_builder.add_node(snapshot_node, last_node=last_node)

        elif mode == "histogram":
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
                        f"{process}__{dataset}__{histogram_spec.variable}__{variation}.root",
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
                    variable=histogram_spec.variable,
                    expression=histogram_spec.expression,
                    bin_edges=histogram_spec.bin_edges,
                    output_file=histogram_output_file,
                )
                graph_builder.add_node(histogram_node, last_node=last_node)

    # --- Create final graph ---------------------------------------------------

    # Create the graph object
    graph = networkx.DiGraph()
    for node in graph_builder.nodes.values():
        graph.add_node(node.hash, type=node.type, spec=asdict(node))
    graph.add_edges_from(graph_builder.edges)

    # Convert the graph into a JSON-serializable format
    graph_specs = networkx.readwrite.json_graph.node_link_data(graph)

    return graph_specs


# ------------------------------------------------------------------------------
# Graph processing
# ------------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Actions on nodes
# -----------------------------------------------------------------------------


def _input_files(
    node: InputFilesNode,
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    logger.debug(
        "\n".join(
            [
                "Initialize data frame from input files for",
                f"    campaign: {node.campaign}",
                f"    channel:  {node.channel}",
                f"    dataset:  {node.dataset}",
            ]
        )
    )

    start = time()

    # Create the chains of the input files
    chains = {}
    for key, files in node.files.items():
        chain = ROOT.TChain("ntuple")
        for file in files:
            chain.Add(file)
        chains[key] = chain

    # Add friends to main chain
    main_chain = chains.pop("main")
    for key, chain in chains.items():
        if chain.GetListOfFiles().GetEntries() > 0:
            main_chain.AddFriend(chain)

    # Create the RDataFrame
    data_frame = ROOT.RDataFrame(main_chain)

    stop = time()

    delta = round(stop - start, 2)
    logger.debug(
        "\n".join(
            [
                f"Initialized data frame in {delta} s",
            ]
        )
    )

    return {
        "data_frame": data_frame,
        "main_chain": main_chain,
        "friend_chains": chains,
    }


def _filter(node: FilterNode, artifacts: dict[str, Any]) -> dict[str, Any]:
    logger.debug(
        "\n".join(
            [
                "Declare selection on data frame",
                f"    name:       {node.name}",
                f"    expression: {node.expression}",
            ]
        )
    )
    if len(artifacts) != 1:
        raise ValueError(
            "Expect exactly one input artifact from predecessor node"
        )
    data_frame = next(iter(artifacts.values()))["data_frame"]
    data_frame = data_frame.Filter(node.expression, node.name)
    return {
        "data_frame": data_frame,
    }


def _weights(node: WeightsNode, artifacts: dict[str, Any]) -> dict[str, Any]:
    # Set the expression
    expression = node.expression
    logger.debug(
        "\n".join(
            [
                "Declare weights on data frame",
                f"    expression: '{expression}'",
            ]
        )
    )

    # Get the data frame from the predecessor node
    if len(artifacts) != 1:
        raise ValueError(
            "Expect exactly one input artifact from predecessor node"
        )
    data_frame = next(iter(artifacts.values()))["data_frame"]

    # Define the new total weight
    data_frame = data_frame.Define("__total_weight", expression)

    return {
        "data_frame": data_frame,
    }


def _snapshot(
    node: SnapshotNode, artifacts: dict[str, Any], output_dir: Path
) -> dict[str, Any]:
    logger.debug(
        "\n".join(
            [
                "Declare data frame snapshot",
                f"    campaign:  {node.campaign}",
                f"    channel:   {node.channel}",
                f"    category:  {node.category}",
                f"    dataset:   {node.dataset}",
                f"    process:   {node.process}",
                f"    variation: {node.variation}",
            ]
        )
    )
    if len(artifacts) != 1:
        raise ValueError(
            "Expect exactly one input artifact from predecessor node"
        )

    # Get the data frame from the predecessor node
    data_frame = next(iter(artifacts.values()))["data_frame"]
    options = ROOT.RDF.RSnapshotOptions()
    options.fLazy = True

    # Create the output directory if it does not exist yet
    output_file = output_dir / Path(node.output_file)
    if not output_file.parent.exists():
        output_file.parent.mkdir(parents=True)
        logger.debug(f"Created directory {output_file.parent}")

    # Trigger snapshot creation
    snapshot = data_frame.Snapshot(
        "ntuple",
        str(output_file),
        data_frame.GetColumnNames(),
        options,
    )

    return {
        "lazy_object": snapshot,
        "lazy_object_type": "snapshot",
        "output_file": output_file,
    }


def _histogram(
    node: HistogramNode,
    artifacts: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    logger.debug(
        "\n".join(
            [
                "Declare histogram",
                f"    campaign:   {node.campaign}",
                f"    channel:    {node.channel}",
                f"    category:   {node.category}",
                f"    dataset:    {node.dataset}",
                f"    process:    {node.process}",
                f"    variation:  {node.variation}",
                f"    variable:   {node.variable}",
                f"    expression: {node.expression}",
            ]
        )
    )
    if len(artifacts) != 1:
        raise ValueError(
            "Expect exactly one input artifact from predecessor node"
        )

    # Load output data frame from predecessor node
    artifacts = next(iter(artifacts.values()))
    data_frame = artifacts["data_frame"]

    # Define custom expression if needed
    column = node.variable
    if node.variable != node.expression:
        column = f"__{node.variable}"
        data_frame = data_frame.Define(column, node.expression)

    # Get the histogram
    rh = data_frame.Histo1D(
        (
            node.variable,
            node.variable,
            len(node.bin_edges) - 1,
            np.array(node.bin_edges),
        ),
        column,
        "__total_weight",
    )

    return {
        "data_frame": data_frame,
        "lazy_object": rh,
        "lazy_object_type": "histogram",
        "output_file": output_dir / node.output_file,
    }


def action(
    node: GraphNode,
    artifacts: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    if isinstance(node, InputFilesNode):
        return _input_files(node, artifacts)
    elif isinstance(node, FilterNode):
        return _filter(node, artifacts)
    elif isinstance(node, WeightsNode):
        return _weights(node, artifacts)
    elif isinstance(node, SnapshotNode):
        return _snapshot(node, artifacts, output_dir)
    elif isinstance(node, HistogramNode):
        return _histogram(node, artifacts, output_dir)
    else:
        raise ValueError(f"Unknown node type: {type(node)}")


# -----------------------------------------------------------------------------
# Graph processing
# -----------------------------------------------------------------------------


def run_subgraph(
    subgraph: networkx.DiGraph,
    output_dir: Path,
):
    # Store for all artifacts of actions on graph nodes. The key corresponds
    # to the node hash and the value to an output dictionary.
    artifacts = {}

    logger.info(f"Running subgraph {hash(subgraph)}")

    start = time()

    # Declare actions
    for node_hash in networkx.topological_sort(subgraph):
        # Get the node's spec and sanitize output files
        spec = subgraph.nodes[node_hash]["spec"]

        # Get the node specs
        node = GraphNode.create_instance(
            subgraph.nodes[node_hash]["type"],
            **spec,
        )

        # Get predecessors' artifacts
        predecessors = subgraph.predecessors(node_hash)
        input_artifacts = {k: artifacts[k] for k in predecessors}

        # Execute the action on the node
        artifacts[node_hash] = action(node, input_artifacts, output_dir)

    # Get the hashes of leaf nodes. Only keep leafs, for which output files
    # do not exist yet
    leaf_nodes = []
    for leaf_node in list(networkx.topological_generations(subgraph))[-1]:
        output_file = artifacts[leaf_node]["output_file"]
        if output_file.exists():
            logger.debug(f"Skipping already existing target {output_file}")
            continue
        leaf_nodes.append(leaf_node)

    if len(leaf_nodes) == 0:
        logger.debug("No leaf nodes left to process")
        return

    # Run all RDataFrame graphs coming from this subgraph. This program only
    # triggers the production of artifacts that are not available yet as output
    # file.
    logger.debug("Processing RDataFrame graphs")
    graph_elements = [
        artifacts[leaf_node]["lazy_object"] for leaf_node in leaf_nodes
    ]
    ROOT.RDF.RunGraphs(graph_elements)

    # Create the output files from materialized objects
    for leaf_node in leaf_nodes:
        a = artifacts[leaf_node]
        output_object = a["lazy_object"]
        object_type = a["lazy_object_type"]
        output_file = a["output_file"]

        # Check that the output file exists
        # if output_file.exists():
        #     logger.info(f"Skipping already existing target {output_file}")
        #     continue

        # Check if the lazy object has already been computed
        if not output_object.IsReady():
            raise RuntimeError(
                "Lazy object has not been materialized before writing it to a "
                + "file, processing is corrupted"
            )

        if object_type == "snapshot":
            logger.debug(f"Wrote snapshot to {output_file}")

        if object_type == "histogram":
            # Create the output file's parent directory
            if not output_file.parent.exists():
                output_file.parent.mkdir(parents=True)
                logger.debug(f"Created directory {output_file.parent}")

            # Dump histogram to output file
            f = ROOT.TFile.Open(str(output_file), "UPDATE")
            output_object.Write()
            f.Close()
            logger.debug(f"Wrote histogram to {output_file}")

    stop = time()

    delta = round(stop - start, 3)
    logger.info(f"Finished running subgraph {hash(subgraph)} in {delta} s")


def run_graph(
    graph_specs,
    output_dir,
    num_workers,
):
    # Turn graph specs into a networkx graph object
    graph = networkx.readwrite.node_link_graph(graph_specs)

    # Get independent subgraphs
    subgraphs = [
        graph.subgraph(c).copy()
        for c in networkx.weakly_connected_components(graph)
    ]
    n_subgraphs = len(subgraphs)
    logger.info(f"Found {n_subgraphs} independent subgraphs")

    # Check that all subgraphs are directed acyclic graphs
    for subgraph in subgraphs:
        if not networkx.is_directed_acyclic_graph(subgraph):
            raise RuntimeError(
                "Found subgraph that is not a directed acyclic graph"
            )

    if num_workers == 1:
        # If number of workers is 1, set up primitive single-threaded
        # processing logic
        for i, subgraph in enumerate(subgraphs):
            run_subgraph(subgraph, output_dir)
            logger.info(f"Finished {i} of {n_subgraphs} subgraphs")

    else:
        with ProcessPoolExecutor(max_workers=num_workers) as pool:
            # Distribute subgraphs across workers
            futures = []
            for subgraph in subgraphs:
                pool.submit(run_subgraph, subgraph, output_dir)
            for i, future in enumerate(as_completed(futures)):
                _ = future.result()
                logger.info(f"Finished {i} of {n_subgraphs} subgraphs")

    logger.info("Finished processing all graphs")
