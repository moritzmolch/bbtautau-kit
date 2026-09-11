import logging
from dataclasses import asdict
from pathlib import Path

from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.io import dump_json
from xyh.core.specs.dataset import create_dataset_specs

# Get the logger for this module
logger = logging.getLogger(__name__)


@hydra_cli("create_dataset_specs")
def main(cfg: DictConfig):
    # Initialize the logger
    log_level = cfg["log_level"]
    logger.setLevel(log_level)

    # Create the dataset specs
    dataset_specs = create_dataset_specs(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        xrootd_server=cfg["ntuples"]["xrootd_server"],
        ntuple_base_dir=Path(cfg["ntuples"]["base_dir"]),
        ntuple_tag=cfg["tags"]["ntuple_tag"],
        ntuple_friends=cfg["ntuples"]["friends"],
    )

    # # Dump specs to output file
    dump_json(
        [asdict(d) for d in dataset_specs],
        Path(cfg["output_file"]),
    )


if __name__ == "__main__":
    main()
