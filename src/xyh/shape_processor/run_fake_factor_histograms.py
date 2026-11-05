from pathlib import Path

from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.histograms.fake_factors import run_fake_factor_histograms


@hydra_cli("run_fake_factor_histograms")
def main(cfg: DictConfig):
    # Run graph processing and production of output files
    run_fake_factor_histograms(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        inventory_factory_kwargs=cfg["inventory"]["factory_fn_kwargs"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        categories=cfg["inventory"]["categories"],
        variables=cfg["inventory"]["variables"],
        histograms_dir=Path(cfg["histograms_dir"]),
    )


if __name__ == "__main__":
    main()
