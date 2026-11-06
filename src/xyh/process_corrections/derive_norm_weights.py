import logging
from pathlib import Path

from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.config import load_inventory
from xyh.process_corrections._norm import derive_norm_weights

logger = logging.getLogger(__name__)


@hydra_cli("derive_norm_weights")
def main(cfg: DictConfig):
    # Get properties from the config
    inventory_factory_fn = cfg["inventory"]["factory_fn"]
    inventory_factory_fn_kwargs = cfg["inventory"]["factory_fn_kwargs"]
    campaigns = cfg["inventory"]["campaigns"]
    channel = cfg["channel"]
    categories = cfg["categories"]
    yield_variable = cfg["yield_variable"]
    process_tag = cfg["process_tag"]
    unc_rel_norm_other = cfg["unc_rel_norm_other"]
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
        derive_norm_weights(
            inventory,
            categories,
            yield_variable,
            process_tag,
            unc_rel_norm_other,
            histograms_dir,
            output_dir / f"{process_tag}_norm_{campaign}.json",
        )


if __name__ == "__main__":
    main()
