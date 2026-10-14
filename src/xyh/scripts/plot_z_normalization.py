"""Summary plot of the Z normalization factors per jet multiplicity.

Reads the correctionlib files written by ``xyh.shape_processor.
derive_z_pt_weights`` and plots ``z_normalization`` for every jet multiplicity
bin, with one set of markers per input file (campaign). The error bars are the
statistical uncertainty ``z_normalization_stat_unc``, if stored in the file.

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

matplotlib.use("Agg")


def _bin_labels(edges: list[float]) -> list[str]:
    """Labels of the jet multiplicity bins, the last one is open-ended."""
    labels = []
    for i, low in enumerate(edges[:-1]):
        last = i == len(edges) - 2
        labels.append(f"$\\geq${int(low)}" if last else f"{int(low)}")
    return labels


def load(path: Path) -> dict:
    """Normalizations and uncertainties (`None` if not stored) per jet bin."""
    cset = schemav2.CorrectionSet.model_validate_json(path.read_text())
    corrections = {c.name: c for c in cset.corrections}
    norm = corrections["z_normalization"].data
    unc = corrections.get("z_normalization_stat_unc")
    return {
        "edges": [float(e) for e in norm.edges],
        "values": np.array(norm.content, dtype=float),
        "errors": None
        if unc is None
        else np.array(unc.data.content, dtype=float),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--name", default="z_normalization")
    parser.add_argument("--format", default="png")
    args = parser.parse_args()

    data = {p.stem: load(p) for p in args.inputs}
    edges = next(iter(data.values()))["edges"]
    if any(d["edges"] != edges for d in data.values()):
        raise ValueError("The inputs have different jet multiplicity bins")
    x = np.arange(len(edges) - 1)

    matplotlib.style.use(mplhep.style.CMS)
    fig, ax = plt.subplots()
    width = 0.6
    for i, (name, d) in enumerate(data.items()):
        offset = (i - (len(data) - 1) / 2) * width / len(data)
        ax.errorbar(
            x + offset,
            d["values"],
            yerr=d["errors"],
            fmt="o",
            capsize=3,
            label=name,
        )
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax.set_xticks(x, _bin_labels(edges))
    ax.set_xlim(-0.6, len(x) - 0.4)
    ax.set_xlabel("Number of jets")
    ax.set_ylabel("Z normalization factor")
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.25 * (hi - lo))
    ax.legend(fontsize=14)
    mplhep.cms.label(
        ax=ax, data=True, com=13.6, lumi=None, text="Work in progress"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / f"{args.name}.{args.format}"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
