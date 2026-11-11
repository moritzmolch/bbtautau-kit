import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import ROOT
from correctionlib import schemav2

from xyh.core.config import Inventory
from xyh.core.config.util import gen_process_insts
from xyh.core.histograms.util import (
    TH1Wrapper,
    add_histograms,
    get_histograms_for_process_set,
    load_all,
)
from xyh.core.z_pt_reweighting import _jet_binning

logger = logging.getLogger(__name__)

_BDR_CHUNK_SIZE = 500


def _kernel_matrix(
    x: np.ndarray,
    x_p: np.ndarray,
    bw: float,
) -> np.ndarray:
    """
    Gaussian kernel weights between the interpolation points `x_p` (dimension
    0) and the data points `x` (dimension 1) for the bandwidth `bw`, scaled
    as in R's ksmooth. Weights at distances >= 4 scaled bandwidths are 0.
    """
    # Adapt bandwidth and define cutoff
    bw = bw * 0.3706506
    cutoff = 4 * bw

    # Calculate distance of data and interpolation points, normalized to
    # bandwidth
    d = np.abs(x[None, :] - x_p[:, None])

    # Calculate the kernel weight and set those outside the considered
    # window to 0
    k = np.exp(-0.5 * np.pow(d / bw, 2))
    k[d >= cutoff] = 0.0
    return k


def _bdr_ksmooth(
    x: np.ndarray,
    y: np.ndarray,
    x_p: np.ndarray,
    bw: float = 1.0,
) -> np.ndarray:
    """
    Smooth data with specified kernel.
    Based on R function ksmooth: Translated to C++ by C. Stratowa
    (R source file: ksmooth.c by B.D.Ripley Copyright (C) 1998)

    Taken from: https://root.cern/doc/v622/TGraphSmooth_8cxx_source.html#l00157
    """

    # Define chunks
    chunk_edges = np.concatenate(
        (np.arange(0, len(x_p), _BDR_CHUNK_SIZE), [len(x_p)]),
        axis=0,
    )

    # Results of individual chunks
    y_p = []

    for i_c in range(len(chunk_edges) - 1):
        # Get start and stop index of the chunk
        start, stop = chunk_edges[i_c], chunk_edges[i_c + 1]

        # Kernel weights with dimension 0 corresponding to x_p_chunk indices
        # and dimension 1 to x indices
        k = _kernel_matrix(x, x_p[start:stop], bw)

        # Matrix multiplication with dimensions (len(x_p_chunk), len(x)) @
        # (len(x), ) leading to an output shape of (len(x_p_chunk), )
        num = k @ y[:]
        den = np.sum(k, axis=1)

        # Calculate interpolated y value
        y_p_chunk = np.where(den > 0, num / den, np.nan)

        # Append to global output list
        y_p.append(y_p_chunk)

    return np.concatenate(y_p, axis=0)


