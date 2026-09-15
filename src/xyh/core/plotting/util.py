from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import mplhep
import numpy as np
import ROOT

mpl.style.use(mplhep.style.CMS)


def plot_distribution(
    ax: mpl.axes.Axes,
    hist: ROOT.TH1,
    yerr: bool = True,
    **kwargs,
):
    """
    Plot histogram of a single shape.
    """

    # set the yerr of histplot based on whether show_yerr is set to True or False
    yerr_val = False
    if yerr:
        # if yerr is True, use the square root of the sum of squared weights as uncertainties
        yerr_val = np.array(
            [hist.GetBinError(i) for i in range(1, hist.GetNbinsX() + 1)]
        )

    # set defaults for some keyword arguments of the `histplot` method
    _kwargs = {
        "histtype": "step",
    }

    # overwrite default values with user-provided ones
    _kwargs.update(kwargs)

    # plot the band
    mplhep.histplot(
        ax=ax,
        H=hist,
        yerr=yerr_val,
        **_kwargs,
    )


def plot_band(
    ax: mpl.axes.Axes,
    hist: ROOT.TH1,
    **kwargs,
):
    # check that kwargs does not contain `x`, `y1`, `y2`, and `step` as these parameters of `fill_between` are provided by the code in this function
    not_allowed_kwargs = ["x", "y1", "y2", "step"]
    if any(k in kwargs for k in not_allowed_kwargs):
        raise ValueError(f"Keyword arguments {not_allowed_kwargs} not allowed")

    # extract edges and values from the numpy-style histogram
    values = hist.values()
    edges = np.array(
        [
            hist.GetXaxis().GetBinLowEdge(i)
            for i in range(1, hist.GetNbinsX() + 1)
        ]
        + [hist.GetXaxis().GetBinUpEdge(hist.GetNbinsX())]
    )

    # calculate lower and upper value bounds from the sum of squared weights; if `w2` is not provided, use `values` as the squared uncertainties (~ Poissonian uncertainties)
    unc = np.array(
        [hist.GetBinError(i) for i in range(1, hist.GetNbinsX() + 1)]
    )
    values_lower = values - unc
    values_upper = values + unc

    # append dummy value at the end to synchronize array length with edges
    values_lower = np.append(values_lower, values_lower[-1])
    values_upper = np.append(values_upper, values_upper[-1])

    _kwargs = {
        "edgecolor": "gray",
        "facecolor": ("gray", 0.7),
    }

    _kwargs.update(kwargs)

    # plot the band
    ax.fill_between(
        x=edges,
        y1=values_lower,
        y2=values_upper,
        step="post",
        **_kwargs,
    )


def plot_data(
    ax: mpl.axes.Axes,
    hist: ROOT.TH1,
    yerr: bool = True,
    **kwargs,
):
    # check if an equidistant binning has been chosen; if this is not the case, also draw horizontal uncertainty bars
    # width = hist.axes[0].edges[1:] - hist.axes[0].edges[:-1]
    # xerr = not np.all(np.isclose(width, np.repeat(width[0], len(width))))

    # set defaults for some keyword arguments of the `histplot` method
    _kwargs = {
        "marker": "o",
        "markersize": 5,
        "elinewidth": 2,
        "color": "black",
        "linestyle": "none",
    }

    # overwrite default values with user-provided ones
    _kwargs.update(kwargs)

    # plot the data distribution
    plot_distribution(
        ax,
        hist,
        # xerr=xerr,
        yerr=yerr,
        histtype="errorbar",
        **_kwargs,
    )


