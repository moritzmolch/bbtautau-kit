"""Unit tests for `xyh.fit.config`."""

import pytest
from omegaconf import OmegaConf

from xyh.fit.config import as_list


def test_as_list_none_stays_none():
    assert as_list(None) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [("tt", ["tt"]), (5, [5]), ([1, 2], [1, 2]), ([], [])],
)
def test_as_list_plain_values(value, expected):
    assert as_list(value) == expected


def test_as_list_omegaconf_list_becomes_plain_list():
    value = as_list(OmegaConf.create([[1, 2], [3, 4]]))
    assert value == [[1, 2], [3, 4]]
    assert type(value) is list
