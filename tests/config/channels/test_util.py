"""
Unit tests for xyh.config.channels.util module.

These tests are completely isolated and use mocks for all external dependencies.
"""

from unittest.mock import Mock

import pytest

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def setup_module():
    """Setup fixture to ensure clean imports with proper mocking."""
    import sys

    # Mock the campaigns.util module
    mock_campaigns_util = Mock()
    mock_campaigns_util.get_format_string_parameters = (
        mock_get_format_string_parameters
    )
    sys.modules["xyh.config.campaigns.util"] = mock_campaigns_util

    # Clear any cached imports
    if "xyh.config.channels.util" in sys.modules:
        del sys.modules["xyh.config.channels.util"]

    yield

    # Cleanup
    if "xyh.config.campaigns.util" in sys.modules:
        del sys.modules["xyh.config.campaigns.util"]


def mock_get_format_string_parameters(format_string: str) -> set[str]:
    """Mock implementation of get_format_string_parameters."""
    import string

    return {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(format_string)
        if field_name is not None
    }


# =============================================================================
# Tests for CategoryProxy initialization
# =============================================================================


class TestCategoryProxyInit:
    """Tests for CategoryProxy initialization."""

    def test_category_proxy_creation_minimal_params(self):
        """Verify CategoryProxy can be created with minimal parameters."""

        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test", id=1)

        assert proxy is not None
        assert proxy.name == "test"
        assert proxy.id == 1

    def test_category_proxy_creation_all_params(self):
        """Verify CategoryProxy accepts all parameters."""
        from order import Channel

        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(
            name="test",
            id=1,
            channel=Channel(name="et", id="+"),
            categories=[],
            label="Test Label",
            label_short="Test",
            selection="x > 0",
            str_selection_mode="root",
            tags=["tag1", "tag2"],
            aux={"key": "value"},
        )

        assert proxy.name == "test"
        assert proxy.id == 1
        assert proxy.label == "Test Label"
        assert proxy.label_short == "Test"
        assert proxy.tags == {"tag1", "tag2"}
        assert proxy.aux == {"key": "value"}

    def test_category_proxy_extracts_parameters_from_name(self):
        """Verify CategoryProxy extracts format parameters from name."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test_{param1}_{param2}", id=1)

        assert hasattr(proxy, "_parameters")
        assert proxy._parameters == {"param1", "param2"}

    def test_category_proxy_no_parameters_in_name(self):
        """Verify CategoryProxy handles names without format parameters."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="static_name", id=1)

        assert hasattr(proxy, "_parameters")
        assert proxy._parameters == set()

    def test_category_proxy_complex_format_string(self):
        """Verify CategoryProxy handles complex format strings."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="cat_{a}_{b}_{c}_mx{x}_my{y}", id=1)

        assert proxy._parameters == {"a", "b", "c", "x", "y"}

    def test_category_proxy_default_values(self):
        """Verify CategoryProxy uses default values for optional params."""
        from order import UniqueObjectIndex

        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test", id=1)

        assert proxy.channel is None
        assert isinstance(proxy.categories, UniqueObjectIndex)
        assert len(proxy.categories) == 0
        assert proxy.label == "test"
        assert proxy.label_short == "test"
        assert proxy.selection == "1"
        assert proxy.str_selection_mode == "numexpr"
        assert proxy.tags == set()
        assert proxy.aux == {}


# =============================================================================
# Tests for CategoryProxy.eval() method
# =============================================================================


class TestCategoryProxyEval:
    """Tests for the eval() method."""

    def test_eval_with_all_parameters(self, setup_module):
        """Verify eval() returns a Category with all parameters provided."""
        from order import Category

        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test_{x}_{y}", id=1, label="Test {x}")
        result = proxy.eval(x=10, y=20)

        assert result is not None
        assert isinstance(result, Category)
        assert result.name == "test_10_20"

    def test_eval_preserves_other_attributes(self, setup_module):
        """Verify eval() preserves other attributes in copied category."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(
            name="test_{x}",
            id=1,
            label="Test",
            label_short="T",
            tags=["tag1"],
        )
        result = proxy.eval(x=5)

        assert result.id == 1
        assert result.label == "Test"
        assert result.label_short == "T"
        assert result.tags == {"tag1"}

    def test_eval_missing_parameters_raises_error(self, setup_module):
        """Verify eval() raises ValueError when parameters are missing."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test_{x}_{y}", id=1)

        with pytest.raises(ValueError, match="Missing parameters.*y.*"):
            proxy.eval(x=10)

    def test_eval_missing_multiple_parameters_raises_error(self, setup_module):
        """Verify eval() reports all missing parameters."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test_{a}_{b}_{c}", id=1)

        with pytest.raises(ValueError, match="Missing parameters") as exc_info:
            proxy.eval(a=1)

        assert "Missing parameters" in str(exc_info.value)
        assert "b" in str(exc_info.value)
        assert "c" in str(exc_info.value)

    def test_eval_no_parameters_needed(self, setup_module):
        """Verify eval() works when no parameters are needed."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="static", id=1)
        result = proxy.eval()

        assert result is not None
        assert result.name == "static"

    def test_eval_extra_parameters_ignored(self, setup_module):
        """Verify eval() ignores extra parameters not in format string."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test_{x}", id=1)
        result = proxy.eval(x=10, y=20, z=30)

        assert result.name == "test_10"

    def test_eval_with_string_parameters(self, setup_module):
        """Verify eval() works with string parameter values."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="cat_{mode}_{type}", id=1)
        result = proxy.eval(mode="tight", type="signal")

        assert result.name == "cat_tight_signal"

    def test_eval_with_mixed_parameter_types(self, setup_module):
        """Verify eval() works with mixed parameter types."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="cat_{str_param}_{int_param}", id=1)
        result = proxy.eval(str_param="test", int_param=42)

        assert result.name == "cat_test_42"

    @pytest.mark.parametrize(
        "name_format,params,expected_name",
        [
            ("test_{x}", {"x": 1}, "test_1"),
            ("{a}_{b}", {"a": "hello", "b": "world"}, "hello_world"),
            (
                "mx{x}_my{y}",
                {"x": 300, "y": 60},
                "mx300_my60",
            ),
            (
                "complex_{p1}_{p2}_{p3}",
                {"p1": "a", "p2": "b", "p3": "c"},
                "complex_a_b_c",
            ),
        ],
    )
    def test_eval_various_format_strings(
        self, setup_module, name_format, params, expected_name
    ):
        """Verify eval() handles various format string patterns."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name=name_format, id=1)
        result = proxy.eval(**params)

        assert result.name == expected_name


# =============================================================================
# Tests for CategoryProxy inheritance
# =============================================================================


class TestCategoryProxyInheritance:
    """Tests for CategoryProxy inheritance from Category."""

    def test_category_proxy_is_category_subclass(self, setup_module):
        """Verify CategoryProxy is a subclass of Category."""
        from order import Category

        from xyh.config.channels.util import CategoryProxy

        assert issubclass(CategoryProxy, Category)

    def test_category_proxy_instance_of_category(self, setup_module):
        """Verify CategoryProxy instances are Category instances."""
        from order import Category

        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test", id=1)
        assert isinstance(proxy, Category)

    def test_category_proxy_calls_parent_init(self, setup_module):
        """Verify CategoryProxy.__init__ calls parent __init__."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(
            name="test",
            id=1,
            label="Test",
            tags=["tag1"],
            aux={"key": "val"},
        )

        # Check that parent attributes are set
        assert proxy.name == "test"
        assert proxy.id == 1
        assert proxy.label == "Test"
        assert proxy.tags == {"tag1"}
        assert proxy.aux == {"key": "val"}

    def test_category_proxy_copy_method_exists(self, setup_module):
        """Verify CategoryProxy inherits copy() method from Category."""
        from xyh.config.channels.util import CategoryProxy

        proxy = CategoryProxy(name="test", id=1)
        assert hasattr(proxy, "copy")
        assert callable(proxy.copy)
