"""
Unit tests for xyh.config.channels.categories_base module.

These tests are completely isolated and use mocks for all external dependencies.
"""

from unittest.mock import Mock

import pytest

# =============================================================================
# Dummy classes for external dependencies
# =============================================================================


class DummyChannel:
    """Dummy Channel class for testing."""

    def __init__(self, name="test_channel", label="Test Label"):
        self.name = name
        self.label = label
        self._categories = []

    def add_category(self, name=None, label=None, label_short=None):
        """Mock method to add a category."""
        category = Mock()
        category.name = name
        category.label = label
        category.label_short = label_short
        self._categories.append(category)
        return category


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_channel():
    """Fixture to create a mock channel instance."""
    return DummyChannel()


# =============================================================================
# Import after fixtures to avoid issues with missing dependencies
# =============================================================================


@pytest.fixture(autouse=True)
def setup_module():
    """Setup fixture to ensure clean imports."""
    # Clear any cached imports
    import sys

    if "xyh.config.channels.categories_base" in sys.modules:
        del sys.modules["xyh.config.channels.categories_base"]
    yield


# =============================================================================
# Tests for add_base_category function
# =============================================================================


class TestAddBaseCategory:
    """Tests for the add_base_category function."""

    def test_add_base_category_returns_category(self, setup_module):
        """Verify function returns a category instance."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="et")
        result = add_base_category(channel)

        assert result is not None

    def test_add_base_category_calls_add_category(self, setup_module):
        """Verify function calls add_category on the channel."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="et")
        add_base_category(channel)

        assert len(channel._categories) == 1

    def test_add_base_category_correct_name(self, setup_module):
        """Verify category name matches channel name."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="mt")
        result = add_base_category(channel)

        assert result.name == "mt"

    def test_add_base_category_correct_label(self, setup_module):
        """Verify category label includes channel name and description."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="tt")
        result = add_base_category(channel)

        assert result.label == "tt (base selection)"

    def test_add_base_category_correct_label_short(self, setup_module):
        """Verify category label_short matches channel name."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="em")
        result = add_base_category(channel)

        assert result.label_short == "em"

    @pytest.mark.parametrize(
        "channel_name",
        ["et", "mt", "tt", "em", "ee", "mm"],
    )
    def test_add_base_category_all_channel_types(
        self, setup_module, channel_name
    ):
        """Verify function works with all channel types."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name=channel_name)
        result = add_base_category(channel)

        assert result.name == channel_name
        assert result.label == f"{channel_name} (base selection)"
        assert result.label_short == channel_name

    def test_add_base_category_with_custom_channel_label(self, setup_module):
        """Verify function ignores channel label and uses only name."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="custom", label="Custom Channel Label")
        result = add_base_category(channel)

        assert result.name == "custom"
        assert result.label == "custom (base selection)"
        assert result.label_short == "custom"

    def test_add_base_category_multiple_calls_same_channel(self, setup_module):
        """Verify multiple calls add multiple categories to same channel."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="et")
        result1 = add_base_category(channel)
        result2 = add_base_category(channel)

        assert len(channel._categories) == 2
        assert result1 is not result2

    def test_add_base_category_preserves_channel_state(self, setup_module):
        """Verify channel's other attributes are not modified."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="mt", label="Muon Tau Channel")
        original_label = channel.label

        add_base_category(channel)

        assert channel.label == original_label
        assert channel.name == "mt"


# =============================================================================
# Edge case tests
# =============================================================================


class TestAddBaseCategoryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_add_base_category_empty_string_name(self, setup_module):
        """Verify function handles empty string channel name."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="")
        result = add_base_category(channel)

        assert result.name == ""
        assert result.label == " (base selection)"
        assert result.label_short == ""

    def test_add_base_category_special_characters_in_name(self, setup_module):
        """Verify function handles special characters in channel name."""
        from xyh.config.channels.categories_base import add_base_category

        channel = DummyChannel(name="test_123")
        result = add_base_category(channel)

        assert result.name == "test_123"
        assert result.label == "test_123 (base selection)"

    def test_add_base_category_very_long_name(self, setup_module):
        """Verify function handles very long channel names."""
        from xyh.config.channels.categories_base import add_base_category

        long_name = "a" * 100
        channel = DummyChannel(name=long_name)
        result = add_base_category(channel)

        assert result.name == long_name
        assert result.label == f"{long_name} (base selection)"
