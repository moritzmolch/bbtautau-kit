from pathlib import Path

import ROOT
from omegaconf import DictConfig, OmegaConf

from xyh.core.cli import hydra_cli
from xyh.core.plotting.control_plots import plot_shapes

# Detach ROOT histogram objects from files
ROOT.TH1.AddDirectory(0)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


@hydra_cli("plot_shapes")
def main(cfg: DictConfig):
    # Produce the control plots. The inventory settings are converted to
    # plain Python objects, so that the plot tasks can be sent to worker
    # processes.
    inventory_cfg = OmegaConf.to_container(cfg["inventory"], resolve=True)
    plot_shapes(
        inventory_factory_fn_path=inventory_cfg["factory_fn"],
        inventory_factory_kwargs=inventory_cfg["factory_fn_kwargs"],
        campaigns=inventory_cfg["campaigns"],
        channels=inventory_cfg["channels"],
        categories=inventory_cfg["categories"],
        variables=inventory_cfg["variables"],
        merged_histograms_file=Path(cfg["merged_histograms_file"]),
        output_dir=Path(cfg["output_dir"]),
        extensions=list(cfg["control_plots"]["extensions"]),
        num_workers=cfg.get("num_workers", 1),
    )


if __name__ == "__main__":
    main()
