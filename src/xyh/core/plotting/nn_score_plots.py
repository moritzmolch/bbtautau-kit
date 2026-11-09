"""Plots of the NN scores of all output classes from a fit ``shapes.root``.

The ``shapes.root`` file of a fit point holds one directory per Combine bin
``<channel>_<cls>_<campaign>``. Each output class has its own NN score axis,
so the classes of a channel are concatenated along x into one histogram per
process, in the order of ``CLASSES``. The signal class (``xyh``) is blinded:
data is zeroed there, the signal is still drawn.
"""

import logging
import re
from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import ROOT

from xyh.core.config import load_inventory
from xyh.fit.mass_points import CLASSES, SIGNAL_PREFIX
from xyh.fit.shapes import DATA_OBS_NAME, Shape, list_keys, read_shape

from .util import plot

logger = logging.getLogger(__name__)

# Class whose data is blinded
BLINDED_CLASS = "xyh"

# Short labels of the output classes
CLASS_LABELS = {
    "xyh": "X $\\to$ HY",
    "t_tt": "$\\text{t}\\bar{\\text{t}}$",
    "z2tau": "DY",
    "jetfakes": "Jet $\\to \\tau_{\\text{h}}$",
}

# Fallback style of signal processes missing in the process set
_SIGNAL_STYLE = {"color": "#bd1f01", "label": "X $\\to$ HY"}

# Bin directories are named `<channel>_<cls>_<campaign>`
_BIN_RE = re.compile(
    r"^(?P<channel>[a-z]+)_(?P<cls>"
    + "|".join(CLASSES)
    + r")_(?P<campaign>.+)$"
)


