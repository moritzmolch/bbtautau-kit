"""
Construction of correctionlib files with b-jet normalization weights.

The b-jet normalization factor of a simulated process compensates the effect
of the b-jet weights (the `id_wgt_bjet_shape` weight) on its yield: it is the
ratio of the yield without b-jet weights to the yield with them, derived per
channel, process and jet multiplicity. See
`xyh.btag_weight_renormalization.run_btag_weight_renormalization` for the
derivation.

All factors are stored in a correctionlib `CorrectionSet` with a single
correction `bjet_normalization` that is evaluated with the parameters
`(channel, process, n_jets)`.
"""

from correctionlib import schemav2

from .z_pt_reweighting import MULTIPLICITY_UPPER_EDGE

CORRECTION_NAME = "bjet_normalization"


def _n_jets_binning(sf_by_n_jets: dict[int, float]) -> schemav2.Binning:
    """
    Binning in `n_jets` with the given scale factors, keyed by the lower
    edges of the jet multiplicity bins. Out-of-range values are clamped.
    """
    edges = sorted(sf_by_n_jets)
    return schemav2.Binning(
        nodetype="binning",
        input="n_jets",
        edges=[float(e) for e in edges] + [MULTIPLICITY_UPPER_EDGE],
        content=[float(sf_by_n_jets[e]) for e in edges],
        flow="clamp",
    )


def build_correction_set(
    scale_factors: dict[tuple[str, str, int], float],
    description: str = "",
) -> schemav2.CorrectionSet:
    """
    Build the correctionlib set with the correction `bjet_normalization`
    (inputs `channel`, `process`, `n_jets`). The scale factors are keyed by
    `(channel, process, n_jets)`, where `n_jets` is the lower edge of a jet
    multiplicity bin. Combinations missing from the file evaluate to 1.
    """
    channel_items = []
    for channel in sorted({c for c, _, _ in scale_factors}):
        process_items = []
        for process in sorted({p for c, p, _ in scale_factors if c == channel}):
            sf_by_n_jets = {
                n_jets: sf
                for (c, p, n_jets), sf in scale_factors.items()
                if c == channel and p == process
            }
            process_items.append(
                schemav2.CategoryItem(
                    key=process,
                    value=_n_jets_binning(sf_by_n_jets),
                )
            )
        channel_items.append(
            schemav2.CategoryItem(
                key=channel,
                value=schemav2.Category(
                    nodetype="category",
                    input="process",
                    content=process_items,
                    default=1.0,
                ),
            )
        )

    return schemav2.CorrectionSet(
        schema_version=2,
        description=description,
        corrections=[
            schemav2.Correction(
                name=CORRECTION_NAME,
                description=(
                    "Normalization factor of a simulated process compensating "
                    "the effect of the b-jet weights on its yield"
                ),
                version=1,
                inputs=[
                    schemav2.Variable(
                        name="channel",
                        type="string",
                        description="Lepton channel",
                    ),
                    schemav2.Variable(
                        name="process",
                        type="string",
                        description="Physics process",
                    ),
                    schemav2.Variable(
                        name="n_jets",
                        type="int",
                        description="Number of jets",
                    ),
                ],
                output=schemav2.Variable(name="weight", type="real"),
                data=schemav2.Category(
                    nodetype="category",
                    input="channel",
                    content=channel_items,
                    default=1.0,
                ),
            ),
        ],
    )
