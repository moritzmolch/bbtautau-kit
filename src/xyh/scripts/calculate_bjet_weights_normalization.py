"""
Calculate b-jet normalization weights and write a correctionlib file.

The b-jet normalization scale factor of a simulated process is the ratio of
its yield without b-jet weights to its yield with them, derived per jet
multiplicity category from the merged histograms of two shapes
tags of the same production (with and without b-jet weights). The factors are
stored in a correctionlib file per campaign with the single correction
`bjet_normalization`, evaluated with the parameters `(channel, process,
n_jets)`. See `xyh.core.bjet_normalization` for the construction.
"""

import logging
from pathlib import Path

import ROOT

from xyh import ROOT_DIR
from xyh.core.bjet_normalization import build_correction_set
from xyh.core.config import load_inventory
from xyh.core.config.util import gen_process_insts
from xyh.core.z_pt_reweighting import parse_n_jets

logger = logging.getLogger(__name__)

BASE_OUTPUT_DIR = ROOT_DIR / "data" / "output"

CAMPAIGNS = [
    "2022_pre_ee_nano_v12",
    "2022_post_ee_nano_v12",
    "2023_pre_bpix_nano_v12",
    "2023_post_bpix_nano_v12",
    # "2024_nano_v15",
]
CHANNELS = ["et", "mt", "tt", "ee", "mm", "em"]
JET_SELECTIONS = ["eq0j", "eq1j", "eq2j", "geq3j"]

SHAPES_TAG_WITH_BJET_WEIGHTS = (
    "shapes-2026-10-22-without-bjet-filters-with-bjet-weights"
)
SHAPES_TAG_WITHOUT_BJET_WEIGHTS = (
    "shapes-2026-10-22-without-bjet-filters-without-bjet-weights"
)


def get_file_path(
    base_output_dir: Path,
    shapes_tag: str,
    campaign_inst,
    channel_inst,
    category_inst,
    variable_inst,
) -> str:
    return str(
        base_output_dir
        / shapes_tag
        / "merged_histograms"
        / campaign_inst.name
        / f"{channel_inst.name}__{category_inst.name}"
        / f"{variable_inst.name}.root"
    )


def get_hist(
    root_file,
    campaign_inst,
    channel_inst,
    category_inst,
    process_inst,
    variable_inst,
):
    return root_file.Get(
        "/".join(
            (
                campaign_inst.name,
                channel_inst.name,
                category_inst.name,
                process_inst.name,
                f"{variable_inst.name}__nominal",
            )
        )
    )


def calculate_norm_corrections(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict,
    campaign: str,
    channel: str,
    categories: list[str],
    base_output_dir: Path,
    shapes_tag_with_bjet_weights: str,
    shapes_tag_without_bjet_weights: str,
) -> dict[tuple[str, str, int], float]:
    """
    Derive the b-jet normalization scale factors of all simulated processes in
    the given categories of a channel as the ratio of the yields without and
    with b-jet weights. Returns the factors keyed by
    `(channel, process, n_jets)`.
    """
    # Load the analysis inventory for this campaign and channel
    inventory = load_inventory(
        inventory_factory_fn_path,
        campaign,
        channel,
        **inventory_factory_kwargs,
    )

    # Get the campaign and channel instances
    campaign_inst = inventory.campaign
    channel_inst = inventory.channel
    variable_inst = inventory.variables.get("yield")

    # Dictionary with scale factors, `(channel, process, n_jets) -> factor`
    scale_factors = {}

    # Iterate through categories of this channel
    for category_name in categories:
        if not channel_inst.has_category(category_name):
            continue
        category_inst = channel_inst.get_category(category_name)
        n_jets = parse_n_jets(category_name)

        path_with = get_file_path(
            base_output_dir,
            shapes_tag_with_bjet_weights,
            campaign_inst,
            channel_inst,
            category_inst,
            variable_inst,
        )
        path_without = get_file_path(
            base_output_dir,
            shapes_tag_without_bjet_weights,
            campaign_inst,
            channel_inst,
            category_inst,
            variable_inst,
        )
        rf_with = ROOT.TFile.Open(path_with, "READ")
        if not rf_with or rf_with.IsZombie():
            logger.warning(f"Cannot open {path_with}")
            continue
        rf_without = ROOT.TFile.Open(path_without, "READ")
        if not rf_without or rf_without.IsZombie():
            logger.warning(f"Cannot open {path_without}")
            rf_with.Close()
            continue

        try:
            # Get the histograms for all simulated processes from the ROOT files
            for process_inst in gen_process_insts(inventory):
                # Skip data
                if process_inst.is_data:
                    continue

                # Get histograms from the ROOT files
                hist_with = get_hist(
                    rf_with,
                    campaign_inst,
                    channel_inst,
                    category_inst,
                    process_inst,
                    variable_inst,
                )
                hist_without = get_hist(
                    rf_without,
                    campaign_inst,
                    channel_inst,
                    category_inst,
                    process_inst,
                    variable_inst,
                )
                if not isinstance(hist_with, ROOT.TH1) or not isinstance(
                    hist_without, ROOT.TH1
                ):
                    logger.debug(
                        "No histogram for %s %s %s %s",
                        campaign_inst.name,
                        channel_inst.name,
                        category_inst.name,
                        process_inst.name,
                    )
                    continue

                # Calculate scale factor
                sf = 1.0
                if hist_with.Integral() > 0:
                    sf = hist_without.Integral() / hist_with.Integral()

                # Add scale factor to the dictionary
                scale_factors[
                    (channel_inst.name, process_inst.name, n_jets)
                ] = sf
        finally:
            rf_with.Close()
            rf_without.Close()

    return scale_factors


def main():
    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)
    logging.basicConfig(level=logging.INFO)

    for campaign in CAMPAIGNS:
        scale_factors = {}
        for channel in CHANNELS:
            categories = [f"{channel}_{sel}" for sel in JET_SELECTIONS]
            scale_factors.update(
                calculate_norm_corrections(
                    "xyh.config.inventory.create_inventory",
                    {"process_set": "default"},
                    campaign,
                    channel,
                    categories,
                    BASE_OUTPUT_DIR,
                    SHAPES_TAG_WITH_BJET_WEIGHTS,
                    SHAPES_TAG_WITHOUT_BJET_WEIGHTS,
                )
            )

        if not scale_factors:
            logger.warning("No scale factors derived for %s", campaign)
            continue

        correction_set = build_correction_set(
            scale_factors,
            description=(
                f"b-jet normalization factors for {campaign}, derived from "
                "the ratio of the yields without and with b-jet weights"
            ),
        )
        output_path = (
            BASE_OUTPUT_DIR
            / SHAPES_TAG_WITH_BJET_WEIGHTS
            / "bjet_normalization"
            / f"{campaign}.json"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            correction_set.model_dump_json(exclude_unset=True, indent=1)
        )
        logger.info("Wrote %s", output_path)

        for (channel, process, n_jets), sf in sorted(scale_factors.items()):
            print(f"{campaign}, {channel}, {process}, {n_jets} jets: {sf:.6f}")


if __name__ == "__main__":
    main()
