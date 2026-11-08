"""Brazil-band plots of the expected limits."""

from collections.abc import Sequence
from pathlib import Path

from xyh.fit.limits import LimitResult


def select_for_plot(
    results: Sequence[LimitResult], ydm: str, hdm: str, my: int
) -> list[LimitResult]:
    """Results of one decay mode and m_y, sorted by m_x."""
    return sorted(
        (r for r in results if (r.ydm, r.hdm, r.my) == (ydm, hdm, my)),
        key=lambda r: r.mx,
    )


def plot_brazil_band(
    results: Sequence[LimitResult],
    output_file: Path,
    title: str = "",
    show_observed: bool = False,
) -> None:
    """Plot the limit versus m_x with 1 and 2 sigma bands.

    `results` must share decay modes and m_y.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not results:
        raise ValueError("No results to plot")
    results = sorted(results, key=lambda r: r.mx)
    mx = [r.mx for r in results]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.fill_between(
        mx,
        [r.exp_m2 for r in results],
        [r.exp_p2 for r in results],
        color="#f5e050",
        label=r"expected $\pm 2\sigma$",
    )
    ax.fill_between(
        mx,
        [r.exp_m1 for r in results],
        [r.exp_p1 for r in results],
        color="#43b563",
        label=r"expected $\pm 1\sigma$",
    )
    ax.plot(mx, [r.exp for r in results], "k--", label="expected")
    if show_observed:
        ax.plot(mx, [r.obs for r in results], "ko-", label="observed")
    ax.set_yscale("log")
    ax.set_xlabel(r"$m_X$ [GeV]")
    ax.set_ylabel(r"95% CL limit on $\sigma\,\mathcal{B}$ [pb]")
    ax.set_title(title)
    ax.legend()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, bbox_inches="tight")
    plt.close(fig)


def plot_all_limits(
    results: Sequence[LimitResult],
    output_dir: Path,
    show_observed: bool = False,
) -> list[Path]:
    """One plot per decay mode and m_y."""
    written = []
    groups = sorted({(r.ydm, r.hdm, r.my) for r in results})
    for ydm, hdm, my in groups:
        out = output_dir / f"limits_{ydm}_{hdm}_my{my}.pdf"
        plot_brazil_band(
            select_for_plot(results, ydm, hdm, my),
            out,
            title=f"{ydm}, {hdm}, $m_Y$ = {my} GeV",
            show_observed=show_observed,
        )
        written.append(out)
    return written
