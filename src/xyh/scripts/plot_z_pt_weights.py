"""Plot the Z pt correction as a function of pt, one figure per campaign.

Reads the correctionlib files written by ``xyh.process_corrections.
derive_z_pt_weights`` (one file per campaign) and draws one panel per jet
multiplicity bin of the correction ``z_pt`` (n_jets = 0, 1, 2, >= 3). Each
panel shows

- the binned correction ``z_pt_binned`` with its statistical uncertainty as
  points with error bars (if present in the file),
- the smoothed correction ``z_pt`` as a line,
- the envelopes of its uncertainty sources (statistical, kernel bandwidth,
  normalization of the subtracted backgrounds; variations ``<source>_up`` and
  ``<source>_down``) as lines,
- the total uncertainty, the quadratic sum of the upward and downward
  deviations of all sources, as a filled band.

With ``--bw-scan-dir`` the bandwidth scans written by the derivation (one
JSON file per campaign) are plotted as well: per campaign one panel per
category with chi2/ndf as a function of the bandwidth, the maximum accepted
chi2/ndf and the chosen bandwidth.

The normalization factors are shown by ``plot_z_normalization``.

Usage
-----
    python3 -m xyh.scripts.plot_z_pt_weights \\
        data/output/<tag>/z_pt_weights/*.json --output-dir plots \\
        [--bw-scan-dir data/output/<tag>/z_pt_weights/bw_scan]
"""

import argparse
import json
from pathlib import Path

import correctionlib
import matplotlib
import matplotlib.pyplot as plt
import mplhep
import numpy as np
from correctionlib import schemav2

matplotlib.use("Agg")

# Labels and colors of the uncertainty sources, keyed by the variation prefix
_SOURCES = {
    "stat": ("Stat.", "#3f90da"),
    "bw": ("Bandwidth", "#ffa90e"),
    "norm_other": ("Bkg. norm.", "#bd1f01"),
}


def _leaf_binnings(node) -> dict[int, object]:
    """The pt binning of each n_jets bin of the binning."""
    return {
        int(j): leaf
        for j, leaf in zip(node.edges[:-1], node.content, strict=True)
    }


def _binned(evaluator, n_jets: int, leaf) -> dict:
    """The binned correction and its error at the bin centers of `leaf`."""
    edges = np.array(leaf.edges, dtype=float)
    centers = 0.5 * (edges[:-1] + edges[1:])
    corr = evaluator["z_pt_binned"]
    up = corr.evaluate(n_jets, centers, "stat_up")
    down = corr.evaluate(n_jets, centers, "stat_down")
    return {
        "centers": centers,
        "values": corr.evaluate(n_jets, centers, "nominal"),
        "errors": 0.5 * np.abs(up - down),
    }


def load(path: Path) -> dict:
    """Evaluate the pt correction for all jet multiplicity bins.

    The correction ``z_pt`` is evaluated at the pt bin centers of each
    variation. ``shifts`` maps the variation names (e.g. ``stat_up``) to the
    shifted corrections. If the correction ``z_pt_binned`` is present,
    ``binned`` holds its values and statistical uncertainties (half
    difference of ``stat_up`` and ``stat_down``) at its own bin centers,
    otherwise `None`.
    """
    # Load the correction set for the structure and the evaluator
    cset = schemav2.CorrectionSet.model_validate_json(path.read_text())
    evaluator = correctionlib.CorrectionSet.from_file(str(path))
    names = {c.name for c in cset.corrections}
    corr = next(c for c in cset.corrections if c.name == "z_pt")
    variations = [item.key for item in corr.data.content]
    nominal_node = next(
        item.value for item in corr.data.content if item.key == "nominal"
    )

    # Binning of the binned correction, if present
    binned_leaves = None
    if "z_pt_binned" in names:
        corr_binned = next(
            c for c in cset.corrections if c.name == "z_pt_binned"
        )
        binned_leaves = _leaf_binnings(
            next(
                item.value
                for item in corr_binned.data.content
                if item.key == "nominal"
            )
        )

    # Evaluate all variations per jet multiplicity
    result = {}
    for n_jets, leaf in _leaf_binnings(nominal_node).items():
        edges = np.array(leaf.edges, dtype=float)
        centers = 0.5 * (edges[:-1] + edges[1:])
        values = {
            v: evaluator["z_pt"].evaluate(n_jets, centers, v)
            for v in variations
        }
        result[n_jets] = {
            "x": centers,
            "values": values.pop("nominal"),
            "shifts": values,
            "binned": _binned(evaluator, n_jets, binned_leaves[n_jets])
            if binned_leaves is not None
            else None,
        }
    return result


