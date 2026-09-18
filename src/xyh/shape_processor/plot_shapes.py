from pathlib import Path

import ROOT
from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.io import load_json
from xyh.core.plotting.control_plots import plot_shapes

# Detach ROOT histogram objects from files
ROOT.TH1.AddDirectory(0)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


@hydra_cli("plot_shapes")
def main(cfg: DictConfig):
    # Load data from input files
    graph_specs = load_json(Path(cfg["graph_specs_file"]))

    # Run graph processing and production of output files
    plot_shapes(
        cfg["inventory"]["factory_fn"],
        graph_specs,
        Path(cfg["merged_histograms_dir"]),
        Path(cfg["output_dir"]),
        cfg["control_plots"]["extensions"],
    )


if __name__ == "__main__":
    main()