def plot_stack(
    ax: mpl.axes.Axes,
    hists: list[tuple[ROOT.TH1, dict[str, Any]]],
    **kwargs,
):
    """
    Plot histogram of a single shape.
    """

    # set defaults for some keyword arguments of the `histplot` method
    _kwargs = {
        "histtype": "fill",
    }

    # overwrite default values with user-provided ones
    _kwargs.update(kwargs)

    # plot the band
    mplhep.histplot(
        ax=ax,
        H=[hist for hist, _ in hists],
        yerr=False,
        label=[style.get("label", None) for _, style in hists],
        color=[style.get("color", None) for _, style in hists],
        # fillcolor=[style.get("fillcolor", None) for _, style in hists],
        # edgecolor=[style.get("edgecolor", None) for _, style in hists],
        linestyle=[style.get("linestyle", None) for _, style in hists],
        stack=True,
        **_kwargs,
    )


def plot_fitted_hist_ratio(
    ax: mpl.axes.Axes,
    results: dict[str, Any],
):
    # plot the constant line fit result
    ax.axhline(results["c"], color="red", linestyle="dashed")

    # plot information about the fit result
    common_kwargs = {
        "fontsize": "xx-small",
        "color": "red",
        "verticalalignment": "top",
        "horizontalalignment": "left",
        "transform": ax.transAxes,
    }
    ax.text(
        0.02,
        0.95,
        (
            f"$\\chi^2/n_{{\\text{{df}}}} = {results['chi2']:.2f} / {results['ndf']:d} "
            f"= {results['chi2_reduced']:.2f}$"
        ),
        **common_kwargs,
    )
    ax.text(
        0.02,
        0.80,
        f"$c = {results['c']:.2f} \\pm {results['c_err']:.2f}$",
        **common_kwargs,
    )


def get_hist_backgrounds_total(hist_backgrounds: list[ROOT.TH1]):
    h = hist_backgrounds[0].Clone().Clear()
    for h_add in hist_backgrounds:
        h.Add(h_add)
    return h


def get_hist_ratio(
    hist_num: ROOT.TH1,
    hist_den: ROOT.TH1,
    hist_num_w2method: str = "sqrt",
    ratio_uncertainty_type: str = "uncorrelated",
):
    # Calculate the histogram ratio and its uncertainties
    ratio_values, ratio_unc_low, ratio_unc_high = mplhep.comp.get_ratio(
        hist_num,
        hist_den,
        h1_w2method=hist_num_w2method,
        ratio_uncertainty_type=ratio_uncertainty_type,
    )

    # Fill ROOT histogram with values and uncertainties
    hist_ratio = hist_num.Clone()
    hist_ratio.Divide(hist_den)
    # for i in range(1, hist_ratio.GetNbinsX() + 1):
    #     hist_ratio.SetBinContent(i, ratio_values[i - 1])
    #     hist_ratio.SetBinError(i, ratio_values[i - 1] - ratio_unc_low[i - 1])

    return hist_ratio


def fit_hist_ratio(
    hist_ratio: ROOT.TH1,
):
    # get (x, y) points and the uncertainties in y
    x, y, y_err = (
        [
            hist_ratio.GetXaxis().GetBinCenter(i)
            for i in range(1, hist_ratio.GetNbinsX() + 1)
        ],
        [
            hist_ratio.GetBinContent(i)
            for i in range(1, hist_ratio.GetNbinsX() + 1)
        ],
        [
            hist_ratio.GetBinError(i)
            for i in range(1, hist_ratio.GetNbinsX() + 1)
        ],
    )

    # remove data points with nan values
    valid = ~(np.isnan(y) | np.isnan(y_err))
    x, y, y_err = x[valid], y[valid], y_err[valid]

    # if no data points are left, return dummy fit results
    if len(x) == 0:
        return {
            "c": 1,
            "c_err": 1,
            "chi2": 1000,
            "ndf": 1,
            "chi2_reduced": 1000,
        }

    # import iminuit
    from iminuit import Minuit
    from iminuit.cost import LeastSquares

    # define the cost function and minimize it
    cost_function = LeastSquares(x, y, y_err, lambda x, c: c * np.ones_like(x))
    m = Minuit(cost_function, c=1.0)
    m.migrad()

    # get the fit results
    results = {
        "c": m.values["c"],
        "c_err": m.errors["c"],
        "chi2": m.fval,
        "ndf": int(m.ndof),
        "chi2_reduced": m.fmin.reduced_chi2,
    }

    return results


