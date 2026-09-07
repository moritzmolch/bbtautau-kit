from collections import OrderedDict

from xyh.core.wrapper import Wrapper


@Wrapper.wrap
def tautau_from_genuine_tau_selection(self) -> OrderedDict[str, str]:
    """
    Select events with genuine tau lepton pairs at generator level based on the
    matching of the di-tau pair candidates to generator-level particles.

    The generator matching results for each candidate (`"gen_match_1"`,
    `"gen_match_2"`) are encoded as integers:

    | code | meaning                                       |
    |:----:|:---------------------------------------------:|
    | 0    | not matched / unknown                         |
    | 1    | prompt electron (e.g. from $Z \\to \\mu\\mu$) |
    | 2    | prompt muon (e.g. from $Z \\to \\mu\\mu$)     |
    | 3    | tau decay into electron                       |
    | 4    | tau decay into muon                           |
    | 5    | hadronic tau decay                            |
    | 6    | hadronic tau faked by a jet                   |

    In each channel, the selection requires that both reconstructed tau
    candidates match the corresponding tau decays at generator level, e.g., in
    the $e\\tau_{\\text{h}}$ channel, the first candidate must match to a tau
    decay into an electron, and the second candidate must match to a hadronic
    tau decay.
    """

    # Container for generator-level tau selections
    selections = OrderedDict()

    # Select genuine tau pairs based on the generator matching results
    # depending on the channel
    expression = None
    if self.channel_inst.name == "et":
        expression = "(gen_match_1 == 3) && (gen_match_2 == 5)"
    elif self.channel_inst.name == "mt":
        expression = "(gen_match_1 == 4) && (gen_match_2 == 5)"
    elif self.channel_inst.name == "tt":
        expression = "(gen_match_1 == 5) && (gen_match_2 == 5)"
    if self.channel_inst.name == "em":
        expression = "(gen_match_1 == 3) && (gen_match_2 == 4)"
    elif self.channel_inst.name == "ee":
        expression = "(gen_match_1 == 3) && (gen_match_2 == 3)"
    elif self.channel_inst.name == "mm":
        expression = "(gen_match_1 == 4) && (gen_match_2 == 4)"

    # Add selection to dictionary
    selections["tautau_from_genuine_tau"] = expression

    return selections


@Wrapper.wrap
def tautau_from_jet_fake_selection(self) -> OrderedDict[str, str]:
    """
    Select events with at least one $\\text{jet} \\to \\tau_{\\text{h}}$ fake
    at generator level based on the matching of the di-tau pair candidates to
    generator-level particles.

    The generator matching results for each candidate (`"gen_match_1"`,
    `"gen_match_2"`) are encoded as integers:

    | code | meaning                                       |
    |:----:|:---------------------------------------------:|
    | 0    | not matched / unknown                         |
    | 1    | prompt electron (e.g. from $Z \\to \\mu\\mu$) |
    | 2    | prompt muon (e.g. from $Z \\to \\mu\\mu$)     |
    | 3    | tau decay into electron                       |
    | 4    | tau decay into muon                           |
    | 5    | hadronic tau decay                            |
    | 6    | hadronic tau faked by a jet                   |

    In the fullhadronic and semileptonic channels, the selection requires that
    no genuine di-tau pair is found and that at least one hadronic tau is not
    matched to any lepton or tau lepton decay (i.e., it has generator matching
    code 6). In the dileptonic channels, $\\text{jet} \\to \\tau_{\\text{h}}$
    cannot occur.
    """

    # Container for generator-level tau selections
    selections = OrderedDict()

    # Get the selection for genuine tau pairs to veto them here
    genuine_tau_selections = self.get_instance(
        "tautau_from_genuine_tau_selection"
    )()

    # Select jet -> tau_h  fakes based on the generator matching results
    # depending on the channel. For channels without hadronic taus, no jet ->
    # tau_h fakes can occur.
    expression = ""
    expression_tautau = " && ".join(genuine_tau_selections.values())
    if self.channel_inst.name in ["et", "mt"]:
        expression = f"""
            !({expression_tautau})
            && (gen_match_2 == 6)
        """
    elif self.channel_inst.name == "tt":
        expression = f"""
            !({expression_tautau})
            && ( (gen_match_1 == 6) || (gen_match_2 == 6) )
        """
    else:
        expression = "false"

    # Add selection to dictionary
    selections["tautau_from_jet_fake"] = expression

    return selections


@Wrapper.wrap
def tautau_from_remaining_selection(self) -> OrderedDict[str, str]:
    """
    Select events with $\\ell \\to \\tau_{\\text{h}}$ fakes or lepton fakes at
    generator level based on the matching of the di-tau pair candidates to
    generator-level particles. This selection includes all events, that are not
    covered by the genuine tau pair selection or the
    $\\text{jet} \\to \\tau_{\\text{h}}$ fake selection in
    `tautau_from_genuine_tau_selection` and `tautau_from_jet_fake_selection`.

    The generator matching results for each candidate (`"gen_match_1"`,
    `"gen_match_2"`) are encoded as integers:

    | code | meaning                                       |
    |:----:|:---------------------------------------------:|
    | 0    | not matched / unknown                         |
    | 1    | prompt electron (e.g. from $Z \\to \\mu\\mu$) |
    | 2    | prompt muon (e.g. from $Z \to \\mu\\mu$)      |
    | 3    | tau decay into electron                       |
    | 4    | tau decay into muon                           |
    | 5    | hadronic tau decay                            |
    | 6    | hadronic tau faked by a jet                   |

    In all channels, the selection requires that no genuine di-tau pair and no
    $\\text{jet} \\to \\tau_{\\text{h}}$ fake is found in the event.
    """

    # Container for generator-level tau selections
    selections = OrderedDict()

    # Get the selections for genuine tau pairs and jet -> tau_h fakes to veto
    # them here
    genuine_tau_selections = self.get_instance(
        "tautau_from_genuine_tau_selection"
    )()
    jet_fake_selections = self.get_instance("tautau_from_jet_fake_selection")()
    expression_tautau = " && ".join(genuine_tau_selections.values())
    expression_jet_fake = " && ".join(jet_fake_selections.values())

    # Select genuine tau pairs based on the generator matching results
    # depending on the channel. Select events that do not have a genuine tau
    # pair and that do not have a jet -> tau_h fake.
    selections["tautau_from_lepton_fake"] = f"""
        (
            !({expression_tautau})
            && !({expression_jet_fake})
        )
    """

    return selections
