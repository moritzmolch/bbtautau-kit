"""
Unit tests for the xyh.core.cli module.

This module tests the ``hydra_cli`` decorator factory. The Hydra package
and the project's ``ROOT_DIR`` are mocked out so that the tests are fully
isolated from any real filesystem or Hydra machinery.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from omegaconf import DictConfig

from xyh.core.cli import hydra_cli


@pytest.fixture(autouse=True)
def _mock_hydra():
    """Replace the real ``hydra.main`` decorator with a passthrough mock.

    The mock records its invocation arguments so tests can assert that the
    wrapper was built with the expected ``config_path``/``config_name``.
    """
    mock_main = Mock()
    # ``hydra.main`` is a real decorator: it receives kwargs and must return
    # a callable that turns the target function into a decorated one.
    mock_main.return_value = Mock(side_effect=lambda fn: fn)
    with patch("xyh.core.cli.hydra.main", mock_main):
        yield mock_main


@pytest.fixture
def mock_root_dir():
    """Provide a fake ROOT_DIR location for the module under test."""
    with patch("xyh.core.cli.ROOT_DIR", Path("/fake/root")):
        yield


def test_hydra_cli_returns_a_decorator():
    """hydra_cli must return a callable used as a decorator."""
    decorator = hydra_cli("my_config")
    assert callable(decorator)


def test_hydra_cli_decorator_returns_a_callable_wrapper():
    """The returned decorator must wrap a function into a new callable."""
    decorator = hydra_cli("my_config")

    def entry(cfg: DictConfig) -> None:
        pass

    wrapped = decorator(entry)
    assert callable(wrapped)
    assert wrapped is not entry  # wrapper should be a distinct function


def test_hydra_cli_passes_config_path_and_config_name_to_hydra_main(
    mock_root_dir, _mock_hydra
):
    """hydra.main must be invoked with the project hydra_config directory
    and the user-supplied config name."""
    config_name = "selecting"
    decorator = hydra_cli(config_name)

    def entry(cfg: DictConfig) -> None:
        pass

    decorator(entry)

    _mock_hydra.assert_called_once_with(
        config_path=str(Path("/fake/root") / "hydra_config"),
        config_name=config_name,
        version_base=None,
    )


def test_hydra_cli_uses_entry_specific_config_name(mock_root_dir, _mock_hydra):
    """Different config names must be propagated to hydra.main."""
    decorator = hydra_cli("other_config")

    def entry(cfg: DictConfig) -> None:
        pass

    decorator(entry)

    _mock_hydra.assert_called_once_with(
        config_path=str(Path("/fake/root") / "hydra_config"),
        config_name="other_config",
        version_base=None,
    )


def test_hydra_cli_wrapper_forwards_cfg_to_original_function(
    mock_root_dir, _mock_hydra
):
    """The produced wrapper must invoke the original function with the
    composed ``cfg`` DictConfig and return its result."""
    decorator = hydra_cli("my_config")
    received = {}

    def entry(cfg: DictConfig) -> str:
        received["cfg"] = cfg
        return "done"

    wrapped = decorator(entry)

    cfg = {"param": "value"}
    result = wrapped(cfg)

    assert received["cfg"] is cfg
    assert result == "done"


def test_hydra_cli_wrapper_passes_through_return_value(mock_root_dir, _mock_hydra):
    """The wrapper must return the value returned by the original function."""
    decorator = hydra_cli("my_config")

    def entry(cfg: DictConfig) -> int:
        return 42

    wrapped = decorator(entry)
    assert wrapped({}) == 42
