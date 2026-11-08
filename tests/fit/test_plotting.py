"""Unit tests for `xyh.fit.plotting`."""

import pytest

from xyh.fit.limits import LimitResult
from xyh.fit.plotting import plot_all_limits, plot_brazil_band, select_for_plot


def _result(mx, my=100, ydm="y2b", hdm="h2tau"):
    return LimitResult(ydm, hdm, mx, my, 0.1, 0.2, 0.3, 0.4, 0.5, 0.35)


def test_select_for_plot_filters_and_sorts_by_mx():
    results = [
        _result(3000),
        _result(1000),
        _result(2000, my=200),
        _result(2000, ydm="y2tau"),
    ]
    selected = select_for_plot(results, "y2b", "h2tau", 100)
    assert [r.mx for r in selected] == [1000, 3000]


def test_select_for_plot_no_match_returns_empty():
    assert select_for_plot([_result(1000)], "y2b", "h2tau", 999) == []


def test_plot_brazil_band_empty_results_raises(tmp_path):
    with pytest.raises(ValueError, match="No results to plot"):
        plot_brazil_band([], tmp_path / "p.pdf")


@pytest.mark.parametrize("show_observed", [False, True])
def test_plot_brazil_band_writes_file(tmp_path, show_observed):
    out = tmp_path / "sub" / "p.png"
    plot_brazil_band(
        [_result(2000), _result(1000)], out, show_observed=show_observed
    )
    assert out.stat().st_size > 0


def test_plot_all_limits_writes_one_file_per_group(tmp_path):
    results = [
        _result(1000),
        _result(2000),
        _result(1000, my=200),
        _result(1000, ydm="y2tau", hdm="h2b"),
    ]
    written = plot_all_limits(results, tmp_path)
    assert sorted(p.name for p in written) == [
        "limits_y2b_h2tau_my100.pdf",
        "limits_y2b_h2tau_my200.pdf",
        "limits_y2tau_h2b_my100.pdf",
    ]
    assert all(p.exists() for p in written)


def test_plot_all_limits_no_results_returns_empty(tmp_path):
    assert plot_all_limits([], tmp_path) == []
