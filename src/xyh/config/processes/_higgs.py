from order import Process

from ._util import add_process

# TODO These processes might be added:
# # H -> tau tau
# # H -> WW
# "gluglu_h_2w_2l2nu",
# "vbf_h_2w_2l2nu",
# "gluglu_h_2w_lnu2q",
# "vbf_h_2w_lnu2q",
# # H -> bb
# "wminush_h2b_w2q",
# "wminush_h2b_wlnu",
# "wplush_h2b_w2q",
# "wplush_h2b_wlnu",
# "zh_h_2b_z2l",
# "zh_h_2b_z2q
# # H -> ZZ
# "gluglu_h_2z_2l2q",
# "gluglu_h_2z_4l",
# "vbf_h_2z_4l"
# # Remaining HH
# "gluglu_hh_4b",
# "vbf_hh_4b",
# "gluglu_hh_4v",
# "vbf_hh_4v",


def get_higgs_2tau_processes() -> list[Process]:
    """
    Higgs -> tau tau production
    """

    # List of processes
    processes = []

    # Default tags for these processes
    _default_tags = {"background", "h_2tau"}

    # Higgs -> tau tau production; genuine tau tau pairs
    add_process(
        processes,
        name="h_2tau_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # Higgs -> tau tau production; jets faking hadronic taus
    add_process(
        processes,
        name="h_2tau_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_jetfakes"},
    )

    # Higgs -> tau tau production; remaining events (leptons faking hadronic taus
    # and prompt leptons)
    add_process(
        processes,
        name="h_2tau_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes


def get_higgs_2b_processes() -> list[Process]:
    """
    Higgs -> b b production
    """

    # List of processes
    processes = []

    # Default tags for these processes
    _default_tags = {"background", "h_2b"}

    # Higgs -> b b production; genuine tau tau pairs
    add_process(
        processes,
        name="h_2b_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # Higgs -> b b production; jets faking hadronic taus
    add_process(
        processes,
        name="h_2b_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_jetfakes"},
    )

    # Higgs -> b b production; remaining events (leptons faking hadronic taus
    # and prompt leptons)
    add_process(
        processes,
        name="h_2b_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes


def get_tth_processes() -> list[Process]:
    """
    Associated top quark pair + Higgs production
    """

    # List of processes
    processes = []

    # Default tags for these processes
    _default_tags = {"background", "tth"}

    # ttH production; genuine tau tau pairs
    add_process(
        processes,
        name="tth_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # ttH production; jets faking hadronic taus
    add_process(
        processes,
        name="tth_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_jetfakes"},
    )

    # ttH production; remaining events (leptons faking hadronic taus and prompt
    # leptons)
    add_process(
        processes,
        name="tth_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes


def get_hh_2b2tau_processes() -> list[Process]:
    """
    HH -> b b tau tau production
    """

    # List of processes
    processes = []

    # Default tags for these processes
    _default_tags = {"background", "hh_2b2tau"}

    # HH -> b b tau tau production, gluon-gluon fusion
    add_process(
        processes,
        name="gluglu_hh_2b2tau",
        id="+",
        is_data=False,
        tags=_default_tags | {"gluglu_hh_2b2tau"},
    )

    # HH -> b b tau tau production, vector boson fusion
    add_process(
        processes,
        name="vbf_hh_2b2tau",
        id="+",
        is_data=False,
        tags=_default_tags | {"vbf_hh_2b2tau"},
    )

    return processes
