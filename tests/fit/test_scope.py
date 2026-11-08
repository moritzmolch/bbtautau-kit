"""Unit tests for `xyh.fit.scope`."""

import pytest

from xyh.fit.mass_points import CLASSES, MassPoint
from xyh.fit.scope import FitBin, FitScope, resolve_scope, short_campaign_name

CAMPAIGNS = ["2023_post_bpix_nano_v12", "2024_nano_v15"]
CHANNELS = ["et", "mt", "tt"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("2024_nano_v15", "2024"),
        ("2023_post_bpix_nano_v12", "2023_post_bpix"),
        ("2024", "2024"),
    ],
)
def test_short_campaign_name_strips_version(name, expected):
    assert short_campaign_name(name) == expected


class TestResolveScope:
    def test_all_selects_everything_and_sets_flags(self):
        scope = resolve_scope("all", ["all"], CAMPAIGNS, CHANNELS)
        assert scope.campaigns == tuple(CAMPAIGNS)
        assert scope.channels == tuple(CHANNELS)
        assert scope.all_campaigns and scope.all_channels
        assert scope.tag == "all_all"

    def test_single_campaign_short_name_and_channel(self):
        scope = resolve_scope("2024", "tt", CAMPAIGNS, CHANNELS)
        assert scope.campaigns == ("2024_nano_v15",)
        assert scope.channels == ("tt",)
        assert scope.tag == "2024_tt"

    def test_integer_campaign_from_hydra_is_accepted(self):
        scope = resolve_scope(2024, ["tt"], CAMPAIGNS, CHANNELS)
        assert scope.campaigns == ("2024_nano_v15",)

    def test_full_campaign_name_is_accepted(self):
        scope = resolve_scope(
            ["2024_nano_v15"], ["et", "mt"], CAMPAIGNS, CHANNELS
        )
        assert scope.campaigns == ("2024_nano_v15",)
        assert scope.tag == "2024_et-mt"

    def test_all_listed_explicitly_sets_all_flag_without_all_keyword(self):
        scope = resolve_scope(
            ["2024", "2023_post_bpix"], ["tt"], CAMPAIGNS, CHANNELS
        )
        assert scope.all_campaigns
        assert not scope.all_channels
        assert scope.tag == "all_tt"

    def test_duplicate_requests_are_deduplicated(self):
        scope = resolve_scope(
            ["2024", "2024_nano_v15"], "tt", CAMPAIGNS, CHANNELS
        )
        assert scope.campaigns == ("2024_nano_v15",)

    def test_unknown_campaign_raises(self):
        with pytest.raises(ValueError, match="'2018' is not available"):
            resolve_scope("2018", "tt", CAMPAIGNS, CHANNELS)

    def test_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="'em' is not available"):
            resolve_scope("2024", ["em"], CAMPAIGNS, CHANNELS)

    def test_empty_selection_raises(self):
        with pytest.raises(ValueError, match="Empty selection"):
            resolve_scope([], "tt", CAMPAIGNS, CHANNELS)


class TestFitScope:
    def test_bins_cover_campaigns_channels_and_classes(self):
        scope = resolve_scope("all", "all", CAMPAIGNS, CHANNELS)
        bins = scope.bins()
        assert len(bins) == 2 * 3 * len(CLASSES)
        assert len({b.name for b in bins}) == len(bins)

    def test_single_channel_single_campaign_has_one_bin_per_class(self):
        scope = resolve_scope("2024", "tt", CAMPAIGNS, CHANNELS)
        assert [b.cls for b in scope.bins()] == list(CLASSES)

    def test_tag_of_non_all_selection_joins_names(self):
        scope = FitScope(("2024_nano_v15", "2023_nano_v12"), ("tt", "et"))
        assert scope.tag == "2024-2023_tt-et"


class TestFitBin:
    def test_name_joins_campaign_channel_and_class(self):
        assert (
            FitBin("2024_nano_v15", "tt", "xyh").name == "tt_xyh_2024_nano_v15"
        )

    def test_category_delegates_to_mass_point(self):
        point = MassPoint("y2b", "h2tau", 2000, 500)
        assert FitBin("c", "mt", "z2tau").category(point) == (
            "mt_clf_z2tau_xyh_y2b_h2tau_mx2000_my500"
        )
