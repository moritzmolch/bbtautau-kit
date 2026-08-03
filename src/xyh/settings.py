import logging
import os
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, override

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parent.parent / "config" / "config.yaml"
)


class SingletonMeta(type):
    """
    Metaclass for singletons.

    Implementation according to
    https://stackoverflow.com/questions/6760685/what-is-the-best-way-of-implementing-a-singleton-in-python.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Settings(Mapping, metaclass=SingletonMeta):
    # --- Constructor and initialization ---------------------------------------

    def __init__(self):
        # Get the configuration file path and load the configuration
        self._config_file = self._get_config_file()
        self._config = self._load_config(self._config_file)

    # --- Internal methods for loading and accessing configuration -------------

    def _get_config_file(self) -> Path:
        # Set default config file to config/config.yaml
        config_file = DEFAULT_CONFIG_FILE

        # Check if environment variable KIT_CONFIG_FILE has been set
        if "KIT_CONFIG_FILE" in os.environ:
            config_file = Path(os.environ["KIT_CONFIG_FILE"])

        logger.info(f"Configuration file: {config_file}")
        return config_file

    def _load_config(self, config_file: Path) -> dict[str, Any]:
        # Check if configuration file exists
        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_file}"
            )

        # Load the configuration with YAML parser
        with config_file.open("r") as f:
            config = yaml.safe_load(f)

        # Validate that the loaded config is a dictionary
        config = config if config is not None else {}

        return config

    # --- Public methods to get configuration items ----------------------------

    def get(self, key: str, default: Any | None = None) -> Any:
        """
        Get a config value, supporting dot notation for nested keys.

        Example: `config.get("analysis.name")` returns
        `config["analysis"]["name"]`

        Parameters
        ----------
            key : str
                The configuration key (dot-separated for nested access)

            default : Any | None
                Default value to return if key is not found (optional).

        Returns:
            The configuration value or the default
        """
        return self._get(key, default=default, raises_if_not_found=False)

    @override
    def __getitem__(self, key: str):
        return self._get(key, default=None, raises_if_not_found=True)

    def _get(
        self,
        key: str,
        default: Any | None = None,
        raises_if_not_found: bool = False,
    ) -> Any:
        """
        Common implementation for get and __getitem__, with optional default
        value.
        """

        # Split up key into parts for nested access
        keys = key.split(".")

        # Traverse the configuration dictionary according to the keys
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                if raises_if_not_found:
                    # If the key is not found, raise a KeyError
                    # (__getitem__ behavior)
                    raise KeyError(f"Configuration key '{key}' not found")
                else:
                    # If the key is not found, return the default value
                    # (get behavior)
                    return default

        return value

    # --- Additional special methods to support Mapping interface --------------

    @override
    def __iter__(self) -> Iterator[str]:
        """Create an iterator over the top-level keys in the configuration."""
        return iter(self._config)

    @override
    def __len__(self) -> int:
        """Return the number of top-level keys in the configuration."""
        return len(self._config)

    @override
    def __contains__(self, key: object) -> bool:
        """
        Check if a key exists in the configuration (supports dot notation).
        """
        if not isinstance(key, str):
            return False
        try:
            self[key]
            return True
        except KeyError:
            return False

    # --- Properties to access configuration file and raw config ---------------

    @property
    def config_file(self) -> Path:
        """Return the path to the loaded configuration file."""
        return self._config_file

    @property
    def raw_config(self) -> dict[str, Any]:
        """Return the raw configuration dictionary."""
        return self._config.copy()
