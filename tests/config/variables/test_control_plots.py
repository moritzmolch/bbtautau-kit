"""Unit tests for the `max_score` variable in the control plot variables."""

import pytest
from order import Category, Channel

from xyh.config.variables._control_plots import (
    _max_score_expression,
    get_control_plot_variables,
)


def _clf_category(m_x=300, m_y=60):
    return Category(name="clf_cat", tags={"clf"}, aux={"m_x": m_x, "m_y": m_y})


class TestMaxScoreExpression:
    @pytest.mark.parametrize(
        ("m_x", "m_y"), [(300, 60), (550, 150)], ids=["low", "high"]
    )
    def test_clf_category_gives_column_of_mass_hypothesis(self, m_x, m_y):
        expression = _max_score_expression(_clf_category(m_x, m_y))
        assert expression == f"max_score_m_x_{m_x}_m_y_{m_y}"

    def test_non_clf_category_raises_naming_variable_and_category(self):
        category_inst = Category(name="plain_cat", tags={"other"})
        with pytest.raises(ValueError, match="'max_score'.*'plain_cat'"):
            _max_score_expression(category_inst)

    def test_category_without_tags_raises(self):
        with pytest.raises(ValueError, match="classifier category"):
            _max_score_expression(Category(name="plain_cat"))


class TestGetControlPlotVariables:
    @pytest.fixture
    def variables(self):
        channel_inst = Channel(name="tt", id=3, label="tt")
        return {v.name: v for v in get_control_plot_variables(channel_inst)}

    def test_max_score_expression_is_the_category_callable(self, variables):
        assert variables["max_score"].expression is _max_score_expression

    def test_max_score_expression_resolves_for_clf_category(self, variables):
        expression = variables["max_score"].expression(_clf_category(400, 70))
        assert expression == "max_score_m_x_400_m_y_70"

    def test_other_variables_keep_string_or_no_expression(self, variables):
        assert variables["yield"].expression == "0.5"
        assert not callable(variables["pt_1"].expression)
