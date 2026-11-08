"""
Derive data-driven Z normalization and pt corrections.

Reads the merged histograms of a shapes tag (`yield` and `pt_vis`), subtracts
all non-Z processes from data and writes one correctionlib file per campaign
to `output_dir`. The derivation has two stages: the Z normalization is derived
per (n_jets, n_bjets) category, then the pt correction is derived per n_jets
from the histograms inclusive in b jets, with the Z prediction scaled by the
normalization of the jet multiplicity derived from its yields. See `xyh.core.z_pt_reweighting`
for the method. The weights are applied in a new production by setting `XYH_Z_PT_WEIGHTS_DIR`, see
`xyh.weights.processes`.

The corrections must be derived from a production without Z corrections.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import ROOT
from omegaconf import DictConfig, OmegaConf

from xyh.core.cli import hydra_cli
from xyh.core.config import load_inventory
from xyh.core.config.util import gen_process_insts
from xyh.core.z_pt_reweighting import (
    Binned,
    build_correction_set,
    compute_normalization,
    compute_pt_correction,
    compute_pt_ratio,
    concatenate,
    find_merge_groups,
    is_possible_category,
    jet_category,
    smooth_kernel,
    sparsify,
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


@dataclass
class DerivationSettings:
    """Settings of the derivation in one category, see the Hydra config."""

    rebin: int = 1
    max_rel_error: float | None = None
    bandwidth: float | None = None
    stat_sigma: float = 1.0
    bandwidth_variations: tuple[float, float] = (0.5, 1.5)
    n_samples: int = 100
    seed: int = 19
    sparsify_threshold: float = 0.01
    pt_clip: float | None = None


def _apply_scope(
    base: dict[str, Any], scope: Mapping[str, Any]
) -> dict[str, Any]:
    """Overlay the settings of one nesting level of `scope` on `base`.

    The structural keys `channels` and `categories` nest the next levels and
    are not settings.
    """
    effective = dict(base)
    for key in scope:
        if key not in ("channels", "categories"):
            effective[key] = scope[key]
    return effective


def resolve_settings(
    derivation_settings: Mapping[str, Any],
    campaign: str,
    channel: str,
    category: str,
) -> DerivationSettings:
    """
    Settings of the category, resolved from the most specific to the most
    general scope: category, channel, campaign, and finally the top-level
    defaults, as for the binning settings, see
    `xyh.binning.derive.resolve_binning_settings`. The category is the jet
    multiplicity without b-jet selection (mm_eq2j etc.).
    """
    effective = dict(derivation_settings)
    campaign_scope = (derivation_settings.get("campaigns") or {}).get(
        campaign, {}
    )
    effective = _apply_scope(effective, campaign_scope)
    channel_scope = (campaign_scope.get("channels") or {}).get(channel, {})
    effective = _apply_scope(effective, channel_scope)
    category_scope = (channel_scope.get("categories") or {}).get(category, {})
    effective = _apply_scope(effective, category_scope)
    effective.pop("campaigns", None)
    if "bandwidth_variations" in effective:
        effective["bandwidth_variations"] = tuple(
            effective["bandwidth_variations"]
        )
    return DerivationSettings(**effective)


def derive_z_pt_weights(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict,
    campaign: str,
    channel: str,
    categories: list[str],
    merged_histograms_dir: Path,
    output_file: Path,
    derivation_settings: Mapping[str, Any],
    yield_variable: str = "yield",
    pt_variable: str = "pt_vis",
):
    inventory = load_inventory(
        inventory_factory_fn_path,
        campaign,
        channel,
        **inventory_factory_kwargs,
    )

    # Categories with more b-tagged jets than jets are empty by construction
    impossible = [c for c in categories if not is_possible_category(c)]
    if impossible:
        logger.warning("Ignoring impossible categories %s", impossible)
    categories = [c for c in categories if c not in impossible]

    # Stage 1: normalization per (n_jets, n_bjets) category from the yields
    normalizations = {}
    normalization_errors = {}
    for category in categories:
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
        normalizations[category] = norm
        normalization_errors[category] = norm_err

    # Stage 2: pt correction per n_jets from the histograms of the jet
    # multiplicity inclusive in b jets. The Z prediction is scaled with the
    # normalization of the jet multiplicity, derived from its yields like the
    # ones of the (n_jets, n_bjets) categories.
    jet_categories = list(dict.fromkeys(jet_category(c) for c in categories))

    jet_normalizations = {}
    jet_normalization_errors = {}
    pt_corrections = {}
    pt_stat_uncs = {}
    pt_variations = {}
    raw_ratios = {}
    for jet_cat in jet_categories:
        settings = resolve_settings(derivation_settings, campaign, channel, jet_cat)
        yield_data, yield_z, yield_others = _read_processes(
            merged_histograms_dir, inventory, jet_cat, yield_variable
        )
        jet_normalization, jet_norm_err = compute_normalization(
            yield_data, yield_z, yield_others
        )
        logger.info(
            "%s, %s: Z normalization %.4f +- %.4f",
            campaign,
            jet_cat,
            jet_normalization,
            jet_norm_err,
        )
        jet_normalizations[jet_cat] = jet_normalization
        jet_normalization_errors[jet_cat] = jet_norm_err
        data, z, others = _read_processes(
            merged_histograms_dir, inventory, jet_cat, pt_variable
        )
        z = z.scale(jet_normalization)
        if settings.rebin > 1:
            data, z = data.rebin(settings.rebin), z.rebin(settings.rebin)
            others = [h.rebin(settings.rebin) for h in others]
        # Merge all bins above pt_clip into a single tail bin
        has_tail = False
        if settings.pt_clip is not None:
            data, has_tail = data.merge_above(settings.pt_clip)
            z, _ = z.merge_above(settings.pt_clip)
            others = [h.merge_above(settings.pt_clip)[0] for h in others]
        # Smoothing needs the fine binning, so it replaces the merging
        if settings.max_rel_error is not None and settings.bandwidth is None:
            starts = find_merge_groups(data, z, others, settings.max_rel_error)
            data, z = data.merge(starts), z.merge(starts)
            others = [h.merge(starts) for h in others]
        if settings.bandwidth is None:
            pt_corr = compute_pt_correction(
                data,
                z,
                others,
            )
        else:
            # Smooth the raw ratios, in which no bins are dropped
            ratio, weights = compute_pt_ratio(data, z, others)
            raw_ratios[jet_cat] = ratio
            # The tail bin is not smoothed, it stays a single bin
            n_smooth = len(ratio.values) - 1 if has_tail else None
            head = ratio.slice(0, n_smooth)
            if len(head.values) > 0:
                smoothed = smooth_kernel(
                    head,
                    settings.bandwidth,
                    weights[:n_smooth] > 0,
                    stat_sigma=settings.stat_sigma,
                    bandwidth_variations=settings.bandwidth_variations,
                    n_samples=settings.n_samples,
                    seed=settings.seed,
                )
                # Store the curves with as few bins as needed
                curves = {
                    "nominal": smoothed.nominal.values,
                    "stat_unc": np.sqrt(smoothed.nominal.variances),
                    **smoothed.variations,
                }
                sparse = {}
                for name, values in curves.items():
                    edges, values = sparsify(
                        smoothed.nominal.edges,
                        values,
                        settings.sparsify_threshold,
                    )
                    sparse[name] = Binned(edges, values, np.zeros_like(values))
                if has_tail:
                    tail = ratio.slice(n_smooth)
                    unchanged = Binned(
                        tail.edges, tail.values, np.zeros_like(tail.values)
                    )
                    error = Binned(
                        tail.edges, np.sqrt(tail.variances), unchanged.variances
                    )
                    sparse = {
                        name: concatenate(
                            hist, error if name == "stat_unc" else unchanged
                        )
                        for name, hist in sparse.items()
                    }
                pt_corr = sparse.pop("nominal")
                pt_stat_uncs[jet_cat] = sparse.pop("stat_unc")
                for name, hist in sparse.items():
                    pt_variations.setdefault(name, {})[jet_cat] = hist
            else:
                pt_corr = ratio
        logger.info(
            "%s, %s: %d pt bins", campaign, jet_cat, len(pt_corr.values)
        )
        logger.info(
            "%s, %s: pt correction in [%.3f, %.3f]",
            campaign,
            jet_cat,
            pt_corr.values.min(),
            pt_corr.values.max(),
        )
        pt_corrections[jet_cat] = pt_corr

    # Jet multiplicities without smoothing are not varied
    for variations in pt_variations.values():
        for jet_cat, pt_corr in pt_corrections.items():
            variations.setdefault(
                jet_cat,
                Binned(
                    pt_corr.edges, pt_corr.values, np.zeros_like(pt_corr.values)
                ),
            )

    cset = build_correction_set(
        normalizations,
        pt_corrections,
        normalization_errors,
        raw_pt_ratios=raw_ratios or None,
        pt_stat_uncs=pt_stat_uncs or None,
        pt_variations=pt_variations or None,
        jet_normalizations=jet_normalizations,
        jet_normalization_errors=jet_normalization_errors,
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
            OmegaConf.to_container(cfg["derivation_settings"], resolve=True),
            yield_variable=cfg["yield_variable"],
            pt_variable=cfg["pt_variable"],
        )


if __name__ == "__main__":
    main()
