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
        analysis=cfg["analysis_context"]["analysis"],
        campaigns=cfg["analysis_context"]["campaigns"],
        categories=cfg["analysis_context"]["categories"],
        variables=cfg["analysis_context"]["variables"],
    )

    # Dump specs to output file
    dump_json([asdict(h) for h in histogram_specs], Path(cfg["output_file"]))


if __name__ == "__main__":
    main()
