import os
from collections import OrderedDict
from pathlib import Path

from xyh.core.wrapper import Wrapper

# Environment variable with the directory of the correctionlib files holding
# the data-driven Z corrections, see `xyh.shape_processor.derive_z_pt_weights`
Z_CORRECTIONS_DIR_ENV = "XYH_Z_PT_WEIGHTS_DIR"


def _z_corrections_file(campaign: str) -> str | None:
    """
    Absolute path of the correctionlib file with the Z corrections of the
    campaign, or `None` if the corrections are not enabled.
    """
    directory = os.environ.get(Z_CORRECTIONS_DIR_ENV, "")
    if not directory:
        return None
    path = (Path(directory) / f"{campaign}.json").resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Z corrections file does not exist: {path}")
    return str(path)


@Wrapper.wrap
def z_pt_reweighting(self) -> OrderedDict[str, str]:
    """
    Apply the data-driven Z boson $p_{\\text{T}}$ correction as function of the
    number of jets and the generator-level boson $p_{\\text{T}}$. The
    correction is derived with `bin/derive_z_pt_weights` on a production
    without Z corrections.

    The correction is only applied if the directory with the correctionlib
    files is set in the environment variable `XYH_Z_PT_WEIGHTS_DIR`.
    """

    if not self.process_inst.has_tag("z"):
        return OrderedDict([])

    file = _z_corrections_file(self.campaign_inst.name)
    if file is None:
        return OrderedDict([])

    return OrderedDict(
        [
            (
                "z_pt_weight",
                f'xyh_z_pt_correction("{file}", n_jets, gen_boson_p4.Pt())',
            ),
        ],
    )


@Wrapper.wrap
def top_pt_reweighting(self) -> OrderedDict[str, str]:
    """Apply the top quark $p_{\\text{T}}$ reweighting."""

    if not self.process_inst.has_tag("tt"):
        return OrderedDict([])

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

    if not self.process_inst.has_tag("tt"):
        return OrderedDict([])

    # tt normalization factors per era
    normalization_factor = {
        "2022_pre_ee_nano_v12": 1.0,
        "2022_post_ee_nano_v12": 1.0,
        "2023_pre_bpix_nano_v12": 1.0,
        "2023_post_bpix_nano_v12": 1.0,
        "2024_nano_v15": 0.95,
        "2025_nano_v15": 0.93,
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


@Wrapper.wrap
def z_normalization(self) -> OrderedDict[str, str]:
    """
    Weight to scale the $\\text{Z}(\\ell\\ell)$ normalization to the value
    that has been observed in the $\\mu\\mu$ control region, as function of
    the number of jets and b jets. It must be applied together with the
    $p_{\\text{T}}$ correction of `z_pt_reweighting`, which is derived on the
    normalized Z prediction.

    The weight is only applied if the directory with the correctionlib files
    is set in the environment variable `XYH_Z_PT_WEIGHTS_DIR`.
    """

    if not self.process_inst.has_tag("z"):
        return OrderedDict([])

    file = _z_corrections_file(self.campaign_inst.name)
    if file is None:
        return OrderedDict([])

    return OrderedDict(
        [
            (
                "z_normalization_weight",
                f'xyh_z_normalization("{file}", n_jets, n_bjets)',
            ),
        ],
    )
