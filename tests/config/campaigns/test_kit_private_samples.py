"""
Integration tests for the kit-private signal samples in the campaigns.
"""

import importlib
import os

import pytest

from xyh.config.profiles import get_profile


@pytest.fixture
def full_profile_campaigns():
    """
    Build the 2024 and 2025 campaigns with the FULL analysis profile.

    The campaign modules are reloaded to rebuild them with the FULL profile.
    The `campaigns` index created in ``xyh.config.campaigns`` keeps the objects
    that were built when the package was first imported, so the remaining test
    suite is not affected by this fixture.
    """
    # Activate the FULL analysis profile and clear the cache
    previous_profile = os.environ.pop("XYH_PROFILE", None)
    os.environ["XYH_PROFILE"] = "FULL"
    get_profile.cache_clear()

    import xyh.config.campaigns._2024_nano_v15 as _2024_module
    import xyh.config.campaigns._2025_nano_v15 as _2025_module

    try:
        _2024_module = importlib.reload(_2024_module)
        _2025_module = importlib.reload(_2025_module)
        yield _2024_module.cpn_2024_nano_v15, _2025_module.cpn_2025_nano_v15
    finally:
        # Restore the previous profile state
        if previous_profile is not None:
            os.environ["XYH_PROFILE"] = previous_profile
        get_profile.cache_clear()


def test_signal_datasets_contain_kit_private_nicks(full_profile_campaigns):
    """Test that the kit-private nicks are added to the signal datasets."""
    for campaign in full_profile_campaigns:
        dataset = campaign.datasets.get(
            "xyh_y2b_h2tau_mx300_my60_madgraph"
        )
        assert dataset is not None
        assert len(dataset.x.nicks) == 2
        # One official production and one kit-private production
        assert sum(
            nick.endswith("-kit-private") for nick in dataset.x.nicks
        ) == 1

        dataset = campaign.datasets.get(
            "xyh_y2tau_h2b_mx300_my60_madgraph"
        )
        assert dataset is not None
        assert len(dataset.x.nicks) == 2
        assert sum(
            nick.endswith("-kit-private") for nick in dataset.x.nicks
        ) == 1


def test_kit_private_productions_are_merged(full_profile_campaigns):
    """Test that both kit-private productions are merged into one dataset."""
    for campaign in full_profile_campaigns:
        dataset = campaign.datasets.get(
            "xyh_y2b_h2tau_mx1000_my100_madgraph"
        )
        assert dataset is not None
        assert len(dataset.x.nicks) == 3
        # Two kit-private productions of the same sample
        assert sum(
            nick.endswith("-kit-private") for nick in dataset.x.nicks
        ) == 2
        assert dataset.n_events == 202000


def test_no_kit_private_datasets_added(full_profile_campaigns):
    """Test that no additional datasets are added for the kit-private samples."""
    for campaign in full_profile_campaigns:
        assert not any(
            name.endswith("_kitprivate")
            for name in campaign.datasets.names()
        )

        # Signal points without an official production remain unavailable
        for name in [
            "xyh_y2b_h2tau_mx2500_my800_madgraph",
            "xyh_y2tau_h2b_mx2500_my90_madgraph",
        ]:
            assert name not in campaign.datasets
