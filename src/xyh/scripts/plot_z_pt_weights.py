"""Plot the Z pt correction as a function of pt for each (n_jets, n_bjets).

Reads the correctionlib files written by ``xyh.shape_processor.
derive_z_pt_weights`` and evaluates ``z_pt_correction`` at the pt bin centers
for every jet / b-jet multiplicity bin of the correction. One plot per
multiplicity bin is written, with one curve per input file (campaign). The
normalization factors are listed in the legend.

Usage
-----
    python3 -m xyh.scripts.plot_z_pt_weights \\
        data/output/<tag>/z_pt_weights/*.json --output-dir plots
"""

import argparse
from pathlib import Path

import correctionlib
import matplotlib
import matplotlib.pyplot as plt
import mplhep
import numpy as np
from correctionlib import schemav2

matplotlib.use("Agg")


def _multiplicity_bins(node) -> list[tuple[int, int]]:
    """Lower edges of all (n_jets, n_bjets) bins of the nested binning."""
    bins = []
    for j, child in zip(node.edges[:-1], node.content, strict=True):
        for b in child.edges[:-1]:
            bins.append((int(j), int(b)))
    return bins


def _pt_edges(node) -> np.ndarray:
    return np.array(node.content[0].content[0].edges, dtype=float)


def load(path: Path) -> dict:
    """Evaluate normalization and pt correction for all multiplicity bins."""
    cset = schemav2.CorrectionSet.model_validate_json(path.read_text())
    evaluator = correctionlib.CorrectionSet.from_file(str(path))
    pt_corr = next(c for c in cset.corrections if c.name == "z_pt_correction")
    edges = _pt_edges(pt_corr.data)
    centers = 0.5 * (edges[:-1] + edges[1:])
    result = {}
    for n_jets, n_bjets in _multiplicity_bins(pt_corr.data):
        result[(n_jets, n_bjets)] = (
            float(evaluator["z_normalization"].evaluate(n_jets, n_bjets)),
            np.array(
                [
                    evaluator["z_pt_correction"].evaluate(n_jets, n_bjets, pt)
                    for pt in centers
                ]
            ),
        )
    return {"edges": edges, "bins": result}


def _label(n_jets: int, n_bjets: int, jets_open: bool, bjets_open: bool):
    j = f"$\\geq${n_jets}" if jets_open else f"{n_jets}"
    b = f"$\\geq${n_bjets}" if bjets_open else f"{n_bjets}"
    return f"$n_{{jets}}$ = {j}, $n_{{b-jets}}$ = {b}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--format", default="png")
    parser.add_argument("--log-y", action="store_true")
    args = parser.parse_args()

    data = {p.stem: load(p) for p in args.inputs}
    all_bins = sorted({k for d in data.values() for k in d["bins"]})
    max_jets = max(j for j, _ in all_bins)
    max_bjets = max(b for _, b in all_bins)

    matplotlib.style.use(mplhep.style.CMS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for n_jets, n_bjets in all_bins:
        fig, ax = plt.subplots()
        for name, d in data.items():
            if (n_jets, n_bjets) not in d["bins"]:
                continue
            norm, values = d["bins"][(n_jets, n_bjets)]
            ax.stairs(
                values,
                d["edges"],
                baseline=None,
                label=f"{name} (norm. {norm:.3f})",
            )
        ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
        ax.set_xlabel(r"$p_{T}$ [GeV]")
        ax.set_ylabel("Z $p_{T}$ correction")
        if args.log_y:
            ax.set_yscale("log")
        legend_title = _label(
            n_jets,
            n_bjets,
            n_jets == max_jets,
            n_bjets == max_bjets,
        )
        ax.legend(title=legend_title, fontsize=14, title_fontsize=14)
        mplhep.cms.label(
            ax=ax, data=True, com=13.6, lumi=None, text="Work in progress"
        )
        out = args.output_dir / f"z_pt_correction_{n_jets}j_{n_bjets}b"
        fig.savefig(f"{out}.{args.format}", dpi=150)
        plt.close(fig)
        print(f"Wrote {out}.{args.format}")


if __name__ == "__main__":
    main()
