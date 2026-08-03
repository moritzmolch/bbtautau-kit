"""
Unit tests for the xyh.config.analysis module.

This module tests the create_xyh_analysis function and validates
the DECAY_MODES and XY_MASSES configurations.
"""

from unittest.mock import Mock, patch

import pytest

# Import the module under test
from xyh.config.analysis import (
    DECAY_MODES,
    XY_MASSES,
    create_xyh_analysis,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_order_analysis():
    """
    Fixture to mock the order.Analysis class.

    This prevents actual instantiation of the Analysis object
    and allows us to verify how it's called.
    """
    with patch("xyh.config.analysis.Analysis") as mock_analysis:
        # Create a mock instance
        mock_instance = Mock(spec=["name", "id", "aux"])
        mock_instance.name = "mock_analysis"
        mock_instance.id = "+"
        mock_instance.aux = {}
        mock_analysis.return_value = mock_instance
        yield mock_analysis


@pytest.fixture
def valid_decay_mode_pair():
    """Provide a valid decay mode pair for testing."""
    return ("y2b", "h2tau")


@pytest.fixture
def valid_mass_pair():
    """Provide a valid mass pair for testing."""
    return (300, 60)


# =============================================================================
# Tests for DECAY_MODES configuration
# =============================================================================


class TestDecayModesConfiguration:
    """Tests for the DECAY_MODES list configuration."""

    def test_decay_modes_is_list(self):
        """Verify DECAY_MODES is a list."""
        assert isinstance(DECAY_MODES, list)

    def test_decay_modes_not_empty(self):
        """Verify DECAY_MODES contains at least one entry."""
        assert len(DECAY_MODES) > 0

    def test_decay_modes_are_strings(self):
        """Verify all decay modes are strings."""
        for mode in DECAY_MODES:
            assert isinstance(mode, str), f"Expected string, got {type(mode)}"

    def test_decay_modes_contain_y2b_h2tau(self):
        """Verify y2b_h2tau decay mode is present."""
        assert "y2b_h2tau" in DECAY_MODES

    def test_decay_modes_contain_y2tau_h2b(self):
        """Verify y2tau_h2b decay mode is present."""
        assert "y2tau_h2b" in DECAY_MODES

    def test_decay_modes_format_valid(self):
        """Verify all decay modes follow the expected format."""
        valid_prefixes = ["y2b", "y2tau"]
        valid_suffixes = ["h2b", "h2tau"]

        for mode in DECAY_MODES:
            parts = mode.split("_")
            assert len(parts) == 2, f"Invalid format: {mode}"
            assert parts[0] in valid_prefixes, f"Invalid Y decay: {parts[0]}"
            assert parts[1] in valid_suffixes, f"Invalid H decay: {parts[1]}"


# =============================================================================
# Tests for XY_MASSES configuration
# =============================================================================


class TestXYMassesConfiguration:
    """Tests for the XY_MASSES list configuration."""

    def test_xy_masses_is_list(self):
        """Verify XY_MASSES is a list."""
        assert isinstance(XY_MASSES, list)

    def test_xy_masses_not_empty(self):
        """Verify XY_MASSES contains at least one entry."""
        assert len(XY_MASSES) > 0

    def test_xy_masses_are_tuples(self):
        """Verify all mass entries are tuples."""
        for mass_pair in XY_MASSES:
            assert isinstance(mass_pair, tuple), (
                f"Expected tuple, got {type(mass_pair)}"
            )

    def test_xy_masses_tuple_length(self):
        """Verify all mass tuples have exactly 2 elements."""
        for mass_pair in XY_MASSES:
            assert len(mass_pair) == 2, (
                f"Expected 2 elements, got {len(mass_pair)}"
            )

    def test_xy_masses_are_integers(self):
        """Verify all mass values are integers."""
        for m_x, m_y in XY_MASSES:
            assert isinstance(m_x, int), f"m_x should be int, got {type(m_x)}"
            assert isinstance(m_y, int), f"m_y should be int, got {type(m_y)}"

    def test_xy_masses_positive_values(self):
        """Verify all mass values are positive."""
        for m_x, m_y in XY_MASSES:
            assert m_x > 0, f"m_x should be positive, got {m_x}"
            assert m_y > 0, f"m_y should be positive, got {m_y}"

    def test_xy_masses_m_x_greater_than_m_y(self):
        """Verify m_x is always greater than m_y."""
        for m_x, m_y in XY_MASSES:
            assert m_x > m_y, f"m_x ({m_x}) should be greater than m_y ({m_y})"

    def test_xy_masses_contains_expected_values(self):
        """Verify some expected mass combinations are present."""
        expected_combinations = [
            (300, 60),
            (500, 100),
            (1000, 500),
            (2000, 1000),
        ]
        for combination in expected_combinations:
            assert combination in XY_MASSES, (
                f"Missing combination: {combination}"
            )


# =============================================================================
# Tests for create_xyh_analysis function
# =============================================================================


class TestCreateXYHAnalysis:
    """Tests for the create_xyh_analysis function."""

    def test_create_xyh_analysis_valid_parameters_returns_instance(
        self, mock_order_analysis, valid_decay_mode_pair, valid_mass_pair
    ):
        """Verify function returns an Analysis instance with valid parameters."""
        y_decay, h_decay = valid_decay_mode_pair
        m_x, m_y = valid_mass_pair

        result = create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        assert result is not None
        mock_order_analysis.assert_called_once()

    def test_create_xyh_analysis_calls_analysis_with_correct_name(
        self, mock_order_analysis, valid_decay_mode_pair, valid_mass_pair
    ):
        """Verify Analysis is instantiated with correct name format."""
        y_decay, h_decay = valid_decay_mode_pair
        m_x, m_y = valid_mass_pair

        create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        call_kwargs = mock_order_analysis.call_args[1]
        expected_name = f"xyh_{y_decay}_{h_decay}_mx{m_x}_my{m_y}"
        assert call_kwargs["name"] == expected_name

    def test_create_xyh_analysis_calls_analysis_with_correct_id(
        self, mock_order_analysis, valid_decay_mode_pair, valid_mass_pair
    ):
        """Verify Analysis is instantiated with id='+'."""
        y_decay, h_decay = valid_decay_mode_pair
        m_x, m_y = valid_mass_pair

        create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        call_kwargs = mock_order_analysis.call_args[1]
        assert call_kwargs["id"] == "+"

    def test_create_xyh_analysis_stores_aux_data_correctly(
        self, mock_order_analysis, valid_decay_mode_pair, valid_mass_pair
    ):
        """Verify aux dictionary contains correct signal hypothesis data."""
        y_decay, h_decay = valid_decay_mode_pair
        m_x, m_y = valid_mass_pair

        create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        call_kwargs = mock_order_analysis.call_args[1]
        aux = call_kwargs["aux"]

        assert aux["y_decay_mode"] == y_decay
        assert aux["h_decay_mode"] == h_decay
        assert aux["m_x"] == m_x
        assert aux["m_y"] == m_y

    @pytest.mark.parametrize(
        "y_decay,h_decay",
        [
            ("y2b", "h2tau"),
            ("y2tau", "h2b"),
        ],
    )
    def test_create_xyh_analysis_all_valid_decay_modes(
        self, mock_order_analysis, y_decay, h_decay, valid_mass_pair
    ):
        """Verify function works with all valid decay mode combinations."""
        m_x, m_y = valid_mass_pair

        result = create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        assert result is not None
        call_kwargs = mock_order_analysis.call_args[1]
        assert call_kwargs["aux"]["y_decay_mode"] == y_decay
        assert call_kwargs["aux"]["h_decay_mode"] == h_decay

    @pytest.mark.parametrize(
        "m_x,m_y",
        [
            (300, 60),
            (500, 100),
            (1000, 500),
            (2000, 1000),
        ],
    )
    def test_create_xyh_analysis_various_valid_masses(
        self, mock_order_analysis, valid_decay_mode_pair, m_x, m_y
    ):
        """Verify function works with various valid mass combinations."""
        y_decay, h_decay = valid_decay_mode_pair

        result = create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        assert result is not None
        call_kwargs = mock_order_analysis.call_args[1]
        assert call_kwargs["aux"]["m_x"] == m_x
        assert call_kwargs["aux"]["m_y"] == m_y

    def test_create_xyh_analysis_invalid_y_decay_mode_raises_error(
        self, mock_order_analysis, valid_mass_pair
    ):
        """Verify ValueError is raised for invalid Y decay mode."""
        m_x, m_y = valid_mass_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis("y2invalid", "h2tau", m_x, m_y)

        assert "('y2invalid', 'h2tau') not found in DECAY_MODES" in str(
            exc_info.value
        )

    def test_create_xyh_analysis_invalid_h_decay_mode_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair, valid_mass_pair
    ):
        """Verify ValueError is raised for invalid H decay mode."""
        y_decay, _ = valid_decay_mode_pair
        m_x, m_y = valid_mass_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis(y_decay, "h2invalid", m_x, m_y)

        assert f"('{y_decay}', 'h2invalid') not found in DECAY_MODES" in str(
            exc_info.value
        )

    def test_create_xyh_analysis_both_invalid_decay_modes_raises_error(
        self, mock_order_analysis, valid_mass_pair
    ):
        """Verify ValueError is raised when both decay modes are invalid."""
        m_x, m_y = valid_mass_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis("y2invalid", "h2invalid", m_x, m_y)

        assert "('y2invalid', 'h2invalid') not found in DECAY_MODES" in str(
            exc_info.value
        )

    def test_create_xyh_analysis_invalid_mass_pair_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify ValueError is raised for mass combination not in XY_MASSES."""
        y_decay, h_decay = valid_decay_mode_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis(y_decay, h_decay, 999, 999)

        assert "(999, 999) not found in XY_MASSES" in str(exc_info.value)

    def test_create_xyh_analysis_invalid_m_x_only_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify ValueError is raised when only m_x is invalid."""
        y_decay, h_decay = valid_decay_mode_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis(y_decay, h_decay, 9999, 60)

        assert "(9999, 60) not found in XY_MASSES" in str(exc_info.value)

    def test_create_xyh_analysis_invalid_m_y_only_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify ValueError is raised when only m_y is invalid."""
        y_decay, h_decay = valid_decay_mode_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis(y_decay, h_decay, 300, 999)

        assert "(300, 999) not found in XY_MASSES" in str(exc_info.value)

    def test_create_xyh_analysis_zero_mass_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify ValueError is raised for zero mass values."""
        y_decay, h_decay = valid_decay_mode_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis(y_decay, h_decay, 0, 60)

        assert "(0, 60) not found in XY_MASSES" in str(exc_info.value)

    def test_create_xyh_analysis_negative_mass_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify ValueError is raised for negative mass values."""
        y_decay, h_decay = valid_decay_mode_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis(y_decay, h_decay, -300, 60)

        assert "(-300, 60) not found in XY_MASSES" in str(exc_info.value)

    def test_create_xyh_analysis_m_y_greater_than_m_x_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify ValueError is raised when m_y > m_x."""
        y_decay, h_decay = valid_decay_mode_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis(y_decay, h_decay, 300, 400)

        assert "(300, 400) not found in XY_MASSES" in str(exc_info.value)

    def test_create_xyh_analysis_equal_masses_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify ValueError is raised when m_x == m_y."""
        y_decay, h_decay = valid_decay_mode_pair

        with pytest.raises(ValueError) as exc_info:
            create_xyh_analysis(y_decay, h_decay, 300, 300)

        assert "(300, 300) not found in XY_MASSES" in str(exc_info.value)

    def test_create_xyh_analysis_analysis_constructor_called_once(
        self, mock_order_analysis, valid_decay_mode_pair, valid_mass_pair
    ):
        """Verify Analysis constructor is called exactly once."""
        y_decay, h_decay = valid_decay_mode_pair
        m_x, m_y = valid_mass_pair

        create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        assert mock_order_analysis.call_count == 1

    def test_create_xyh_analysis_returns_mock_instance(
        self, mock_order_analysis, valid_decay_mode_pair, valid_mass_pair
    ):
        """Verify the function returns the Analysis instance."""
        y_decay, h_decay = valid_decay_mode_pair
        m_x, m_y = valid_mass_pair

        result = create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        assert result == mock_order_analysis.return_value


# =============================================================================
# Edge case tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_create_xyh_analysis_minimum_mass_in_config(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify function works with minimum mass values from config."""
        y_decay, h_decay = valid_decay_mode_pair
        # Find minimum mass combination
        min_mass = min(XY_MASSES, key=lambda x: (x[0], x[1]))
        m_x, m_y = min_mass

        result = create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        assert result is not None
        call_kwargs = mock_order_analysis.call_args[1]
        assert call_kwargs["aux"]["m_x"] == m_x
        assert call_kwargs["aux"]["m_y"] == m_y

    def test_create_xyh_analysis_maximum_mass_in_config(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify function works with maximum mass values from config."""
        y_decay, h_decay = valid_decay_mode_pair
        # Find maximum mass combination
        max_mass = max(XY_MASSES, key=lambda x: (x[0], x[1]))
        m_x, m_y = max_mass

        result = create_xyh_analysis(y_decay, h_decay, m_x, m_y)

        assert result is not None
        call_kwargs = mock_order_analysis.call_args[1]
        assert call_kwargs["aux"]["m_x"] == m_x
        assert call_kwargs["aux"]["m_y"] == m_y

    def test_create_xyh_analysis_string_type_validation(
        self, mock_order_analysis, valid_mass_pair
    ):
        """Verify function handles non-string decay modes appropriately."""
        m_x, m_y = valid_mass_pair

        # Non-string decay mode should fail validation
        with pytest.raises((ValueError, TypeError)):
            create_xyh_analysis(123, "h2tau", m_x, m_y)

    def test_create_xyh_analysis_none_decay_mode_raises_error(
        self, mock_order_analysis, valid_mass_pair
    ):
        """Verify function handles None decay mode."""
        m_x, m_y = valid_mass_pair

        with pytest.raises((ValueError, TypeError)):
            create_xyh_analysis(None, "h2tau", m_x, m_y)

    def test_create_xyh_analysis_none_mass_raises_error(
        self, mock_order_analysis, valid_decay_mode_pair
    ):
        """Verify function handles None mass value."""
        y_decay, h_decay = valid_decay_mode_pair

        with pytest.raises((ValueError, TypeError)):
            create_xyh_analysis(y_decay, h_decay, None, 60)

    def test_decay_modes_no_duplicates(self):
        """Verify DECAY_MODES has no duplicate entries."""
        assert len(DECAY_MODES) == len(set(DECAY_MODES))

    def test_xy_masses_no_duplicates(self):
        """Verify XY_MASSES has no duplicate mass combinations."""
        assert len(XY_MASSES) == len(set(XY_MASSES))
