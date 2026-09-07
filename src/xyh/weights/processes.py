from collections import OrderedDict

from xyh.filters.wrapper import Wrapper


@Wrapper.wrap
def z_pt_reweighting(self) -> OrderedDict[str, str]:
    """Apply the Z boson $p_{\\text{T}}$ reweighting."""

    return OrderedDict(
        [
            (
                "z_pt_weight",
                "ZPtMassReweightWeight",
            ),
        ],
    )


@Wrapper.wrap
def top_pt_reweighting(self) -> OrderedDict[str, str]:
    """Apply the top quark $p_{\\text{T}}$ reweighting."""

    return OrderedDict(
        [
            (
                "top_pt_weight",
                "topPtReweightWeight",
            ),
        ],
    )


@Wrapper.wrap
def tt_normalization(self) -> OrderedDict[str, str]:
    """
    Weight to scale $\\text{t}\\bar{\\text{t}}$ normalization to value that
    has been observed in an $\\text{e}\\mu$ control region.
    """

    # tt normalization factors per era
    normalization_factor = {
        "2022_pre_ee_nano_v12": 0.91,
        "2022_post_ee_bpix_nano_v12": 0.89,
        "2023_pre_bpix_nano_v12": 0.85,
        "2023_post_bpix_nano_v12": 0.83,
        "2024_nano_v15": 0.90,
        "2025_nano_v15": 1.0,  # TODO determine scale factor
    }[self.campaign_inst.name]

    # Do not apply a correction factor in the em channel, as this channel is
    # used to derive the correction factor
    if self.channel_inst.name == "em":
        return OrderedDict([])

    return OrderedDict(
        [
            (
                "tt_normalization_weight",
                f"{normalization_factor}",
            ),
        ],
    )
