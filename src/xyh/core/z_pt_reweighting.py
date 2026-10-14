"""
Derivation of Z boson normalization and pt reweighting corrections.

The corrections are derived from control region histograms by subtracting all
non-Z backgrounds from data and comparing the result to the Z prediction:

1. The *normalization* is the ratio of the background-subtracted data yield to
   the Z yield, derived per jet multiplicity category.
2. The *pt correction* is the binwise ratio of the background-subtracted data
   to the (normalized) Z prediction in a pt distribution. The Z prediction is
   scaled with the normalization first, so that the two weights factorize.

All corrections are stored in a correctionlib `CorrectionSet`.
"""

import re
from dataclasses import dataclass

import numpy as np
from correctionlib import schemav2

# Upper edge used for the open-ended jet multiplicity bin
MULTIPLICITY_UPPER_EDGE = 100.0

_N_JETS_PATTERN = re.compile(r"_(?:eq|geq)(\d+)j(?:_|$)")


@dataclass
class Binned:
    """A one-dimensional histogram with bin contents and their variances."""

    edges: np.ndarray
    values: np.ndarray
    variances: np.ndarray

    def __post_init__(self):
        self.edges = np.asarray(self.edges, dtype=float)
        self.values = np.asarray(self.values, dtype=float)
        self.variances = np.asarray(self.variances, dtype=float)
        if not (
            len(self.edges) == len(self.values) + 1
            and self.values.shape == self.variances.shape
        ):
            raise ValueError("Inconsistent histogram shapes")

    def __sub__(self, other: "Binned") -> "Binned":
        self._check_compatible(other)
        return Binned(
            self.edges,
            self.values - other.values,
            self.variances + other.variances,
        )

    def _check_compatible(self, other: "Binned"):
        if self.edges.shape != other.edges.shape or not np.allclose(
            self.edges, other.edges
        ):
            raise ValueError("Histograms have different binning")

    def scale(self, factor: float) -> "Binned":
        """Scale the contents by a constant factor without uncertainty."""
        return Binned(
            self.edges, self.values * factor, self.variances * factor**2
        )

    def rebin(self, factor: int) -> "Binned":
        """Merge `factor` adjacent bins."""
        n_bins = len(self.values)
        if factor < 1 or n_bins % factor != 0:
            raise ValueError(
                f"Cannot rebin {n_bins} bins by a factor of {factor}"
            )
        return Binned(
            self.edges[::factor],
            self.values.reshape(-1, factor).sum(axis=1),
            self.variances.reshape(-1, factor).sum(axis=1),
        )

    def merge_above(self, pt_clip: float) -> tuple["Binned", bool]:
        """
        Merge all bins with a lower edge at or above `pt_clip` into a single
        bin. Returns the histogram and whether a tail bin has been formed,
        i.e. whether `pt_clip` lies below the upper edge. A bin that contains
        `pt_clip` in its interior is kept as it is.
        """
        n_bins = len(self.values)
        first = int(np.searchsorted(self.edges[:-1], pt_clip - 1e-9))
        if first >= n_bins:
            return self, False
        return self.merge([*range(first), first]), True

    def slice(self, start: int, stop: int | None = None) -> "Binned":
        """The bins with indices from `start` up to `stop`."""
        stop = len(self.values) if stop is None else stop
        return Binned(
            self.edges[start : stop + 1],
            self.values[start:stop],
            self.variances[start:stop],
        )

    def merge(self, starts: list[int]) -> "Binned":
        """Merge bins into groups beginning at the given bin indices."""
        idx = np.asarray(starts, dtype=int)
        return Binned(
            np.append(self.edges[idx], self.edges[-1]),
            np.add.reduceat(self.values, idx),
            np.add.reduceat(self.variances, idx),
        )


def concatenate(first: Binned, second: Binned) -> Binned:
    """Join two histograms where the first ends where the second begins."""
    if not np.isclose(first.edges[-1], second.edges[0]):
        raise ValueError("Histograms are not adjacent")
    return Binned(
        np.append(first.edges, second.edges[1:]),
        np.append(first.values, second.values),
        np.append(first.variances, second.variances),
    )


def sum_binned(hists: list[Binned]) -> Binned:
    """Sum a non-empty list of histograms with identical binning."""
    total = hists[0]
    for h in hists[1:]:
        total._check_compatible(h)
        total = Binned(
            total.edges, total.values + h.values, total.variances + h.variances
        )
    return total


