"""
Calculate b-jet normalization weights and write correctionlib files.

The b-jet normalization scale factor of a simulated process is the ratio of
its yield without b-jet weights to its yield with them, derived per jet
multiplicity category from the merged histograms of two productions of the
same campaign and channel (with and without b-jet weights). The factors are
stored in one correctionlib file per era and channel with the single
correction `bjet_normalization`, evaluated with the parameters `(channel,
process, n_jets)`. See `xyh.core.bjet_normalization` for the construction and
`hydra_config/run_btag_renormalization.yaml` for the configuration.
"""

import logging
from pathlib import Path

import ROOT
from omegaconf import DictConfig

from xyh.core.bjet_normalization import build_correction_set
from xyh.core.cli import hydra_cli
from xyh.core.config import load_inventory
from xyh.core.config.util import gen_process_insts
from xyh.core.z_pt_reweighting import parse_n_jets

logger = logging.getLogger(__name__)


def get_file_path(
    merged_histograms_dir: Path,
    campaign_inst,
    channel_inst,
    category_inst,
    variable_inst,
) -> str:
    return str(
        merged_histograms_dir
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
    merged_histograms_dir_with: Path,
    merged_histograms_dir_without: Path,
) -> tuple[str, dict[tuple[str, str, int], float]]:
    """
    Derive the b-jet normalization scale factors of all simulated processes in
    the given categories of a channel as the ratio of the yields without and
    with b-jet weights. Returns the short era handle of the campaign and the
    factors keyed by `(channel, process, n_jets)`.
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

    # Short era handle of the campaign, e.g. `2022preEE`
    era = f"{campaign_inst.x.year}{campaign_inst.x.postfix or ''}"

    # Dictionary with scale factors, `(channel, process, n_jets) -> factor`
    scale_factors = {}

    # Iterate through categories of this channel
    for category_name in categories:
        if not channel_inst.has_category(category_name):
            continue
        category_inst = channel_inst.get_category(category_name)
        n_jets = parse_n_jets(category_name)

        path_with = get_file_path(
            merged_histograms_dir_with,
            campaign_inst,
            channel_inst,
            category_inst,
            variable_inst,
        )
        path_without = get_file_path(
            merged_histograms_dir_without,
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

    return era, scale_factors


@hydra_cli("run_btag_renormalization")
def main(cfg: DictConfig):
    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    for campaign in cfg["campaigns"]:
        for channel in cfg["channels"]:
            # Categories of the channel, one per jet multiplicity selection
            categories = [f"{channel}_{sel}" for sel in cfg["jet_selections"]]

            era, scale_factors = calculate_norm_corrections(
                cfg["inventory"]["factory_fn"],
                dict(cfg["inventory"]["factory_fn_kwargs"]),
                campaign,
                channel,
                categories,
                Path(cfg["merged_histograms_dir_with_btag_weight"]),
                Path(cfg["merged_histograms_dir_without_btag_weight"]),
            )

            if not scale_factors:
                logger.warning(
                    "No scale factors derived for %s, %s", campaign, channel
                )
                continue

            correction_set = build_correction_set(
                scale_factors,
                description=(
                    f"b-jet normalization factors for {campaign}, {channel}, "
                    "derived from the ratio of the yields without and with "
                    "b-jet weights"
                ),
            )
            output_file = Path(cfg["output_dir"]) / (
                f"btag_renormalization_weights_{era}_{channel}.json"
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                correction_set.model_dump_json(exclude_unset=True, indent=1)
            )
            logger.info("Wrote %s", output_file)

            for (channel_name, process, n_jets), sf in sorted(
                scale_factors.items()
            ):
                print(
                    f"{campaign}, {channel_name}, {process}, {n_jets} jets:"
                    f" {sf:.6f}"
                )


if __name__ == "__main__":
    main()
