#!/usr/bin/env python
"""Plot muon scale-factor corrections as a function of pt or eta.

Loads a correctionlib v2 JSON (typically a ``.json.gz`` metadata file) and
plots the scale factor of a chosen correction over one kinematic variable.
Each output plot corresponds to a single bin of the other variable and shows
the scale factor vs that variable (plus any extra variation overlays):

* **SF vs pt**: one plot per eta bin.
* **SF vs eta**: one plot per pt bin.

The fixed bin is encoded in the output filename via :func:`_bin_token` (e.g.
``pt40to60`` or ``etam0p2to0``).

The last pt bin (``[60, inf)`` for ``NUM_TightPFIso_DEN_MediumID``) has no
finite bin center and is therefore skipped. The plotting style follows the
CMS conventions used elsewhere in this repository (mplhep CMS style, CMS label,
step curves with small legends). Only the scale-factor name is drawn as a
title; no data/MC ratio panel is produced.

The script is generic: it discovers the binning structure (variable order,
bin edges, and available ``scale_factors`` keys) from the correction's data
node, so it works for any correction in the file, not just the default.

Usage
-----
    # Default correction, both scans
    python scripts/plot_muon_sf.py --input /path/to/muon_Z.json.gz

    # Only the eta scan
    python scripts/plot_muon_sf.py --only eta --input /path/to/muon_Z.json.gz

    # Draw extra variation keys as thin lines
    python scripts/plot_muon_sf.py --variations nominal,stat \\
        --input /path/to/muon_Z.json.gz

Note
----
    The script has been generated using DeepSeek V4 Flash.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

INPUT_DFT = Path(
    "/cvmfs/cms-griddata.cern.ch/cat/metadata/MUO/"
    "Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15/"
    "2026-06-18/muon_Z.json.gz"
)

DEFAULT_CORRECTION = "NUM_TightPFIso_DEN_MediumID"
DEFAULT_VARIATIONS = ("nominal",)


def _finite_width_edges(edges: list[float]) -> list[tuple[float, float]]:
    """Return ``(lo, hi)`` pairs for all finite-width bins of ``edges``.

    Bins whose edges are not both finite (e.g. a trailing ``[60, inf)`` pt
    bin) cannot be represented by a single point and are skipped.
    """
    return [
        (lo, hi)
        for lo, hi in zip(edges, edges[1:], strict=False)
        if np.isfinite(lo) and np.isfinite(hi)
    ]


def load_correction(input_file: Path) -> tuple:
    """Load the correction set from a correctionlib JSON.gz file.

    Returns
    -------
    tuple
        ``(schema_set, evaluator_set)`` where ``schema_set`` is the parsed
        ``schemav2.CorrectionSet`` (for introspecting binning structure) and
        ``evaluator_set`` is the highlevel evaluator (for evaluating weights).
    """
    try:
        from correctionlib import schemav2
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise ImportError(
            "correctionlib is required. Install it in the active "
            "environment (e.g. `pixi install`)."
        ) from exc

    with gzip.open(input_file) as handle:
        raw = json.load(handle)
    schema_set = schemav2.CorrectionSet.model_validate(raw)
    return schema_set, schema_set.to_evaluator()


def _correction_from_schema(schema_set: object, name: str) -> object:
    """Return the schemav2 correction model by name."""
    for correction in schema_set.corrections:
        if correction.name == name:
            return correction
    raise KeyError(name)


def inspect_binning(schema_correction: object) -> tuple:
    """Discover the binning structure of a correction.

    Returns
    -------
    tuple
        (binning_variables, edges, cat_keys)

    where ``binning_variables`` is the ordered list of binned variables,
    ``edges`` maps each binned variable to its edge values, and ``cat_keys``
    is the set of valid ``scale_factors`` keys.
    """
    data = schema_correction.data.model_dump()

    binning_variables = []
    edges: dict[str, list[float]] = {}

    current = data
    while current.get("nodetype") == "binning":
        variable = current["input"]
        binning_variables.append(variable)
        edges[variable] = [float(value) for value in current["edges"]]
        content = current.get("content", [])
        # descend into the first child; once it is no longer a binning node
        # (category or value), the binning part is exhausted
        current = content[0] if content else {}

    cat_keys: set[str] = set()
    if current.get("nodetype") == "category":
        cat_keys = {entry["key"] for entry in current.get("content", [])}

    return binning_variables, edges, cat_keys


def _bin_center(bin_edges: tuple[float, float]) -> float:
    """Return the center of a finite-width bin."""
    return 0.5 * (bin_edges[0] + bin_edges[1])


def evaluate_family(
    correction: object,
    binning_variables: list,
    edges: dict,
    varying_var: str,
    family_var: str,
    variations: tuple[str, ...],
) -> list[dict]:
    """Evaluate the correction over ``varying_var`` for every bin of ``family_var``.

    Returns
    -------
    list[dict]
        One dict per finite-width bin of ``family_var`` with keys ``lo``,
        ``hi`` (the family-bin bounds), ``x`` (varying-bin centers) and
        ``values`` (mapping variation -> list of scale factors).
    """
    family_bins = _finite_width_edges(edges[family_var])
    varying_bins = _finite_width_edges(edges[varying_var])
    varying_centers = [_bin_center(b) for b in varying_bins]

    curves = []
    for lo, hi in family_bins:
        fixed_point = 0.5 * (lo + hi)
        values: dict[str, list[float]] = {
            variation: [] for variation in variations
        }
        for x_center in varying_centers:
            coord = {varying_var: x_center, family_var: fixed_point}
            for variation in variations:
                args = [coord[v] for v in binning_variables] + [variation]
                values[variation].append(float(correction.evaluate(*args)))
        curves.append(
            {"lo": lo, "hi": hi, "x": varying_centers, "values": values}
        )
    return curves


def _bin_token(lo: float, hi: float, variable: str) -> str:
    """Return a filename-safe token identifying a bin edge range.

    Examples
    --------
    pt [40, 60)          -> ``pt40to60``
    eta [-0.2, 0)         -> ``etam0p2to0``
    eta [0, 0.2)          -> ``eta0to0p2``
    """
    prefix = {"pt": "pt", "eta": "eta"}[variable]

    def fmt_edge(value: float) -> str:
        text = f"{value:g}"
        if variable == "eta":
            text = text.replace("-", "m").replace(".", "p")
        return text

    return f"{prefix}{fmt_edge(lo)}to{fmt_edge(hi)}"


def _format_bin_note(
    lo: float, hi: float, family_var: str, varying_var: str
) -> str:
    """Return a short note describing the fixed bin shown in the plot."""
    symbol = {"pt": r"$p_T$", "eta": r"$\eta$"}
    if family_var == "pt":
        bin_range = f"{lo:g} \u2013 {hi:g} GeV"
    else:
        bin_range = rf"$[{lo:+.2g},\ {hi:+.2g})$"
    return f"{symbol[family_var]} bin {bin_range}, SF vs {symbol[varying_var]}"


def _plot_family(
    fig,
    ax,
    curves: list[dict],
    xlabel: str,
    ylabel: str,
    variations: tuple[str, ...],
    correction_name: str,
    bin_note: str,
) -> None:
    """Draw the single family curve in the repo CMS style.

    The nominal correction is drawn in the campaign-comparison blue; any
    extra variations are drawn as thin gray dotted overlays. The scale-factor
    name and a note describing the fixed bin are placed as stacked labels
    directly below the legend box.
    """
    fixed_color = "#1f77b4"
    nominal_idx = variations.index("nominal") if "nominal" in variations else 0
    nominal = variations[nominal_idx]

    for curve in curves:
        x = np.asarray(curve["x"])
        y = np.asarray(curve["values"][nominal])
        ax.step(x, y, where="mid", color=fixed_color, lw=2)

    # draw any extra variations as thin dotted overlays on the first curve
    x0 = np.asarray(curves[0]["x"])
    for variation in variations:
        if variation == nominal:
            continue
        y = np.asarray(curves[0]["values"][variation])
        ax.step(
            x0,
            y,
            where="mid",
            color="gray",
            lw=1,
            ls=":",
            alpha=0.8,
            label=variation,
        )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)

    # only extra variations get legend entries so the box stays small
    handles, labels = ax.get_legend_handles_labels()

    # place the correction name (and bin note) below the optional legend box
    fig.canvas.draw()
    top_y = 0.98
    if handles:
        legend = ax.legend(
            handles,
            labels,
            fontsize="small",
            loc="upper left",
            ncols=1,
        )
        fig.canvas.draw()
        legend_bbox = legend.get_window_extent()
        legend_bottom = ax.transAxes.inverted().transform(
            (legend_bbox.x0, legend_bbox.y0)
        )[1]
        top_y = legend_bottom - 0.02

    ax.text(
        0.02,
        top_y,
        correction_name,
        fontsize="x-small",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax.transAxes,
    )

    # place the bin note directly below the correction name
    ax.text(
        0.02,
        top_y - 0.03,
        bin_note,
        fontsize="x-small",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax.transAxes,
    )


def _finalize_plot(
    fig,
    ax,
    outdir: Path,
    correction_name: str,
    varying_var: str,
    bin_token: str,
) -> Path:
    """Apply the CMS label, save the figure, and return its output path."""
    import mplhep

    mplhep.cms.label(
        ax=ax,
        text="Work in progress",
        com=None,
        lumi=None,
        year=None,
        fontsize=20,
    )

    out_name = outdir / (f"{correction_name}_vs_{varying_var}_{bin_token}.png")
    fig.tight_layout()
    fig.savefig(out_name, dpi=150)
    return out_name


def _write_chunked_plots(
    args,
    plt,
    curves: list[dict],
    varying_var: str,
    family_var: str,
    xlabel: str,
    variations: tuple[str, ...],
) -> list[Path]:
    """Write one PNG per family bin, naming each file by its bin range.

    Each output plot shows the scale factor vs ``varying_var`` for a single
    bin of ``family_var`` (plus any extra variation overlays). The family bin
    is encoded in the filename via :func:`_bin_token` (e.g. ``pt40to60`` or
    ``etam0p2to0``).
    """
    written = []
    for curve in curves:
        fig, ax = plt.subplots()
        bin_token = _bin_token(curve["lo"], curve["hi"], family_var)
        bin_note = _format_bin_note(
            curve["lo"], curve["hi"], family_var, varying_var
        )
        _plot_family(
            fig,
            ax,
            [curve],
            xlabel=xlabel,
            ylabel="Scale factor",
            variations=variations,
            correction_name=args.correction,
            bin_note=bin_note,
        )
        out_name = _finalize_plot(
            fig,
            ax,
            args.outdir,
            args.correction,
            varying_var,
            bin_token,
        )
        plt.close(fig)
        written.append(out_name)
    return written


def main() -> None:
    import matplotlib
    import matplotlib.pyplot as plt
    import mplhep

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=INPUT_DFT,
        help="Path to the correctionlib .json.gz file",
    )
    parser.add_argument(
        "--correction",
        "-c",
        default=DEFAULT_CORRECTION,
        help="Name of the correction to plot",
    )
    parser.add_argument(
        "--only",
        choices=("pt", "eta"),
        default=None,
        help="Plot only the pt or eta scan (default: both)",
    )
    parser.add_argument(
        "--variations",
        type=str,
        default=",".join(DEFAULT_VARIATIONS),
        help="Comma-separated scale_factors keys to draw",
    )
    parser.add_argument(
        "--outdir",
        "-o",
        type=Path,
        default=Path("sf_plots"),
        help="Directory to write the PNG plots into",
    )
    args = parser.parse_args()

    # CMS style used across the repository
    matplotlib.style.use(mplhep.style.CMS)

    schema_set, evaluator_set = load_correction(args.input)
    try:
        evaluator_correction = evaluator_set[args.correction]
    except KeyError as exc:
        names = sorted(evaluator_set.keys())
        raise SystemExit(
            f"Correction {args.correction!r} not found. Available: {names}"
        ) from exc
    schema_correction = _correction_from_schema(schema_set, args.correction)

    binning_variables, edges, cat_keys = inspect_binning(schema_correction)

    requested = tuple(
        v.strip() for v in args.variations.split(",") if v.strip()
    )
    unknown = [v for v in requested if v not in cat_keys]
    if unknown:
        print(
            f"warning: unknown variations {unknown}; available: {sorted(cat_keys)}"
        )
    variations = tuple(v for v in requested if v in cat_keys) or (
        "nominal" if "nominal" in cat_keys else DEFAULT_VARIATIONS
    )

    args.outdir.mkdir(parents=True, exist_ok=True)

    if "pt" not in binning_variables or "eta" not in binning_variables:
        raise SystemExit(
            f"Correction {args.correction!r} does not bin over eta and pt; "
            f"found variables: {binning_variables}"
        )

    made = []
    # ---- pt scan: x = pt, one eta bin per plot ----
    if args.only in (None, "pt"):
        curves_pt = evaluate_family(
            evaluator_correction,
            binning_variables,
            edges,
            varying_var="pt",
            family_var="eta",
            variations=variations,
        )
        made.extend(
            _write_chunked_plots(
                args,
                plt,
                curves=curves_pt,
                varying_var="pt",
                family_var="eta",
                xlabel=r"$p_T$ [GeV]",
                variations=variations,
            )
        )

    # ---- eta scan: x = eta, one pt bin per plot ----
    if args.only in (None, "eta"):
        curves_eta = evaluate_family(
            evaluator_correction,
            binning_variables,
            edges,
            varying_var="eta",
            family_var="pt",
            variations=variations,
        )
        made.extend(
            _write_chunked_plots(
                args,
                plt,
                curves=curves_eta,
                varying_var="eta",
                family_var="pt",
                xlabel=r"$\eta$",
                variations=variations,
            )
        )

    for path in made:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