def _total_uncertainty(
    nominal: np.ndarray,
    shifts: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """
    Downward and upward total uncertainty: per source, the largest downward
    and upward deviations of its variations from the nominal, added in
    quadrature over the sources.
    """
    down = np.zeros_like(nominal)
    up = np.zeros_like(nominal)
    for source in _sources(shifts):
        deviations = np.stack(
            [
                shifts[f"{source}_up"] - nominal,
                shifts[f"{source}_down"] - nominal,
            ]
        )
        up += np.maximum(deviations.max(axis=0), 0.0) ** 2
        down += np.minimum(deviations.min(axis=0), 0.0) ** 2
    return np.sqrt(down), np.sqrt(up)


def _sources(shifts: dict[str, np.ndarray]) -> list[str]:
    """Uncertainty sources with both an up and a down variation."""
    sources = []
    for name in shifts:
        if name.endswith("_up") and f"{name[:-3]}_down" in shifts:
            sources.append(name[:-3])
    return sources


def _plot_panel(ax, h: dict, label: str):
    """Draw the correction of one jet multiplicity bin into `ax`."""
    x, nominal, shifts = h["x"], h["values"], h["shifts"]

    # Total uncertainty as filled band
    down, up = _total_uncertainty(nominal, shifts)
    ax.fill_between(
        x,
        nominal - down,
        nominal + up,
        color="#94a4a2",
        alpha=0.4,
        linewidth=0,
        label="Total unc.",
    )

    # Envelopes of the individual sources as lines
    for source in _sources(shifts):
        name, color = _SOURCES.get(source, (source, None))
        line = ax.plot(
            x, shifts[f"{source}_up"], color=color, linewidth=1, label=name
        )[0]
        ax.plot(
            x,
            shifts[f"{source}_down"],
            color=line.get_color(),
            linewidth=1,
            linestyle="--",
        )

    # Smoothed nominal correction
    ax.plot(x, nominal, color="black", linewidth=1.5, label="Smoothed")

    # Binned correction with stat. uncertainty
    binned = h["binned"]
    if binned is not None:
        ax.errorbar(
            binned["centers"],
            binned["values"],
            yerr=binned["errors"],
            fmt="o",
            markersize=3,
            linewidth=1,
            color="black",
            label="Binned",
        )

    # Axis range: grid of the smoothed correction, total band and binned
    # points within it
    ax.set_xlim(x[0], x[-1])
    lo = (nominal - down).min()
    hi = (nominal + up).max()
    if binned is not None:
        in_range = binned["centers"] <= x[-1]
        lo = min(lo, (binned["values"] - binned["errors"])[in_range].min())
        hi = max(hi, (binned["values"] + binned["errors"])[in_range].max())
    margin = 0.1 * (hi - lo)
    ax.set_ylim(lo - margin, hi + 2 * margin)

    ax.axhline(1.0, color="gray", linestyle=":", linewidth=1)
    ax.text(
        0.97,
        0.95,
        label,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=18,
    )
    ax.set_xlabel(r"$p_{T}^{\mu\mu}$ [GeV]")
    ax.set_ylabel("Z $p_{T}$ correction")


def _label(n_jets: int, jets_open: bool):
    j = f"$\\geq${n_jets}" if jets_open else f"{n_jets}"
    return f"$n_{{jets}}$ = {j}"


def _plot_bw_scan_panel(ax, scan: dict, label: str):
    """Draw chi2/ndf as a function of the bandwidth into `ax`."""
    bw = np.array(scan["bw"], dtype=float)
    chi2_ndf = np.array(
        [np.nan if v is None else v for v in scan["chi2_ndf"]], dtype=float
    )

    # chi2/ndf of the scan (undefined values are not drawn)
    ax.plot(
        bw,
        chi2_ndf,
        marker="o",
        markersize=3,
        linewidth=1,
        color="black",
        label=r"$\chi^{2}$/ndf",
    )

    # Accepted maximum and chosen bandwidth
    ax.axhline(
        scan["chi2_ndf_max"],
        color="#bd1f01",
        linestyle="--",
        linewidth=1,
        label=r"Max. $\chi^{2}$/ndf",
    )
    ax.axvline(
        scan["chosen"],
        color="#3f90da",
        linestyle="-",
        linewidth=1.5,
        label=f"Chosen: {scan['chosen']:.3g} GeV",
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.text(
        0.97,
        0.05,
        label,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=18,
    )
    ax.set_xlabel("Bandwidth [GeV]")
    ax.set_ylabel(r"$\chi^{2}$/ndf")
    ax.legend(loc="upper left", fontsize=14)


def _plot_bw_scans(path: Path, output_dir: Path, fmt: str):
    """One figure with a panel per category for the scan file `path`."""
    scans = json.loads(path.read_text())
    categories = list(scans)
    n_cols = 2
    n_rows = -(-len(categories) // n_cols)
    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(10 * n_cols, 9 * n_rows),
        squeeze=False,
    )
    for ax, category in zip(axes.flat, categories, strict=False):
        _plot_bw_scan_panel(ax, scans[category], category)
    for ax in axes.flat[len(categories) :]:
        ax.set_visible(False)

    # Labels
    campaign = path.stem.split("_pt_bw_scan_", 1)[-1]
    mplhep.cms.label(
        ax=axes[0][0],
        data=True,
        com=13.6,
        lumi=None,
        text="Work in progress",
    )
    axes[0][-1].set_title(campaign, loc="right", fontsize=20)

    fig.tight_layout()
    out = output_dir / f"bw_scan_{campaign}.{fmt}"
    fig.savefig(out, dpi=100)
    plt.close(fig)
    print(f"Wrote {out}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--format", default="png")
    parser.add_argument(
        "--bw-scan-dir",
        type=Path,
        default=None,
        help="Directory with the bandwidth scan files, one plot per file",
    )
    args = parser.parse_args()

    matplotlib.style.use(mplhep.style.CMS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path in args.inputs:
        # One figure per campaign with one panel per jet multiplicity
        data = load(path)
        n_jets_bins = sorted(data)
        n_cols = 2
        n_rows = -(-len(n_jets_bins) // n_cols)
        fig, axes = plt.subplots(
            n_rows,
            n_cols,
            figsize=(10 * n_cols, 9 * n_rows),
            squeeze=False,
        )
        for ax, n_jets in zip(axes.flat, n_jets_bins, strict=False):
            _plot_panel(
                ax,
                data[n_jets],
                _label(n_jets, n_jets == n_jets_bins[-1]),
            )
        for ax in axes.flat[len(n_jets_bins) :]:
            ax.set_visible(False)

        # Labels and legend
        campaign = path.stem.removeprefix("z_pt_")
        mplhep.cms.label(
            ax=axes[0][0],
            data=True,
            com=13.6,
            lumi=None,
            text="Work in progress",
        )
        axes[0][-1].set_title(campaign, loc="right", fontsize=20)
        axes[0][0].legend(loc="upper left", fontsize=14, ncols=2)

        fig.tight_layout()
        out = args.output_dir / f"z_pt_correction_{campaign}.{args.format}"
        fig.savefig(out, dpi=100)
        plt.close(fig)
        print(f"Wrote {out}")

    # Bandwidth scans
    if args.bw_scan_dir is not None:
        scan_files = sorted(args.bw_scan_dir.glob("*_pt_bw_scan_*.json"))
        if not scan_files:
            raise FileNotFoundError(
                f"No bandwidth scan files in {args.bw_scan_dir}"
            )
        for path in scan_files:
            _plot_bw_scans(path, args.output_dir, args.format)


if __name__ == "__main__":
    main()
