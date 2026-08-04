"""
Physics processes relevant for this analysis.
"""

from itertools import chain

from order import Process, UniqueObjectIndex

# Import process indices from submodules
from .data import processes as data_processes
from .ewk import processes as ewk_processes
from .higgs import processes as higgs_processes
from .jetfakes import processes as jetfakes_processes
from .top import processes as top_processes
from .xyh import processes as xyh_processes

# Merge all processes into a single index
processes = UniqueObjectIndex(
    Process,
    chain(
        data_processes.values(),
        ewk_processes.values(),
        higgs_processes.values(),
        jetfakes_processes.values(),
        top_processes.values(),
        xyh_processes.values(),
    ),
)
