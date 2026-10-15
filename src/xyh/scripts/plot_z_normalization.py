"""Summary plots of the Z normalization factors.

Reads the correctionlib files written by ``xyh.shape_processor.
derive_z_pt_weights`` and writes two plots:

* ``<name>_jets``: the normalization per jet multiplicity (categories
  inclusive in b jets, ``z_normalization_jets``) with the statistical
  uncertainty ``z_normalization_jets_stat_unc``, with the inputs (campaigns)
  side by side in each jet multiplicity.
* ``<name>_jets_bjets``: the normalization per (n_jets, n_bjets) bin
  (``z_normalization``) as a 2D plot with one panel per input. The values are
  printed in the bins, bins that cannot hold events (more b jets than jets)
  stay empty.

Usage
-----
    python3 -m xyh.scripts.plot_z_normalization \\
        data/output/<tag>/z_pt_weights/*.json --output-dir plots
"""

import argparse
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import mplhep
import numpy as np
from correctionlib import schemav2
from matplotlib.colors import TwoSlopeNorm

matplotlib.use("Agg")


def _label(edges: list[float], i: int) -> str:
    """Label of bin `i`, open-ended for the last one."""
    low = int(edges[i])
    return f"$\\geq${low}" if i == len(edges) - 2 else f"{low}"


def _leaves(node) -> dict[int, object]:
    return {
        int(low): leaf
        for low, leaf in zip(node.edges[:-1], node.content, strict=True)
    }


def load(path: Path) -> dict:
    """Normalizations of a correctionlib file.

    Returns the jet edges, the b-jet edges, the value of every (n_jets,
    n_bjets) bin and, if stored, the value and uncertainty of every jet
    multiplicity (`None` otherwise).
    """
    cset = schemav2.CorrectionSet.model_validate_json(path.read_text())
    corrections = {c.name: c for c in cset.corrections}
    norm = corrections["z_normalization"].data

    bins = {}
    b_edges = set()
    for j, child in _leaves(norm).items():
        b_edges.update(child.edges[:-1])
        for b, value in _leaves(child).items():
            bins[(j, b)] = float(value)

    jets = None
    if "z_normalization_jets" in corrections:
        values = _leaves(corrections["z_normalization_jets"].data)
        unc = corrections.get("z_normalization_jets_stat_unc")
        errors = None if unc is None else _leaves(unc.data)
        jets = {
            j: (float(v), None if errors is None else float(errors[j]))
            for j, v in values.items()
        }
    return {
        "j_edges": [float(e) for e in norm.edges],
        "b_edges": sorted(float(e) for e in b_edges) + [float(norm.edges[-1])],
        "bins": bins,
        "jets": jets,
    }


def plot_jets(data: dict, j_edges: list[float], out: Path) -> None:
    """Normalization per jet multiplicity, the inputs side by side."""
    n_j, n_in = len(j_edges) - 1, len(data)
    fig, ax = plt.subplots(figsize=(10, 7))
    width = 0.6
    for k, (name, d) in enumerate(data.items()):
        points = [
            (ij, *d["jets"][int(j_edges[ij])])
            for ij in range(n_j)
            if int(j_edges[ij]) in d["jets"]
        ]
        errors = [e for _, _, e in points]
        ax.errorbar(
            [ij + (k - (n_in - 1) / 2) * width / n_in for ij, _, _ in points],
            [v for _, v, _ in points],
            yerr=None if None in errors else errors,
            fmt="o",
            capsize=3,
            label=name,
        )
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax.set_xticks(range(n_j), [_label(j_edges, i) for i in range(n_j)])
    ax.set_xlabel("Number of jets")
    ax.set_ylabel("Z normalization factor")
    ax.legend(loc="upper right", fontsize=14)
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.2 * (hi - lo))
    mplhep.cms.label(ax=ax, data=True, com=13.6, lumi=None, text="Work in progress")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def plot_jets_bjets(
    data: dict, j_edges: list[float], b_edges: list[float], out: Path
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
        for ij in range(n_j):
            for ib in range(n_b):
                key = (int(j_edges[ij]), int(b_edges[ib]))
                if key in d["bins"]:
                    grid[ib, ij] = d["bins"][key]
        grids[name] = grid
    low = min(np.nanmin(g) for g in grids.values())
    high = max(np.nanmax(g) for g in grids.values())
    norm = TwoSlopeNorm(
        vcenter=1.0, vmin=min(low, 0.99), vmax=max(high, 1.01)
    )

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
    fig.colorbar(image, ax=axes[0].tolist(), label="Z normalization factor")
    mplhep.cms.label(
        ax=axes[0, 0], data=True, com=13.6, lumi=None, text="Work in progress"
    )
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--name", default="z_normalization")
    parser.add_argument("--format", default="png")
    args = parser.parse_args()

    data = {p.stem: load(p) for p in args.inputs}
    first = next(iter(data.values()))
    j_edges, b_edges = first["j_edges"], first["b_edges"]
    if any(
        d["j_edges"] != j_edges or d["b_edges"] != b_edges
        for d in data.values()
    ):
        raise ValueError("The inputs have different multiplicity bins")

    matplotlib.style.use(mplhep.style.CMS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if all(d["jets"] is not None for d in data.values()):
        plot_jets(
            data,
            j_edges,
            args.output_dir / f"{args.name}_jets.{args.format}",
        )
    else:
        print(
            "Skipping the plot per jet multiplicity: z_normalization_jets is "
            "not stored in all inputs"
        )
    plot_jets_bjets(
        data,
        j_edges,
        b_edges,
        args.output_dir / f"{args.name}_jets_bjets.{args.format}",
    )


if __name__ == "__main__":
    main()
