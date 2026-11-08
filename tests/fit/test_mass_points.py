"""Unit tests for `xyh.fit.mass_points`."""

import pytest

from xyh.fit.mass_points import (
    CLASSES,
    MassPoint,
    discover_mass_points,
    parse_category_name,
    parse_mass_pair,
    select_mass_points,
)

P1 = MassPoint("y2b", "h2tau", 2000, 500)
P2 = MassPoint("y2b", "h2tau", 3000, 100)
P3 = MassPoint("y2tau", "h2b", 2000, 500)


class TestMassPoint:
    def test_labels_and_signal_process(self):
        assert P1.decay_label == "y2b_h2tau"
        assert P1.mass_label == "mx2000_my500"
        assert P1.signal_process == "xyh_y2b_h2tau_mx2000_my500"

    @pytest.mark.parametrize("cls", CLASSES)
    def test_category_known_class_builds_name(self, cls):
        assert P1.category("tt", cls) == (
            f"tt_clf_{cls}_xyh_y2b_h2tau_mx2000_my500"
        )

    def test_category_unknown_class_raises(self):
        with pytest.raises(ValueError, match="Unknown class 'foo'"):
            P1.category("tt", "foo")

    def test_ordering_is_by_decay_modes_then_masses(self):
        assert sorted([P3, P2, P1]) == [P1, P2, P3]


class TestParseCategoryName:
    @pytest.mark.parametrize("cls", CLASSES)
    def test_roundtrip_with_category_builder(self, cls):
        name = P1.category("mt", cls)
        assert parse_category_name(name) == ("mt", cls, P1)

    @pytest.mark.parametrize(
        "name",
        [
            "tt_signal_region",
            "tt_clf_unknown_xyh_y2b_h2tau_mx2000_my500",
            "tt_clf_xyh_xyh_y2b_h2tau_mx2000_myabc",
            "tt_clf_xyh_y2b_h2tau_mx2000_my500",
            "",
        ],
        ids=["regular", "bad-class", "bad-mass", "missing-xyh", "empty"],
    )
    def test_non_classifier_name_returns_none(self, name):
        assert parse_category_name(name) is None


class TestDiscoverMassPoints:
    def test_unique_sorted_and_ignores_other_categories(self):
        names = [
            P2.category("tt", "xyh"),
            P1.category("tt", "xyh"),
            P1.category("tt", "t_tt"),
            P3.category("tt", "jetfakes"),
            "tt_other",
        ]
        assert discover_mass_points(names) == [P1, P2, P3]

    def test_no_classifier_categories_returns_empty(self):
        assert discover_mass_points(["a", "b"]) == []


class TestParseMassPair:
    @pytest.mark.parametrize(
        "spec",
        ["2000_500", "mx2000_my500", [2000, 500], ["2000", "500"], (2000, 500)],
        ids=["plain", "prefixed", "list", "str-list", "tuple"],
    )
    def test_valid_spec_returns_ints(self, spec):
        assert parse_mass_pair(spec) == (2000, 500)

    @pytest.mark.parametrize("spec", ["2000", "a_b", "2000-500", ""])
    def test_invalid_string_raises(self, spec):
        with pytest.raises(ValueError, match="Cannot parse mass point"):
            parse_mass_pair(spec)

    @pytest.mark.parametrize("spec", [[1], [1, 2, 3], []])
    def test_wrong_length_raises(self, spec):
        with pytest.raises(ValueError, match="must have two entries"):
            parse_mass_pair(spec)


class TestSelectMassPoints:
    AVAILABLE = [P3, P2, P1, P1]

    def test_no_filters_returns_sorted_unique(self):
        assert select_mass_points(self.AVAILABLE) == [P1, P2, P3]

    def test_filter_by_decay_modes(self):
        assert select_mass_points(self.AVAILABLE, ydm=["y2tau"]) == [P3]
        assert select_mass_points(self.AVAILABLE, hdm=["h2tau"]) == [P1, P2]

    def test_filter_by_mass_pairs(self):
        selected = select_mass_points(
            self.AVAILABLE, mass_points=["2000_500", [3000, 100]]
        )
        assert selected == [P1, P2, P3]

    def test_mass_pair_matches_all_decay_modes(self):
        assert select_mass_points(self.AVAILABLE, mass_points=["2000_500"]) == [
            P1,
            P3,
        ]

    def test_unavailable_mass_pair_raises(self):
        with pytest.raises(ValueError, match="not available"):
            select_mass_points(self.AVAILABLE, mass_points=["1_1"])

    def test_mass_pair_excluded_by_decay_filter_raises(self):
        with pytest.raises(ValueError, match="not available"):
            select_mass_points(
                self.AVAILABLE, mass_points=["3000_100"], ydm=["y2tau"]
            )

    def test_empty_selection_raises(self):
        with pytest.raises(ValueError, match="No mass points selected"):
            select_mass_points(self.AVAILABLE, ydm=["nope"])

    def test_no_available_points_raises(self):
        with pytest.raises(ValueError, match="No mass points selected"):
            select_mass_points([])
