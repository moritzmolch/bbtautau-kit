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
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        inventory_factory_kwargs=cfg["inventory"]["factory_fn_kwargs"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        categories=cfg["inventory"]["categories"],
        variables=cfg["inventory"]["variables"],
        merged_histograms_file=Path(cfg["merged_histograms_file"]),
        output_dir=Path(cfg["output_dir"]),
        extensions=cfg["control_plots"]["extensions"],
    )


if __name__ == "__main__":
    main()