def find_merge_groups(
    data: Binned,
    z: Binned,
    others: list[Binned],
    max_rel_error: float,
) -> list[int]:
    """
    Group adjacent bins from low to high such that the statistical uncertainty
    of the data-over-Z ratio is below `max_rel_error` in every group. Returns
    the start indices of the groups. A remainder that does not reach the
    threshold is merged into the last group. The uncertainty of the
    normalization is common to all bins and therefore not considered.
    """
    subtracted = data - sum_binned(others) if others else data
    n_bins = len(data.values)
    starts = [0]
    sum_data = sum_var_data = sum_z = sum_var_z = 0.0
    open_group = True
    for i in range(n_bins):
        sum_data += subtracted.values[i]
        sum_var_data += subtracted.variances[i]
        sum_z += z.values[i]
        sum_var_z += z.variances[i]
        if sum_data > 0 and sum_z > 0:
            rel_var = sum_var_data / sum_data**2 + sum_var_z / sum_z**2
            if rel_var < max_rel_error**2:
                starts.append(i + 1)
                open_group = False
                sum_data = sum_var_data = sum_z = sum_var_z = 0.0
                continue
        open_group = True
    # The last start is either past the end or begins an incomplete group,
    # which is merged into the previous one
    if len(starts) > 1 and (open_group or starts[-1] >= n_bins):
        starts.pop()
    return starts


def compute_normalization(
    data: Binned, z: Binned, others: list[Binned]
) -> tuple[float, float]:
    """
    Normalization of Z such that its integral matches the background-subtracted
    data. Returns the factor and its statistical uncertainty. A factor of 1 is
    returned if the Z yield is not positive.
    """
    n_data, var_data = data.values.sum(), data.variances.sum()
    n_others = sum(h.values.sum() for h in others)
    var_others = sum(h.variances.sum() for h in others)
    n_z, var_z = z.values.sum(), z.variances.sum()
    if n_z <= 0:
        return 1.0, 0.0
    num = n_data - n_others
    var_num = var_data + var_others
    factor = num / n_z
    error = np.sqrt(var_num / n_z**2 + var_z * num**2 / n_z**4)
    return float(factor), float(error)


def compute_pt_correction(
    data: Binned,
    z: Binned,
    others: list[Binned],
    normalization: float = 1.0,
) -> Binned:
    """
    Binwise correction factors for Z such that the (normalized) Z prediction
    matches the background-subtracted data. Bins without a positive Z
    prediction or with a non-positive subtracted data content get a factor
    of 1. The result holds the factors and their variances.

    The variances contain only the statistical uncertainties of the bin
    contents, which are uncorrelated between the bins. The uncertainty of the
    normalization is common to all bins and anti-correlated to the factors
    (the product of both is fixed by the data in each bin), so it is treated
    separately, see `compute_normalization`.
    """
    ratio, _ = compute_pt_ratio(data, z, others, normalization)
    subtracted = data - sum_binned(others) if others else data
    ok = (z.values > 0) & (subtracted.values > 0) & (normalization > 0)
    values = np.where(ok, ratio.values, 1.0)
    variances = np.where(ok, ratio.variances, 0.0)
    return Binned(z.edges, values, variances)


def compute_pt_ratio(
    data: Binned,
    z: Binned,
    others: list[Binned],
    normalization: float = 1.0,
) -> tuple[Binned, np.ndarray]:
    """
    Unbiased input for the smoothing of the pt correction.

    Returns the raw binwise ratio of background-subtracted data to the
    normalized Z prediction, including bins with a zero or negative content,
    which must not be dropped in order not to bias the average. Bins without a
    positive Z prediction get a ratio of 1 and a vanishing weight. The
    variances are the observed statistical variances of the ratios.

    The second return value are the weights for the averaging: the inverse of
    the variance expected for a ratio of 1. Using the expectation instead of
    the observed variance avoids the bias that arises when bins with
    downward fluctuations get a larger weight.
    """
    subtracted = data - sum_binned(others) if others else data
    z_norm = z.scale(normalization)
    ok = z_norm.values > 0
    safe_z = np.where(ok, z_norm.values, 1.0)
    background = (
        sum_binned(others)
        if others
        else Binned(z.edges, 0 * z.values, 0 * z.values)
    )

    values = np.where(ok, subtracted.values / safe_z, 1.0)
    variances = np.where(
        ok,
        subtracted.variances / safe_z**2
        + z_norm.variances * subtracted.values**2 / safe_z**4,
        0.0,
    )
    expected_variance = (
        safe_z + background.values + background.variances + z_norm.variances
    ) / safe_z**2
    weights = np.where(ok, 1.0 / expected_variance, 0.0)
    return Binned(z.edges, values, variances), weights


