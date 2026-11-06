"""Summary plots of normalization weights.

Reads the correctionlib files written by ``xyh.process_corrections.
derive_norm_weights`` (``<process_tag>_norm_<campaign>.json``, one per
campaign) and writes two plots:

* ``<name>_summary``: the nominal normalization in every (n_jets, n_bjets)
  bin, with the inputs (campaigns) side by side in each bin. The inner error
  bars show the statistical uncertainty, the outer ones the statistical
  uncertainty and the normalization uncertainty of the subtracted processes
  added in quadrature.
* ``<name>_jets_bjets``: the nominal normalization per (n_jets, n_bjets) bin
  as a 2D plot with one panel per input. The values are printed in the bins,
  bins without a stored value stay empty.

The correction is found by its name ``<process_tag>_normalization``, or has
to be given with ``--correction`` if a file holds several.

Usage
-----
    python3 -m xyh.process_corrections.plot_norm_weights \\
        data/output/<tag>/tt_norm/*.json --output-dir plots
"""

import argparse
import logging
from math import hypot
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import mplhep
import numpy as np
from correctionlib import schemav2
from matplotlib.colors import TwoSlopeNorm

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

SUFFIX = "_normalization"


def _label(edges: list[float], i: int) -> str:
    """Label of bin `i`, open-ended for the last one."""
    low = int(edges[i])
    return f"$\\geq${low}" if i == len(edges) - 2 else f"{low}"


def _leaves(node) -> dict[int, object]:
    return {
        int(low): leaf
        for low, leaf in zip(node.edges[:-1], node.content, strict=True)
    }


def _bins(node) -> dict[tuple[int, int], float]:
    """Values of a nested (n_jets, n_bjets) binning."""
    return {
        (j, b): float(value)
        for j, child in _leaves(node).items()
        for b, value in _leaves(child).items()
    }


def _find_correction(cset, name: str | None):
    corrections = {c.name: c for c in cset.corrections}
    if name is not None:
        return corrections[name]
    candidates = [c for n, c in corrections.items() if n.endswith(SUFFIX)]
    if len(candidates) != 1:
        raise ValueError(
            f"Expected exactly one correction ending in '{SUFFIX}', got "
            f"{sorted(corrections)}; select one with --correction"
        )
    return candidates[0]


def load(path: Path, correction: str | None = None) -> dict:
    """Normalizations of a correctionlib file.

    Returns the correction name, the jet and b-jet edges and, for the
    nominal and every stored variation, the value of every (n_jets, n_bjets)
    bin under `"variations"`.
    """
    cset = schemav2.CorrectionSet.model_validate_json(path.read_text())
    corr = _find_correction(cset, correction)
    if corr.data.nodetype != "category":
        raise ValueError(
            f"{corr.name} in {path} is not binned in a variation category"
        )
    variations = {item.key: _bins(item.value) for item in corr.data.content}
    if "nominal" not in variations:
        raise ValueError(f"{corr.name} in {path} has no nominal variation")

    keys = variations["nominal"]
    j_low = sorted({j for j, _ in keys})
    b_low = sorted({b for _, b in keys})
    # The upper edge only closes the last bin, which is open-ended
    top = next(iter(_leaves(corr.data.content[0].value).values()))
    j_top = corr.data.content[0].value.edges[-1]
    return {
        "name": corr.name,
        "j_edges": [float(j) for j in j_low] + [float(j_top)],
        "b_edges": [float(b) for b in b_low] + [float(top.edges[-1])],
        "variations": variations,
    }


def _uncertainties(
    variations: dict[str, dict], key: tuple[int, int]
) -> tuple[float | None, float | None]:
    """Statistical and total uncertainty of a bin, `None` if not stored."""
    nominal = variations["nominal"][key]
    if "stat_up" not in variations:
        return None, None
    stat = variations["stat_up"][key] - nominal
    other = (
        variations["norm_other_up"][key] - nominal
        if "norm_other_up" in variations
        else 0.0
    )
    return stat, hypot(stat, other)


def plot_summary(
    data: dict, j_edges, b_edges, ylabel: str, out: Path
) -> None:
    """Normalization in every (n_jets, n_bjets) bin, inputs side by side."""
    keys = [
        (int(j_edges[ij]), int(b_edges[ib]))
        for ij in range(len(j_edges) - 1)
        for ib in range(len(b_edges) - 1)
    ]
    keys = [k for k in keys if any(k in d["variations"]["nominal"] for d in data.values())]
    n_in = len(data)
    width = 0.6
    fig, ax = plt.subplots(figsize=(max(10, 1.1 * len(keys)), 7))
    for k, (name, d) in enumerate(data.items()):
        pos, val, stat, total = [], [], [], []
        for i, key in enumerate(keys):
            if key not in d["variations"]["nominal"]:
                continue
            s, t = _uncertainties(d["variations"], key)
            pos.append(i + (k - (n_in - 1) / 2) * width / n_in)
            val.append(d["variations"]["nominal"][key])
            stat.append(s)
            total.append(t)
        has_unc = None not in stat
        line = ax.errorbar(
            pos,
            val,
            yerr=total if has_unc else None,
            fmt="o",
            capsize=3,
            elinewidth=1,
            label=name,
        )
        if has_unc:
            ax.errorbar(
                pos,
                val,
                yerr=stat,
                fmt="none",
                elinewidth=3,
                color=line[0].get_color(),
            )
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax.set_xticks(
        range(len(keys)),
        [
            f"{_label(j_edges, j_edges.index(j))}j\n"
            f"{_label(b_edges, b_edges.index(b))}b"
            for j, b in ((float(j), float(b)) for j, b in keys)
        ],
    )
    ax.set_xlabel("Number of jets / b-jets")
    ax.set_ylabel(ylabel)
    ax.legend(loc="upper right", fontsize=14)
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.2 * (hi - lo))
    mplhep.cms.label(ax=ax, data=True, com=13.6, lumi=None, text="Work in progress")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Wrote {out}")


