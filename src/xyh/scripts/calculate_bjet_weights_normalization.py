from pathlib import Path

import ROOT

from xyh import ROOT_DIR
from xyh.core.config import load_inventory
from xyh.core.config.util import gen_process_insts

BASE_OUTPUT_DIR = ROOT_DIR / "data" / "output"

CAMPAIGNS = [
    "2022_pre_ee_nano_v12",
    "2022_post_ee_nano_v12",
    "2023_pre_bpix_nano_v12",
    "2023_post_bpix_nano_v12",
    "2024_nano_v15",
]
CATEGORIES_N_JETS_MAP = {
    channel: {
        **{f"{channel}_eq{n}j": n for n in range(4)},
        **{f"{channel}_geq4j": 4},
    }
    for channel in ["ee", "mm", "em"]
}

SHAPES_TAG_WITH_BJET_WEIGHTS = (
    "shapes-2026-09-17-bjet-weights-norm-with-bjet-weights"
)
SHAPES_TAG_WITHOUT_BJET_WEIGHTS = (
    "shapes-2026-09-17-bjet-weights-norm-without-bjet-weights"
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
) -> None:
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


def calculate_norm_correction(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict,
    campaign: str,
    channel: str,
    categories: list[str],
    base_output_dir: Path,
    shapes_tag_with_bjet_weights: str,
    shapes_tag_without_bjet_weights: str,
) -> list[dict]:
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

    # Dictionary with correction factors
    scale_factors = []

    # Iterate through categories of this channel
    for category_inst in (
        channel_inst.get_category(c)
        for c in categories
        if channel_inst.has_category(c)
    ):
        # Get the file path for histograms with and without b-jet weights
        rf_with = ROOT.TFile.Open(
            str(
                get_file_path(
                    base_output_dir,
                    shapes_tag_with_bjet_weights,
                    campaign_inst,
                    channel_inst,
                    category_inst,
                    variable_inst,
                )
            ),
            "READ",
        )
        rf_without = ROOT.TFile.Open(
            get_file_path(
                base_output_dir,
                shapes_tag_without_bjet_weights,
                campaign_inst,
                channel_inst,
                category_inst,
                variable_inst,
            ),
            "READ",
        )

        # Get the file path for histograms with and without b-jet weights
        rf_with = ROOT.TFile.Open(
            get_file_path(
                base_output_dir,
                shapes_tag_with_bjet_weights,
                campaign_inst,
                channel_inst,
                category_inst,
                variable_inst,
            ),
            "READ",
        )
        rf_without = ROOT.TFile.Open(
            str(
                get_file_path(
                    base_output_dir,
                    shapes_tag_without_bjet_weights,
                    campaign_inst,
                    channel_inst,
                    category_inst,
                    variable_inst,
                )
            ),
            "READ",
        )

        # Get the histograms for all simulated processes from the ROOT file
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

            # Calculate scale factor
            sf = 1.0
            if hist_with.Integral() > 0:
                sf = hist_without.Integral() / hist_with.Integral()

            # Add scale factor and related information to the dictionary
            scale_factors.append(
                {
                    "campaign": campaign_inst.name,
                    "channel": channel_inst.name,
                    "category": category_inst.name,
                    "process": process_inst.name,
                    "scale_factor": sf,
                }
            )

    return scale_factors


def main():
    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    for campaign in CAMPAIGNS:
        for channel, dict_channel in CATEGORIES_N_JETS_MAP.items():
            categories = list(dict_channel.keys())
            corrections = calculate_norm_correction(
                "xyh.config.inventory.create_inventory",
                {"process_set": "default"},
                campaign,
                channel,
                categories,
                BASE_OUTPUT_DIR,
                SHAPES_TAG_WITH_BJET_WEIGHTS,
                SHAPES_TAG_WITHOUT_BJET_WEIGHTS,
            )

            for c in corrections:
                print(
                    f"{c['campaign']}, {c['channel']}, {c['category']}, {c['process']}: {c['scale_factor']}"
                )


if __name__ == "__main__":
    main()
