"""Unit tests for `plot` in xyh.core.plotting.util."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402
import ROOT  # noqa: E402

from xyh.core.plotting.util import plot  # noqa: E402


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.fixture(autouse=True)
def restore_th1_directory_status():
    previous = ROOT.TH1.AddDirectoryStatus()
    ROOT.TH1.AddDirectory(False)
    yield
    ROOT.TH1.AddDirectory(previous)


def _hist(name, values):
    hist = ROOT.TH1D(name, name, len(values), 0.0, float(len(values)))
    hist.Sumw2()
    for i, value in enumerate(values, start=1):
        hist.SetBinContent(i, value)
        hist.SetBinError(i, value**0.5)
    return hist


def _plot(**kwargs):
    """Call `plot` the way `control_plots` does (fixed ratio y limits)."""
    return plot(y_limits_bottom=(0.7, 1.3), **kwargs)


@pytest.fixture
def backgrounds():
    return [
        (_hist("bkg_a", [50.0, 60.0, 70.0]), {"label": "a", "color": "C0"}),
        (_hist("bkg_b", [20.0, 30.0, 40.0]), {"label": "b", "color": "C1"}),
    ]


@pytest.fixture
def data():
    return (_hist("data", [72.0, 85.0, 105.0]), {"label": "data"})


@pytest.mark.parametrize("fit_ratio", [False, True], ids=["nofit", "fit"])
def test_plot_without_data_does_not_raise(backgrounds, fit_ratio):
    # Regression: blinded categories used to raise UnboundLocalError for
    # `hist_data_ratio` when the ratio was fitted
    fig, axes = _plot(
        hist_data=None, hist_backgrounds=backgrounds, fit_ratio=fit_ratio
    )
    assert fig is not None
    assert axes.shape == (2,)


def test_plot_without_data_draws_no_data_points_in_ratio_panel(backgrounds):
    _, (_, ax_bottom) = _plot(
        hist_data=None, hist_backgrounds=backgrounds, fit_ratio=True
    )
    # Only the reference line at 1 is drawn; no fit result is added
    assert len(ax_bottom.lines) == 1
    assert list(ax_bottom.lines[0].get_ydata()) == [1, 1]


def test_plot_with_data_fit_adds_lines_to_ratio_panel(backgrounds, data):
    _, (_, ax_fit) = _plot(
        hist_data=data, hist_backgrounds=backgrounds, fit_ratio=True
    )
    plt.close("all")
    _, (_, ax_nofit) = _plot(
        hist_data=data, hist_backgrounds=backgrounds, fit_ratio=False
    )
    assert len(ax_fit.lines) > len(ax_nofit.lines)
