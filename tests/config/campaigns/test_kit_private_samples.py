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


def test_kit_private_datasets_in_campaigns():
    """Test that the kit-private signal datasets are added to the campaigns."""
    from xyh.config.campaigns._2024_nano_v15 import cpn_2024_nano_v15
    from xyh.config.campaigns._2025_nano_v15 import cpn_2025_nano_v15

    for campaign in (cpn_2024_nano_v15, cpn_2025_nano_v15):
        # The datasets of the signal points that are not covered by the
        # official productions must be available
        for name in [
            "xyh_y2b_h2tau_mx2500_my800_madgraph_kitprivate",
            "xyh_y2tau_h2b_mx2500_my90_madgraph_kitprivate",
        ]:
            assert campaign.datasets.get(name) is not None

        # All kit-private datasets are MC samples with a defined cross section
        # and generator weight
        for dataset in campaign.datasets.values():
            if "_kitprivate" in dataset.name:
                assert not dataset.is_data
                assert dataset.x.xsec is not None
                assert dataset.x.generator_weight is not None


def test_kit_private_dataset_merges_productions():
    """Test that both productions of the same sample are merged."""
    from xyh.config.campaigns._2024_nano_v15 import cpn_2024_nano_v15
    from xyh.config.campaigns._2025_nano_v15 import cpn_2025_nano_v15

    for campaign in (cpn_2024_nano_v15, cpn_2025_nano_v15):
        dataset = campaign.datasets.get(
            "xyh_y2b_h2tau_mx1000_my100_madgraph_kitprivate"
        )
        assert dataset is not None
        assert len(dataset.x.nicks) == 2
        # Events are summed over both productions
        assert dataset.n_events == 102000


def test_kit_private_datasets_have_expected_properties():
    """Test the properties of the kit-private signal datasets."""
    from xyh.config.campaigns._2024_nano_v15 import cpn_2024_nano_v15
    from xyh.config.campaigns._2025_nano_v15 import cpn_2025_nano_v15

    for campaign in (cpn_2024_nano_v15, cpn_2025_nano_v15):
        dataset = campaign.datasets.get(
            "xyh_y2b_h2tau_mx300_my60_madgraph_kitprivate"
        )
        assert dataset is not None
        assert len(dataset.x.nicks) == 1
        assert dataset.x.nicks[0].endswith("-150X-kit-private")


def test_process_datasets_map_with_full_profile(full_profile_campaigns):
    """Test that the kit-private datasets are wired to the signal processes."""
    from xyh.config.channels import channels
    from xyh.config.process_datasets_map import get_process_datasets_map

    for campaign in full_profile_campaigns:
        process_datasets_map = get_process_datasets_map(
            campaign, channels.get("et")
        )

        # Signal points with an official production get the kit-private
        # dataset appended
        assert process_datasets_map["xyh_y2b_h2tau_mx300_my60"] == [
            "xyh_y2b_h2tau_mx300_my60_madgraph",
            "xyh_y2b_h2tau_mx300_my60_madgraph_kitprivate",
        ]

        # Signal points that are only available as kit-private samples are
        # covered by the kit-private dataset alone
        assert process_datasets_map["xyh_y2b_h2tau_mx2500_my800"] == [
            "xyh_y2b_h2tau_mx2500_my800_madgraph_kitprivate",
        ]
        assert process_datasets_map["xyh_y2tau_h2b_mx2500_my90"] == [
            "xyh_y2tau_h2b_mx2500_my90_madgraph_kitprivate",
        ]