def find_bins(shapes_file: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Map (campaign, channel) to the Combine bin directory of each class.

    Raises
    ------
    FileNotFoundError
        If `shapes_file` cannot be opened.
    ValueError
        If a campaign and channel does not have all classes.
    """
    root_file = ROOT.TFile.Open(str(shapes_file), "READ")
    if not root_file or root_file.IsZombie():
        raise FileNotFoundError(f"Cannot open {shapes_file}")
    try:
        names = [key.GetName() for key in root_file.GetListOfKeys()]
    finally:
        root_file.Close()

    bins: dict[tuple[str, str], dict[str, str]] = {}
    for name in names:
        match = _BIN_RE.match(name)
        if match is None:
            continue
        key = (match["campaign"], match["channel"])
        bins.setdefault(key, {})[match["cls"]] = name

    for (campaign, channel), classes in bins.items():
        missing = [c for c in CLASSES if c not in classes]
        if missing:
            raise ValueError(
                f"Bins of {channel}/{campaign} miss the classes {missing}"
            )
    return bins


def read_class_shapes(
    root_file, bin_names: dict[str, str]
) -> dict[str, dict[str, Shape]]:
    """Read all processes (and data_obs) of the bins of each class."""
    return {
        cls: {
            process: read_shape(root_file, f"{bin_names[cls]}/{process}")
            for process in list_keys(root_file, bin_names[cls])
            # Systematic variations are stored next to the nominal shapes
            if not process.endswith(("Up", "Down"))
        }
        for cls in CLASSES
    }


def sum_channels(
    per_channel: Sequence[dict[str, dict[str, Shape]]],
) -> dict[str, dict[str, Shape]]:
    """Sum the shapes of several channels class by class and process.

    Raises
    ------
    ValueError
        If the binning of a class differs between the channels.
    """
    result: dict[str, dict[str, Shape]] = {cls: {} for cls in CLASSES}
    for shapes in per_channel:
        for cls in CLASSES:
            for process, shape in shapes[cls].items():
                total = result[cls].get(process)
                if total is None:
                    result[cls][process] = Shape(
                        shape.edges.copy(),
                        shape.values.copy(),
                        shape.sumw2.copy(),
                    )
                    continue
                if not np.array_equal(total.edges, shape.edges):
                    raise ValueError(
                        f"Cannot sum channels: the binning of class {cls} "
                        "differs between the channels"
                    )
                total.values += shape.values
                total.sumw2 += shape.sumw2
    return result


def concatenate_classes(
    class_shapes: dict[str, dict[str, Shape]],
    processes: Sequence[str],
    name: str,
    blind: bool = False,
) -> ROOT.TH1D:
    """Concatenate the classes of a group of processes along x.

    The bin ``i`` of the result covers ``[i, i + 1]``. Processes that are
    missing in a class contribute zero. With `blind`, the content and
    uncertainty of the blinded class are set to zero.
    """
    n_bins = [
        len(next(iter(class_shapes[cls].values())).values) for cls in CLASSES
    ]
    values = np.zeros(sum(n_bins))
    sumw2 = np.zeros(sum(n_bins))

    start = 0
    for cls, n in zip(CLASSES, n_bins, strict=True):
        if not (blind and cls == BLINDED_CLASS):
            for process in processes:
                shape = class_shapes[cls].get(process)
                if shape is not None:
                    values[start : start + n] += shape.values
                    sumw2[start : start + n] += shape.sumw2
        start += n

    hist = ROOT.TH1D(name, name, len(values), 0.0, float(len(values)))
    hist.SetDirectory(0)
    hist.Sumw2()
    for i, (v, w2) in enumerate(zip(values, sumw2, strict=True), start=1):
        hist.SetBinContent(i, v)
        hist.SetBinError(i, float(np.sqrt(w2)))
    return hist


def _has_process(class_shapes, processes: Sequence[str]) -> bool:
    return any(
        p in shapes for shapes in class_shapes.values() for p in processes
    )


def _plot_inputs(class_shapes, process_set, point_signals, channel):
    """Histograms and matplotlib styles of the data, signals and backgrounds."""
    data = concatenate_classes(
        class_shapes, [DATA_OBS_NAME], "data", blind=True
    )

    backgrounds = []
    claimed = set()
    for group in process_set.backgrounds:
        if not _has_process(class_shapes, group.processes):
            continue
        claimed.update(group.processes)
        hist = concatenate_classes(class_shapes, group.processes, group.name)
        kwargs = {"color": group.color, "label": group.label}
        if group.scale_factor is not None:
            kwargs["scale_factor"] = group.scale_factor.get(channel, 1.0)
        backgrounds.append((hist, kwargs))

    # Every process in the file must be drawn, otherwise the stack is wrong
    present = {p for s in class_shapes.values() for p in s}
    unknown = sorted(
        p
        for p in present - claimed - {DATA_OBS_NAME}
        if not p.startswith(SIGNAL_PREFIX)
    )
    if unknown:
        raise ValueError(
            f"Processes {unknown} are not in the background groups of the "
            f"process set {process_set.name!r}"
        )

    signals = []
    for signal in point_signals:
        group = next(
            (g for g in process_set.signals if signal in g.processes), None
        )
        style = (
            {"color": group.color, "label": group.label}
            if group is not None
            else dict(_SIGNAL_STYLE)
        )
        signals.append(
            (concatenate_classes(class_shapes, [signal], signal), style)
        )
    return data, signals, backgrounds


def _segment_edges(class_shapes) -> list[int]:
    """Cumulative bin counts, i.e. the x positions of the class borders."""
    edges = [0]
    for cls in CLASSES:
        n = len(next(iter(class_shapes[cls].values())).values)
        edges.append(edges[-1] + n)
    return edges


def _decorate(fig_axes, edges, labels, log_y, hist_total):
    """Class borders, class names and the y scale."""
    ax_top, ax_bottom = fig_axes
    for ax in (ax_top, ax_bottom):
        for x in edges[1:-1]:
            ax.axvline(x, color="gray", linestyle="dotted", linewidth=1.5)

    # Class names below the ratio panel, above the x axis label
    for label, low, high in zip(labels, edges[:-1], edges[1:], strict=True):
        ax_bottom.text(
            (low + high) / 2,
            -0.03,
            label,
            fontsize="x-small",
            horizontalalignment="center",
            verticalalignment="top",
            transform=ax_bottom.get_xaxis_transform(),
        )

    if log_y:
        contents = np.array(
            [
                hist_total.GetBinContent(i)
                for i in range(1, hist_total.GetNbinsX() + 1)
            ]
        )
        positive = contents[contents > 0]
        low = positive.min() / 5 if len(positive) else 1e-3
        ax_top.set_yscale("log")
        ax_top.set_ylim(low, contents.max() * 1e2)


def plot_channel(
    class_shapes: dict[str, dict[str, Shape]],
    inventory,
    channel: str,
    class_labels: Sequence[str],
    data_mode: str,
    output_files: Sequence[Path],
    log_y: bool = True,
) -> None:
    """Plot the four classes of a channel in one figure and save it.

    Parameters
    ----------
    class_shapes
        Shapes of every process per class.
    inventory
        Inventory providing the process set and campaign.
    channel
        Channel name, used to select the process group scale factors.
    class_labels
        Labels of the classes in the order of `CLASSES`.
    data_mode
        Data mode of the fit; Asimov data is marked in the label.
    output_files
        Files to save the figure to.
    log_y
        Use a logarithmic y axis.
    """
    ROOT.TH1.AddDirectory(0)
    campaign = inventory.campaign

    point_signals = sorted(
        {
            p
            for shapes in class_shapes.values()
            for p in shapes
            if p.startswith(SIGNAL_PREFIX)
        }
    )
    data, signals, backgrounds = _plot_inputs(
        class_shapes, inventory.process_set, point_signals, channel
    )

    data_label = "Asimov data" if data_mode.startswith("asimov") else "Data"
    fig, axes = plot(
        hist_data=(data, {"label": data_label}),
        hist_backgrounds=backgrounds,
        hist_signals=signals,
        stack_kwargs=None,
        x_label_top=None,
        y_label_top="Events",
        x_label_bottom="NN output score (per class)",
        y_label_bottom=r"Ratio to background",
        y_limits_top=None,
        y_limits_bottom=(0.7, 1.3),
        category_label=f"{channel}, {data_mode}",
        lumi=campaign.x.lumi,
        era=None,
        sqrt_s=campaign.ecm,
        # The blinded segment has no data, so the line fit is not meaningful
        fit_ratio=False,
    )

    total = backgrounds[0][0].Clone()
    for hist, _ in backgrounds[1:]:
        total.Add(hist)
    _decorate(axes, _segment_edges(class_shapes), class_labels, log_y, total)

    # The bin index is meaningless as a number
    axes[1].set_xticks([])
    axes[1].xaxis.labelpad = 25

    for output_file in output_files:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_file)
        logger.info(f"Wrote NN score plot to {output_file}")
    plt.close(fig)


def plot_nn_scores(
    point_dir: Path,
    output_dir: Path,
    extensions: Sequence[str],
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict,
    data_mode: str,
    combine_channels: bool = False,
    log_y: bool = True,
) -> list[Path]:
    """Plot the NN scores of all classes for each campaign and channel.

    Writes ``<output_dir>/<campaign>/<channel>.<ext>``, and ``combined.<ext>``
    if `combine_channels` is set. Returns the written files.
    """
    bins = find_bins(point_dir / "shapes.root")
    if not bins:
        raise ValueError(f"No Combine bins found in {point_dir}/shapes.root")

    root_file = ROOT.TFile.Open(str(point_dir / "shapes.root"), "READ")
    written: list[Path] = []
    try:
        by_campaign: dict[str, dict[str, dict]] = {}
        for (campaign, channel), bin_names in sorted(bins.items()):
            by_campaign.setdefault(campaign, {})[channel] = read_class_shapes(
                root_file, bin_names
            )

        for campaign, channels in by_campaign.items():
            jobs = dict(channels)
            if combine_channels:
                jobs["combined"] = sum_channels(list(channels.values()))

            for name, class_shapes in jobs.items():
                # The combined plot uses the inventory of the first channel
                channel = next(iter(channels)) if name == "combined" else name
                inventory = load_inventory(
                    inventory_factory_fn_path,
                    campaign,
                    channel,
                    **inventory_factory_kwargs,
                )
                labels = [CLASS_LABELS[cls] for cls in CLASSES]
                files = [
                    output_dir / campaign / f"{name}.{ext}"
                    for ext in extensions
                ]
                plot_channel(
                    class_shapes,
                    inventory,
                    name,
                    labels,
                    data_mode,
                    files,
                    log_y,
                )
                written.extend(files)
    finally:
        root_file.Close()
    return written
