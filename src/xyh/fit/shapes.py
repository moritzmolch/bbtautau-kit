"""Read merged histograms and write the input shapes of the datacard.

The pure helpers operate on `Shape` objects (numpy arrays). Only
`read_shape`, `list_keys`, `read_bin_processes` and `write_shapes_file` touch
ROOT.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from xyh.fit.mass_points import SIGNAL_PREFIX, MassPoint
from xyh.fit.scope import FitBin, FitScope

logger = logging.getLogger(__name__)

DATA_MODES = ("asimov_bkg", "asimov_sb", "observed")

# Names in the merged file and in the datacard
DATA_PROCESS = "data"
SIGNAL_NAME = "signal"
DATA_OBS_NAME = "data_obs"


@dataclass(eq=False)
class Shape:
    """A 1D histogram: bin edges, contents and sum of squared weights."""

    edges: np.ndarray
    values: np.ndarray
    sumw2: np.ndarray

    @property
    def integral(self) -> float:
        return float(np.sum(self.values))


@dataclass(eq=False)
class BinShapes:
    """The shapes of one Combine bin."""

    signal: Shape | None
    backgrounds: dict[str, Shape]
    data_obs: Shape


def is_signal_process(name: str) -> bool:
    return name.startswith(SIGNAL_PREFIX)


def clip_negative(shape: Shape) -> Shape:
    """Set negative bin contents to zero."""
    return Shape(
        shape.edges.copy(),
        np.clip(shape.values, 0.0, None),
        shape.sumw2.copy(),
    )


def add_shapes(shapes: Sequence[Shape]) -> Shape:
    """Sum shapes with identical binning."""
    if not shapes:
        raise ValueError("Cannot add an empty list of shapes")
    first = shapes[0]
    for s in shapes[1:]:
        if s.edges.shape != first.edges.shape or not np.allclose(
            s.edges, first.edges
        ):
            raise ValueError("Cannot add shapes with different binning")
    return Shape(
        first.edges.copy(),
        np.sum([s.values for s in shapes], axis=0),
        np.sum([s.sumw2 for s in shapes], axis=0),
    )


def rebin_shape(shape: Shape, factor: int) -> Shape:
    """Merge groups of `factor` adjacent bins."""
    n = len(shape.values)
    if factor < 1 or n % factor != 0:
        raise ValueError(f"Cannot rebin {n} bins by a factor of {factor}")
    return Shape(
        shape.edges[::factor].copy(),
        shape.values.reshape(-1, factor).sum(axis=1),
        shape.sumw2.reshape(-1, factor).sum(axis=1),
    )


def build_bin_shapes(
    processes: Mapping[str, Shape],
    point: MassPoint,
    data_mode: str,
    exclude: Sequence[str] = (),
    rebin: int | None = None,
) -> BinShapes:
    """Assemble signal, backgrounds and data_obs of one bin.

    All processes that are neither data, a signal nor excluded are
    backgrounds. Negative bins are clipped and processes without a positive
    integral are dropped. Asimov data is the sum of the backgrounds (and of
    the signal at its template normalization for ``asimov_sb``).

    Raises
    ------
    ValueError
        For an unknown `data_mode`, missing signal/observed-data input, or a
        bin without backgrounds.
    """
    if data_mode not in DATA_MODES:
        raise ValueError(f"Unknown data mode {data_mode!r}, use {DATA_MODES}")

    def prepare(shape: Shape) -> Shape:
        shape = clip_negative(shape)
        return rebin_shape(shape, rebin) if rebin and rebin > 1 else shape

    def usable(shape: Shape) -> bool:
        return bool(np.isfinite(shape.integral) and shape.integral > 0.0)

    if point.signal_process not in processes:
        raise ValueError(f"Signal process {point.signal_process} not found")

    backgrounds = {}
    for name, shape in processes.items():
        if name == DATA_PROCESS or is_signal_process(name) or name in exclude:
            continue
        shape = prepare(shape)
        if usable(shape):
            backgrounds[name] = shape
        else:
            logger.debug(f"Drop process {name} with vanishing integral")
    if not backgrounds:
        raise ValueError("No background with positive integral in bin")

    signal = prepare(processes[point.signal_process])
    if not usable(signal):
        signal = None

    if data_mode == "observed":
        if DATA_PROCESS not in processes:
            raise ValueError(f"Process {DATA_PROCESS!r} not found")
        observed = prepare(processes[DATA_PROCESS])
        data_obs = Shape(
            observed.edges,
            observed.values,
            observed.values.copy(),
        )
    else:
        parts = list(backgrounds.values())
        if data_mode == "asimov_sb" and signal is not None:
            parts.append(signal)
        total = add_shapes(parts)
        data_obs = Shape(total.edges, total.values, total.values.copy())

    return BinShapes(signal, backgrounds, data_obs)


# ROOT I/O


def read_shape(root_file, path: str) -> Shape:
    """Read a TH1 from an open ROOT file."""
    hist = root_file.Get(path)
    if not hist:
        raise KeyError(f"Histogram {path} not found in {root_file.GetName()}")
    n = hist.GetNbinsX()
    axis = hist.GetXaxis()
    edges = np.array(
        [axis.GetBinLowEdge(i) for i in range(1, n + 1)] + [axis.GetXmax()]
    )
    values = np.array([hist.GetBinContent(i) for i in range(1, n + 1)])
    errors = np.array([hist.GetBinError(i) for i in range(1, n + 1)])
    return Shape(edges, values, errors**2)


def list_keys(root_file, directory: str) -> list[str]:
    """Names of the keys in a directory of an open ROOT file."""
    tdir = root_file.GetDirectory(directory)
    if not tdir:
        raise KeyError(
            f"Directory {directory} not found in {root_file.GetName()}"
        )
    return [key.GetName() for key in tdir.GetListOfKeys()]


def read_bin_processes(
    root_file,
    campaign: str,
    channel: str,
    category: str,
    variable: str,
    variation: str = "nominal",
) -> dict[str, Shape]:
    """Read the nominal shapes of all processes in a category."""
    base = f"{campaign}/{channel}/{category}"
    return {
        process: read_shape(
            root_file, f"{base}/{process}/{variable}__{variation}"
        )
        for process in list_keys(root_file, base)
    }


def list_categories(root_file, campaign: str, channel: str) -> list[str]:
    """Names of the categories of a campaign and channel."""
    return list_keys(root_file, f"{campaign}/{channel}")


def build_point_shapes(
    merged_file: Path,
    point: MassPoint,
    scope: FitScope,
    variable: str,
    data_mode: str,
    exclude: Sequence[str] = (),
    rebin: int | None = None,
) -> dict[FitBin, BinShapes]:
    """Read the shapes of all bins of `scope` for one mass point.

    Raises
    ------
    KeyError
        If a category of the scope is missing in the merged file.
    ValueError
        If no bin is left after dropping empty ones.
    """
    import ROOT

    result: dict[FitBin, BinShapes] = {}
    root_file = ROOT.TFile.Open(str(merged_file), "READ")
    if not root_file or root_file.IsZombie():
        raise FileNotFoundError(f"Cannot open {merged_file}")
    try:
        for fit_bin in scope.bins():
            processes = read_bin_processes(
                root_file,
                fit_bin.campaign,
                fit_bin.channel,
                fit_bin.category(point),
                variable,
            )
            try:
                result[fit_bin] = build_bin_shapes(
                    processes, point, data_mode, exclude, rebin
                )
            except ValueError as err:
                logger.warning(f"Skip bin {fit_bin.name}: {err}")
    finally:
        root_file.Close()
    if not result:
        raise ValueError(f"No usable bins for {point.signal_process}")
    return result


def write_shapes_file(path: Path, bins: Mapping[FitBin, BinShapes]) -> None:
    """Write ``{bin}/{process}`` histograms (and ``data_obs``) to `path`."""
    import ROOT

    path.parent.mkdir(parents=True, exist_ok=True)
    root_file = ROOT.TFile.Open(str(path), "RECREATE")
    try:
        for fit_bin, shapes in bins.items():
            directory = root_file.mkdir(fit_bin.name)
            directory.cd()
            named = dict(shapes.backgrounds)
            if shapes.signal is not None:
                named[SIGNAL_NAME] = shapes.signal
            named[DATA_OBS_NAME] = shapes.data_obs
            for name, shape in named.items():
                hist = ROOT.TH1D(
                    name, name, len(shape.values), shape.edges.astype("d")
                )
                hist.SetDirectory(directory)
                for i, (v, w2) in enumerate(
                    zip(shape.values, shape.sumw2, strict=True), start=1
                ):
                    hist.SetBinContent(i, float(v))
                    hist.SetBinError(i, float(np.sqrt(w2)))
                hist.Write()
            root_file.cd()
    finally:
        root_file.Close()
