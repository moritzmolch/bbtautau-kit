from order import Process, UniqueObjectIndex

# Index of top quark processes
processes = UniqueObjectIndex(Process, [])


# ------------------------------------------------------------------------------
# Top quark pair production
# ------------------------------------------------------------------------------


# Default tags, which are added to all tt processes
_default_tags = {"background", "tt"}


# tt production; genuine tau tau pairs
tt_tautau = processes.add(
    name="tt_tautau",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_genuine"},
)


# tt production; jets faking hadronic taus
tt_jetfakes = processes.add(
    name="tt_jetfakes",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_jetfakes"},
)


# tt production; remaining events (leptons faking hadronic taus and prompt
# leptons)
tt_rem = processes.add(
    name="tt_rem",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_remaining"},
)


# ------------------------------------------------------------------------------
# Single top quark production
# ------------------------------------------------------------------------------


# Default tags, which are added to all tt processes
_default_tags = {"background", "single_t"}


# Single top quark production; genuine tau tau pairs
single_t_tautau = processes.add(
    name="single_t_tautau",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_genuine"},
)


# Single top production; jets faking hadronic taus
single_t_jetfakes = processes.add(
    name="single_t_jetfakes",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_jetfakes"},
)


# Single top production; remaining events (leptons faking hadronic taus and
# prompt leptons)
single_t_rem = processes.add(
    name="single_t_rem",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_remaining"},
)
