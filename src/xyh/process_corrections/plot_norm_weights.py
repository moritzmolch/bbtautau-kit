"""Plots of normalization weights.

Reads the correctionlib files written by ``xyh.process_corrections.
derive_norm_weights`` (``<process_tag>_norm_<campaign>.json``, one per
campaign) and writes one plot per era:

* ``<name>_<era>``: one plot per input (era/campaign) with the nominal
  normalization in every (n_jets, n_bjets) bin as 2D plot. The values are
  printed in the bins together with the statistical uncertainty and the
  normalization uncertainty of the subtracted processes. Bins without a
  stored value stay empty.

The correction is found by its name ``<process_tag>_normalization``.

Usage
-----
Hydra stage with the config of the corresponding derivation, which selects
the campaigns and the input directory:

    python3 -m xyh.process_corrections.plot_norm_weights \\
        --config-name plot_norm_weights_tt
"""

import logging
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import mplhep
import numpy as np
from correctionlib import schemav2
from matplotlib.colors import TwoSlopeNorm
from omegaconf import DictConfig

from xyh.core.cli import hydra_cli

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
            f"{sorted(corrections)}"
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


def _shift(variations: dict[str, dict], name: str, key) -> float | None:
    """Up shift `name` of a bin relative to nominal, `None` if not stored."""
    if f"{name}_up" not in variations:
        return None
    return variations[f"{name}_up"][key] - variations["nominal"][key]


def plot_jets_bjets(
    d: dict, era: str, j_edges, b_edges, ylabel: str, out: Path
) -> None:
    """Normalization per (n_jets, n_bjets) of one era as 2D plot.

    Every bin shows the nominal value and, if stored, the statistical and
    the other-process normalization uncertainty.
    """
    n_j, n_b = len(j_edges) - 1, len(b_edges) - 1
    variations = d["variations"]
    nominal = variations["nominal"]
    grid = np.full((n_b, n_j), np.nan)
    keys = {}
    for ij in range(n_j):
        for ib in range(n_b):
            key = (int(j_edges[ij]), int(b_edges[ib]))
            if key in nominal:
                grid[ib, ij] = nominal[key]
                keys[(ib, ij)] = key
    norm = TwoSlopeNorm(
        vcenter=1.0,
        vmin=min(np.nanmin(grid), 0.99),
        vmax=max(np.nanmax(grid), 1.01),
    )

    fig, ax = plt.subplots(
        figsize=(1.9 * n_j + 3, 1.6 * n_b + 3), layout="constrained"
    )
    image = ax.imshow(
        np.ma.masked_invalid(grid),
        origin="lower",
        cmap="RdBu_r",
        norm=norm,
        aspect="auto",
    )
    for (ib, ij), key in keys.items():
        lines = [f"{grid[ib, ij]:.3f}"]
        for name, label in (("stat", "stat"), ("norm_other", "other")):
            shift = _shift(variations, name, key)
            if shift is not None:
                lines.append(f"$\\pm${abs(shift):.3f} ({label})")
        # White text on dark cells
        r, g, b, _ = image.cmap(norm(grid[ib, ij]))
        dark = 0.299 * r + 0.587 * g + 0.114 * b < 0.45
        ax.text(
            ij,
            ib,
            "\n".join(lines),
            ha="center",
            va="center",
            fontsize=13,
            color="white" if dark else "black",
        )
    ax.set_xticks(range(n_j), [_label(j_edges, i) for i in range(n_j)])
    ax.set_yticks(range(n_b), [_label(b_edges, i) for i in range(n_b)])
    ax.set_xlabel("Number of jets")
    ax.set_ylabel("Number of b-jets")
    ax.set_title(era, fontsize=16, pad=40)
    ax.tick_params(which="minor", length=0)
    fig.colorbar(image, ax=ax, label=ylabel)
    mplhep.cms.label(
        ax=ax, data=True, com=13.6, lumi=None, text="Work in progress"
    )
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Wrote {out}")


def plot_norm_weights(
    inputs: dict[str, Path],
    output_dir: Path,
    name: str,
    label: str,
    file_format: str = "png",
    correction: str | None = None,
) -> None:
    """Write one plot per input, keyed by its era (campaign).

    The plots are written to ``output_dir/<name>_<era>.<file_format>``.
    """
    data = {era: load(path, correction) for era, path in inputs.items()}
    first = next(iter(data.values()))
    j_edges, b_edges = first["j_edges"], first["b_edges"]
    if any(
        d["j_edges"] != j_edges or d["b_edges"] != b_edges
        for d in data.values()
    ):
        raise ValueError("The inputs have different multiplicity bins")

    matplotlib.style.use(mplhep.style.CMS)
    output_dir.mkdir(parents=True, exist_ok=True)
    for era, d in data.items():
        plot_jets_bjets(
            d,
            era,
            j_edges,
            b_edges,
            f"{label} normalization factor",
            output_dir / f"{name}_{era}.{file_format}",
        )


@hydra_cli("plot_norm_weights")
def main(cfg: DictConfig):
    process_tag = cfg["process_tag"]
    output_dir = Path(cfg["output_dir"])
    plot_norm_weights(
        {
            campaign: output_dir / f"{process_tag}_norm_{campaign}.json"
            for campaign in cfg["inventory"]["campaigns"]
        },
        Path(cfg["plots_dir"]),
        name=f"{process_tag}_normalization",
        label=process_tag,
        file_format=cfg["plot_format"],
    )


if __name__ == "__main__":
    main()
