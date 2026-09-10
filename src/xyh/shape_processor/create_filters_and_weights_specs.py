import logging
from pathlib import Path

from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.io import dump_json
from xyh.core.specs.filters_and_weights import create_filters_and_weights_specs

# Get the logger for this module
logger = logging.getLogger(__name__)


@hydra_cli("create_filters_and_weights_specs")
def main(cfg: DictConfig) -> None:
    # Create the filter and weight specs
    filters_and_weights_specs = create_filters_and_weights_specs(
        campaigns=cfg["analysis_context"]["campaigns"],
        categories=cfg["analysis_context"]["categories"],
    )

    # Dump specs to output file
    dump_json(filters_and_weights_specs, Path(cfg["output_file"]))


if __name__ == "__main__":
    main()
