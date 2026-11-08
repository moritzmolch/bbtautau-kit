import logging
from math import sqrt
from pathlib import Path

import numpy as np
import ROOT
from correctionlib import schemav2

from xyh.core.config import Inventory
from xyh.core.config.util import gen_process_insts
from xyh.core.histograms.util import (
    add_histograms,
    get_histograms_for_process_set,
    load_all,
)
from xyh.core.z_pt_reweighting import _nested_binning

logger = logging.getLogger(__name__)


def _compute_nominal_and_shifts(
    h_data: ROOT.TH1,
    h_proc: ROOT.TH1,
    h_other: ROOT.TH1,
    unc_rel_norm_other: float,
) -> tuple[float, dict[str, float]]:
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

    # Correction factor
    norm = n_data_subtracted / n_proc

    # Uncertainties: statistical uncertainty in data, statistical uncertainty in
    # Z simulation, and normalization uncertainty of non-Z processes
    shifts = {}

    # Statistical uncertainty in data and Z simulation
    sigma_stat = norm * sqrt(
        np.sum(h_data_subtracted.GetSumw2()) / n_data_subtracted**2
        + np.sum(h_proc.GetSumw2()) / n_proc**2
    )
    for s in [("up", 1), ("down", -1)]:
        shifts[f"stat_{s[0]}"] = norm + s[1] * sigma_stat

    # Normalization/model uncertainty in non-process processes
    sigma_norm_other = unc_rel_norm_other * n_other / n_proc
    for s in [("up", 1), ("down", -1)]:
        shifts[f"norm_other_{s[0]}"] = norm - s[1] * sigma_norm_other

    return norm, shifts


def _calculate_normalization_weight(
    histograms_dir: Path,
    inventory: Inventory,
    campaign: str,
    channel: str,
    category: str,
    variable: str,
    process_tag: str,
    unc_rel_norm_other: float,
):
    # Get process instances
    process_insts_lookup = {p.name: p for p in gen_process_insts(inventory)}

    # Load histograms for the process
    histograms = load_all(histograms_dir)
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

    # Compute the normalization factor and its uncertainty
    norm, shifts = _compute_nominal_and_shifts(
        h_data,
        h_proc,
        h_other,
        unc_rel_norm_other,
    )

    # Print results
    logger.info(f"{campaign.name}, {category}")
    logger.info(f"        normalization factor {norm:.4f}")
    logger.info(f"        stat +- {shifts['stat_up'] - norm:.4f}")
    logger.info(
        f"        other process norm +- {shifts['norm_other_up'] - norm:.4f}"
    )

    return norm, shifts


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


def derive_norm_weights(
    inventory: Inventory,
    categories: list[str],
    yield_variable: str,
    process_tag: str,
    unc_rel_norm_other: float,
    histograms_dir: Path,
    output_file: Path,
):

    results = {}
    for category in categories:
        # Get the category instance
        category_inst = inventory.channel.get_category(category)

        # Raise exception if the category is not a jet multiplicity without
        # b-jet selection
        if not category_inst.has_tag("jet_bjet_cat"):
            raise ValueError(
                "Normalization weights derivation is only implemented for "
                + "jet multiplicities with b-jet selection, but got "
                + f" {category}"
            )

        # Get the number of jets and b-jets in this category
        n_jets = category_inst.x.n_jets
        n_bjets = category_inst.x.n_bjets

        # Calculate normalization and store it with the number of jets in this
        # bin as key
        norm, shifts = _calculate_normalization_weight(
            histograms_dir,
            inventory,
            inventory.campaign,
            inventory.channel,
            category,
            yield_variable,
            process_tag,
            unc_rel_norm_other,
        )
        results[(n_jets, n_bjets)] = (norm, shifts)

    # Build the correction set and dump it to an output file
    cset = build_correction_set(
        results,
        process_tag,
        description=(
            f"{process_tag} normalization weights of "
            + f"{inventory.campaign.name}, derived in the "
            + f"{inventory.channel.name} channel"
        ),
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(cset.model_dump_json(exclude_unset=True, indent=1))
    logger.info(f"Wrote {output_file}")
