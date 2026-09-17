from pathlib import Path

import ROOT
from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.io import load_json
from xyh.core.specs.graph import run_graph


@hydra_cli("run_graphs")
def main(cfg: DictConfig):
    # Load data from input files
    graph_specs = load_json(Path(cfg["graph_specs_file"]))

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
