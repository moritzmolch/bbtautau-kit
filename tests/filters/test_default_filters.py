"""Unit tests for `default_filters` in xyh.filters (sub-selections stubbed)."""

from collections import OrderedDict
from types import SimpleNamespace

import pytest

from xyh.filters import default_filters

SUB_SELECTIONS = (
    "triggers",
    "jet_vetomap",
    "ll_pair",
    "bb_pair",
    "tautau_gen_selection",
    "jet_categories",
)


@pytest.fixture
def requested(monkeypatch):
    """Stub `get_instance` so that the sub-selections are not evaluated."""
    names = []

    def fake_get_instance(self, name):
        names.append(name)
        return SimpleNamespace(
            nominal=lambda: OrderedDict({f"sel_{name}": f"expr_{name}"})
        )

    monkeypatch.setattr(default_filters, "get_instance", fake_get_instance)
    return names


def _category(tags=(), **aux):
    return SimpleNamespace(
        has_tag=lambda tag: tag in tags,
        x=SimpleNamespace(**aux),
    )


def _call(category_inst):
    selections = default_filters(category_inst=category_inst).nominal()
    return selections, None


@pytest.fixture
def clf_category():
    return _category(
        tags={"clf"},
        output_class="z2tau",
        output_class_index=2,
        m_x=300,
        m_y=60,
    )


def test_default_filters_non_clf_category_has_only_sub_selections(requested):
    selections, _ = _call(_category())
    assert list(selections) == [f"sel_{n}" for n in SUB_SELECTIONS]


def test_default_filters_non_clf_category_has_no_clf_selection(requested):
    selections, _ = _call(_category())
    assert not any(key.startswith("clf_") for key in selections)


def test_default_filters_clf_category_selects_output_class_index(
    requested,
    clf_category,
):
    selections, _ = _call(clf_category)
    assert selections["clf_z2tau"] == "max_score_index_m_x_300_m_y_60 == 2"


def test_default_filters_clf_selection_is_last(requested, clf_category):
    selections, _ = _call(clf_category)
    assert list(selections)[-1] == "clf_z2tau"
    assert list(selections)[:-1] == [f"sel_{n}" for n in SUB_SELECTIONS]


@pytest.mark.parametrize(
    ("output_class", "index", "m_x", "m_y"),
    [("xyh", 0, 400, 70), ("jetfakes", 3, 550, 150)],
    ids=["xyh", "jetfakes"],
)
def test_default_filters_clf_selection_follows_category_aux(
    requested, output_class, index, m_x, m_y
):
    category_inst = _category(
        tags={"clf"},
        output_class=output_class,
        output_class_index=index,
        m_x=m_x,
        m_y=m_y,
    )
    selections, _ = _call(category_inst)
    assert selections[f"clf_{output_class}"] == (
        f"max_score_index_m_x_{m_x}_m_y_{m_y} == {index}"
    )


def test_default_filters_requests_all_sub_selections_in_order(requested):
    _call(_category())
    assert requested == list(SUB_SELECTIONS)