def set_axes_labels(
    ax: mpl.axes.Axes,
    x_label: str | None = None,
    y_label: str | None = None,
):
    if x_label is not None:
        ax.set_xlabel(x_label)
    if y_label is not None:
        ax.set_ylabel(y_label)


def set_axes_limits_distributions(
    ax: mpl.axes.Axes,
    hists: ROOT.TH1 | None = None,
    custom_y_limits: tuple[float, float] | None = None,
):
    # use histogram boundaries to limit the x axis
    ax.set_xlim(
        hists[0].GetXaxis().GetBinLowEdge(1),
        hists[0].GetXaxis().GetBinUpEdge(hists[0].GetNbinsX()),
    )

    if custom_y_limits is not None:
        # set user-defined limits if the custom_y_limits parameter has been set
        ax.set_ylim(*custom_y_limits)

    else:
        # get the largest y value defined by the graphics objects
        y_maxs = np.array(
            [hist.GetMaximum() + np.sqrt(hist.GetMaximum()) for hist in hists],
        )
        y_max = np.max(y_maxs[~np.isnan(y_maxs)])

        # for non-logarithmic plots, always start at 0
        # add a 60% margin to the maximum y value to leave space for the legend
        if y_max != 0:
            ax.set_ylim(0, y_max * 1.75)
        else:
            ax.set_ylim(0, 1)


def set_axes_limits_ratio(
    ax: mpl.axes.Axes,
    hists: ROOT.TH1 | None = None,
    custom_y_limits: tuple[float, float] | None = None,
):
    # use histogram boundaries to limit the x axis
    ax.set_xlim(
        hists[0].GetXaxis().GetBinLowEdge(1),
        hists[0].GetXaxis().GetBinUpEdge(hists[0].GetNbinsX()),
    )

    if custom_y_limits:
        # set user-defined limits if the custom_y_limits parameter has been set
        ax.set_ylim(*custom_y_limits)

    else:
        # get the smallest and the largest y value defined by the graphics objects
        y_mins = np.concatenate(
            [hist.GetMinimum() - np.sqrt(hist.GetMinimum()) for hist in hists],
            axis=0,
        )
        y_maxs = np.concatenate(
            [hist.GetMaximum() + np.sqrt(hist.GetMaximum()) for hist in hists],
            axis=0,
        )
        y_min = np.min(y_mins[~np.isnan(y_mins)])
        y_max = np.max(y_maxs[~np.isnan(y_maxs)])

        # symmetrize the distance to 1
        distance_to_unity = max(abs(1 - y_min), abs(y_max - 1))

        # set y axis limits
        if distance_to_unity < 0.5:
            ax.set_ylim(
                1 - 1.05 * distance_to_unity, 1 + 1.05 * distance_to_unity
            )
        else:
            ax.set_ylim(1 - 1.05 * 0.5, 1 + 1.05 * 0.5)


