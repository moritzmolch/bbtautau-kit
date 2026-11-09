from order import Process

from ._util import add_process


def get_tt_processes() -> list[Process]:
    """
    Top quark pair production
    """

    # List of processes
    processes = []

    # Default tags, which are added to all tt processes
    _default_tags = {"background", "tt"}

    # tt production; genuine tau tau pairs
    add_process(
        processes,
        name="tt_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # tt production; jets faking hadronic taus
    add_process(
        processes,
        name="tt_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_jetfakes"},
    )

    # tt production; remaining events (leptons faking hadronic taus and prompt
    # leptons)
    add_process(
        processes,
        name="tt_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes


def get_single_t_processes() -> list[Process]:
    """
    Single top quark production
    """

    # List of processes
    processes = []

    # Default tags, which are added to all tt processes
    _default_tags = {"background", "single_t"}

    # Single top quark production; genuine tau tau pairs
    add_process(
        processes,
        name="single_t_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # Single top production; jets faking hadronic taus
    add_process(
        processes,
        name="single_t_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_jetfakes"},
    )

    # Single top production; remaining events (leptons faking hadronic taus and
    # prompt leptons)
    add_process(
        processes,
        name="single_t_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes


def get_ttx_processes() -> list[Process]:
    """
    tt+X production
    """

    # List of processes
    processes = []

    # Default tags, which are added to all tt processes
    _default_tags = {"background", "ttx"}

    # tt+X quark production; genuine tau tau pairs
    add_process(
        processes,
        name="ttx_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # tt+X production; jets faking hadronic taus
    add_process(
        processes,
        name="ttx_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_jetfakes"},
    )

    # tt+X production; remaining events (leptons faking hadronic taus and
    # prompt leptons)
    add_process(
        processes,
        name="ttx_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes


def get_ttxx_processes() -> list[Process]:
    """
    tt+XX production
    """

    # List of processes
    processes = []

    # Default tags, which are added to all tt processes
    _default_tags = {"background", "ttxx"}

    # tt+XX quark production; genuine tau tau pairs
    add_process(
        processes,
        name="ttxx_tautau",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_genuine"},
    )

    # tt+XX production; jets faking hadronic taus
    add_process(
        processes,
        name="ttxx_jetfakes",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_jetfakes"},
    )

    # tt+XX production; remaining events (leptons faking hadronic taus and
    # prompt leptons)
    add_process(
        processes,
        name="ttxx_rem",
        id="+",
        is_data=False,
        tags=_default_tags | {"tautau_remaining"},
    )

    return processes