def smooth_gaussian(
    hist: Binned,
    sigma: float,
    grid_step: float = 1.0,
    weights: np.ndarray | None = None,
) -> Binned:
    """
    Smooth binwise correction factors with a Gaussian kernel to obtain a
    continuous approximation.

    The smoothed value at position x is the kernel-weighted average of the bin
    values, evaluated at the bin centers, where each bin enters with its
    weight times the Gaussian kernel of width `sigma`. By default the weight
    is `1 / variance`; bins with a vanishing weight (or variance) are ignored.
    The result is evaluated on a regular grid with the given step, covering
    the range of `hist`. Its variances are propagated from the (uncorrelated)
    bin variances, `sum((K w)^2 var) / sum(K w)^2`. They are correlated
    between neighboring points of the grid.
    """
    if sigma <= 0 or grid_step <= 0:
        raise ValueError("sigma and grid_step must be positive")
    if weights is None:
        weights = np.where(
            hist.variances > 0,
            1.0 / np.where(hist.variances > 0, hist.variances, 1.0),
            0.0,
        )
    weights = np.asarray(weights, dtype=float)
    n_grid = max(int(round((hist.edges[-1] - hist.edges[0]) / grid_step)), 1)
    edges = np.linspace(hist.edges[0], hist.edges[-1], n_grid + 1)
    valid = weights > 0
    if not valid.any():
        return Binned(edges, np.ones(n_grid), np.zeros(n_grid))
    centers = (0.5 * (hist.edges[:-1] + hist.edges[1:]))[valid]
    values = hist.values[valid]
    variances = hist.variances[valid]
    weights = weights[valid]
    x = 0.5 * (edges[:-1] + edges[1:])

    kw = weights[None, :] * np.exp(
        -0.5 * ((x[:, None] - centers[None, :]) / sigma) ** 2
    )
    norm = kw.sum(axis=1)
    smoothed = np.empty(n_grid)
    variance = np.empty(n_grid)
    ok = norm > 1e-100
    smoothed[ok] = (kw[ok] * values[None, :]).sum(axis=1) / norm[ok]
    variance[ok] = (kw[ok] ** 2 * variances[None, :]).sum(axis=1) / norm[
        ok
    ] ** 2
    # Far away from all valid bins the kernel vanishes: use the nearest bin
    if (~ok).any():
        nearest = np.abs(x[~ok][:, None] - centers[None, :]).argmin(axis=1)
        smoothed[~ok] = values[nearest]
        variance[~ok] = variances[nearest]
    return Binned(edges, smoothed, variance)


def parse_multiplicities(category: str) -> int:
    """
    Extract the lower edge of the jet multiplicity bin from a category name
    such as `mm_geq4j`.
    """
    m_jets = _N_JETS_PATTERN.search(category)
    if m_jets is None:
        raise ValueError(f"Cannot determine jet multiplicity of '{category}'")
    return int(m_jets.group(1))


def _multiplicity_binning(
    input_name: str, lower_edges: list[int], content: list
) -> schemav2.Binning:
    return schemav2.Binning(
        nodetype="binning",
        input=input_name,
        edges=[float(e) for e in lower_edges] + [MULTIPLICITY_UPPER_EDGE],
        content=content,
        flow="clamp",
    )


def _jet_binning(leaves: dict[int, object]) -> schemav2.Binning:
    """
    Binning in `n_jets` with the given leaves, keyed by the lower edges of
    the jet bins. Out-of-range values are clamped.
    """
    jet_edges = sorted(leaves)
    return _multiplicity_binning(
        "n_jets", jet_edges, [leaves[j] for j in jet_edges]
    )


def _pt_binning(edges, content) -> schemav2.Binning:
    return schemav2.Binning(
        nodetype="binning",
        input="genboson_pt",
        edges=[float(e) for e in edges],
        content=[float(v) for v in content],
        flow="clamp",
    )


