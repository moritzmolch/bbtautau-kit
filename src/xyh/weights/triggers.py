from collections import OrderedDict

from xyh.core.wrapper import Wrapper


def _get_ditau_trigger_efficiency(trigger_flag, data_type):
    return (
        f"trg_{trigger_flag} * trg_eff_{data_type}_{trigger_flag}_leg1 "
        + f"* trg_eff_{data_type}_{trigger_flag}_leg2"
    )


def _get_ditaujet_trigger_efficiency(trigger_flag, data_type):
    return (
        f"trg_{trigger_flag} * trg_eff_{data_type}_{trigger_flag}_leg1 "
        + f"* trg_eff_{data_type}_{trigger_flag}_leg2"
        + f"* trg_eff_{data_type}_{trigger_flag}_leg3"
    )


@Wrapper.wrap
def trigger_weights(self) -> OrderedDict[str, str]:
    """
    Apply trigger weights depending on the trigger used in the respective
    campaign and analysis channel. The function returns an ordered dictionary
    with the weight names as keys and the ROOT expression to define the weight
    as values.

    :param analysis_context: Analysis context, to which the selections should
        be tailored. Attributes used in this function are
        :py:attr:`~shape_producer.operations.AnalysisContext.channel` and
        :py:attr:`~shape_producer.operations.AnalysisContext.campaign`.

    :return: Collection of weight definitions.
    """

    # Construct di-tau+jet trigger weight for 2022/2023
    ditau_eff_data = _get_ditau_trigger_efficiency(
        "double_tau35_mediumdeeptau", "data"
    )
    ditau_eff_mc = _get_ditau_trigger_efficiency(
        "double_tau35_mediumdeeptau", "mc"
    )
    ditaujet_eff_data = _get_ditau_trigger_efficiency(
        "double_tau30_jet60_mediumdeeptau", "data"
    )
    ditaujet_eff_mc = _get_ditau_trigger_efficiency(
        "double_tau30_jet60_mediumdeeptau", "mc"
    )
    wgt_tt_2022_2023 = (
        f"({ditau_eff_data} + {ditaujet_eff_data} - {ditau_eff_data} * {ditaujet_eff_data})"
        + " / "
        f"({ditau_eff_mc} + {ditaujet_eff_mc} - {ditau_eff_mc} * {ditaujet_eff_mc})"
    )

    # Construct di-tau+jet trigger weight for 2024/2025
    ditau_eff_data = _get_ditau_trigger_efficiency("double_tau30_pnet", "data")
    ditau_eff_mc = _get_ditau_trigger_efficiency("double_tau30_pnet", "mc")
    ditaujet_eff_data = _get_ditau_trigger_efficiency(
        "double_tau26_jet60_pnet", "data"
    )
    ditaujet_eff_mc = _get_ditau_trigger_efficiency(
        "double_tau26_jet60_pnet", "mc"
    )
    wgt_tt_2024_2025 = (
        f"({ditau_eff_data} + {ditaujet_eff_data} - {ditau_eff_data} * {ditaujet_eff_data})"
        + " / "
        f"({ditau_eff_mc} + {ditaujet_eff_mc} - {ditau_eff_mc} * {ditaujet_eff_mc})"
    )

    # Trigger weights are summarized in a nested map, where the first key
    # is an era or a tuple of eras, and the second key is the channel.
    trigger_weights = {
        (
            "2022_pre_ee_nano_v12",
            "2022_post_ee_nano_v12",
            "2023_pre_bpix_nano_v12",
            "2023_post_bpix_nano_v12",
        ): {
            "et": "trg_wgt_single_ele30",
            "mt": "trg_wgt_single_mu24",
            "tt": wgt_tt_2022_2023,
            "em": "trg_wgt_single_ele30",
            "ee": "trg_wgt_single_ele30",
            "mm": "trg_wgt_single_mu24",
        },
        ("2024_nano_v15", "2025_nano_v15"): {
            "et": "trg_wgt_single_ele30",
            "mt": "trg_wgt_single_mu24",
            "tt": wgt_tt_2024_2025,
            "em": "trg_wgt_single_ele30",
            "ee": "trg_wgt_single_ele30",
            "mm": "trg_wgt_single_mu24",
        },
    }

    # Get the trigger selection for the given era and channel
    expression = None
    for campaign_tuple, trigger_weights_era in trigger_weights.items():
        if not isinstance(campaign_tuple, tuple):
            campaign_tuple = (campaign_tuple,)
        if self.campaign_inst.name in campaign_tuple:
            expression = trigger_weights_era[self.channel_inst.name]
    if expression is None:
        raise ValueError(
            f"No trigger weight for channel {self.channel_inst.name} in "
            + f"campaign {self.campaign_inst.name} declared"
        )

    return OrderedDict([("trigger_weight", expression)])
