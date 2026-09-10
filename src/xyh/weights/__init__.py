from collections import OrderedDict
from itertools import chain

from xyh.core.wrapper import Wrapper

# Import weight submodules to initialize wrapper subclasses
from .event import normalization, pileup
from .jets import b_jets
from .leptons import electrons, hadronic_taus
from .processes import top_pt_reweighting, tt_normalization, z_pt_reweighting
from .triggers import triggers


@Wrapper.wrap
def default(self) -> OrderedDict[str, str]:
    # Chain the reconstruction-level selections from filter submodules
    weights = OrderedDict(
        chain(
            # Experimental weights
            self.get_instance("triggers")().items(),
            self.get_instance("electrons")().items(),
            self.get_instance("muons")().items(),
            self.get_instance("hadronic_taus")().items(),
            self.get_instance("b_jets")().items(),
            self.get_instance("pileup")().items(),
            # Theory weights
            self.get_instance("top_pt_reweighting")().items(),
            self.get_instance("z_pt_reweighting")().items(),
            # Normalization weights
            self.get_instance("normalization")().items(),
            self.get_instance("tt_normalization")().items(),
        )
    )

    return weights
