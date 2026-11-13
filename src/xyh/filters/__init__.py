from collections import OrderedDict
from itertools import chain

from xyh.core.wrapper import Wrapper

# Import filter submodules to initialize wrapper subclasses
from .gen import tautau_gen_selection
from .jet_categories import jet_categories
from .jets import bb_pair, jet_vetomap
from .leptons import ll_pair
from .triggers import triggers


@Wrapper.wrap
def default_filters(self) -> OrderedDict[str, str]:
    """
    Default filter selection for the analysis.

    This includes the following selections:

    - Trigger selection
    - Jet vetomap veto
    - bb pair selection
    - Dilepton pair selection
    - Generator-level tau pair selections
    """

    # Chain the reconstruction-level selections from filter submodules
    selections = OrderedDict(
        chain(
            # Reconstruction-level selections
            self.get_instance("triggers").nominal().items(),
            self.get_instance("jet_vetomap").nominal().items(),
            self.get_instance("ll_pair").nominal().items(),
            self.get_instance("bb_pair").nominal().items(),
            # Generator-level selections: taus origin
            self.get_instance("tautau_gen_selection").nominal().items(),
            # Jet category selections
            self.get_instance("jet_categories").nominal().items(),
        )
    )

    # Check if this is a classifier output category
    if self.category_inst.has_tag("clf"):
        # Get the output class name and index and the hypotheses masses
        output_class = self.category_inst.x.output_class
        m_x = self.category_inst.x.m_x
        m_y = self.category_inst.x.m_y
        output_class_index = self.category_inst.x.output_class_index

        # Select events assigned to this output class
        selections[f"clf_{output_class}"] = (
            f"max_score_index_m_x_{m_x}_m_y_{m_y} == {output_class_index}"
        )

    return selections


@Wrapper.wrap
def default_filters_without_bjets(self) -> OrderedDict[str, str]:
    """
    Default filter selection for the analysis.

    This includes the following selections:

    - Trigger selection
    - Jet vetomap veto
    - bb pair selection
    - Dilepton pair selection
    - Generator-level tau pair selections
    """

    # Get the default filters
    filters = self.get_instance("default_filters").nominal()

    # Drop b jet-related selections
    filters.pop("nbtag_selection", None)
    filters.pop("bb_pair_kinematics", None)
    filters.pop("bb_pair_delta_r", None)

    return filters


@Wrapper.wrap
def default_filters_for_normalization_corrections(
    self,
) -> OrderedDict[str, str]:

    # Get the default filters without b jet cuts
    filters = self.get_instance("default_filters_without_bjets").nominal()

    # Add m_ll filter in the di-muon channeel to enhance Z -> ll events
    if self.channel_inst.name == "mm":
        filters["m_ll"] = "(m_vis > 70) && (m_vis < 110)"

    return filters


@Wrapper.wrap
def default_filters_for_fake_factors(self) -> OrderedDict[str, str]:
    """
    Loose preselection used as input for the TauFakeFactors framework.

    Same as the default filters without b jet selections and without the
    opposite-sign, extra lepton veto and lepton isolation requirements, but with the tau-vs-jet ID loosened to the anti-ID working point of the channel, such
    that the application and determination regions can be built downstream
    from the `id_tau_vsJet_*` columns.
    """

    # Get the filters without b jet selections
    filters = self.get_instance("default_filters_without_bjets").nominal()

    # Keep same-sign pairs, they are needed for the QCD and W + jets regions
    filters.pop("ll_pair_os", None)

    # Drop the extra lepton vetoes, events failing them are used in the
    # DR -> SR corrections of the fake factor framework
    for key in ("extraelec_veto", "extramuon_veto", "dilepton_veto"):
        filters.pop(key, None)

    # Drop the lepton isolation requirements, the non-isolated events are
    # needed for the DR -> SR corrections
    for key in list(filters):
        if key.startswith(("electron", "muon")) and key.endswith("_iso"):
            del filters[key]

    # Loosen the tau-vs-jet ID (no effect in channels without hadronic taus)
    if "tau_id_vs_jet" in filters:
        wp = self.channel_inst.x.tau["antiid_vs_jet_wp"]
        indices = {"et": [2], "mt": [2], "tt": [1, 2]}[self.channel_inst.name]
        filters["tau_id_vs_jet"] = " && ".join(
            f"(id_tau_vsJet_{wp}_{i} > 0.5)" for i in indices
        )

    return filters
