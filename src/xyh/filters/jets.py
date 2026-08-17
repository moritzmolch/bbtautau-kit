from collections import OrderedDict

from xyh.filters.wrapper import Wrapper


@Wrapper.wrap
def jet_vetomap(self) -> OrderedDict[str, str]:
    """
    Apply vetoes on events with jets in vetomap regions.
    """

    # Storage for all vetoes
    selections = OrderedDict()

    # Jet vetomap selection
    selections["jet_vetomap_veto"] = "(jet_vetomap_veto < 0.5)"

    return selections


@Wrapper.wrap
def bb_pair(self) -> OrderedDict[str, str]:
    """
    Kinematic and geometric selection of the resolved bb pair.
    """

    # Storage for all bb pair selections
    selections = OrderedDict()

    # Select events with at least one medium b-tagged jet
    selections["nbtag_selection"] = "(n_bjets >= 1)"

    # Select events with at least one b-tagged jets and at least two valid b
    # candidates
    selections["bb_pair_kinematics"] = "(bpair_pt_1 > 20) && (bpair_pt_2 > 20)"

    # Require a minimum spatial separation of the two b candidates
    selections["bb_pair_delta_r"] = "(bpair_deltaR > 0.4)"

    return selections
