from pathlib import Path

import networkx
from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.io import dump_json, load_json
from xyh.core.specs.graph import build_graph


@hydra_cli("create_graph_specs")
def main(cfg: DictConfig) -> None:
    # Load data from input files
    dataset_specs = load_json(Path(cfg["dataset_specs_file"]))
    histogram_specs = load_json(Path(cfg["histogram_specs_file"]))
    filters_and_weights_specs = load_json(
        Path(cfg["filters_and_weights_specs_file"])
    )

    # Create the dataset specs
    graph = build_graph(
        dataset_specs,
        histogram_specs,
        filters_and_weights_specs,
        "histogram",  # TODO also enable 'snapshot' mode
    )

    # Convert the graph into a JSON-serializable format
    graph_specs = networkx.readwrite.json_graph.node_link_data(graph)

    # Dump graph to output file
    dump_json(graph_specs, Path(cfg["output_file"]))


if __name__ == "__main__":
    main()