def plot(
    hist_data: tuple[ROOT.TH1, dict[str, Any]] | None = None,
    hist_backgrounds: list[tuple[ROOT.TH1, dict[str, Any]]] | None = None,
    hist_signals: list[tuple[ROOT.TH1, dict[str, Any]]] | None = None,
    stack_kwargs: dict[str, Any] | None = None,
    x_label_top: str | None = None,
    y_label_top: str | None = None,
    x_label_bottom: str | None = None,
    y_label_bottom: str | None = None,
    y_limits_top: tuple[float, float] | None = None,
    y_limits_bottom: tuple[float, float] | None = None,
    category_label: str | None = None,
    lumi: float | None = None,
    era: str | None = None,
    sqrt_s: float | None = None,
    fit_ratio: bool = False,
):
    # set parameters which are not provided to default values
    hist_signals = hist_signals or []
    hist_backgrounds = hist_backgrounds or []
    stack_kwargs = stack_kwargs or {}

    # create the matplotlib figure and axis
    fig, (ax_top, ax_bottom) = plt.subplots(
        ncols=1,
        nrows=2,
        sharex=True,
        height_ratios=[0.7, 0.3],
        gridspec_kw={"hspace": 0.0},
    )

    #
    # histograms in top panel
    #

    # get the total background histogram
    h_bkg_iter = iter(h[0] for h in hist_backgrounds)
    hist_backgrounds_total = next(h_bkg_iter, None)
    if hist_backgrounds_total is not None:
        hist_backgrounds_total = hist_backgrounds_total.Clone()
    for h in h_bkg_iter:
        hist_backgrounds_total.Add(h)

    # hist_backgrounds_total = reduce(add, [h[0] for h in hist_backgrounds])

    # plot background processes as histogram stack
    plot_stack(ax_top, hist_backgrounds, **stack_kwargs)

    # band for the total background uncertainties
    plot_band(ax_top, hist_backgrounds_total)

    # signal shape
    for hist_signal in hist_signals:
        # get the signal and background normalization
        plot_kwargs = hist_signal[1]
        c = plot_kwargs.pop("scale_factor", 1.0)
        h = c * hist_signal[0]
        plot_distribution(ax_top, h, yerr=True, linewidth=3, **plot_kwargs)

    # nominal shape without uncertainties
    # plot_distribution(ax_top, hist_backgrounds_total, color="black", show_yerr=False)

    # plot the data
    if hist_data is not None:
        plot_data(ax_top, hist_data[0], **hist_data[1])

    #
    # histograms in bottom panel
    #

    # get the ratio histograms
    hist_backgrounds_total_ratio = get_hist_ratio(
        hist_backgrounds_total, hist_backgrounds_total
    )

    if hist_data is not None:
        # get data/background ratio
        hist_data_ratio = get_hist_ratio(hist_data[0], hist_backgrounds_total)

        # plot the data/total background ratio
        plot_data(ax_bottom, hist_data_ratio, **hist_data[1])

    # plot a reference line at 1
    ax_bottom.axhline(1, color="black", linestyle="dashed")

    # plot the relative uncertainty of the total background
    plot_band(ax_bottom, hist_backgrounds_total_ratio)

    if fit_ratio and hist_data_ratio is not None:
        # do the fit
        results = fit_hist_ratio(hist_data_ratio)

        # plot fitted line and fit results
        plot_fitted_hist_ratio(ax_bottom, results)

    #
    # plot style
    #

    # set labels
    set_axes_labels(ax_top, x_label=x_label_top, y_label=y_label_top)
    set_axes_labels(ax_bottom, x_label=x_label_bottom, y_label=y_label_bottom)

    # restrict axes ranges
    hist_list = [hist_backgrounds_total]
    if hist_data is not None:
        hist_list.append(hist_data[0])
    set_axes_limits_distributions(
        ax_top,
        hist_list,
        custom_y_limits=y_limits_top,
    )
    hist_list_ratio = [hist_backgrounds_total_ratio]
    if hist_data is not None:
        hist_list.append(hist_data_ratio)
    set_axes_limits_ratio(
        ax_bottom,
        hist_list,
        custom_y_limits=y_limits_bottom,
    )

    # add CMS label
    mplhep.cms.label(
        ax=ax_top,
        text="Work in progress",
        com=sqrt_s,
        lumi=lumi,
        year=era,
        data=True,
        fontsize=20,
    )

    # add category label
    if category_label is not None:
        ax_top.text(
            0.02,
            0.95,
            category_label,
            fontsize="small",
            horizontalalignment="left",
            verticalalignment="top",
            transform=ax_top.transAxes,
        )

    # show the legend in the top panel
    ax_top.legend(
        fontsize="xx-small",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.85),
        bbox_transform=ax_top.transAxes,
        ncols=3,
    )

    return fig, np.array([ax_top, ax_bottom])
