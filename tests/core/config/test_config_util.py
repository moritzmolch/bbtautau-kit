"""Unit tests for `skip_process_in_category` in xyh.core.config.util."""

from types import SimpleNamespace

import pytest
from order import Category, Process

from xyh.core.config.util import skip_process_in_category


@pytest.fixture
def process_inst():
    return Process(name="proc", id=1)


def _category(**aux):
    return Category(name="cat", aux=aux)


def test_skip_process_in_category_without_aux_returns_false(process_inst):
    assert skip_process_in_category(_category(), process_inst) is False


@pytest.mark.parametrize(
    ("returned", "expected"),
    [(True, True), (False, False), (1, True), (0, False), (None, False)],
    ids=["true", "false", "truthy", "falsy", "none"],
)
def test_skip_process_in_category_returns_bool_of_aux_result(
    process_inst, returned, expected
):
    category_inst = _category(skip_process_inst=lambda p: returned)
    result = skip_process_in_category(category_inst, process_inst)
    assert result is expected


def test_skip_process_in_category_passes_process_to_aux(process_inst):
    received = []
    category_inst = _category(
        skip_process_inst=lambda p: received.append(p) or False
    )
    skip_process_in_category(category_inst, process_inst)
    assert received == [process_inst]


def test_skip_process_in_category_works_with_duck_typed_category(
    process_inst,
):
    category_inst = SimpleNamespace(
        has_aux=lambda key: key == "skip_process_inst",
        x=SimpleNamespace(skip_process_inst=lambda p: p.name == "proc"),
    )
    assert skip_process_in_category(category_inst, process_inst) is True
