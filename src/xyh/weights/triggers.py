from collections import OrderedDict

from xyh.core.wrapper import Wrapper


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
            "tt": "trg_wgt_double_tau35_mediumdeeptau_leg1 * trg_wgt_double_tau35_mediumdeeptau_leg2",
            "em": "trg_wgt_single_ele30",
            "ee": "trg_wgt_single_ele30",
            "mm": "trg_wgt_single_mu24",
        },
        ("2024_nano_v15", "2025_nano_v15"): {
            "et": "trg_wgt_single_ele30",
            "mt": "trg_wgt_single_mu24",
            "tt": """
                (
                    trg_wgt_double_tau30_mediumpnet_leg1
                    * trg_wgt_double_tau30_mediumpnet_leg2
                )
            """,
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
