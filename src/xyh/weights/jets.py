from collections import OrderedDict

from xyh.core.wrapper import Wrapper


@Wrapper.wrap
def b_jets(self) -> OrderedDict[str, str]:
    """Add b jet identification weight."""
    return OrderedDict([("id_wgt_bjet_shape", "id_wgt_bjet")])
