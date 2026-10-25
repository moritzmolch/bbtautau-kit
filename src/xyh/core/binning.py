"""
Data-driven binning and binning overrides.

The binning of the variables is defined in the inventory. This module provides
the means to derive an equipopulated binning from an array of event values and
to store, load and look up binnings that override the inventory binning. The
overrides are stored as nested dictionaries

    {campaign: {channel: {category: {variable: [edge, ...]}}}}

in a JSON file, see `xyh.binning` and the `binning` output mode of
`run_graphs`.
"""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from xyh.core.io import dump_json, load_json

logger = logging.getLogger(__name__)

BinningOverrides = dict[str, dict[str, dict[str, dict[str, list[float]]]]]


def _round_significant(values: np.ndarray, precision: int) -> np.ndarray:
    """Round to `precision` significant digits."""
    values = np.asarray(values, dtype=float)
    out = np.zeros_like(values)
    nonzero = values != 0
    exponent = np.floor(np.log10(np.abs(values[nonzero])))
    factor = 10.0 ** (precision - 1 - exponent)
    out[nonzero] = np.round(values[nonzero] * factor) / factor
    return out


def equipopulated_edges(
    values: Sequence[float],
    n_bins: int,
    *,
    range: tuple[float, float] | None = None,
    precision: int | None = None,
) -> list[float]:
    """
    Derive bin edges such that every bin holds the same number of values.

    Parameters
    ----------
    values : Sequence[float]
        The (unweighted) event values. Non-finite values are ignored.

    n_bins : int
        The requested number of bins.

    range : tuple[float, float], optional
        Restrict the values to this range. The outer edges are the range
        limits, so values outside of it fall into the under-/overflow.

    precision : int, optional
        Round the edges to this number of significant digits.

    Returns
    -------
    list[float]
        The strictly increasing bin edges. For discrete data, where quantiles
        coincide, there are fewer than `n_bins` bins.
    """
    if n_bins < 1:
        raise ValueError(f"n_bins must be positive, got {n_bins}")

    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if range is not None:
        low, high = range
        values = values[(values >= low) & (values <= high)]
    if len(values) == 0:
        raise ValueError("No values to derive a binning from.")

    edges = np.quantile(
        values, np.linspace(0.0, 1.0, n_bins + 1, endpoint=True)
    )
    if range is not None:
        edges[0], edges[-1] = range
    if precision is not None:
        edges = _round_significant(edges, precision)

    # Quantiles of discrete or rounded data may coincide
    edges = np.unique(edges)
    if len(edges) < 2:
        raise ValueError("All values are identical, cannot define bins.")
    if len(edges) - 1 < n_bins:
        logger.warning(
            f"Only {len(edges) - 1} of {n_bins} bins are distinct for this data"
        )

    return [float(e) for e in edges]


def lookup_binning(
    overrides: BinningOverrides | None,
    campaign: str,
    channel: str,
    category: str,
    variable: str,
) -> list[float] | None:
    """Return the overriding bin edges or `None` if there are none."""
    if not overrides:
        return None
    return (
        overrides.get(campaign, {})
        .get(channel, {})
        .get(category, {})
        .get(variable)
    )


def set_binning(
    overrides: BinningOverrides,
    campaign: str,
    channel: str,
    category: str,
    variable: str,
    edges: Sequence[float],
) -> None:
    """Store bin edges in the nested overrides dictionary."""
    entry = (
        overrides.setdefault(campaign, {})
        .setdefault(channel, {})
        .setdefault(category, {})
    )
    entry[variable] = [float(e) for e in edges]


def iter_binning(overrides: BinningOverrides):
    """Iterate over `(campaign, channel, category, variable)` of the entries."""
    for campaign, channels in overrides.items():
        for channel, categories in channels.items():
            for category, variables in categories.items():
                for variable in variables:
                    yield campaign, channel, category, variable


def dump_binning_overrides(overrides: BinningOverrides, path: Path) -> None:
    """Write the overrides to a JSON file."""
    dump_json(overrides, Path(path))


def load_binning_overrides(path: Path | str) -> BinningOverrides:
    """Load the overrides from a JSON file written by the derivation."""
    data: Any = load_json(Path(path))
    for campaign, channel, category, variable in iter_binning(data):
        edges = data[campaign][channel][category][variable]
        if len(edges) < 2 or any(
            b <= a for a, b in zip(edges, edges[1:], strict=False)
        ):
            raise ValueError(
                f"Invalid bin edges for {campaign}/{channel}/{category}/"
                f"{variable}: {edges}"
            )
    return data
