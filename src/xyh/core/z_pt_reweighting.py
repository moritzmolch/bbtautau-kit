"""
Derivation of Z boson normalization and pt reweighting corrections.

The corrections are derived from control region histograms by subtracting all
non-Z backgrounds from data and comparing the result to the Z prediction:

1. The *normalization* is the ratio of the background-subtracted data yield to
   the Z yield, derived per jet / b-jet category.
2. The *pt correction* is the binwise ratio of the background-subtracted data
   to the (normalized) Z prediction in a pt distribution. The Z prediction is
   scaled with the normalization first, so that the two weights factorize.

All corrections are stored in a correctionlib `CorrectionSet`.
"""

import re
from dataclasses import dataclass

import numpy as np
from correctionlib import schemav2

# Upper edge used for the open-ended jet and b-jet multiplicity bins
MULTIPLICITY_UPPER_EDGE = 100.0

_N_JETS_PATTERN = re.compile(r"_(?:eq|geq)(\d+)j(?:_|$)")
_N_BJETS_PATTERN = re.compile(r"_(?:eq|geq)(\d+)b(?:_|$)")


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

    def scale(self, factor: float, factor_error: float = 0.0) -> "Binned":
        """Scale by a factor with uncertainty (uncorrelated with the bins)."""
        values = self.values * factor
        variances = (
            self.variances * factor**2 + (self.values * factor_error) ** 2
        )
        return Binned(self.edges, values, variances)

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

    def merge(self, starts: list[int]) -> "Binned":
        """Merge bins into groups beginning at the given bin indices."""
        idx = np.asarray(starts, dtype=int)
        return Binned(
            np.append(self.edges[idx], self.edges[-1]),
            np.add.reduceat(self.values, idx),
            np.add.reduceat(self.variances, idx),
        )

    @property
    def integral(self) -> tuple[float, float]:
        return float(self.values.sum()), float(np.sqrt(self.variances.sum()))


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
    normalization_error: float = 0.0,
    min_value: float | None = None,
    max_value: float | None = None,
) -> Binned:
    """
    Binwise correction factors for Z such that the (normalized) Z prediction
    matches the background-subtracted data. Bins without a positive Z
    prediction or with a non-positive subtracted data content get a factor
    of 1. The result holds the factors as values and their variances.
    """
    subtracted = data
    if others:
        subtracted = data - sum_binned(others)
    z_norm = z.scale(normalization, normalization_error)

    ok = (z_norm.values > 0) & (subtracted.values > 0)
    safe_z = np.where(ok, z_norm.values, 1.0)
    ratio = np.where(ok, subtracted.values / safe_z, 1.0)
    variance = np.where(
        ok,
        subtracted.variances / safe_z**2
        + z_norm.variances * subtracted.values**2 / safe_z**4,
        0.0,
    )
    if min_value is not None or max_value is not None:
        ratio = np.clip(ratio, min_value, max_value)
    return Binned(z.edges, ratio, variance)


def parse_multiplicities(category: str) -> tuple[int, int]:
    """
    Extract the lower edges of the jet and b-jet multiplicity bins from a
    category name such as `mm_geq4j_eq2b`.
    """
    m_jets = _N_JETS_PATTERN.search(category)
    m_bjets = _N_BJETS_PATTERN.search(category)
    if m_jets is None or m_bjets is None:
        raise ValueError(
            f"Cannot determine jet and b-jet multiplicity of '{category}'"
        )
    return int(m_jets.group(1)), int(m_bjets.group(1))


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


def _nested_binning(leaves: dict[tuple[int, int], object]) -> schemav2.Binning:
    """
    Nested binning in `n_jets` and `n_bjets` with the given leaves, keyed by the
    lower edges of the jet and b-jet bins. Out-of-range values are clamped.
    """
    jet_edges = sorted({j for j, _ in leaves})
    content = []
    for j in jet_edges:
        bjet_edges = sorted(b for jj, b in leaves if jj == j)
        content.append(
            _multiplicity_binning(
                "n_bjets", bjet_edges, [leaves[(j, b)] for b in bjet_edges]
            )
        )
    return _multiplicity_binning("n_jets", jet_edges, content)


def build_correction_set(
    normalizations: dict[str, float],
    pt_corrections: dict[str, Binned],
    description: str = "",
) -> schemav2.CorrectionSet:
    """
    Build the correctionlib set with the corrections `z_normalization`
    (inputs `n_jets`, `n_bjets`) and `z_pt_correction` (inputs `n_jets`,
    `n_bjets`, `genboson_pt`). Both dictionaries are keyed by category names.
    """
    if set(normalizations) != set(pt_corrections):
        raise ValueError(
            "Normalizations and pt corrections need same categories"
        )

    norm_leaves = {}
    pt_leaves = {}
    for category, norm in normalizations.items():
        key = parse_multiplicities(category)
        norm_leaves[key] = float(norm)
        hist = pt_corrections[category]
        pt_leaves[key] = schemav2.Binning(
            nodetype="binning",
            input="genboson_pt",
            edges=[float(e) for e in hist.edges],
            content=[float(v) for v in hist.values],
            flow="clamp",
        )

    int_inputs = [
        schemav2.Variable(
            name="n_jets", type="int", description="Number of jets"
        ),
        schemav2.Variable(
            name="n_bjets", type="int", description="Number of b-tagged jets"
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
                data=_nested_binning(norm_leaves),
            ),
            schemav2.Correction(
                name="z_pt_correction",
                description=(
                    "Binwise correction of the Z boson pt spectrum, to be "
                    "applied after the normalization. Derived from the "
                    "reconstructed pt of the dilepton system."
                ),
                version=1,
                inputs=[
                    *int_inputs,
                    schemav2.Variable(
                        name="genboson_pt",
                        type="real",
                        description="Generator-level pt of the boson in GeV",
                    ),
                ],
                output=output,
                data=_nested_binning(pt_leaves),
            ),
        ],
    )
