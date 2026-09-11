from order import Process

from ._util import add_process


def get_z_processes() -> list[Process]:
    """
    Z -> leptons + jets production
    """

    # List of processes
    processes = []

    # Default tags to be used for these processes
    _default_tags = {"background", "z"}
    _default_tags_light = _default_tags | {"ee", "mumu"}
    _default_tags_tau = _default_tags | {"tautau"}

    # Z -> light leptons + jets production; genuine tau tau pairs
    add_process(
        processes,
        name="z_2e_2mu_tautau",
        id="+",
        is_data=False,
        tags=_default_tags_light | {"tautau_genuine"},
    )

    # Z -> light leptons + jets production; jets faking hadronic taus
    add_process(
        processes,
        name="z_2e_2mu_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags_light | {"tautau_jetfakes"},
    )

    # Z -> light leptons + jets production; remaining events (leptons faking
    # hadronic taus and prompt leptons)
    add_process(
        processes,
        name="z_2e_2mu_rem",
        id="+",
        is_data=False,
        tags=_default_tags_light | {"tautau_remaining"},
    )

    # Z -> tau leptons + jets production; genuine tau tau pairs
    add_process(
        processes,
        name="z_2tau_tautau",
        id="+",
        is_data=False,
        tags=_default_tags_tau | {"tautau_genuine"},
    )

    # Z -> tau leptons + jets production; jets faking hadronic taus
    add_process(
        processes,
        name="z_2tau_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags_tau | {"tautau_jetfakes"},
    )

    # Z -> tau leptons + jets production; remaining events (leptons faking
    # hadronic taus and prompt leptons)
    add_process(
        processes,
        name="z_2tau_rem",
        id="+",
        is_data=False,
        tags=_default_tags_tau | {"tautau_remaining"},
    )

    return processes


def get_w_processes() -> list[Process]:
    """
    W -> leptons + jets production
    """
    # List of processes
    processes = []

    # Default tags to be used for these processes
    _default_tags = {"background", "w"}

    # W -> leptons + jets production; genuine tau tau pairs
    add_process(
        processes,
        name="w_lnu_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # W (-> ell nu) production -- jets faking hadronic taus
    add_process(
        processes,
        name="w_lnu_jetfakes",
        id="+",
        is_data=False,
        tags={"background", "w", "tautau_jetfakes"},
    )

    # W -> leptons + jets production; remaining events (leptons faking
    # hadronic taus and prompt leptons)
    add_process(
        processes,
        name="w_lnu_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes


def get_vv_processes() -> list[Process]:
    """
    Diboson production
    """

    # List of processes
    processes = []

    # Default tags to be used for these processes
    _default_tags = {"background", "vv"}

    # Diboson production; genuine tau tau pairs
    add_process(
        processes,
        name="vv_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # Diboson production; jets faking hadronic taus
    add_process(
        processes,
        name="vv_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_jetfakes"},
    )

    # Diboson production; remaining events (leptons faking hadronic taus and prompt
    # leptons)
    add_process(
        processes,
        name="vv_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes
