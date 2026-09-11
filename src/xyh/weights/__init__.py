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
            self.get_instance("trigger_weights")().items(),
            self.get_instance("electron_weights")().items(),
            self.get_instance("muon_weights")().items(),
            self.get_instance("hadronic_tau_weights")().items(),
            self.get_instance("b_jet_weights")().items(),
            self.get_instance("pileup_weights")().items(),
            # Theory weights
            self.get_instance("top_pt_reweighting")().items(),
            self.get_instance("z_pt_reweighting")().items(),
            # Normalization weights
            self.get_instance("normalization")().items(),
            self.get_instance("tt_normalization")().items(),
        )
    )

    return weights
