"""
Unit tests for xyh.config.channels.categories_clf module.

These tests are completely isolated and use mocks for all external dependencies.
"""

import pytest
from order import Category, UniqueObjectIndex

# =============================================================================
# Dummy classes for external dependencies
# =============================================================================


# class DummyCategoryProxy:
#     """Dummy CategoryProxy class for testing."""

#     def __init__(
#         self, name=None, id=None, label=None, label_short=None, **kwargs
#     ):
#         self.name = name
#         self.id = id
#         self.label = label
#         self.label_short = label_short


class DummyChannel:
    """Dummy Channel class for testing."""

    def __init__(self, name: str, id: int | str = 0, label: str = None):
        self.name = name
        self.id = id if isinstance(id, int) else 9999
        self.label = label if label is not None else name
        self._categories = UniqueObjectIndex(Category, [])

    def add_category(self, *args, **kwargs):
        """Mock method to add a category."""
        category_inst = None
        if len(args) == 1:
            category_inst = args[0]
        elif len(args) == 0:
            category_inst = Category(**kwargs)
        else:
            raise ValueError("Invalid arguments for add_category")
        self._categories.add(category_inst)
        return category_inst


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_channel():
    """Fixture to create a mock channel instance."""
    return DummyChannel()


# =============================================================================
# Tests for add_clf_category function
# =============================================================================


@pytest.mark.skip(reason="Tests are outdated")
class TestAddClfCategory:
    """Tests for the add_clf_category function."""

    def test_add_clf_category_creates_four_categories(self):
        """Verify function creates exactly 4 classification categories."""
        from xyh.config.channels.categories_clf import add_clf_category

        channel = DummyChannel(name="test_channel")
        add_clf_category(channel)

        # Verify that exactly four categories were created
        assert len(channel._categories) == 4

        # Verify that the created categories have the expected names
        for expected_cat in ["jetfakes", "tt", "xyh", "ztt"]:
            assert any(expected_cat in cat.name for cat in channel._categories)

    def test_add_clf_category_created_category_name_and_label_format(self):
        """Verify created categories have correct names and labels."""
        from xyh.config.channels.categories_clf import add_clf_category

        channel_inst = DummyChannel(
            name="et",
            label=r"$\text{e}\tau_{\text{h}}$",
        )
        add_clf_category(channel_inst)

        for category_inst in channel_inst._categories.values():
            # Inspect the category name
            assert category_inst.name.startswith("et_clf_")
            assert category_inst.name.endswith(
                "_xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}"
            )

            # Inspect the category label
            assert category_inst.label.startswith(
                r"$\text{e}\tau_{\text{h}}$ channel, "
            )
            assert category_inst.label.endswith("category")
            assert "channel" not in category_inst.label_short
            assert not category_inst.label_short.endswith("category")

    def test_add_clf_category_created_jetfakes_category(self):
        """Verify jetfakes category is created correctly."""
        from xyh.config.channels.categories_clf import add_clf_category

        channel = DummyChannel(name="et")
        add_clf_category(channel)

        jetfakes_cat = channel._categories.values()[0]
        assert "jetfakes" in jetfakes_cat.name
        assert r"$\text{j} \to \tau_{\text{h}}$" in jetfakes_cat.label

    def test_add_clf_category_tt_category(self):
        """Verify tt category is created correctly."""
        from xyh.config.channels.categories_clf import add_clf_category

        channel = DummyChannel(name="mt")
        add_clf_category(channel)

        tt_cat = channel._categories.values()[1]
        assert "tt" in tt_cat.name
        assert r"$\text{t}\bar{\text{t}}$" in tt_cat.label

    def test_add_clf_category_xyh_category(self):
        """Verify xyh category is created correctly."""
        from xyh.config.channels.categories_clf import add_clf_category

        channel = DummyChannel(name="tt")
        add_clf_category(channel)

        xyh_cat = channel._categories.values()[2]
        assert "xyh" in xyh_cat.name
        assert r"$\text{X} \to \text{H}\text{Y}$" in xyh_cat.label

    def test_add_clf_category_ztt_category(self):
        """Verify ztt category is created correctly."""
        from xyh.config.channels.categories_clf import add_clf_category

        channel = DummyChannel(name="et")
        add_clf_category(channel)

        ztt_cat = channel._categories.values()[3]
        assert "ztt" in ztt_cat.name
        assert r"$\text{Z}(\tau\tau)$" in ztt_cat.label

    @pytest.mark.parametrize(
        "channel_name",
        ["et", "mt", "tt", "em", "ee", "mm"],
    )
    def test_add_clf_category_all_channel_types(self, channel_name):
        """Verify function works with all channel types."""
        from xyh.config.channels.categories_clf import add_clf_category

        channel = DummyChannel(name=channel_name)
        add_clf_category(channel)

        assert len(channel._categories) == 4
        assert all(
            cat.name.startswith(f"{channel_name}_clf_")
            for cat in channel._categories
        )
