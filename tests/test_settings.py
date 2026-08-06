"""
Unit tests for the xyh.settings module.

This module tests the Settings singleton class, including configuration loading,
dot notation access, environment variable handling, and Mapping interface.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# Import the module under test
from xyh.settings import (
    DEFAULT_CONFIG_FILE,
    Settings,
    SingletonMeta,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def reset_settings_singleton():
    """
    Fixture to reset the Settings singleton between tests.

    This ensures each test starts with a fresh singleton instance.
    """
    # Clear the singleton instances before test
    SingletonMeta._instances.clear()
    yield
    # Clear after test as well
    SingletonMeta._instances.clear()


@pytest.fixture
def sample_config_dict():
    """Provide a sample configuration dictionary for testing."""
    return {
        "analysis": {
            "name": "test_analysis",
            "version": "1.0.0",
        },
        "data": {
            "path": "/path/to/data",
            "format": "parquet",
        },
        "debug": True,
        "threshold": 0.95,
    }


@pytest.fixture
def mock_config_file(sample_config_dict):
    """
    Create a mock configuration file with sample content.

    Returns a tuple of (mock_path, mock_file_content).
    """
    import yaml

    yaml_content = yaml.dump(sample_config_dict)
    mock_path = Path("/fake/path/config.yaml")
    return mock_path, yaml_content


@pytest.fixture
def mock_yaml_file_reader(mock_config_file):
    """
    Mock the file reading and YAML loading.

    This fixture mocks both Path.exists() and yaml.safe_load().
    """
    mock_path, yaml_content = mock_config_file

    with patch("xyh.settings.Path") as mock_path_class:
        # Setup the mock path instance
        mock_path_instance = Mock(spec=Path)
        mock_path_instance.exists.return_value = True

        # Mock the file open context manager properly
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read.return_value = yaml_content
        mock_path_instance.open.return_value = mock_file

        mock_path_instance.resolve.return_value.parent.parent = (
            mock_path.parent.parent
        )
        mock_path_class.return_value = mock_path_instance

        with patch("xyh.settings.yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = sample_config_dict_from_content(
                yaml_content
            )
            yield mock_path_class, mock_yaml


def sample_config_dict_from_content(content):
    """Helper to parse YAML content to dict for mocking."""
    import yaml

    return yaml.safe_load(content)


# =============================================================================
# Tests for DEFAULT_CONFIG_FILE constant
# =============================================================================


class TestDefaultConfigFile:
    """Tests for the DEFAULT_CONFIG_FILE constant."""

    def test_default_config_file_is_path_instance(self):
        """Verify DEFAULT_CONFIG_FILE is a Path instance."""
        assert isinstance(DEFAULT_CONFIG_FILE, Path)

    def test_default_config_file_exists_in_project(self):
        """Verify the default config file path points to expected location."""
        # Should point to src/config/config.yaml relative to settings.py
        assert DEFAULT_CONFIG_FILE.name == "config.yaml"
        assert "config" in str(DEFAULT_CONFIG_FILE)

    def test_default_config_file_exists_as_file(self):
        """Verify that the default config file actually exists in the project."""
        # This test assumes the default config file is present in the repo
        assert DEFAULT_CONFIG_FILE.exists()
        assert DEFAULT_CONFIG_FILE.is_file()


# =============================================================================
# Tests for SingletonMeta metaclass
# =============================================================================


class TestSingletonMeta:
    """Tests for the SingletonMeta metaclass behavior."""

    def test_singleton_creates_instance_once(self, reset_settings_singleton):
        """Verify singleton creates only one instance."""
        with patch.object(
            Settings, "_get_config_file", return_value=Path("/fake.yaml")
        ):
            with patch.object(Settings, "_load_config", return_value={}):
                instance1 = Settings()
                instance2 = Settings()

                assert instance1 is instance2

    def test_singleton_multiple_calls_return_same_instance(
        self, reset_settings_singleton
    ):
        """Verify multiple calls to Settings() return same instance."""
        with patch.object(
            Settings, "_get_config_file", return_value=Path("/fake.yaml")
        ):
            with patch.object(Settings, "_load_config", return_value={}):
                instances = [Settings() for _ in range(5)]

                # All instances should be identical
                assert all(instance is instances[0] for instance in instances)


# =============================================================================
# Tests for Settings initialization and config loading
# =============================================================================


class TestSettingsInitialization:
    """Tests for Settings class initialization."""

    def test_settings_initialization_with_mock_config(
        self,
        reset_settings_singleton,
        sample_config_dict,
    ):
        """Verify Settings initializes correctly with valid config."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert settings is not None
                assert isinstance(settings.raw_config, dict)

    def test_settings_get_config_file_default_path(
        self, reset_settings_singleton, mock_yaml_file_reader
    ):
        """Verify _get_config_file returns default path when env var not set."""
        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            # Config file should be the DEFAULT_CONFIG_FILE
            assert settings.config_file == DEFAULT_CONFIG_FILE

    def test_settings_get_config_file_from_env_variable(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify _get_config_file uses KIT_CONFIG_FILE env var when set."""
        custom_path = Path("/custom/path/config.yaml")

        with patch.dict(os.environ, {"KIT_CONFIG_FILE": str(custom_path)}):
            # Mock Path.exists() to return True
            with patch.object(Path, "exists", return_value=True):
                # Mock Path.open() as a context manager
                mock_file = MagicMock()
                mock_file.__enter__ = Mock(return_value=mock_file)
                mock_file.__exit__ = Mock(return_value=False)

                with patch.object(Path, "open", return_value=mock_file):
                    with patch(
                        "xyh.settings.yaml.safe_load",
                        return_value=sample_config_dict,
                    ):
                        settings = Settings()

                        assert settings.config_file == custom_path

    def test_settings_load_config_file_not_found_raises_error(
        self, reset_settings_singleton
    ):
        """Verify _load_config raises FileNotFoundError when file missing."""
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError) as exc_info:
                Settings()

            assert "Configuration file not found" in str(exc_info.value)

    def test_settings_load_config_valid_yaml(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify _load_config correctly parses YAML file."""
        import yaml

        # Create the sample data
        mock_data = yaml.dump(sample_config_dict)

        # Mock Path.open() to return the mock file
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_file_handle.__exit__.return_value = False
        mock_file_handle.read.return_value = yaml.dump(mock_data)

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "open", return_value=mock_file_handle):
                with patch("yaml.safe_load", return_value=sample_config_dict):
                    settings = Settings()

                    assert settings.raw_config == sample_config_dict
                # settings = Settings()

                # assert settings.raw_config == sample_config_dict

    def test_settings_load_config_empty_file_returns_empty_dict(
        self, reset_settings_singleton
    ):
        """Verify _load_config handles empty YAML file gracefully."""
        m = mock_open(read_data="")

        # Mock the file handle to behave as a context manager
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_file_handle.__exit__.return_value = False
        mock_file_handle.read.return_value = ""

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "open", return_value=mock_file_handle):
                settings = Settings()

                assert settings.raw_config == {}


