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
        dataset = campaign.datasets.get("xyh_y2b_h2tau_mx300_my60_madgraph")
        assert dataset is not None
        assert len(dataset.x.nicks) == 2
        # One official production and one kit-private production
        assert (
            sum(nick.endswith("-kit-private") for nick in dataset.x.nicks) == 1
        )

        dataset = campaign.datasets.get("xyh_y2tau_h2b_mx300_my60_madgraph")
        assert dataset is not None
        assert len(dataset.x.nicks) == 2
        assert (
            sum(nick.endswith("-kit-private") for nick in dataset.x.nicks) == 1
        )


def test_kit_private_productions_are_merged(full_profile_campaigns):
    """Test that both kit-private productions are merged into one dataset."""
    for campaign in full_profile_campaigns:
        dataset = campaign.datasets.get("xyh_y2b_h2tau_mx1000_my100_madgraph")
        assert dataset is not None
        assert len(dataset.x.nicks) == 3
        # Two kit-private productions of the same sample
        assert (
            sum(nick.endswith("-kit-private") for nick in dataset.x.nicks) == 2
        )
        assert dataset.n_events == 202000


def test_kit_private_only_signal_datasets(full_profile_campaigns):
    """Test the datasets that exclusively use the kit-private samples."""
    for campaign in full_profile_campaigns:
        # The MX-2500-MY-800 sample in the y2b channel has no official
        # production and uses only the kit-private sample
        dataset = campaign.datasets.get("xyh_y2b_h2tau_mx2500_my800_madgraph")
        assert dataset is not None
        assert dataset.x.nicks == [
            "NMSSM-XtoYHto2B2Tau_Par-MX-2500-MY-800_TuneCP5_13p6TeV_madgraph-pythia8_"
            f"RunIII{campaign.x.year}Summer24NanoAODv15-150X-kit-private"
        ]
        assert dataset.n_events == 100000

        # The MX-2500-MY-90 sample in the y2tau channel has no official
        # production and uses only the kit-private sample
        dataset = campaign.datasets.get("xyh_y2tau_h2b_mx2500_my90_madgraph")
        assert dataset is not None
        assert dataset.x.nicks == [
            "NMSSM-XtoYHto2Tau2B_Par-MX-2500-MY-90_TuneCP5_13p6TeV_madgraph-pythia8_"
            f"RunIII{campaign.x.year}Summer24NanoAODv15-150X-kit-private"
        ]
        assert dataset.n_events == 100000


def test_no_separate_kit_private_datasets(full_profile_campaigns):
    """Test that no additional datasets are added for the kit-private samples."""
    for campaign in full_profile_campaigns:
        assert not any(
            name.endswith("_kitprivate") for name in campaign.datasets.names()
        )


def test_kit_private_only_processes_are_wired(full_profile_campaigns):
    """Test that the kit-private-only signal points are wired to processes."""
    from xyh.config.channels import channels
    from xyh.config.process_datasets_map import get_process_datasets_map

    for campaign in full_profile_campaigns:
        process_datasets_map = get_process_datasets_map(
            campaign, channels.get("et")
        )
        assert process_datasets_map["xyh_y2b_h2tau_mx2500_my800"] == [
            "xyh_y2b_h2tau_mx2500_my800_madgraph"
        ]
        assert process_datasets_map["xyh_y2tau_h2b_mx2500_my90"] == [
            "xyh_y2tau_h2b_mx2500_my90_madgraph"
        ]
