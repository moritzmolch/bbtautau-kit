import logging
from dataclasses import asdict
from pathlib import Path

from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.io import dump_json
from xyh.core.specs.histogram import create_histogram_specs

# Get the logger for this module
logger = logging.getLogger(__name__)


@hydra_cli("create_histogram_specs")
def main(cfg: DictConfig) -> None:
    # Create the histogram specs
    histogram_specs = create_histogram_specs(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        categories=cfg["inventory"]["categories"],
        variables=cfg["inventory"]["variables"],
    )

    # Dump specs to output file
    dump_json([asdict(h) for h in histogram_specs], Path(cfg["output_file"]))


if __name__ == "__main__":
    main()
