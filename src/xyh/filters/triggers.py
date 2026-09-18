from collections import OrderedDict

from xyh.core.wrapper import Wrapper


def _unroll(packed_dict):
    """Helper function to unroll a dictionary with tuple keys."""

    # Start with the packed dictionary
    result_dict = {}

    for key, value in packed_dict.items():
        # If the value is a dictionary, perform the unroll operation on the
        # subdictionary first
        if isinstance(value, dict):
            value = _unroll(value)

        if isinstance(key, str):
            # If the key is a string, the entry is already in unrolled
            # format
            continue

        elif isinstance(key, tuple):
            # If the key is a tuple, define entries with the elements of
            # key with the same value
            for k in key:
                # Check if key exists more than once, raise an error
                # otherwise
                if k in result_dict:
                    raise KeyError(
                        f"Key {key} cannot be added to unrolled "
                        + "dictionary: key already exists"
                    )

                # Add value to the dictionary
                result_dict[k] = value

        else:
            # Other cases are ill-defined
            raise KeyError(
                f"Key has unexpected type {type(key)}. Expected object of "
                + "type tuple or str"
            )

    return result_dict


@Wrapper.wrap
def triggers(self) -> OrderedDict[str, str]:
    """
    Apply trigger selection depending on the data-taking campaign and the
    analysis channel.

    - In the $\\text{e}\\tau_{\\text{h}}$, $\\text{e}\\mu$, and
      $\\text{e}\\text{e}$ channels, an unprescaled single-electron trigger is
      used.

    - In the $\\mu\\tau_{\\text{h}}$ and $\\mu\\mu$ channels, an unprescaled
      single-muon trigger is used.

    - In the $\\tau_{\\text{h}}\\tau_{\\text{h}}$ channel, a double-hadronic
      tau trigger is used. The identification algorithm varies with the
      data-taking campaign.
    """

    # Storage for trigger selections
    selections = OrderedDict()

    # Trigger selections are summarized in a nested map, where the first key
    # is an era or a tuple of eras, and the second key is the channel or a
    # tuple of channels.
    trigger_selections = _unroll(
        {
            (
                "2022_pre_ee_nano_v12",
                "2022_post_ee_nano_v12",
                "2023_pre_bpix_nano_v12",
                "2023_post_bpix_nano_v12",
            ): {
                ("et", "em", "ee"): "(pt_1 >= 32) && (trg_single_ele30 > 0.5)",
                ("mt", "mm"): "(pt_1 >= 26) && (trg_single_mu24 > 0.5)",
                "tt": """
                    (pt_1 >= 40)
                    && (pt_2 >= 40)
                    && (trg_double_tau35_mediumdeeptau > 0.5)
                """,
            },
            ("2024_nano_v15", "2025_nano_v15"): {
                ("et", "em", "ee"): "(pt_1 >= 32) && (trg_single_ele30 > 0.5)",
                ("mt", "mm"): "(pt_1 >= 26) && (trg_single_mu24 > 0.5)",
                "tt": """
                    (pt_1 >= 35)
                    && (pt_2 >= 35)
                    && (trg_double_tau30_mediumpnet > 0.5)
                """,
            },
        }
    )

    # Get the expression for the considered era and channel
    expression = trigger_selections.get(self.campaign_inst.name, {}).get(
        self.channel_inst.name, None
    )

    # Raise error if trigger selection could not be found
    if expression is None:
        raise ValueError(
            f"No trigger selection for channel {self.channel_inst.name} in "
            f"campaign {self.campaign_inst.name} declared"
        )

    # Add trigger selection to dictionary
    selections["trigger_selection"] = expression

    return selections
