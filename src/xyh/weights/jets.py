import os
from collections import OrderedDict
from pathlib import Path

from xyh.core.wrapper import Wrapper

# Environment variable with the directory of the correctionlib files holding
# the b-tag weight normalization corrections, see
# `xyh.btag_weight_renormalization`
BTAG_RENORM_WEIGHTS_DIR_ENV = "XYH_BTAG_RENORM_WEIGHTS_DIR"


def _btag_renormalization_file(campaign_inst, channel: str) -> str | None:
    """
    Absolute path of the correctionlib file with the b-tag weight
    normalization of the campaign's era and channel, or `None` if the
    corrections are not enabled.
    """
    directory = os.environ.get(BTAG_RENORM_WEIGHTS_DIR_ENV, "")
    if not directory:
        return None
    era = f"{campaign_inst.x.year}{campaign_inst.x.postfix or ''}"
    path = (
        Path(directory) / f"btag_renormalization_weights_{era}_{channel}.json"
    ).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"b-tag renormalization weights file does not exist: {path}"
        )
    return str(path)


@Wrapper.wrap
def b_jet_weights(self) -> OrderedDict[str, str]:
    """Add b jet identification weight, compensated by the b-tag weight
    normalization of `xyh.btag_weight_renormalization` if the corrections are
    enabled."""
    if self.process_inst.is_data:
        return OrderedDict([])

    file = _btag_renormalization_file(
        self.campaign_inst, self.channel_inst.name
    )
    if file is None:
        return OrderedDict([("id_wgt_bjet_shape", "id_wgt_bjet")])

    return OrderedDict(
        [
            (
                "id_wgt_bjet_shape",
                f'id_wgt_bjet * xyh_bjet_normalization("{file}", '
                f'"{self.channel_inst.name}", "{self.process_inst.name}", '
                f"n_jets)",
            ),
        ],
    )


@Wrapper.wrap
def b_jet_weights_raw(self) -> OrderedDict[str, str]:
    """Add the raw b jet identification weight, without the normalization of
    `b_jet_weights`. Used by the production the b-tag weight renormalization
    is derived from."""
    return OrderedDict([("id_wgt_bjet_shape", "id_wgt_bjet")])
