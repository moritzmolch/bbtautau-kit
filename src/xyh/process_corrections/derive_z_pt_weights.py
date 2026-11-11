import logging
from pathlib import Path

from omegaconf import DictConfig, OmegaConf

from xyh.core.cli import hydra_cli
from xyh.core.config import load_inventory
from xyh.process_corrections._pt import SmoothingSettings, derive_z_pt_weights

logger = logging.getLogger(__name__)


def _resolve_smoothing_settings(
    smoothing: dict,
    campaign: str,
    categories: list[str],
) -> dict[str, SmoothingSettings]:
    """
    Resolve the smoothing settings of each category: the defaults (all keys of
    `smoothing` except `overrides`) updated with
    `smoothing["overrides"][campaign][category]`. A campaign without overrides
    uses the defaults. Unknown override keys and override categories which are
    not in `categories` raise a `ValueError`.
    """
    # Split defaults and overrides
    defaults = {k: v for k, v in smoothing.items() if k != "overrides"}
    campaign_overrides = (smoothing.get("overrides") or {}).get(campaign) or {}

    # Check that the overrides refer to known categories
    unknown_categories = sorted(set(campaign_overrides) - set(categories))
    if unknown_categories:
        raise ValueError(
            f"Smoothing overrides of campaign {campaign} for categories "
            f"{unknown_categories} which are not in {list(categories)}"
        )

    # Merge the defaults with the overrides of each category
    settings = {}
    for category in categories:
        override = campaign_overrides.get(category) or {}
        unknown_keys = sorted(set(override) - set(defaults))
        if unknown_keys:
            raise ValueError(
                f"Unknown smoothing override keys {unknown_keys} for "
                f"{campaign}/{category}, allowed: {sorted(defaults)}"
            )
        settings[category] = SmoothingSettings(**{**defaults, **override})

    return settings


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
    smoothing = OmegaConf.to_container(cfg["smoothing"], resolve=True)
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

        # Resolve the smoothing settings of each category
        settings = _resolve_smoothing_settings(
            smoothing, campaign, list(categories)
        )

        # Derive the weights
        derive_z_pt_weights(
            inventory,
            categories,
            pt_variable,
            process_tag,
            settings,
            unc_rel_norm_other,
            histograms_dir,
            output_dir / f"{process_tag}_pt_{campaign}.json",
            output_dir
            / "bw_scan"
            / f"{process_tag}_pt_bw_scan_{campaign}.json",
        )


if __name__ == "__main__":
    main()
