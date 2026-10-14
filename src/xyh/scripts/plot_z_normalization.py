"""Summary plot of the Z normalization factors per jet and b-jet multiplicity.

Reads the correctionlib files written by ``xyh.shape_processor.
derive_z_pt_weights`` and plots ``z_normalization`` for every (n_jets,
n_bjets) bin. There is one panel per input file (campaign), the markers of
the b-jet multiplicities are shifted against each other within each jet
multiplicity. The error bars are the statistical uncertainty
``z_normalization_stat_unc``, if stored in the file.

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
from correctionlib import schemav2

matplotlib.use("Agg")


def _label(edges: list[float], i: int, label: str) -> str:
    """Label of bin `i`, open-ended for the last one."""
    low = int(edges[i])
    if i == len(edges) - 2:
        return f"$\\geq${low} {label}"
    return f"{low} {label}"


def _leaves(node) -> dict[int, object]:
    return {
        int(low): leaf
        for low, leaf in zip(node.edges[:-1], node.content, strict=True)
    }


def load(path: Path) -> dict:
    """Normalizations and uncertainties (`None` if not stored).

    Returns the jet edges, the b-jet edges and, per (n_jets, n_bjets) bin,
    the value and the uncertainty.
    """
    cset = schemav2.CorrectionSet.model_validate_json(path.read_text())
    corrections = {c.name: c for c in cset.corrections}
    norm = corrections["z_normalization"].data
    unc = corrections.get("z_normalization_stat_unc")
    unc_leaves = None if unc is None else _leaves(unc.data)

    bins = {}
    b_edges = set()
    for j, child in _leaves(norm).items():
        b_edges.update(child.edges[:-1])
        for b, value in _leaves(child).items():
            error = None
            if unc_leaves is not None:
                error = _leaves(unc_leaves[j])[b]
            bins[(j, b)] = (float(value), error)
    return {
        "j_edges": [float(e) for e in norm.edges],
        "b_edges": sorted(float(e) for e in b_edges) + [float(norm.edges[-1])],
        "bins": bins,
    }


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
    n_j, n_b = len(j_edges) - 1, len(b_edges) - 1

    matplotlib.style.use(mplhep.style.CMS)
    fig, axes = plt.subplots(
        len(data),
        1,
        sharex=True,
        sharey=True,
        squeeze=False,
        figsize=(12, 5 * len(data)),
    )
    width = 0.7
    for ax, (name, d) in zip(axes[:, 0], data.items(), strict=True):
        for ib in range(n_b):
            b = int(b_edges[ib])
            points = [
                (ij, *d["bins"][(int(j_edges[ij]), b)])
                for ij in range(n_j)
                if (int(j_edges[ij]), b) in d["bins"]
            ]
            x = [ij + (ib - (n_b - 1) / 2) * width / n_b for ij, _, _ in points]
            errors = [e for _, _, e in points]
            ax.errorbar(
                x,
                [v for _, v, _ in points],
                yerr=None if None in errors else errors,
                fmt="o",
                capsize=3,
                label=_label(b_edges, ib, "b-jets"),
            )
        ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
        ax.set_ylabel("Z normalization factor")
        ax.text(0.02, 0.95, name, transform=ax.transAxes, va="top")
        ax.legend(ncol=n_b, fontsize=14, loc="upper right")
        lo, hi = ax.get_ylim()
        ax.set_ylim(lo, hi + 0.2 * (hi - lo))
    axes[-1, 0].set_xticks(
        range(n_j), [_label(j_edges, i, "jets") for i in range(n_j)]
    )
    mplhep.cms.label(
        ax=axes[0, 0], data=True, com=13.6, lumi=None, text="Work in progress"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / f"{args.name}.{args.format}"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
