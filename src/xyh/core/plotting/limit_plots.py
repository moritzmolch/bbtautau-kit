from __future__ import annotations

import logging
from itertools import product
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import mplhep
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

mpl.style.use(mplhep.style.CMS)


run2_my150_y2b_h2tau_limits = [
    (280, 0.083398),
    (320, 0.10547),
    (360, 0.063086),
    (400, 0.015857),
    (450, 0.016357),
    (500, 0.010229),
    (550, 0.007959),
    (600, 0.0061401),
    (700, 0.004187),
    (800, 0.003186),
    (900, 0.0028625),
    (1000, 0.0029175),
    (1200, 0.0038086),
    (1400, 0.0054199),
    (1600, 0.007666),
    (1800, 0.011328),
    (2000, 0.01582),
    (2500, 0.03623),
    (3000, 0.075977),
]

# from configuration.xyh_bbtautau.metadata.analysis import analysis
# from src.bbtautau.process_sets import load_process_set

logging.basicConfig(level=logging.INFO)

LIMIT_NAME = "statonly"
CHANNEL = "all"
DECAY_MODE = "y2b_h2tau"
LIMITS_FILE = Path(
    "/work/mmolch/xyh-bbtautau-crown/bbtautau-kit/data/output/fit/shapes-2026-11-07/all_all/asimov_bkg/limits.csv"
)
OUTPUT_DIR = Path(
    "/work/mmolch/xyh-bbtautau-crown/bbtautau-kit/data/output/fit/shapes-2026-11-07/all_all/asimov_bkg/plots"
)


def load_limits(limits_file: Path):
    df = pd.read_csv(limits_file, delimiter=",", header=0)
    return df


def _plot_limit_1d(
    ax,
    x,
    exp_m2,
    exp_m1,
    exp,
    exp_p1,
    exp_p2,
):
    sigma1_color = "#228b22"
    sigma2_color = "#ffcc00"

    # Plot expected limit lines
    ax.plot(
        x,
        exp,
        color="black",
        marker="o",
        label="Median expected",
        zorder=10,
    )
    ax.fill_between(
        x,
        exp_m1,
        exp_p1,
        color=sigma1_color,
        label="68% expected",
        zorder=5,
    )
    ax.fill_between(
        x,
        exp_m2,
        exp_p2,
        color=sigma2_color,
        label="95% expected",
        zorder=-5,
    )


def _plot_limit_2d(
    fig,
    ax,
    x,
    y,
    exp,
):
    # Get unique values for x and y and x -> x_u (y -> y_u) index mapping
    x_u, y_u = np.unique(x), np.unique(y)
    x_i, y_i = np.searchsorted(x_u, x), np.searchsorted(y_u, y)
    ex_u = (x_u[1:] + x_u[:-1]) / 2
    ey_u = (y_u[1:] + y_u[:-1]) / 2
    ex_u = np.concatenate(
        (
            [2 * x_u[0] - ex_u[0]],
            ex_u,
            [2 * x_u[-1] - ex_u[-1]],
        )
    )
    ey_u = np.concatenate(
        (
            [2 * y_u[0] - ey_u[0]],
            ey_u,
            [2 * y_u[-1] - ey_u[-1]],
        )
    )

    # Create the meshgrid
    x_mesh, y_mesh = np.meshgrid(ex_u, ey_u)
    z_mesh = np.full((x_u.shape[0], y_u.shape[0]), np.nan)
    z_mesh[x_i, y_i] = exp
    z_mesh = np.transpose(z_mesh)

    # Set logarithmic z axis
    min_exp, max_exp = (
        np.floor(np.log10(np.min(exp))),
        np.ceil(np.log10(np.max(exp))),
    )
    z_min, z_max = np.pow(10, min_exp), np.pow(10, max_exp)
    norm = LogNorm(vmin=z_min, vmax=z_max)

    # Plot expected limit
    pm = ax.pcolormesh(
        x_mesh,
        y_mesh,
        z_mesh,
        cmap="viridis",
        norm=norm,
        label="Expected",
    )

    # Add colorbar for z axis
    cbar = fig.colorbar(
        pm,
        ax=ax,
        label=r"95% CL upper limit on $\sigma\mathcal{B}$ (pb)",
    )

    return (
        pm,
        cbar,
        (np.min(ex_u), np.max(ex_u)),
        (np.min(ey_u), np.max(ey_u)),
        (z_min, z_max),
    )