def plot_jets_bjets(
    data: dict, j_edges, b_edges, ylabel: str, out: Path
) -> None:
    """Normalization per (n_jets, n_bjets) as 2D plot, one panel per input."""
    n_j, n_b = len(j_edges) - 1, len(b_edges) - 1
    fig, axes = plt.subplots(
        1,
        len(data),
        sharey=True,
        squeeze=False,
        figsize=(1.6 * n_j * len(data) + 3, 1.4 * n_b + 3),
        layout="constrained",
    )
    grids = {}
    for name, d in data.items():
        grid = np.full((n_b, n_j), np.nan)
        nominal = d["variations"]["nominal"]
        for ij in range(n_j):
            for ib in range(n_b):
                key = (int(j_edges[ij]), int(b_edges[ib]))
                if key in nominal:
                    grid[ib, ij] = nominal[key]
        grids[name] = grid
    low = min(np.nanmin(g) for g in grids.values())
    high = max(np.nanmax(g) for g in grids.values())
    norm = TwoSlopeNorm(vcenter=1.0, vmin=min(low, 0.99), vmax=max(high, 1.01))

    for ax, (name, grid) in zip(axes[0], grids.items(), strict=True):
        image = ax.imshow(
            np.ma.masked_invalid(grid),
            origin="lower",
            cmap="RdBu_r",
            norm=norm,
            aspect="auto",
        )
        for ib in range(n_b):
            for ij in range(n_j):
                if np.isfinite(grid[ib, ij]):
                    # White text on dark cells
                    r, g, b, _ = image.cmap(norm(grid[ib, ij]))
                    dark = 0.299 * r + 0.587 * g + 0.114 * b < 0.45
                    ax.text(
                        ij,
                        ib,
                        f"{grid[ib, ij]:.3f}",
                        ha="center",
                        va="center",
                        fontsize=14,
                        color="white" if dark else "black",
                    )
        ax.set_xticks(range(n_j), [_label(j_edges, i) for i in range(n_j)])
        ax.set_yticks(range(n_b), [_label(b_edges, i) for i in range(n_b)])
        ax.set_xlabel("Number of jets")
        ax.set_title(name, fontsize=16, pad=40)
        ax.tick_params(which="minor", length=0)
    axes[0, 0].set_ylabel("Number of b-jets")
    fig.colorbar(image, ax=axes[0].tolist(), label=ylabel)
    mplhep.cms.label(
        ax=axes[0, 0], data=True, com=13.6, lumi=None, text="Work in progress"
    )
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Wrote {out}")


def _input_name(path: Path) -> str:
    """Campaign of a ``<process_tag>_norm_<campaign>`` file, else the stem."""
    return path.stem.split("_norm_", 1)[1] if "_norm_" in path.stem else path.stem


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument(
        "--correction",
        help="Name of the correction, default: the one ending in "
        f"'{SUFFIX}'",
    )
    parser.add_argument(
        "--name", help="Output name prefix, default: the correction name"
    )
    parser.add_argument(
        "--label",
        help="Process label for the axes, default: the process tag",
    )
    parser.add_argument("--format", default="png")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    data = {_input_name(p): load(p, args.correction) for p in args.inputs}
    first = next(iter(data.values()))
    j_edges, b_edges = first["j_edges"], first["b_edges"]
    if any(
        d["j_edges"] != j_edges or d["b_edges"] != b_edges
        for d in data.values()
    ):
        raise ValueError("The inputs have different multiplicity bins")
    names = {d["name"] for d in data.values()}
    if len(names) != 1:
        raise ValueError(f"The inputs hold different corrections: {names}")

    corr_name = first["name"]
    name = args.name or corr_name
    process = args.label or corr_name.removesuffix(SUFFIX)
    ylabel = f"{process} normalization factor"

    matplotlib.style.use(mplhep.style.CMS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plot_summary(
        data,
        j_edges,
        b_edges,
        ylabel,
        args.output_dir / f"{name}_summary.{args.format}",
    )
    plot_jets_bjets(
        data,
        j_edges,
        b_edges,
        ylabel,
        args.output_dir / f"{name}_jets_bjets.{args.format}",
    )


if __name__ == "__main__":
    main()
