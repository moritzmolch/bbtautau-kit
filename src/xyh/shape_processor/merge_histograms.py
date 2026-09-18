from pathlib import Path

from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.histograms.util import merge_histograms
from xyh.core.io import load_json


@hydra_cli("merge_histograms")
def main(cfg: DictConfig):
    # Load graph specs
    graph_specs = load_json(Path(cfg["graph_specs_file"]))

    # Run graph processing and production of output files
    merge_histograms(
        cfg["inventory"]["factory_fn"],
        graph_specs,
        Path(cfg["histograms_dir"]),
        Path(cfg["output_dir"]),
    )


if __name__ == "__main__":
    main()
