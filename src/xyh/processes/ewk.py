from order import Process


# ------------------------------------------------------------------------------
# Z -> leptons + jets production
# ------------------------------------------------------------------------------


# Default tags to be used for these processes
_default_tags = {"background", "z"}
_default_tags_light = _default_tags | {"ee", "mumu"}
_default_tags_tau = _default_tags | {"tautau"}


# Z -> light leptons + jets production; genuine tau tau pairs
z_2e_2mu_tautau = Process(
    name="z_2e_2mu_tautau",
    id="+",
    is_data=False,
    tags=_default_tags_light | {"tautau_genuine"},
)


# Z -> light leptons + jets production; jets faking hadronic taus
z_2e_2mu_jetfakes = Process(
    name="z_2e_2mu_jetfakes",
    id="+",
    is_data=False,
    tags=_default_tags_light | {"tautau_jetfakes"},
)


# Z -> light leptons + jets production; remaining events (leptons faking
# hadronic taus and prompt leptons)
z_2e_2mu_rem = Process(
    name="z_2e_2mu_rem",
    id="+",
    is_data=False,
    tags=_default_tags_light | {"tautau_remaining"},
)


# Z -> tau leptons + jets production; genuine tau tau pairs
z_2tau_tautau = Process(
    name="z_2tau_tautau",
    id="+",
    is_data=False,
    tags=_default_tags_light | {"tautau_genuine"},
)


# Z -> tau leptons + jets production; jets faking hadronic taus
z_2tau_jetfakes = Process(
    name="z_2tau_jetfakes",
    id="+",
    is_data=False,
    tags=_default_tags_light | {"tautau_jetfakes"},
)


# Z -> tau leptons + jets production; remaining events (leptons faking
# hadronic taus and prompt leptons)
z_2tau_rem = Process(
    name="z_2tau_rem",
    id="+",
    is_data=False,
    tags=_default_tags_light | {"tautau_remaining"},
)


# ------------------------------------------------------------------------------
# W -> leptons + jets production
# ------------------------------------------------------------------------------


# Default tags to be used for these processes
_default_tags = {"background", "w"}


# W -> leptons + jets production; genuine tau tau pairs
w_lnu_tautau = Process(
    name="w_lnu_tautau",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_genuine"},
)


# W (-> ell nu) production -- jets faking hadronic taus
w_lnu_jetfakes = Process(
    name="w_lnu_jetfakes",
    id="+",
    is_data=False,
    tags={"background", "w", "tautau_jetfakes"},
)


# W -> leptons + jets production; remaining events (leptons faking
# hadronic taus and prompt leptons)
w_lnu_rem = Process(
    name="w_lnu_rem",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_remaining"},
)


# ------------------------------------------------------------------------------
# Diboson production
# ------------------------------------------------------------------------------


# Default tags to be used for these processes
_default_tags = {"background", "vv"}


# Diboson production; genuine tau tau pairs
vv_tautau = Process(
    name="vv_tautau",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_genuine"}
)


# Diboson production; jets faking hadronic taus
vv_jetfakes = Process(
    name="vv_jetfakes",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_jetfakes"},
)


# Diboson production; remaining events (leptons faking hadronic taus and prompt
# leptons)
vv_rem = Process(
    name="vv_rem",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_remaining"},
)
