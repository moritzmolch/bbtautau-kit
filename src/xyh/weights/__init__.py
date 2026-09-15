from collections import OrderedDict
from itertools import chain

from xyh.core.wrapper import Wrapper

# Import weight submodules to initialize wrapper subclasses
from .event import normalization, pileup_weights
from .jets import b_jet_weights
from .leptons import electron_weights, hadronic_tau_weights, muon_weights
from .processes import top_pt_reweighting, tt_normalization, z_pt_reweighting
from .triggers import trigger_weights


@Wrapper.wrap
def default_weights(self) -> OrderedDict[str, str]:
    # Chain the reconstruction-level selections from filter submodules
    weights = OrderedDict(
        chain(
            # Experimental weights
            self.get_instance("trigger_weights").nominal().items(),
            self.get_instance("electron_weights").nominal().items(),
            self.get_instance("muon_weights").nominal().items(),
            self.get_instance("hadronic_tau_weights").nominal().items(),
            self.get_instance("b_jet_weights").nominal().items(),
            self.get_instance("pileup_weights").nominal().items(),
            # Theory weights
            self.get_instance("top_pt_reweighting").nominal().items(),
            self.get_instance("z_pt_reweighting").nominal().items(),
            # Normalization weights
            self.get_instance("normalization").nominal().items(),
            self.get_instance("tt_normalization").nominal().items(),
        )
    )

    return weights
