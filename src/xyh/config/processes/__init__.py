"""
Physics processes relevant for this analysis.
"""

from itertools import chain

from order import Process, UniqueObjectIndex

from ._data import get_data_processes
from ._ewk import get_vv_processes, get_w_processes, get_z_processes
from ._higgs import (
    get_hh_2b2tau_processes,
    get_higgs_2b_processes,
    get_higgs_2tau_processes,
    get_tth_processes,
)
from ._jetfakes import get_jetfakes_processes
from ._top import get_single_t_processes, get_tt_processes
from ._xyh import get_xyh_processes

# Only expose the processes index
__all__ = ["processes"]

# Merge all processes into a single index
processes = UniqueObjectIndex(
    Process,
    chain(
        # Data
        get_data_processes(),
        # Electroweak processes
        get_z_processes(),
        get_w_processes(),
        get_vv_processes(),
        # Higgs processes
        get_higgs_2tau_processes(),
        get_higgs_2b_processes(),
        get_tth_processes(),
        get_hh_2b2tau_processes(),
        # Jet -> tau_h misidentification
        get_jetfakes_processes(),
        # Top quark processes
        get_tt_processes(),
        get_single_t_processes(),
        # X -> HY signal processes
        get_xyh_processes(),
    ),
)
