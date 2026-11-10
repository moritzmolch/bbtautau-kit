import logging
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
from xyh.core.z_pt_reweighting import _nested_binning

logger = logging.getLogger(__name__)

_BDR_CHUNK_SIZE = 500


def _bdr_ksmooth(
    x,
    y,
    x_p,
    bw: float = 1.0,
):
    """
    Smooth data with specified kernel.
    Based on R function ksmooth: Translated to C++ by C. Stratowa
    (R source file: ksmooth.c by B.D.Ripley Copyright (C) 1998)

    Taken from: https://root.cern/doc/v622/TGraphSmooth_8cxx_source.html#l00157
    """

    # Adapt bandwidth and define cutoff
    bw *= 0.3706506
    cutoff = 4 * bw

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
        x_p_chunk = x_p[start:stop]

        # Calculate distance of data and interpolation points, normalized to
        # bandwidth. The dimensions of the x and x_p arrays are extended.
        # Dimension 0 corresponds to x_p_chunk indices, dimension 1 corresponds
        # to x indices.
        d = np.abs(x[None, :] - x_p_chunk[:, None])

        # Calculate the kernel weight and set those outside the considered
        # window to 0
        k = np.exp(-0.5 * np.pow(d / bw, 2))
        k[d >= cutoff] = 0.0

        # Matrix multiplication with dimensions (len(x_p_chunk), len(x)) @
        # (len(x), ) leading to an output shape of (len(x_p_chunk), )
        num = k @ y[:]
        den = np.sum(k, axis=1)

        # Calculate interpolated y value
        y_p_chunk = np.where(den > 0, num / den, np.nan)

        # Append to global output list
        y_p.append(y_p_chunk)

    return np.concatenate(y_p, axis=0)


def _smooth(
    h_data_subtracted: ROOT.TH1,
    h_proc: ROOT.TH1,
    n_samples: int,
    var_min: float,
    var_max: float,
    var_steps: int,
    bw: float,
):
    # Get random generator
    rand_gen = np.random.default_rng()

    # Get the binned nominal weights and statistical uncertainties
    weights = h_data_subtracted.Clone()
    weights.Divide(h_proc)
    x = np.array(
        [
            weights.GetXaxis().GetBinCenter(i)
            for i in range(1, weights.GetNbinsX() + 1)
        ]
    )
    y = np.array(
        [weights.GetBinContent(i) for i in range(1, weights.GetNbinsX() + 1)],
    )
    yerr = np.array(
        [weights.GetError(i) for i in range(1, weights.GetNbinsX() + 1)],
    )

    # Construct array of interpolation points
    x_p = np.linspace(var_min, var_max, num=var_steps, endpoint=True)

    # Perform kernel regression n_samples times, varied within stat.
    # uncertainties
    y_p_samples = []
    for _ in range(n_samples):
        # Resample y within statistical uncertainties
        ysmp = y + yerr * rand_gen.normal(size=y.shape[0])

        # Get the smoothed y values for this sample
        y_p_samples.append(_bdr_ksmooth(x, ysmp, x_p, bw)[None, :])

    # Concatenate results from different samples. The output array has shape
    # (n_samples, len(x_p))
    y_p_samples = np.concatenate(y_p_samples, axis=0)

    # Get nominal result as mean and uncertainty as standard deviation of
    # samples
    y_p_nom = np.mean(y_p_samples, axis=0)
    y_p_stat = np.std(y_p_samples, axis=0)

    return x_p, y_p_nom, y_p_stat


