from pathlib import Path

from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.histograms.fake_factors import run_fake_factor_histograms
from xyh.core.io import load_json


@hydra_cli("run_fake_factor_histograms")
def main(cfg: DictConfig):
    # Load data from input files
    graph_specs = load_json(Path(cfg["graph_specs_file"]))

    # Run graph processing and production of output files
    run_fake_factor_histograms(
        cfg["inventory"]["factory_fn"],
        graph_specs,
        Path(cfg["histograms_dir"]),
        Path(cfg["output_dir"]),
    )


if __name__ == "__main__":
    main()
