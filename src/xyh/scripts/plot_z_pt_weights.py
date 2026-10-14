"""Plot the Z pt correction as a function of pt for each (n_jets, n_bjets).

Reads the correctionlib files written by ``xyh.shape_processor.
derive_z_pt_weights`` and evaluates ``z_pt_correction`` at the pt bin centers
for every jet / b-jet multiplicity bin of the correction. One plot per
multiplicity bin is written, with one curve per input file (campaign). The
normalization factors are listed in the legend. The shaded band is the
statistical uncertainty of the bin contents, if stored in the file. It is
uncorrelated between pt bins (neighboring points are correlated if the
correction is smoothed) and does not include the normalization uncertainty.

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


def _leaf_binnings(node) -> dict[tuple[int, int], object]:
    """The pt binning of each (n_jets, n_bjets) bin of the nested binning."""
    leaves = {}
    for j, child in zip(node.edges[:-1], node.content, strict=True):
        for b, leaf in zip(child.edges[:-1], child.content, strict=True):
            leaves[(int(j), int(b))] = leaf
    return leaves


def _evaluate(evaluator, name, n_jets, n_bjets, centers) -> np.ndarray:
    return np.array(
        [evaluator[name].evaluate(n_jets, n_bjets, pt) for pt in centers]
    )


def load(path: Path) -> dict:
    """Evaluate normalization and pt correction for all multiplicity bins.

    The pt binning differs between the multiplicity bins. The statistical
    uncertainty is `None` if the file does not contain it.
    """
    cset = schemav2.CorrectionSet.model_validate_json(path.read_text())
    evaluator = correctionlib.CorrectionSet.from_file(str(path))
    pt_corr = next(c for c in cset.corrections if c.name == "z_pt_correction")
    has_norm_unc = any(
        c.name == "z_normalization_stat_unc" for c in cset.corrections
    )
    has_unc = any(
        c.name == "z_pt_correction_stat_unc" for c in cset.corrections
    )
    result = {}
    for (n_jets, n_bjets), leaf in _leaf_binnings(pt_corr.data).items():
        edges = np.array(leaf.edges, dtype=float)
        centers = 0.5 * (edges[:-1] + edges[1:])

        norm_unc = (
            float(
                evaluator["z_normalization_stat_unc"].evaluate(n_jets, n_bjets)
            )
            if has_norm_unc
            else None
        )
        result[(n_jets, n_bjets)] = {
            "norm_unc": norm_unc,
            "edges": edges,
            "norm": float(
                evaluator["z_normalization"].evaluate(n_jets, n_bjets)
            ),
            "values": _evaluate(
                evaluator, "z_pt_correction", n_jets, n_bjets, centers
            ),
            "errors": _evaluate(
                evaluator, "z_pt_correction_stat_unc", n_jets, n_bjets, centers
            )
            if has_unc
            else None,
        }
    return result


def _legend_label(name: str, h: dict) -> str:
    text = f"{name} (norm. {h['norm']:.3f}"
    if h["norm_unc"] is not None:
        text += f" $\\pm$ {h['norm_unc']:.3f}"
    return text + ")"


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
    all_bins = sorted({k for d in data.values() for k in d})
    max_jets = max(j for j, _ in all_bins)
    max_bjets = max(b for _, b in all_bins)

    matplotlib.style.use(mplhep.style.CMS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for n_jets, n_bjets in all_bins:
        fig, ax = plt.subplots()
        for name, d in data.items():
            if (n_jets, n_bjets) not in d:
                continue
            h = d[(n_jets, n_bjets)]
            step = ax.stairs(
                h["values"],
                h["edges"],
                baseline=None,
                label=_legend_label(name, h),
            )
            if h["errors"] is not None:
                ax.stairs(
                    h["values"] + h["errors"],
                    h["edges"],
                    baseline=h["values"] - h["errors"],
                    fill=True,
                    alpha=0.3,
                    color=step.get_edgecolor(),
                    linewidth=0,
                )
        # Make sure the uncertainty bands are fully visible
        lo, hi = ax.get_ylim()
        for d in data.values():
            h = d.get((n_jets, n_bjets))
            if h is not None and h["errors"] is not None:
                margin = 0.05 * (hi - lo)
                lo = min(lo, (h["values"] - h["errors"]).min() - margin)
                hi = max(hi, (h["values"] + h["errors"]).max() + margin)
        if not args.log_y:
            ax.set_ylim(lo, hi)
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