def _compute_pt_weights_and_shifts(
    h_data: ROOT.TH1,
    h_proc: ROOT.TH1,
    h_other: ROOT.TH1,
    n_samples: int,
    var_min: float,
    var_max: float,
    var_steps: int,
    bw: float,
    bw_down_factor: float,
    bw_up_factor: float,
    unc_rel_norm_other: float,
) -> tuple[
    tuple[np.ndarray, np.ndarray], dict[str, tuple[np.ndarray, np.ndarray]]
]:
    # Subtract non-process processes from data
    h_data_subtracted = h_data.Clone()
    h_data_subtracted.Add(h_other, -1.0)

    # Get number of subtracted data and simulated non-process events
    n_data = h_data.Integral()
    n_data_subtracted = h_data_subtracted.Integral()
    n_proc = h_proc.Integral()
    n_other = h_other.Integral()
    logger.info(
        f"Got {n_data} data events, {n_proc} process events, and {n_other} other events"
    )

    # Check that h_data_subtracted is not negative
    if n_data_subtracted <= 0:
        raise ValueError("Subtracted data histogram is negative")

    # Check that h_proc is not negative
    if h_proc.Integral() <= 0:
        raise ValueError("Process histogram is negative")

    # Get nominal result and statistical uncertainties
    x_smooth, nominal_smooth, unc_stat_smooth = _smooth(
        h_data_subtracted,
        h_proc,
        n_samples,
        var_min,
        var_max,
        var_steps,
        bw,
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
    for shift, factor in [("up", bw_up_factor), ("down", bw_down_factor)]:
        x_smooth, shifted_smooth, _ = _smooth(
            h_data_subtracted,
            h_proc,
            n_samples,
            var_min,
            var_max,
            var_steps,
            factor * bw,
        )
        shifts[f"bw_{shift}"] = (x_smooth, shifted_smooth)

    # Get result for shifted "other" subtraction
    for shift, factor in [("up", 1), ("down", -1)]:
        h_other_shifted = h_other.Clone()
        h_other_shifted.Scale(1 + factor * unc_rel_norm_other)
        h_data_subtracted_shifted = h_data.Clone()
        h_data_subtracted_shifted.Add(h_other_shifted, -1)
        x_smooth, shifted_smooth, _ = _smooth(
            h_data_subtracted_shifted,
            h_proc,
            var_min,
            var_max,
            var_steps,
            bw,
            n_samples,
        )
        shifts[f"norm_other_{shift}"] = (x_smooth, shifted_smooth)

    return (x_smooth, nominal_smooth), shifts


def _calculate_pt_weights(
    histograms: list[TH1Wrapper],
    inventory: Inventory,
    campaign: str,
    channel: str,
    category: str,
    variable: str,
    process_tag: str,
    n_samples: int,
    var_min: float,
    var_max: float,
    var_steps: int,
    bw: float,
    bw_down_factor: float,
    bw_up_factor: float,
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

    nominal, shifts = _compute_pt_weights_and_shifts(
        h_data,
        h_proc,
        h_other,
        n_samples,
        var_min,
        var_max,
        var_steps,
        bw,
        bw_down_factor,
        bw_up_factor,
        unc_rel_norm_other,
    )

    return nominal, shifts


def build_correction_set(
    results: dict[tuple[int, int], tuple[float, dict[str, float]]],
    process_tag,
    description: str = "",
) -> schemav2.CorrectionSet:
    """
    Build the correctionlib set with the correction `z_normalization`, which
    gives the Z normalization weight as function of the jet and b-jet
    multiplicity lower edges and a variation, evaluated as
    `correction.evaluate(n_jets, n_bjets, "stat_up")`. The results are keyed
    by `(n_jets, n_bjets)` and map to the nominal normalization and its
    variations, see `_compute_nominal_and_shifts`. Evaluating an unknown
    variation raises.
    """

    # Named variations stored in the correctionlib file, see the shifts returned
    # by `_compute_nominal_and_shifts`
    variation_names = (
        "nominal",
        "stat_up",
        "stat_down",
        "norm_other_up",
        "norm_other_down",
    )

    # Create correctionlib structure for each variation
    variation_leaves = {
        variation: {
            (n_jets, n_bjets): (
                norm if variation == "nominal" else shifts[variation]
            )
            for (n_jets, n_bjets), (norm, shifts) in results.items()
        }
        for variation in variation_names
    }

    return schemav2.CorrectionSet(
        schema_version=2,
        description=description,
        corrections=[
            schemav2.Correction(
                name=f"{process_tag}_normalization",
                description=(
                    f"Normalization factor of the {process_tag} process as "
                    "function of the jet and b-jet multiplicity, nominal and "
                    "its stat and norm_other variations"
                ),
                version=1,
                inputs=[
                    schemav2.Variable(
                        name="n_jets",
                        type="int",
                        description="Number of jets",
                    ),
                    schemav2.Variable(
                        name="n_bjets",
                        type="int",
                        description="Number of b-tagged jets",
                    ),
                    schemav2.Variable(
                        name="variation",
                        type="string",
                        description="Nominal or one of the stat and norm_other shifts",
                    ),
                ],
                output=schemav2.Variable(name="weight", type="real"),
                data=schemav2.Category(
                    nodetype="category",
                    input="variation",
                    content=[
                        schemav2.CategoryItem(
                            key=variation,
                            value=_nested_binning(leaves),
                        )
                        for variation, leaves in variation_leaves.items()
                    ],
                    # Missing variations raise instead of returning a weight
                ),
            ),
        ],
    )


def derive_z_pt_weights(
    inventory: Inventory,
    categories: list[str],
    pt_variable: str,
    process_tag: str,
    n_samples: int,
    var_min: float,
    var_max: float,
    var_steps: int,
    bw: float,
    bw_down_factor: float,
    bw_up_factor: float,
    unc_rel_norm_other: float,
    histograms_dir: Path,
    output_file: Path,
):

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

        # Get the number of jets and b-jets in this category
        n_jets = category_inst.x.n_jets

        # Calculate normalization and store it with the number of jets in this
        # bin as key
        nominal, shifts = _calculate_pt_weights(
            histograms,
            inventory,
            inventory.campaign,
            inventory.channel,
            category,
            pt_variable,
            process_tag,
            n_samples,
            var_min,
            var_max,
            var_steps,
            bw,
            bw_down_factor,
            bw_up_factor,
            unc_rel_norm_other,
        )
        results[n_jets] = (nominal, shifts)

    # Build the correction set and dump it to an output file
    cset = build_correction_set(
        results,
        process_tag,
        description=(
            f"{process_tag} pt weights of "
            + f"{inventory.campaign.name}, derived in the "
            + f"{inventory.channel.name} channel"
        ),
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(cset.model_dump_json(exclude_unset=True, indent=1))
    logger.info(f"Wrote {output_file}")
