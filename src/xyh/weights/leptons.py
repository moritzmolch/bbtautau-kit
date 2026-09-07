from collections import OrderedDict

from xyh.filters.wrapper import Wrapper


@Wrapper.wrap
def electrons(self) -> OrderedDict[str, str]:
    """Add electron ID weights in channels with electrons."""

    # Empty storage for new weights
    weights = OrderedDict()

    # The weight of the first lepton must be used in the et and em channels
    if self.channel_inst.name in ["et", "em"]:
        weights["electron_id_weight"] = "id_wgt_ele_1"

    # The combined weight of the first and the second lepton must be used in
    # the ee channel
    if self.channel_inst.name in ["ee"]:
        weights["electron_id_weight"] = "id_wgt_ele_1 * id_wgt_ele_2"

    # For all other channels, the weight dictionary for electrons stays empty

    return weights


@Wrapper.wrap
def muons(self) -> OrderedDict[str, str]:
    """Add muon isolation and ID weights in channels with electrons."""

    # Empty storage for new weights
    weights = OrderedDict()

    # The weights of the first lepton must be used in the mt channel
    if self.channel_inst.name == "mt":
        weights["muon_id_weight"] = "id_wgt_mu_1"
        weights["muon_iso_weight"] = "iso_wgt_mu_1"

    # The weights of the second lepton must be used in the em channel
    if self.channel_inst.name == "em":
        weights["muon_id_weight"] = "id_wgt_mu_2"
        weights["muon_iso_weight"] = "iso_wgt_mu_2"

    # The combined weights of the first and the second lepton must be used in
    # the mm channel
    if self.channel_inst.name == "mm":
        weights["muon_id_weight"] = "id_wgt_mu_1 * id_wgt_mu_2"
        weights["muon_iso_weight"] = "iso_wgt_mu_1 * iso_wgt_mu_2"

    # For all other channels, the weight dictionary for muons stays empty

    return weights


@Wrapper.wrap
def hadronic_taus(self) -> OrderedDict[str, str]:
    """Add hadronic tau ID weights in channels with hadronic taus."""

    # Empty storage for tau weights
    weights = OrderedDict()

    # Define the tau ID working points
    wp_jet = "Medium"
    wp_ele = "Tight" if self.channel_inst.name == "et" else "VVLoose"
    wp_mu = "Tight" if self.channel_inst.name == "mt" else "VLoose"

    # Construct template strings for the tau ID weights depending on the
    # channel
    id_vs_jet_weight_tpl = f"""
    (
        (gen_match_{{index}} == 5)
        ? id_wgt_tau_vsJet_{wp_jet}_{{index}}
        : 1.0
    )
    """
    id_vs_e_weight_tpl = f"""
    (
        (gen_match_{{index}} == 1) || (gen_match_{{index}} == 3)
        ? id_wgt_tau_vsEle_{wp_ele}_{{index}}
        : 1.0
    )
    """
    id_vs_mu_weight_tpl = f"""
    (
        (gen_match_{{index}} == 2) || (gen_match_{{index}} == 4)
        ? id_wgt_tau_vsMu_{wp_mu}_{{index}}
        : 1.0
    )
    """

    # Apply ID weights to the hadronic taus
    # - In the semileptonic channels, the second candidate is a hadronic tau.
    # - In the fullhadronic channel, the first and the second candidate are
    #   hadronic taus.

    indices = {
        "et": [2],
        "mt": [2],
        "tt": [1, 2],
    }
    if self.channel_inst.name in indices:
        for i in indices[self.channel_inst.name]:
            weights[f"tau{i}_id_vs_jet_weight"] = id_vs_jet_weight_tpl.format(
                index=i
            )
            weights[f"tau{i}_id_vs_e_weight"] = id_vs_e_weight_tpl.format(
                index=i
            )
            weights[f"tau{i}_id_vs_mu_weight"] = id_vs_mu_weight_tpl.format(
                index=i
            )

    return weights