def build_correction_set(
    normalizations: dict[str, float],
    pt_corrections: dict[str, Binned],
    normalization_errors: dict[str, float] | None = None,
    description: str = "",
    raw_pt_ratios: dict[str, Binned] | None = None,
) -> schemav2.CorrectionSet:
    """
    Build the correctionlib set with the corrections `z_normalization`
    (input `n_jets`) and `z_pt_correction` (inputs `n_jets`, `genboson_pt`).
    All dictionaries are keyed by category names.

    If given, the binwise ratios before smoothing are stored for reference
    (e.g. for control plots) as `z_pt_ratio_unsmoothed` and
    `z_pt_ratio_unsmoothed_stat_unc`. They are not meant to be applied.

    The statistical uncertainties are stored as `z_pt_correction_stat_unc`
    (uncorrelated between pt bins, normalization uncertainty not included) and,
    if given, `z_normalization_stat_unc`.
    """
    if set(normalizations) != set(pt_corrections):
        raise ValueError(
            "Normalizations and pt corrections need same categories"
        )

    norm_leaves = {}
    norm_error_leaves = {}
    pt_leaves = {}
    pt_error_leaves = {}
    for category, norm in normalizations.items():
        key = parse_multiplicities(category)
        norm_leaves[key] = float(norm)
        if normalization_errors is not None:
            norm_error_leaves[key] = float(normalization_errors[category])
        hist = pt_corrections[category]
        pt_leaves[key] = schemav2.Binning(
            nodetype="binning",
            input="genboson_pt",
            edges=[float(e) for e in hist.edges],
            content=[float(v) for v in hist.values],
            flow="clamp",
        )
        pt_error_leaves[key] = schemav2.Binning(
            nodetype="binning",
            input="genboson_pt",
            edges=[float(e) for e in hist.edges],
            content=[float(v) for v in np.sqrt(hist.variances)],
            flow="clamp",
        )

    raw_leaves = {}
    raw_error_leaves = {}
    for category, hist in (raw_pt_ratios or {}).items():
        key = parse_multiplicities(category)
        raw_leaves[key] = _pt_binning(hist.edges, hist.values)
        raw_error_leaves[key] = _pt_binning(hist.edges, np.sqrt(hist.variances))

    int_inputs = [
        schemav2.Variable(
            name="n_jets", type="int", description="Number of jets"
        ),
    ]
    pt_inputs = [
        *int_inputs,
        schemav2.Variable(
            name="genboson_pt",
            type="real",
            description="Generator-level pt of the boson in GeV",
        ),
    ]
    output = schemav2.Variable(name="weight", type="real")
    return schemav2.CorrectionSet(
        schema_version=2,
        description=description,
        corrections=[
            schemav2.Correction(
                name="z_normalization",
                description="Normalization factor of the Z boson process",
                version=1,
                inputs=int_inputs,
                output=output,
                data=_jet_binning(norm_leaves),
            ),
            *(
                [
                    schemav2.Correction(
                        name="z_normalization_stat_unc",
                        description=(
                            "Statistical uncertainty of z_normalization"
                        ),
                        version=1,
                        inputs=int_inputs,
                        output=output,
                        data=_jet_binning(norm_error_leaves),
                    )
                ]
                if normalization_errors is not None
                else []
            ),
            schemav2.Correction(
                name="z_pt_correction",
                description=(
                    "Binwise correction of the Z boson pt spectrum, to be "
                    "applied after the normalization. Derived from the "
                    "reconstructed pt of the dilepton system."
                ),
                version=1,
                inputs=pt_inputs,
                output=output,
                data=_jet_binning(pt_leaves),
            ),
            schemav2.Correction(
                name="z_pt_correction_stat_unc",
                description=(
                    "Statistical uncertainty of z_pt_correction from the "
                    "bin contents, uncorrelated between pt bins. The "
                    "uncertainty of the normalization is not included, as "
                    "it is anti-correlated to the pt correction"
                ),
                version=1,
                inputs=pt_inputs,
                output=output,
                data=_jet_binning(pt_error_leaves),
            ),
            *(
                [
                    schemav2.Correction(
                        name=name,
                        description=description,
                        version=1,
                        inputs=pt_inputs,
                        output=output,
                        data=_jet_binning(leaves),
                    )
                    for name, description, leaves in (
                        (
                            "z_pt_ratio_unsmoothed",
                            "Binwise ratio before smoothing, for reference",
                            raw_leaves,
                        ),
                        (
                            "z_pt_ratio_unsmoothed_stat_unc",
                            "Statistical uncertainty of the unsmoothed ratio",
                            raw_error_leaves,
                        ),
                    )
                ]
                if raw_pt_ratios
                else []
            ),
        ],
    )