def scan_bandwidth(
    x: np.ndarray,
    y: np.ndarray,
    yerr: np.ndarray,
    bws: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    chi2 and effective degrees of freedom of the kernel smoother of the
    binned ratio for each bandwidth in `bws`.

    The smoother matrix is `S_ij = K_ij / sum_k K_ik` on the bin centers `x`,
    so that the smoothed values are `S @ y`. Bins with `yerr <= 0` (invalid
    bins) enter the smoothing but not the chi2 and the degrees of freedom:
    `chi2 = sum_i (y_i - (S y)_i)^2 / yerr_i^2` and
    `ndf = n_used - tr(S)` over the used bins. For a bandwidth with `ndf <=
    0` (the smoother interpolates the data) the chi2/ndf is undefined; ndf is
    returned as is and `chi2 / ndf` must be treated as +inf by the caller.

    Returns
    -------
    tuple of np.ndarray
        chi2 and ndf, each with the shape of `bws`.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    yerr = np.asarray(yerr, dtype=float)
    used = yerr > 0
    if not used.any():
        raise ValueError("No bins with a positive uncertainty for the scan")

    chi2 = np.empty(len(bws))
    ndf = np.empty(len(bws))
    for i, bw in enumerate(bws):
        # Smoother matrix, the data points themselves are within the window
        # so that the row sums are positive
        k = _kernel_matrix(x, x, float(bw))
        s = k / k.sum(axis=1, keepdims=True)

        # chi2 and effective degrees of freedom of the used bins
        residual = y - s @ y
        chi2[i] = np.sum((residual[used] / yerr[used]) ** 2)
        ndf[i] = used.sum() - np.trace(s[np.ix_(used, used)])

    return chi2, ndf


def _scan_result(
    bws: np.ndarray,
    chi2: np.ndarray,
    ndf: np.ndarray,
    chosen: float,
    chi2_ndf_max: float,
) -> dict:
    """
    Scan dictionary with `bw`, `chi2`, `ndf` and `chi2_ndf` (`None` where
    undefined, i.e. ndf <= 0) as lists, the `chosen` bandwidth and
    `chi2_ndf_max`.
    """
    chi2_ndf = np.full(len(bws), np.inf)
    np.divide(chi2, ndf, out=chi2_ndf, where=ndf > 0)
    return {
        "bw": np.asarray(bws, dtype=float).tolist(),
        "chi2": chi2.tolist(),
        "ndf": ndf.tolist(),
        "chi2_ndf": [float(v) if np.isfinite(v) else None for v in chi2_ndf],
        "chosen": chosen,
        "chi2_ndf_max": chi2_ndf_max,
    }


def _choose_bandwidth(
    x: np.ndarray,
    y: np.ndarray,
    yerr: np.ndarray,
    bws: np.ndarray,
    chi2_ndf_max: float,
) -> tuple[float, dict]:
    """
    The largest bandwidth of `bws` (ascending) with chi2/ndf <=
    `chi2_ndf_max`, see `scan_bandwidth`. Bandwidths with ndf <= 0 never
    satisfy the criterion. If none does, the smallest bandwidth is used; if
    the largest does, it is used. Both cases log a warning.

    Returns
    -------
    tuple
        The chosen bandwidth and a dictionary with the scan (`bw`, `chi2`,
        `ndf`, `chi2_ndf` as lists, with `None` for undefined chi2/ndf), the
        `chosen` bandwidth and `chi2_ndf_max`.
    """
    bws = np.asarray(bws, dtype=float)
    chi2, ndf = scan_bandwidth(x, y, yerr, bws)

    # chi2/ndf, +inf where undefined
    chi2_ndf = np.full(len(bws), np.inf)
    np.divide(chi2, ndf, out=chi2_ndf, where=ndf > 0)

    # Largest bandwidth satisfying the criterion
    ok = np.flatnonzero(chi2_ndf <= chi2_ndf_max)
    if len(ok) == 0:
        chosen = float(bws[0])
        logger.warning(
            f"No bandwidth in [{bws[0]}, {bws[-1]}] has chi2/ndf <= "
            f"{chi2_ndf_max}, using the smallest ({chosen})"
        )
    else:
        chosen = float(bws[ok[-1]])
        if ok[-1] == len(bws) - 1:
            logger.warning(
                f"The largest scanned bandwidth {chosen} satisfies chi2/ndf "
                f"<= {chi2_ndf_max}, the scan boundary was hit"
            )

    scan = _scan_result(bws, chi2, ndf, chosen, chi2_ndf_max)
    return chosen, scan


@dataclass(frozen=True, kw_only=True)
class SmoothingSettings:
    """
    Settings of the kernel regression smoothing of the binned ratio, see
    `_smooth`.

    Attributes
    ----------
    bw : float or str
        Kernel bandwidth in GeV, or "auto" to choose the largest bandwidth of
        a scan with chi2/ndf <= `chi2_ndf_max` of the binned ratio, see
        `_choose_bandwidth`.
    n_samples : int
        Number of samples within the statistical uncertainties.
    var_min, var_max : float
        Range of the grid on which the smoothed result is evaluated.
    var_steps : int
        Number of points of the grid.
    bw_down_factor, bw_up_factor : float
        Factors applied to `bw` for the bandwidth variations.
    bw_scan_min, bw_scan_max : float
        Range of the geometric bandwidth grid of the scan for `bw="auto"`.
    bw_scan_steps : int
        Number of points of the scan grid.
    chi2_ndf_max : float
        Largest accepted chi2/ndf of the scan.
    """

    bw: float | str
    n_samples: int
    var_min: float
    var_max: float
    var_steps: int
    bw_down_factor: float
    bw_up_factor: float
    bw_scan_min: float
    bw_scan_max: float
    bw_scan_steps: int
    chi2_ndf_max: float

    def __post_init__(self):
        if isinstance(self.bw, str) and self.bw != "auto":
            raise ValueError(
                f"Invalid smoothing bandwidth {self.bw!r}, expected a number "
                'or "auto"'
            )


def _binned_ratio(
    h_data_subtracted: ROOT.TH1,
    h_proc: ROOT.TH1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Binned ratio of the background-subtracted data and the process, with the
    process scaled to the integral of the subtracted data.

    Bins without process content (or a non-finite ratio) cannot be corrected:
    they get the ratio 1 with the uncertainty 0 and a warning is logged.

    Returns
    -------
    tuple of np.ndarray
        The bin edges (length nbins + 1), the ratio and its uncertainty per
        bin.
    """
    # Scale the process to the integral of the subtracted data and divide
    weights = h_data_subtracted.Clone()
    h_proc_norm = h_proc.Clone()
    h_proc_norm.Scale(h_data_subtracted.Integral() / h_proc.Integral())
    weights.Divide(h_proc_norm)

    # Convert to arrays
    n_bins = weights.GetNbinsX()
    axis = weights.GetXaxis()
    edges = np.array([axis.GetBinLowEdge(i) for i in range(1, n_bins + 2)])
    y = np.array([weights.GetBinContent(i) for i in range(1, n_bins + 1)])
    yerr = np.array([weights.GetBinError(i) for i in range(1, n_bins + 1)])
    proc = np.array(
        [h_proc_norm.GetBinContent(i) for i in range(1, n_bins + 1)]
    )

    # Neutral weight for bins which cannot be corrected
    invalid = ~(proc > 0) | ~np.isfinite(y) | ~np.isfinite(yerr)
    for i in np.flatnonzero(invalid):
        logger.warning(
            f"Bin {i + 1} [{edges[i]}, {edges[i + 1]}] has no valid ratio "
            "(no process content), using ratio 1 with uncertainty 0"
        )
    y = np.where(invalid, 1.0, y)
    yerr = np.where(invalid, 0.0, yerr)

    return edges, y, yerr


def _smooth(
    h_data_subtracted: ROOT.TH1,
    h_proc: ROOT.TH1,
    settings: SmoothingSettings,
    bw: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Kernel regression of the binned ratio, see `_binned_ratio`, resampled
    within its statistical uncertainties. `bw` replaces `settings.bw`.
    """
    # Get random generator
    rand_gen = np.random.default_rng()

    # Get the binned nominal weights and statistical uncertainties
    edges, y, yerr = _binned_ratio(h_data_subtracted, h_proc)
    x = 0.5 * (edges[:-1] + edges[1:])
    bw = settings.bw if bw is None else bw

    # Construct array of interpolation points
    x_p = np.linspace(
        settings.var_min,
        settings.var_max,
        num=settings.var_steps,
        endpoint=True,
    )

    # Perform kernel regression n_samples times, varied within stat.
    # uncertainties
    y_p_samples = []
    for _ in range(settings.n_samples):
        # Resample y within statistical uncertainties
        ysmp = y + yerr * rand_gen.normal(size=y.shape[0])

        # Get the smoothed y values for this sample
        y_p_samples.append(_bdr_ksmooth(x, ysmp, x_p, bw)[None, :])

    # Concatenate results from different samples. The output array has shape
    # (n_samples, len(x_p))
    y_p_samples = np.concatenate(y_p_samples, axis=0)

    # Interpolation points without data within the kernel window (outside of
    # the histogram range) are NaN. Extrapolate them with the value of the
    # nearest valid point, which also keeps the correctionlib output finite.
    valid = ~np.isnan(y_p_samples).any(axis=0)
    if not valid.any():
        raise ValueError("Kernel smoothing returned no valid points")
    nearest = np.maximum.accumulate(np.where(valid, np.arange(len(x_p)), -1))
    nearest = np.where(
        nearest < 0, np.argmax(valid), nearest
    )  # leading invalid points
    y_p_samples = y_p_samples[:, nearest]

    # Get nominal result as mean and uncertainty as standard deviation of
    # samples
    y_p_nom = np.mean(y_p_samples, axis=0)
    y_p_stat = np.std(y_p_samples, axis=0)

    return x_p, y_p_nom, y_p_stat


def _compute_pt_weights_and_shifts(
    h_data: ROOT.TH1,
    h_proc: ROOT.TH1,
    h_other: ROOT.TH1,
    settings: SmoothingSettings,
    unc_rel_norm_other: float,
) -> tuple[
    tuple[np.ndarray, np.ndarray],
    dict[str, tuple[np.ndarray, np.ndarray]],
    tuple[np.ndarray, np.ndarray, np.ndarray],
    dict,
]:
    """
    Returns the smoothed nominal `(x, y)`, the smoothed shifts, the binned
    nominal result `(edges, y, yerr)` and the bandwidth scan, see
    `_choose_bandwidth`. For `settings.bw == "auto"` the scan on the binned
    nominal result chooses the bandwidth, which is also the base of the
    bandwidth variations; for a fixed bandwidth the scan has a single point.
    """
    # Subtract non-process processes from data
    h_data_subtracted = h_data.Clone()
    h_data_subtracted.Add(h_other, -1.0)

    # Get number of subtracted data and simulated non-process events
    n_data = h_data.Integral()
    n_data_subtracted = h_data_subtracted.Integral()
    n_proc = h_proc.Integral()
    n_other = h_other.Integral()
    logger.info(
        f"Got {n_data} data events, {n_proc} process events, and {n_other} "
        + "other events"
    )

    # Check that h_data_subtracted is not negative
    if n_data_subtracted <= 0:
        raise ValueError("Subtracted data histogram is negative")

    # Check that h_proc is not negative
    if h_proc.Integral() <= 0:
        raise ValueError("Process histogram is negative")

    # Get the binned nominal result
    binned = _binned_ratio(h_data_subtracted, h_proc)

    # Choose the bandwidth on the binned nominal ratio, or evaluate the fixed
    # one, and continue with concrete settings
    edges, y_binned, yerr_binned = binned
    x_binned = 0.5 * (edges[:-1] + edges[1:])
    if settings.bw == "auto":
        bw, bw_scan = _choose_bandwidth(
            x_binned,
            y_binned,
            yerr_binned,
            np.geomspace(
                settings.bw_scan_min,
                settings.bw_scan_max,
                settings.bw_scan_steps,
            ),
            settings.chi2_ndf_max,
        )
        settings = replace(settings, bw=bw)
    else:
        bw = float(settings.bw)
        bws = np.array([bw])
        chi2, ndf = scan_bandwidth(x_binned, y_binned, yerr_binned, bws)
        bw_scan = _scan_result(bws, chi2, ndf, bw, settings.chi2_ndf_max)
    logger.info(
        f"Bandwidth {bw} with chi2/ndf = {bw_scan['chi2_ndf'][-1]}"
        if settings.bw != "auto"
        else f"Chosen bandwidth {bw} with chi2/ndf = "
        f"{bw_scan['chi2_ndf'][bw_scan['bw'].index(bw)]}"
    )

    # Get nominal result and statistical uncertainties
    x_smooth, nominal_smooth, unc_stat_smooth = _smooth(
        h_data_subtracted, h_proc, settings
    )

    # Get shifted arrays
    shifts = {}

    # Add statistical uncertainty
    for shift, factor in [("up", 1), ("down", -1)]:
        shifts[f"stat_{shift}"] = (
            x_smooth,
            nominal_smooth + factor * unc_stat_smooth,
        )

    # Get result for shifted bandwidth
    for shift, factor in [
        ("up", settings.bw_up_factor),
        ("down", settings.bw_down_factor),
    ]:
        x_smooth, shifted_smooth, _ = _smooth(
            h_data_subtracted, h_proc, settings, bw=factor * settings.bw
        )
        shifts[f"bw_{shift}"] = (x_smooth, shifted_smooth)

    # Get result for shifted "other" subtraction
    for shift, factor in [("up", 1), ("down", -1)]:
        h_other_shifted = h_other.Clone()
        h_other_shifted.Scale(1 + factor * unc_rel_norm_other)
        h_data_subtracted_shifted = h_data.Clone()
        h_data_subtracted_shifted.Add(h_other_shifted, -1)
        x_smooth, shifted_smooth, _ = _smooth(
            h_data_subtracted_shifted, h_proc, settings
        )
        shifts[f"norm_other_{shift}"] = (x_smooth, shifted_smooth)

    return (x_smooth, nominal_smooth), shifts, binned, bw_scan


def _calculate_pt_weights(
    histograms: list[TH1Wrapper],
    inventory: Inventory,
    campaign: str,
    channel: str,
    category: str,
    variable: str,
    process_tag: str,
    settings: SmoothingSettings,
    unc_rel_norm_other: float,
):
    # Get process instances
    process_insts_lookup = {p.name: p for p in gen_process_insts(inventory)}

    # Select the histograms for the process
    histograms_dict = get_histograms_for_process_set(
        histograms,
        inventory.process_set,
        campaign,
        channel,
        category,
        variable,
        "nominal",
    )

    # Get data, process, and other background histograms
    h_data = add_histograms(
        [
            h.histogram
            for g in histograms_dict["data"].values()
            for h_list in g.values()
            for h in h_list
        ]
    )
    h_proc = add_histograms(
        [
            h.histogram
            for g in histograms_dict["backgrounds"].values()
            for p, h_list in g.items()
            for h in h_list
            if process_insts_lookup[p].has_tag(process_tag)
        ]
    )
    h_other = add_histograms(
        [
            h.histogram
            for g in histograms_dict["backgrounds"].values()
            for p, h_list in g.items()
            for h in h_list
            if not process_insts_lookup[p].has_tag(process_tag)
        ]
    )

    return _compute_pt_weights_and_shifts(
        h_data, h_proc, h_other, settings, unc_rel_norm_other
    )


def _pt_binning(x: np.ndarray, y: np.ndarray) -> schemav2.Binning:
    """
    Binning in `pt` with one bin per interpolation point `x`: the bin edges
    are the midpoints between neighbouring points, extrapolated by half a step
    at both ends. Out-of-range values are clamped.
    """
    x = np.asarray(x, dtype=float)
    mid = 0.5 * (x[1:] + x[:-1])
    edges = np.concatenate(
        ([x[0] - (mid[0] - x[0])], mid, [x[-1] + (x[-1] - mid[-1])])
    )
    return schemav2.Binning(
        nodetype="binning",
        input="pt",
        edges=[float(e) for e in edges],
        content=[float(v) for v in y],
        flow="clamp",
    )


def _binned_binning(edges: np.ndarray, y: np.ndarray) -> schemav2.Binning:
    """Binning in `pt` with the given edges, out-of-range values clamped."""
    return schemav2.Binning(
        nodetype="binning",
        input="pt",
        edges=[float(e) for e in edges],
        content=[float(v) for v in y],
        flow="clamp",
    )


def _correction(
    name: str,
    description: str,
    variation_nodes: Mapping[str, schemav2.Binning],
) -> schemav2.Correction:
    """
    Correction with the inputs `n_jets`, `pt` and `variation`, selecting the
    node of the variation. Missing variations raise instead of returning a
    weight.
    """
    return schemav2.Correction(
        name=name,
        description=description,
        version=1,
        inputs=[
            schemav2.Variable(
                name="n_jets", type="int", description="Number of jets"
            ),
            schemav2.Variable(
                name="pt", type="real", description="Transverse momentum"
            ),
            schemav2.Variable(
                name="variation",
                type="string",
                description="Nominal or one of the shifts",
            ),
        ],
        output=schemav2.Variable(name="weight", type="real"),
        data=schemav2.Category(
            nodetype="category",
            input="variation",
            content=[
                schemav2.CategoryItem(key=variation, value=node)
                for variation, node in variation_nodes.items()
            ],
        ),
    )


def build_correction_set(
    results: dict[
        int,
        tuple[
            tuple[np.ndarray, np.ndarray],
            dict[str, tuple[np.ndarray, np.ndarray]],
        ],
    ],
    process_tag: str,
    description: str = "",
    binned_results: (
        dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] | None
    ) = None,
) -> schemav2.CorrectionSet:
    """
    Build the correctionlib set with the correction `<process_tag>_pt`, which
    gives the pt weight as function of the number of jets, the pt and a
    variation, evaluated as `correction.evaluate(n_jets, pt, "stat_up")`. The
    results are keyed by the jet multiplicity lower edge and map to
    `((x, nominal), shifts)` as returned by `_compute_pt_weights_and_shifts`,
    where `shifts` maps the variation names to `(x, y)` arrays. Evaluating an
    unknown variation raises.

    If `binned_results` (jet multiplicity to `(edges, y, yerr)`) is given, the
    correction `<process_tag>_pt_binned` with the same structure is added. It
    contains the unsmoothed binned ratio with the variations `nominal`,
    `stat_up` (y + yerr) and `stat_down` (y - yerr).
    """

    # Variation names from the first result, "nominal" plus all shifts
    n_jets_values = sorted(results)
    shift_names = list(results[n_jets_values[0]][1])
    for n_jets in n_jets_values:
        if set(results[n_jets][1]) != set(shift_names):
            raise ValueError(
                f"Inconsistent variations for n_jets={n_jets}: "
                f"{sorted(results[n_jets][1])} vs {sorted(shift_names)}"
            )

    def _get(n_jets: int, variation: str) -> tuple[np.ndarray, np.ndarray]:
        nominal, shifts = results[n_jets]
        return nominal if variation == "nominal" else shifts[variation]

    # Binning in n_jets (leaves: binning in pt) for each variation
    variation_nodes = {
        variation: _jet_binning(
            {
                n_jets: _pt_binning(*_get(n_jets, variation))
                for n_jets in n_jets_values
            }
        )
        for variation in ["nominal", *shift_names]
    }

    corrections = [
        _correction(
            f"{process_tag}_pt",
            (
                f"pt weight of the {process_tag} process as function of "
                "the jet multiplicity and pt, nominal and its "
                f"{', '.join(shift_names)} variations"
            ),
            variation_nodes,
        )
    ]

    if binned_results is not None:
        # The binned results must cover the same jet multiplicities
        if sorted(binned_results) != n_jets_values:
            raise ValueError(
                f"Binned results for n_jets={sorted(binned_results)} do not "
                f"match the smoothed results for n_jets={n_jets_values}"
            )

        # Nominal and statistical shifts of the binned ratio
        binned_shifts = {
            "nominal": 0.0,
            "stat_up": 1.0,
            "stat_down": -1.0,
        }
        binned_nodes = {}
        for variation, factor in binned_shifts.items():
            leaves = {}
            for n_jets in n_jets_values:
                edges, y, yerr = binned_results[n_jets]
                content = np.asarray(y) + factor * np.asarray(yerr)
                if not np.isfinite(content).all():
                    raise ValueError(
                        f"Non-finite binned {process_tag} pt weight for "
                        f"n_jets={n_jets}, variation={variation}"
                    )
                leaves[n_jets] = _binned_binning(edges, content)
            binned_nodes[variation] = _jet_binning(leaves)
        corrections.append(
            _correction(
                f"{process_tag}_pt_binned",
                (
                    f"Unsmoothed binned pt weight of the {process_tag} "
                    "process as function of the jet multiplicity and pt, "
                    f"nominal and its {', '.join(list(binned_shifts)[1:])} "
                    "variations"
                ),
                binned_nodes,
            )
        )

    return schemav2.CorrectionSet(
        schema_version=2,
        description=description,
        corrections=corrections,
    )


def derive_z_pt_weights(
    inventory: Inventory,
    categories: list[str],
    pt_variable: str,
    process_tag: str,
    settings: Mapping[str, SmoothingSettings],
    unc_rel_norm_other: float,
    histograms_dir: Path,
    output_file: Path,
    bw_scan_file: Path | None = None,
):
    """
    Derive the pt weights of the process with the tag `process_tag` in the
    given jet multiplicity categories (tag `jet_cat`) and write them to a
    correctionlib file, see `build_correction_set`. `settings` holds the
    smoothing settings of each category. If `bw_scan_file` is given, the
    bandwidth scans of all categories (keyed by category) are written to it as
    JSON.
    """

    # Check that the settings cover all categories
    missing = [c for c in categories if c not in settings]
    if missing:
        raise KeyError(f"No smoothing settings for categories {missing}")

    # Load the nominal histograms of the yield variable only, once for all
    # categories
    histograms = load_all(
        histograms_dir,
        campaigns=[inventory.campaign.name],
        channels=[inventory.channel.name],
        variables=[pt_variable],
        variations=["nominal"],
    )

    results = {}
    binned_results = {}
    bw_scans = {}
    for category in categories:
        # Get the category instance
        category_inst = inventory.channel.get_category(category)

        # Raise exception if the category is not a jet multiplicity without
        # b-jet selection
        if not category_inst.has_tag("jet_cat"):
            raise ValueError(
                f"{process_tag} pt weights derivation is only implemented for "
                + "jet multiplicities without b-jet selection, but got "
                + f" {category}"
            )

        # Get the number of jets in this category (stored as string)
        n_jets = int(category_inst.x.n_jets)

        # Calculate the pt weights and store them with the number of jets in
        # this bin as key
        logger.info(f"Smoothing settings of {category}: {settings[category]}")
        nominal, shifts, binned, bw_scan = _calculate_pt_weights(
            histograms,
            inventory,
            inventory.campaign.name,
            inventory.channel.name,
            category,
            pt_variable,
            process_tag,
            settings[category],
            unc_rel_norm_other,
        )
        results[n_jets] = (nominal, shifts)
        binned_results[n_jets] = binned
        bw_scans[category] = bw_scan

    # Build the correction set and dump it to an output file
    cset = build_correction_set(
        results,
        process_tag,
        description=(
            f"{process_tag} pt weights of "
            + f"{inventory.campaign.name}, derived in the "
            + f"{inventory.channel.name} channel"
        ),
        binned_results=binned_results,
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(cset.model_dump_json(exclude_unset=True, indent=1))
    logger.info(f"Wrote {output_file}")

    # Dump the bandwidth scans
    if bw_scan_file is not None:
        bw_scan_file.parent.mkdir(parents=True, exist_ok=True)
        bw_scan_file.write_text(json.dumps(bw_scans, indent=1))
        logger.info(f"Wrote {bw_scan_file}")
