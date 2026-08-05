"""
Data-taking campaigns of the analysis, including corresponding data and
simulation sample metadata.
"""

import importlib
from functools import cache

from order import Campaign, UniqueObjectIndex


@cache
def load_campaign(campaign_name: str) -> Campaign:
    """
    Load a campaign module dynamically based on the provided campaign name.

    Parameters
    ----------
    campaign_name : str
        The name of the campaign to load.

    Raises
    ------
    ValueError
        If the campaign module cannot be found or loaded.
    """
    try:
        # Import the campaign module dynamically based on the provided campaign name
        module = importlib.import_module(f"{campaign_name}", __package__)
        campaign_inst = getattr(module, campaign_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Campaign '{campaign_name}' not found.") from e

    return campaign_inst


@cache
def campaigns() -> UniqueObjectIndex:
    """
    Return a UniqueObjectIndex containing all available campaigns.

    Returns
    -------
    UniqueObjectIndex[Campaign]
        A UniqueObjectIndex containing all available campaigns.
    """

    return UniqueObjectIndex(
        Campaign,
        [
            load_campaign(campaign_name)
            for campaign_name in [
                "cpn_2022_pre_ee_nano_v12",
                "cpn_2022_post_ee_nano_v12",
                "cpn_2023_pre_bpix_nano_v12",
                "cpn_2023_post_bpix_nano_v12",
                "cpn_2024_nano_v15",
                "cpn_2025_nano_v15",
            ]
        ],
    )
