"""
Unit tests for xyh.config.channels._categories_clf module.

The analysis profile is stubbed, the channel and the processes are real
`order` objects.
"""

from types import SimpleNamespace

import pytest
from order import Channel, Process

from xyh.config.channels import _categories_clf
from xyh.config.channels._categories_clf import add_clf_categories

# Signal parameters of the stubbed profile: ((y_decay, h_decay), (m_x, m_y))
SIGNAL_PARAMETERS = [
    (("y2b", "h2tau"), (300, 60)),
    (("y2b", "h2tau"), (400, 70)),
    (("y2tau", "h2b"), (300, 60)),
]

CLASS_NAMES = ["xyh", "t_tt", "z2tau", "jetfakes"]


@pytest.fixture(autouse=True)
def profile(monkeypatch):
    """Patch the (cached, env-dependent) profile where it is looked up."""
    stub = SimpleNamespace(
        iterate_signal_parameters=lambda campaign=None: iter(SIGNAL_PARAMETERS)
    )
    monkeypatch.setattr(_categories_clf, "get_profile", lambda: stub)
    return stub


@pytest.fixture
def channel():
    channel_inst = Channel(name="et", id=1, label="e#tau")
    add_clf_categories(channel_inst)
    return channel_inst


def _category(channel_inst, name, y="y2b", h="h2tau", m_x=300, m_y=60):
    return channel_inst.get_category(
        f"et_clf_{name}_xyh_{y}_{h}_mx{m_x}_my{m_y}"
    )


def _process(name, id_, tags=(), **aux):
    return Process(name=name, id=id_, tags=set(tags), aux=aux)


def _signal(id_, y="y2b", h="h2tau", m_x=300, m_y=60):
    return _process(
        f"sig_{id_}",
        id_,
        tags={"signal"},
        y_decay_mode=y,
        h_decay_mode=h,
        m_x=m_x,
        m_y=m_y,
    )


class TestAddClfCategories:
    def test_creates_four_classes_per_signal_parameter_set(self, channel):
        assert len(channel.categories) == 4 * len(SIGNAL_PARAMETERS)

    @pytest.mark.parametrize("name", CLASS_NAMES)
    def test_category_name_encodes_class_and_signal_hypothesis(
        self, channel, name
    ):
        assert channel.has_category(f"et_clf_{name}_xyh_y2tau_h2b_mx300_my60")

    def test_all_categories_carry_the_clf_tag(self, channel):
        assert all(c.has_tag("clf") for c in channel.categories)

    @pytest.mark.parametrize(("index", "name"), list(enumerate(CLASS_NAMES)))
    def test_aux_holds_class_name_and_index(self, channel, index, name):
        category_inst = _category(channel, name)
        assert category_inst.x.output_class == name
        assert category_inst.x.output_class_index == index

    def test_aux_holds_signal_hypothesis(self, channel):
        category_inst = _category(channel, "xyh", "y2tau", "h2b", 300, 60)
        assert category_inst.x.y_decay_mode == "y2tau"
        assert category_inst.x.h_decay_mode == "h2b"
        assert category_inst.x.m_x == 300
        assert category_inst.x.m_y == 60

    def test_label_contains_channel_label(self, channel):
        category_inst = _category(channel, "jetfakes")
        assert category_inst.label.startswith("e#tau channel, ")
        assert category_inst.label_short.startswith("e#tau, ")

    def test_no_signal_parameters_creates_no_categories(
        self, monkeypatch, profile
    ):
        monkeypatch.setattr(
            profile, "iterate_signal_parameters", lambda campaign=None: iter(())
        )
        channel_inst = Channel(name="et", id=1, label="e#tau")
        add_clf_categories(channel_inst)
        assert len(channel_inst.categories) == 0


class TestSkipSignalProcess:
    @pytest.fixture
    def category_inst(self, channel):
        return _category(channel, "xyh")

    def skip(self, category_inst, process_inst):
        return category_inst.x.skip_process_inst(process_inst)

    def test_matching_signal_is_kept(self, category_inst):
        assert self.skip(category_inst, _signal(10)) is False

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"m_x": 400},
            {"m_y": 70},
            {"y": "y2tau", "h": "h2b"},
            {"y": "y2tau"},
            {"h": "h2b"},
        ],
        ids=["m_x", "m_y", "decay_modes", "y_decay_mode", "h_decay_mode"],
    )
    def test_signal_of_other_hypothesis_is_skipped(self, category_inst, kwargs):
        assert self.skip(category_inst, _signal(11, **kwargs)) is True

    def test_background_is_kept(self, category_inst):
        background = _process("tt", 20, tags={"background"})
        assert self.skip(category_inst, background) is False

    def test_process_with_legacy_is_signal_aux_only_is_not_skipped(
        self, category_inst
    ):
        # Only the `signal` tag counts; the old `is_signal` aux is ignored
        legacy = _process("legacy", 21, is_signal=True, m_x=999)
        assert self.skip(category_inst, legacy) is False

    def test_skip_depends_on_category_hypothesis(self, channel):
        other = _category(channel, "xyh", "y2tau", "h2b")
        signal = _signal(12)  # y2b / h2tau, 300 / 60
        assert self.skip(other, signal) is True
