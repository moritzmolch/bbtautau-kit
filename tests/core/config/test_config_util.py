"""Unit tests for `skip_process_in_category` in xyh.core.config.util."""

from types import SimpleNamespace

import pytest
from omegaconf import ListConfig
from order import Category, Channel, Process

from xyh.core.config.util import gen_category_insts, skip_process_in_category


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


# =============================================================================
# gen_category_insts
# =============================================================================


def _channel(*names):
    channel_inst = Channel(name="tt", id=1)
    for name in names:
        channel_inst.add_category(name=name, id="+")
    return channel_inst


def _names(channel_inst, patterns):
    return [c.name for c in gen_category_insts(channel_inst, patterns)]


def test_gen_category_insts_exact_name_matches_itself():
    channel_inst = _channel("cat_a", "cat_b")
    assert _names(channel_inst, ["cat_b"]) == ["cat_b"]


def test_gen_category_insts_regex_matches_all_fitting_names():
    channel_inst = _channel("clf_a", "clf_b", "other")
    assert _names(channel_inst, [r"clf_.*"]) == ["clf_a", "clf_b"]


def test_gen_category_insts_prefix_alone_does_not_match():
    channel_inst = _channel("cat_a", "cat")
    assert _names(channel_inst, ["cat"]) == ["cat"]


def test_gen_category_insts_pattern_must_match_the_full_name():
    channel_inst = _channel("my_cat")
    assert _names(channel_inst, ["cat"]) == []
    assert _names(channel_inst, ["my"]) == []


def test_gen_category_insts_includes_nested_categories():
    channel_inst = _channel("parent")
    channel_inst.get_category("parent").add_category(name="child", id="+")
    assert _names(channel_inst, ["child"]) == ["child"]
    assert _names(channel_inst, [".*"]) == ["parent", "child"]


def test_gen_category_insts_no_match_gives_nothing():
    assert _names(_channel("cat"), ["nope", r"x.*"]) == []


def test_gen_category_insts_no_patterns_gives_nothing():
    assert _names(_channel("cat"), []) == []


def test_gen_category_insts_malformed_regex_raises_naming_the_entry():
    with pytest.raises(ValueError, match=r"'clf_\(' is not a valid"):
        _names(_channel("cat"), ["cat", "clf_("])


def test_gen_category_insts_malformed_regex_raises_without_categories():
    with pytest.raises(ValueError, match="'\\[' is not a valid"):
        _names(_channel(), ["["])


def test_gen_category_insts_category_matched_twice_is_yielded_once():
    channel_inst = _channel("cat_a", "cat_b")
    assert _names(channel_inst, ["cat_a", r"cat_.*", "cat_a"]) == [
        "cat_a",
        "cat_b",
    ]


def test_gen_category_insts_orders_by_pattern_then_declaration():
    channel_inst = _channel("a1", "b1", "a2", "b2")
    assert _names(channel_inst, [r"b.*", r"a.*"]) == ["b1", "b2", "a1", "a2"]


def test_gen_category_insts_accepts_omegaconf_listconfig():
    channel_inst = _channel("clf_a", "clf_b", "other")
    patterns = ListConfig([r"clf_.*", "other"])
    assert _names(channel_inst, patterns) == ["clf_a", "clf_b", "other"]


def test_gen_category_insts_yields_the_category_objects_of_the_channel():
    channel_inst = _channel("cat")
    (category_inst,) = gen_category_insts(channel_inst, ["cat"])
    assert category_inst is channel_inst.get_category("cat")
