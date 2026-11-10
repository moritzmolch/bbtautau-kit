import logging
from pathlib import Path

from omegaconf import DictConfig, OmegaConf

from xyh.core.cli import hydra_cli
from xyh.core.config import load_inventory
from xyh.process_corrections._pt import derive_z_pt_weights

logger = logging.getLogger(__name__)


@hydra_cli("derive_z_pt_weights")
def main(cfg: DictConfig):
    # Get properties from the config
    inventory_factory_fn = cfg["inventory"]["factory_fn"]
    inventory_factory_fn_kwargs = cfg["inventory"]["factory_fn_kwargs"]
    campaigns = cfg["inventory"]["campaigns"]
    channel = cfg["channel"]
    categories = cfg["categories"]
    pt_variable = cfg["pt_variable"]
    process_tag = cfg["process_tag"]
    unc_rel_norm_other = cfg["unc_rel_norm_other"]
    smoothing = cfg["smoothing"]
    bw_overrides = OmegaConf.to_container(
        smoothing["bw_overrides"], resolve=True
    )
    histograms_dir = Path(cfg["histograms_dir"])
    output_dir = Path(cfg["output_dir"])

    for campaign in campaigns:
        # Load inventory for this campaign and channel
        inventory = load_inventory(
            inventory_factory_fn,
            campaign,
            channel,
            **inventory_factory_fn_kwargs,
        )

        # Derive the weights
        derive_z_pt_weights(
            inventory,
            categories,
            pt_variable,
            process_tag,
            smoothing["n_samples"],
            smoothing["var_min"],
            smoothing["var_max"],
            smoothing["var_steps"],
            smoothing["bw"],
            smoothing["bw_down_factor"],
            smoothing["bw_up_factor"],
            unc_rel_norm_other,
            histograms_dir,
            output_dir / f"{process_tag}_pt_{campaign}.json",
            bw_overrides=bw_overrides.get(campaign),
        )


if __name__ == "__main__":
    main()