def plot_limits_for_constant_my(
    data_frame,
    m_y,
    decay_mode,
):
    # Select rows required for this plot
    data_frame = data_frame.loc[
        (data_frame["m_y"] == m_y) & (data_frame["decay_mode"] == decay_mode)
    ].sort_values("m_x")

    fig, ax = plt.subplots()

    # Add the limit plot
    _plot_limit_1d(
        ax,
        data_frame["m_x"],
        data_frame["exp_m2"],
        data_frame["exp_m1"],
        data_frame["exp"],
        data_frame["exp_p1"],
        data_frame["exp_p2"],
    )

    y_label = {
        "y2tau_h2b": r"$X \to \text{H}(\text{b}\text{b})\text{Y}(\tau\tau)$",
        "y2b_h2tau": r"$X \to \text{H}(\tau\tau)\text{Y}(\text{b}\text{b})$",
    }

    if decay_mode == "y2b_h2tau" and m_y == 150:
        x, y = zip(*run2_my150_y2b_h2tau_limits, strict=True)
        x, y = np.array(x), np.array(y)
        y = np.sqrt(138 / (109.8 + 110.4)) * y
        ax.plot(
            x,
            y,
            color="#bd1f01",
            linestyle="dashed",
            linewidth=2,
            label=f"HIG-20-014 (13 TeV, scaled to {109.8 + 110.4} $fb^{{-1}}$)",
            zorder=20,
        )

    # Set axes labels
    ax.set_xlabel(r"$m_{\text{X}}\ (GeV)$")
    ax.set_ylabel(r"95% CL upper limit on $\sigma\mathcal{B}$ (pb)")

    # Shrink x axis to boundaries of x
    ax.set_xlim(np.min(data_frame["m_x"]), np.max(data_frame["m_x"]))

    # Set logscale
    ax.set_yscale("log")
    ax.set_ylim(1.0e-3, 5.0e-1)

    # Add legend
    ax.legend(fontsize="x-small")

    # Set axis title
    ax.set_title(
        y_label[decay_mode]
        + r", $m_{\text{Y}}$ = "
        + str(m_y)
        + f" GeV, {109.8 + 110.4} $fb^{{-1}}$"
    )

    return fig, ax


def plot_limits_for_constant_mx(
    data_frame,
    m_x,
    decay_mode,
):
    # Select rows required for this plot
    data_frame = data_frame.loc[
        (data_frame["m_x"] == m_x) & (data_frame["decay_mode"] == decay_mode)
    ].sort_values("m_y")

    fig, ax = plt.subplots()

    _plot_limit_1d(
        ax,
        data_frame["m_y"],
        data_frame["exp_m2"],
        data_frame["exp_m1"],
        data_frame["exp"],
        data_frame["exp_p1"],
        data_frame["exp_p2"],
    )

    y_label = {
        "y2tau_h2b": r"$X \to \text{H}(\text{b}\text{b})\text{Y}(\tau\tau)$",
        "y2b_h2tau": r"$X \to \text{H}(\tau\tau)\text{Y}(\text{b}\text{b})$",
    }

    # Set axes labels
    ax.set_xlabel(r"$m_{\text{Y}}\ (GeV)$")
    ax.set_ylabel(r"95% CL upper limit on $\sigma\mathcal{B}$ (pb)")

    # Shrink x axis to boundaries of x
    ax.set_xlim(np.min(data_frame["m_y"]), np.max(data_frame["m_y"]))

    # Set logscale
    ax.set_yscale("log")
    ax.set_ylim(1.0e-3, 5.0e-1)

    # Add legend
    ax.legend(fontsize="x-small")

    # Set axis title
    ax.set_title(
        y_label[decay_mode]
        + r", $m_{\text{X}}$ = "
        + str(m_x)
        + f" GeV, {109.8 + 110.4} $fb^{{-1}}$"
    )

    return fig, ax


def plot_limits(
    data_frame,
    decay_mode,
):
    # Select rows required for this plot
    data_frame = data_frame.loc[
        (data_frame["decay_mode"] == decay_mode)
    ].sort_values(["m_x", "m_y"])

    fig, ax = plt.subplots()

    _, _, x_range, y_range, _ = _plot_limit_2d(
        fig,
        ax,
        data_frame["m_x"],
        data_frame["m_y"],
        data_frame["exp"],
    )

    y_label = {
        "y2tau_h2b": r"$X \to \text{H}(\text{b}\text{b})\text{Y}(\tau\tau)$",
        "y2b_h2tau": r"$X \to \text{H}(\tau\tau)\text{Y}(\text{b}\text{b})$",
    }

    # Set axes labels
    ax.set_xlabel(r"$m_{\text{X}}\ (GeV)$")
    ax.set_ylabel(r"$m_{\text{Y}}\ (GeV)$")

    # Shrink x and y axes to boundaries inputs
    ax.set_xlim(*x_range)
    ax.set_ylim(*y_range)

    # Set axis title
    ax.set_title(y_label[decay_mode] + f", {109.8 + 110.4} $fb^{{-1}}$")

    return fig, ax


def main():
    # Create output directory if it does not exist yet
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True)

    # Load the limits data frame and get unique values of parameters
    df = load_limits(LIMITS_FILE)
    m_x_values = df["m_x"].drop_duplicates().tolist()
    m_y_values = df["m_y"].drop_duplicates().tolist()
    decay_modes = df["decay_mode"].drop_duplicates().tolist()

    # Plot median expected limits in m_x-m_y 2D plane
    for decay_mode in decay_modes:
        fig, ax = plot_limits(
            df,
            decay_mode,
        )
        for ext in ["pdf", "png"]:
            fig.savefig(OUTPUT_DIR / f"limits_xyh_{decay_mode}.{ext}")
        plt.close()

    # Plot limits as function of m_X for constant m_Y
    for m_y, decay_mode in product(m_y_values, decay_modes):
        fig, ax = plot_limits_for_constant_my(
            df,
            m_y,
            decay_mode,
        )
        for ext in ["pdf", "png"]:
            fig.savefig(OUTPUT_DIR / f"limits_xyh_{decay_mode}_my{m_y}.{ext}")
        plt.close()

    for m_x, decay_mode in product(m_x_values, decay_modes):
        fig, ax = plot_limits_for_constant_mx(
            df,
            m_x,
            decay_mode,
        )
        for ext in ["pdf", "png"]:
            fig.savefig(OUTPUT_DIR / f"limits_xyh_{decay_mode}_mx{m_x}.{ext}")
        plt.close()


if __name__ == "__main__":
    main()
