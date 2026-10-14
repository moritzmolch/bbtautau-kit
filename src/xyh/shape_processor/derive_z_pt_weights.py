"""
Derive data-driven Z normalization and pt corrections.

Reads the merged histograms of a shapes tag (`yield` and `pt_vis`), subtracts
all non-Z processes from data and writes one correctionlib file per campaign
to `output_dir`. See `xyh.core.z_pt_reweighting` for the method. The weights
are applied in a new production by setting `XYH_Z_PT_WEIGHTS_DIR`, see
`xyh.weights.processes`.

The corrections must be derived from a production without Z corrections.
"""

import logging
from pathlib import Path

import numpy as np
import ROOT
from omegaconf import DictConfig

from xyh.core.cli import hydra_cli
from xyh.core.config import load_inventory
from xyh.core.config.util import gen_process_insts
from xyh.core.z_pt_reweighting import (
    Binned,
    build_correction_set,
    compute_normalization,
    compute_pt_correction,
    compute_pt_ratio,
    find_merge_groups,
    smooth_gaussian,
    sum_binned,
)

logger = logging.getLogger(__name__)


def _read_hist(root_file, path: str) -> Binned | None:
    """Read a histogram into a `Binned`, or `None` if it does not exist."""
    hist = root_file.Get(path)
    if not hist:
        return None
    n_bins = hist.GetNbinsX()
    edges = np.array([hist.GetBinLowEdge(i) for i in range(1, n_bins + 2)])
    values = np.array([hist.GetBinContent(i) for i in range(1, n_bins + 1)])
    # Data histograms have no sum of weights squared stored: use Poisson errors
    if hist.GetSumw2N() > 0:
        variances = np.array(
            [hist.GetBinError(i) ** 2 for i in range(1, n_bins + 1)]
        )
    else:
        variances = values.copy()
    return Binned(edges, values, variances)


def _read_processes(
    base_dir: Path,
    inventory,
    category: str,
    variable: str,
) -> tuple[Binned, list[Binned], list[Binned]]:
    """Return the histograms of data, Z and all other simulated processes."""
    campaign = inventory.campaign.name
    channel = inventory.channel.name
    path = base_dir / campaign / f"{channel}__{category}" / f"{variable}.root"
    data, z, others = [], [], []
    root_file = ROOT.TFile.Open(str(path), "READ")
    if not root_file or root_file.IsZombie():
        raise FileNotFoundError(f"Cannot open histogram file {path}")
    try:
        for process_inst in gen_process_insts(inventory):
            hist = _read_hist(
                root_file,
                "/".join(
                    (
                        campaign,
                        channel,
                        category,
                        process_inst.name,
                        f"{variable}__nominal",
                    )
                ),
            )
            if hist is None:
                continue
            if process_inst.is_data:
                data.append(hist)
            elif process_inst.has_tag("z"):
                z.append(hist)
            else:
                others.append(hist)
    finally:
        root_file.Close()
    if not data or not z:
        raise ValueError(f"No data or Z histograms found in {path}")
    return sum_binned(data), sum_binned(z), others


def derive_z_pt_weights(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict,
    campaign: str,
    channel: str,
    categories: list[str],
    merged_histograms_dir: Path,
    output_file: Path,
    yield_variable: str = "yield",
    pt_variable: str = "pt_vis",
    rebin: int = 1,
    max_rel_error: float | None = None,
    smoothing_sigma: float | None = None,
    smoothing_grid_step: float = 1.0,
    min_value: float | None = None,
    max_value: float | None = None,
):
    inventory = load_inventory(
        inventory_factory_fn_path,
        campaign,
        channel,
        **inventory_factory_kwargs,
    )

    normalizations = {}
    normalization_errors = {}
    pt_corrections = {}
    for category in categories:
        # Normalization from the yield histograms
        data, z, others = _read_processes(
            merged_histograms_dir, inventory, category, yield_variable
        )
        norm, norm_err = compute_normalization(data, z, others)
        logger.info(
            "%s, %s: Z normalization %.4f +- %.4f",
            campaign,
            category,
            norm,
            norm_err,
        )

        # Binwise correction of the pt spectrum on top of the normalization
        data, z, others = _read_processes(
            merged_histograms_dir, inventory, category, pt_variable
        )
        if rebin > 1:
            data, z = data.rebin(rebin), z.rebin(rebin)
            others = [h.rebin(rebin) for h in others]
        # Smoothing needs the fine binning, so it replaces the merging
        if max_rel_error is not None and smoothing_sigma is None:
            starts = find_merge_groups(data, z, others, max_rel_error)
            data, z = data.merge(starts), z.merge(starts)
            others = [h.merge(starts) for h in others]
        if smoothing_sigma is None:
            pt_corr = compute_pt_correction(
                data,
                z,
                others,
                norm,
                min_value=min_value,
                max_value=max_value,
            )
        else:
            # Smooth the raw ratios, in which no bins are dropped
            ratio, weights = compute_pt_ratio(data, z, others, norm)
            pt_corr = smooth_gaussian(
                ratio, smoothing_sigma, smoothing_grid_step, weights
            )
            if min_value is not None or max_value is not None:
                pt_corr.values = np.clip(pt_corr.values, min_value, max_value)
        logger.info(
            "%s, %s: %d pt bins", campaign, category, len(pt_corr.values)
        )
        logger.info(
            "%s, %s: pt correction in [%.3f, %.3f]",
            campaign,
            category,
            pt_corr.values.min(),
            pt_corr.values.max(),
        )
        normalizations[category] = norm
        normalization_errors[category] = norm_err
        pt_corrections[category] = pt_corr

    cset = build_correction_set(
        normalizations,
        pt_corrections,
        normalization_errors,
        description=(
            f"Z normalization and pt corrections for {campaign}, derived in "
            f"the {channel} channel"
        ),
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(cset.model_dump_json(exclude_unset=True, indent=1))
    logger.info("Wrote %s", output_file)


@hydra_cli("derive_z_pt_weights")
def main(cfg: DictConfig):
    # Detach ROOT histogram objects from files
    ROOT.TH1.AddDirectory(0)

    for campaign in cfg["campaigns"]:
        derive_z_pt_weights(
            cfg["inventory"]["factory_fn"],
            dict(cfg["inventory"]["factory_fn_kwargs"]),
            campaign,
            cfg["channel"],
            list(cfg["categories"]),
            Path(cfg["merged_histograms_dir"]),
            Path(cfg["output_dir"]) / f"{campaign}.json",
            yield_variable=cfg["yield_variable"],
            pt_variable=cfg["pt_variable"],
            rebin=cfg["rebin"],
            max_rel_error=cfg.get("max_rel_error"),
            smoothing_sigma=cfg.get("smoothing_sigma"),
            smoothing_grid_step=cfg.get("smoothing_grid_step", 1.0),
            min_value=cfg.get("min_value"),
            max_value=cfg.get("max_value"),
        )


if __name__ == "__main__":
    main()