# =============================================================================
# Tests for Settings.get() method with dot notation
# =============================================================================


class TestSettingsGet:
    """Tests for the get() method with dot notation support."""

    def test_settings_get_top_level_key(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify get() retrieves top-level configuration values."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert settings.get("debug") is True

    def test_settings_get_nested_key_two_levels(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify get() retrieves nested values with dot notation."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                result = settings.get("analysis.name")
                assert result == "test_analysis"

    def test_settings_get_nested_key_three_levels(
        self, reset_settings_singleton
    ):
        """Verify get() works with deeply nested keys."""
        config = {"level1": {"level2": {"level3": "deep_value"}}}

        with patch.object(Settings, "_load_config", return_value=config):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                result = settings.get("level1.level2.level3")
                assert result == "deep_value"

    def test_settings_get_missing_key_returns_none(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify get() returns None for missing keys by default."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                result = settings.get("nonexistent")
                assert result is None

    def test_settings_get_missing_key_with_default(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify get() returns provided default for missing keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                result = settings.get("nonexistent", default="default_value")
                assert result == "default_value"

    def test_settings_get_nested_missing_key_returns_default(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify get() handles missing nested keys gracefully."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                result = settings.get(
                    "analysis.nonexistent.key", default="missing"
                )
                assert result == "missing"

    def test_settings_get_different_types(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify get() returns correct types for various value types."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                # Boolean
                assert settings.get("debug") is True
                # Float
                assert settings.get("threshold") == 0.95
                # String
                assert settings.get("data.format") == "parquet"
                # Dict
                assert (
                    settings.get("analysis") == sample_config_dict["analysis"]
                )


# =============================================================================
# Tests for Settings.__getitem__() method
# =============================================================================


class TestSettingsGetItem:
    """Tests for the __getitem__() method (bracket notation)."""

    def test_settings_getitem_top_level_key(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify bracket notation retrieves top-level values."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert settings["debug"] is True

    def test_settings_getitem_nested_key(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify bracket notation works with dot notation for nested keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert settings["analysis.name"] == "test_analysis"

    def test_settings_getitem_missing_key_raises_keyerror(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify bracket notation raises KeyError for missing keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                with pytest.raises(KeyError) as exc_info:
                    _ = settings["nonexistent"]

                assert "Configuration key 'nonexistent' not found" in str(
                    exc_info.value
                )

    def test_settings_getitem_nested_missing_key_raises_keyerror(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify bracket notation raises KeyError for missing nested keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                with pytest.raises(KeyError) as exc_info:
                    _ = settings["analysis.nonexistent.key"]

                assert (
                    "Configuration key 'analysis.nonexistent.key' not found"
                    in str(exc_info.value)
                )


# =============================================================================
# Tests for Mapping interface (__iter__, __len__, __contains__)
# =============================================================================


class TestSettingsMappingInterface:
    """Tests for the Mapping interface implementation."""

    def test_settings_iter_yields_top_level_keys(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify __iter__ yields top-level configuration keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                keys = list(settings)
                assert set(keys) == {"analysis", "data", "debug", "threshold"}

    def test_settings_len_returns_top_level_key_count(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify __len__ returns count of top-level keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert len(settings) == 4

    def test_settings_len_empty_config(self, reset_settings_singleton):
        """Verify __len__ returns 0 for empty config."""
        with patch.object(Settings, "_load_config", return_value={}):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert len(settings) == 0

    def test_settings_contains_top_level_key(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify __contains__ finds top-level keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert "debug" in settings
                assert "analysis" in settings

    def test_settings_contains_nested_key_with_dot_notation(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify __contains__ supports dot notation."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert "analysis.name" in settings
                assert "data.path" in settings

    def test_settings_contains_missing_key(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify __contains__ returns False for missing keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert "nonexistent" not in settings

    def test_settings_contains_non_string_key(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify __contains__ returns False for non-string keys."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert 123 not in settings
                assert None not in settings


# =============================================================================
# Tests for Properties (config_file, raw_config)
# =============================================================================


class TestSettingsProperties:
    """Tests for Settings properties."""

    def test_settings_config_file_property(
        self, reset_settings_singleton, mock_yaml_file_reader
    ):
        """Verify config_file property returns the loaded config path."""
        settings = Settings()

        assert isinstance(settings.config_file, Path)

    def test_settings_raw_config_returns_copy(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify raw_config returns a copy, not the original."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                raw = settings.raw_config
                # Modify the returned copy
                raw["modified"] = True

                # Original should be unchanged
                assert "modified" not in settings.raw_config

    def test_settings_raw_config_is_dict(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify raw_config returns a dictionary."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert isinstance(settings.raw_config, dict)


# =============================================================================
# Integration-style tests (with more realistic mocking)
# =============================================================================


class TestSettingsIntegration:
    """Integration-style tests with realistic scenarios."""

    def test_settings_complete_workflow(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Test complete workflow: init, get values, check containment."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                # Test get()
                assert settings.get("analysis.name") == "test_analysis"
                assert settings.get("debug") is True

                # Test __getitem__()
                assert settings["data.format"] == "parquet"

                # Test __contains__()
                assert "threshold" in settings
                assert "missing" not in settings

                # Test __iter__()
                keys = list(settings)
                assert len(keys) == 4

                # Test __len__()
                assert len(settings) == 4

    def test_settings_environment_variable_override(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Test environment variable override with complete flow."""
        custom_path = Path("/custom/config.yaml")

        with patch.dict(os.environ, {"KIT_CONFIG_FILE": str(custom_path)}):
            # Mock Path.exists() to return True
            with patch.object(Path, "exists", return_value=True):
                # Mock Path.open() as a context manager
                mock_file = Mock()
                mock_file.__enter__ = Mock(return_value=mock_file)
                mock_file.__exit__ = Mock(return_value=False)

                with patch.object(Path, "open", return_value=mock_file):
                    with patch(
                        "xyh.settings.yaml.safe_load",
                        return_value=sample_config_dict,
                    ):
                        settings = Settings()

                        assert settings.config_file == custom_path
                        assert settings.get("analysis.version") == "1.0.0"

    def test_settings_complex_nested_structure(self, reset_settings_singleton):
        """Test with complex nested configuration structure."""
        complex_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {"username": "admin", "password": "secret"},
            },
            "features": ["feature1", "feature2", "feature3"],
            "limits": {"max_connections": 100, "timeout": 30.5},
        }

        with patch.object(
            Settings, "_load_config", return_value=complex_config
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                # Deep nested access
                assert settings.get("database.credentials.username") == "admin"
                assert settings.get("database.port") == 5432

                # List access
                assert settings.get("features") == [
                    "feature1",
                    "feature2",
                    "feature3",
                ]

                # Float values
                assert settings.get("limits.timeout") == 30.5


# =============================================================================
# Edge case and error handling tests
# =============================================================================


class TestSettingsEdgeCases:
    """Tests for edge cases and error handling."""

    def test_settings_dot_notation_empty_string_key(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify handling of empty string key."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                # Empty string should not match anything
                result = settings.get("")
                assert result is None

    def test_settings_dot_notation_trailing_dot(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify handling of trailing dot in key."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                result = settings.get("analysis.")
                assert result is None

    def test_settings_dot_notation_leading_dot(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify handling of leading dot in key."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                result = settings.get(".analysis")
                assert result is None

    def test_settings_none_as_default_value(
        self, reset_settings_singleton, sample_config_dict
    ):
        """Verify None can be used as explicit default value."""
        with patch.object(
            Settings, "_load_config", return_value=sample_config_dict
        ):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                result = settings.get("missing", default=None)
                assert result is None

    def test_settings_zero_as_valid_value(self, reset_settings_singleton):
        """Verify 0 is returned correctly (not treated as falsy)."""
        config = {"zero_value": 0, "empty_string": ""}

        with patch.object(Settings, "_load_config", return_value=config):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert settings.get("zero_value") == 0
                assert settings.get("empty_string") == ""

    def test_settings_false_as_valid_value(self, reset_settings_singleton):
        """Verify False is returned correctly (not treated as missing)."""
        config = {"false_value": False}

        with patch.object(Settings, "_load_config", return_value=config):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert settings.get("false_value") is False

    def test_settings_unicode_keys_and_values(self, reset_settings_singleton):
        """Verify Unicode characters in keys and values work correctly."""
        config = {"分析": "测试值", "données": "français"}

        with patch.object(Settings, "_load_config", return_value=config):
            with patch.object(
                Settings, "_get_config_file", return_value=Path("/fake.yaml")
            ):
                settings = Settings()

                assert settings.get("分析") == "测试值"
                assert settings.get("données") == "français"
