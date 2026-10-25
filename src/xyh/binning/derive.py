"""
Derive an equipopulated binning from data events written by `run_graphs`.

`run_graphs` in binning mode (`graph_processing.mode: "binning"`) applies the
selections of the analysis to the data events and writes the values of the
configured variables to a compressed numpy file per dataset, see
`xyh.core.specs.graph._binning`. This module turns these values into bin edges
with an equal number of data events per bin, see
`xyh.core.binning.equipopulated_edges`, and stores them as binning overrides,
which replace the binning of the inventory in a production when set as
`binning_overrides.file` in `run_graphs`. The number of bins and the precision
of the edges are configured in `hydra_config/base/binning.yaml`, per variable
and, optionally, per campaign, channel, and category.
"""

import logging
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

from xyh.core.binning import (
    BinningOverrides,
    dump_binning_overrides,
    equipopulated_edges,
    set_binning,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

logger = logging.getLogger(__name__)


def iter_value_files(
    input_dir: Path,
) -> Iterator[tuple[str, str, str, str, Path]]:
    """Yield the value files of `input_dir` with their analysis context.

    The files are written by `xyh.core.specs.graph._binning` under
    ``<campaign>/<channel>__<category>/<variable>/<dataset>.npz``.
    """
    for path in sorted(Path(input_dir).rglob("*.npz")):
        campaign, channel_category, variable, _ = path.relative_to(
            input_dir
        ).parts
        channel, category = channel_category.split("__", 1)
        yield campaign, channel, category, variable, path


def _apply_scope(
    base: dict[str, Any], scope: Mapping[str, Any]
) -> dict[str, Any]:
    """Overlay the settings of one nesting level of `scope` on `base`."""
    effective = dict(base)
    for key in ("n_bins", "precision", "range"):
        if scope.get(key) is not None:
            effective[key] = scope[key]
    return effective


def resolve_binning_settings(
    settings: Mapping[str, Any],
    campaign: str,
    channel: str,
    category: str,
    variable: str,
) -> tuple[int, int | None, Sequence[float] | None]:
    """Resolve the effective binning settings of a variable.

    The settings are resolved from the most specific to the most general
    scope: variable, category, channel, campaign, and finally the top-level
    defaults.
    """
    effective: dict[str, Any] = {
        "n_bins": settings.get("n_bins"),
        "precision": settings.get("precision"),
        "range": None,
    }
    campaign_scope = (settings.get("campaigns") or {}).get(campaign, {})
    effective = _apply_scope(effective, campaign_scope)
    channel_scope = (campaign_scope.get("channels") or {}).get(channel, {})
    effective = _apply_scope(effective, channel_scope)
    category_scope = (channel_scope.get("categories") or {}).get(category, {})
    effective = _apply_scope(effective, category_scope)
    variable_scope = (settings.get("variables") or {}).get(variable, {})
    effective = _apply_scope(effective, variable_scope)
    n_bins = effective["n_bins"]
    if n_bins is None:
        raise ValueError(
            "No number of bins configured for the binning of "
            f"{campaign}/{channel}/{category}/{variable}"
        )
    return n_bins, effective.get("precision"), effective.get("range")


def _plot(
    values: np.ndarray,
    edges: Sequence[float],
    label: str,
    x_title: str,
    output_file: Path,
) -> None:
    """Plot the data events with the derived binning."""
    counts, _ = np.histogram(values, bins=edges)
    fig, ax = plt.subplots()
    ax.stairs(counts, edges, linewidth=2)
    ax.set_xlabel(x_title)
    ax.set_ylabel("Data events")
    ax.set_ylim(0, 1.3 * counts.max())
    ax.text(0.02, 0.95, label, transform=ax.transAxes, va="top")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file)
    plt.close(fig)


def derive_binning(
    input_dir: Path,
    output_file: Path,
    plots_dir: Path,
    settings: Mapping[str, Any],
    labels: Mapping[tuple[str, str], str] | None = None,
) -> BinningOverrides:
    """Derive an equipopulated binning from the value files of `input_dir`.

    The values of all datasets are combined per campaign, channel, category,
    and variable, and the bin edges are chosen such that every bin holds the
    same number of data events. The edges are written to `output_file` as
    binning overrides, see `xyh.core.binning`, and the data distributions are
    plotted to `plots_dir`. `labels` maps `(channel, variable)` to the axis
    label of the variable, falling back to the variable name.
    """
    values_by_key: dict[tuple[str, str, str, str], list[np.ndarray]] = {}
    for campaign, channel, category, variable, path in iter_value_files(
        input_dir
    ):
        with np.load(path) as value_file:
            values = value_file["values"]
        values_by_key.setdefault(
            (campaign, channel, category, variable), []
        ).append(values)

    overrides: BinningOverrides = {}
    labels = labels or {}
    for key, chunks in sorted(values_by_key.items()):
        campaign, channel, category, variable = key
        values = np.concatenate(chunks)
        n_bins, precision, rng = resolve_binning_settings(
            settings, campaign, channel, category, variable
        )
        try:
            edges = equipopulated_edges(
                values,
                n_bins,
                range=(rng[0], rng[1]) if rng is not None else None,
                precision=precision,
            )
        except ValueError as error:
            logger.warning(
                f"Skipping {campaign}/{channel}/{category}/{variable}: {error}"
            )
            continue
        set_binning(overrides, campaign, channel, category, variable, edges)
        logger.info(
            f"{campaign}/{channel}/{category}/{variable}: {len(values)} "
            f"events, {len(edges) - 1} bins"
        )
        _plot(
            values,
            edges,
            f"{campaign} {category}",
            labels.get((channel, variable), variable),
            plots_dir / campaign / f"{category}__{variable}.png",
        )

    dump_binning_overrides(overrides, output_file)
    logger.info(f"Wrote binning to {output_file}")
    return overrides
