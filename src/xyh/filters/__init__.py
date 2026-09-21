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
