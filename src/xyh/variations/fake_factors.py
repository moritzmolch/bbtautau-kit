from collections import OrderedDict

from xyh.core.variations import append, replace, variation


def _skip_fake_factors(self) -> bool:
    return (
        self.process_inst.has_tag({"signal"})
        or self.process_inst.name == "jetfakes"
        or self.channel_inst.name not in ["et", "mt", "tt"]
    )


@variation(
    skip_fn=_skip_fake_factors,  # skip signals, jetfakes process and non-tau channels
)
def fake_factors(
    self,
    filters: OrderedDict[str, str],
    weights: OrderedDict[str, str],
) -> tuple[OrderedDict[str, str], OrderedDict[str, str]]:
    # Variation is not applied to signal samples
    if self.process_inst.has_tag({"signal"}):
        return filters, weights

    # Raise an error if the channel does not contain a hadronic tau, since
    # fake factor method is not used in these channels
    if self.channel_inst.name not in ["et", "mt", "tt"]:
        raise RuntimeError(
            "Fake factors can only be applied in the et, mt, and tt channels."
        )

    # Get the working points for the tau ID depending on the channel
    id_vs_jet_wp = self.channel_inst.x.tau["id_vs_jet_wp"]
    antiid_vs_jet_wp = self.channel_inst.x.tau["antiid_vs_jet_wp"]

    # Construct ID and anti-ID selection string templates with index as
    # parameter
    id_vs_jet_tpl = f"(id_tau_vsJet_{id_vs_jet_wp}_{{index}} > 0.5)"
    antiid_vs_jet_tpl = f"""
    (
        (id_tau_vsJet_{antiid_vs_jet_wp}_{{index}} > 0.5)
        && (id_tau_vsJet_{id_vs_jet_wp}_{{index}} < 0.5)
    )
    """

    # Define the modification for the AR selection and the fake factor weight
    ar_selection = ""
    ff_weight = ""
    if self.channel_inst.name in ["et", "mt"]:
        ar_selection = antiid_vs_jet_tpl.format(index=2)
        ff_weight = "fake_factor"

    elif self.channel_inst.name == "tt":
        ar_selection = f"""
        (
            {antiid_vs_jet_tpl.format(index=1)}
            && {id_vs_jet_tpl.format(index=2)}
        ) || (
            {id_vs_jet_tpl.format(index=1)}
            && {antiid_vs_jet_tpl.format(index=2)}
        )
        """
        ff_weight = f"""
        0.5 * (
            {antiid_vs_jet_tpl.format(index=1)} * fake_factor_1
            + {antiid_vs_jet_tpl.format(index=2)} * fake_factor_2
        )
        """

    # Replace the tau ID selection with the anti-ID selection
    filters = replace(
        filters,
        key_to_replace="tau_id_vs_jet",
        key="tau_antiid_vs_jet",
        expression=ar_selection,
    )

    # Add the fake factor weight to the weight dictionary
    weights = append(weights, key="fake_factor", expression=ff_weight)

    return filters, weights
