import os
from collections import OrderedDict
from pathlib import Path

from xyh.core.wrapper import Wrapper

# Environment variable with the directory of the correctionlib files holding
# the data-driven Z corrections, see `xyh.shape_processor.derive_z_pt_weights`
Z_CORRECTIONS_DIR_ENV = "XYH_Z_PT_WEIGHTS_DIR"
TT_CORRECTIONS_DIR_ENV = "XYH_TT_CORRECTIONS_DIR"
Z_CORRECTIONS_DIR_ENV = "XYH_Z_CORRECTIONS_DIR"


def _tt_corrections_file(campaign: str) -> str | None:
    """
    Absolute path of the correctionlib file with the tt corrections of the
    campaign, or `None` if the corrections are not enabled.
    """
    directory = os.environ.get(TT_CORRECTIONS_DIR_ENV, "")
    if not directory:
        return None
    path = (Path(directory) / f"tt_norm_{campaign}.json").resolve()
    if not path.is_file():
        raise FileNotFoundError(f"tt corrections file does not exist: {path}")
    return str(path)


def _z_corrections_file(campaign: str) -> str | None:
    """
    Absolute path of the correctionlib file with the Z corrections of the
    campaign, or `None` if the corrections are not enabled.
    """
    directory = os.environ.get(Z_CORRECTIONS_DIR_ENV, "")
    if not directory:
        return None
    path = (Path(directory) / f"z_norm_{campaign}.json").resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Z corrections file does not exist: {path}")
    return str(path)


@Wrapper.wrap
def tt_normalization(self) -> OrderedDict[str, str]:
    """
    Apply the data-driven correction of the (n_jets, n_bjets) spectrum of top
    quark pair production. The correction is derived with `bin/tt_norm_weights`
    on a production without these weights.

    The correction is only applied if the directory with the correctionlib
    files is set in the environment variable `XYH_CORRECTIONS_DIR`.
    """

    # Skip non-ttbar processes
    if not self.process_inst.has_tag("tt"):
        return OrderedDict([])

    file = _tt_corrections_file(self.campaign_inst.name)
    if file is None:
        return OrderedDict([])

    return OrderedDict(
        [
            (
                "tt_normalization_weight",
                f'xyh_tt_normalization("{file}", n_jets, n_bjets, "nominal")',
            ),
        ],
    )


@Wrapper.wrap
def z_normalization(self) -> OrderedDict[str, str]:
    """
    Apply the data-driven correction of the (n_jets, n_bjets) spectrum of Z
    production. The correction is derived with `bin/z_norm_weights` on a
    production without these weights.

    The correction is only applied if the directory with the correctionlib
    files is set in the environment variable `XYH_CORRECTIONS_DIR`.
    """

    # Skip non-Z processes
    if not self.process_inst.has_tag("z"):
        return OrderedDict([])

    file = _z_corrections_file(self.campaign_inst.name)
    if file is None:
        return OrderedDict([])

    return OrderedDict(
        [
            (
                "z_normalization_weight",
                f'xyh_z_normalization("{file}", n_jets, n_bjets, "nominal")',
            ),
        ],
    )


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
