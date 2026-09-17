import logging
from dataclasses import asdict
from pathlib import Path

import ROOT
from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.io import dump_json
from xyh.core.specs.dataset import create_dataset_specs
from xyh.core.specs.filters_and_weights import create_filters_and_weights_specs
from xyh.core.specs.graph import create_graph_specs, run_graph
from xyh.core.specs.histogram import create_histogram_specs


@hydra_cli("run_graphs")
def main(cfg: DictConfig):
    # Set the logging level
    logging.basicConfig(level=cfg["log_level"])

    # Create the dataset specs
    dataset_specs = create_dataset_specs(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        inventory_factory_kwargs=cfg["inventory"]["factory_fn_kwargs"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        xrootd_server=cfg["ntuples"]["xrootd_server"],
        ntuple_base_dir=Path(cfg["ntuples"]["base_dir"]),
        ntuple_tag=cfg["tags"]["ntuple_tag"],
        ntuple_friends=cfg["ntuples"]["friends"],
    )

    # Create the histogram specs
    histogram_specs = create_histogram_specs(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        inventory_factory_kwargs=cfg["inventory"]["factory_fn_kwargs"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        categories=cfg["inventory"]["categories"],
        variables=cfg["inventory"]["variables"],
    )

    # Create the filter and weight specs
    filters_and_weights_specs = create_filters_and_weights_specs(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        inventory_factory_kwargs=cfg["inventory"]["factory_fn_kwargs"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        categories=cfg["inventory"]["categories"],
    )

    # Build the graph from the individual specs
    graph_specs = create_graph_specs(
        dataset_specs,
        histogram_specs,
        filters_and_weights_specs,
        "histogram",  # TODO also enable 'snapshot' mode
    )

    # Dump specs to output file
    dump_json(
        [asdict(d) for d in dataset_specs],
        Path(cfg["dataset_specs_file"]),
    )
    dump_json(
        [asdict(h) for h in histogram_specs],
        Path(cfg["histogram_specs_file"]),
    )
    dump_json(
        [asdict(fw) for fw in filters_and_weights_specs],
        Path(cfg["filters_and_weights_specs_file"]),
    )
    dump_json(graph_specs, Path(cfg["graph_specs_file"]))

    # Set number of threads in ROOT parallel processing
    num_threads = cfg["graph_processing"]["num_threads"]
    if num_threads > 1:
        ROOT.EnableImplicitMT(num_threads)

    # Run graph processing and production of output files
    run_graph(
        graph_specs,
        Path(cfg["output_dir"]),
        cfg["graph_processing"]["num_workers"],
    )


if __name__ == "__main__":
    main()
