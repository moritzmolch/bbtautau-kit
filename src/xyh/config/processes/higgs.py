from order import Process, UniqueObjectIndex

# Index of Higgs processes
processes = UniqueObjectIndex(Process, [])


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


# ------------------------------------------------------------------------------
# Higgs -> tau tau production
# ------------------------------------------------------------------------------


# Default tags for these processes
_default_tags = {"background", "h_2tau"}


# Higgs -> tau tau production; genuine tau tau pairs
h_2tau_tautau = processes.add(
    name="h_2tau_tautau",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_genuine"},
)


# Higgs -> tau tau production; jets faking hadronic taus
h_2tau_jetfakes = processes.add(
    name="h_2tau_jetfakes",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_jetfakes"},
)


# Higgs -> tau tau production; remaining events (leptons faking hadronic taus
# and prompt leptons)
h_2tau_rem = processes.add(
    name="h_2tau_rem",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_remaining"},
)


# ------------------------------------------------------------------------------
# Higgs -> b b production
# ------------------------------------------------------------------------------


# Default tags for these processes
_default_tags = {"background", "h_2b"}


# Higgs -> b b production; genuine tau tau pairs
h_2b_tautau = processes.add(
    name="h_2b_tautau",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_genuine"},
)


# Higgs -> b b production; jets faking hadronic taus
h_2b_jetfakes = processes.add(
    name="h_2b_jetfakes",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_jetfakes"},
)


# Higgs -> b b production; remaining events (leptons faking hadronic taus
# and prompt leptons)
h_2b_rem = processes.add(
    name="h_2b_rem",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_remaining"},
)


# ------------------------------------------------------------------------------
# Associated top quark pair + Higgs production
# ------------------------------------------------------------------------------


# Default tags for these processes
_default_tags = {"background", "tth"}


# ttH production; genuine tau tau pairs
tth_tautau = processes.add(
    name="tth_tautau",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_genuine"},
)


# ttH production; jets faking hadronic taus
tth_jetfakes = processes.add(
    name="tth_jetfakes",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_jetfakes"},
)


# ttH production; remaining events (leptons faking hadronic taus and prompt
# leptons)
tth_rem = processes.add(
    name="tth_rem",
    id="+",
    is_data=False,
    tags=_default_tags | {"tautau_remaining"},
)


# ------------------------------------------------------------------------------
# HH -> b b tau tau production
# ------------------------------------------------------------------------------


# Default tags for these processes
_default_tags = {"background", "hh_2b2tau"}


# HH -> b b tau tau production, gluon-gluon fusion
gluglu_hh_2b2tau = processes.add(
    name="gluglu_hh_2b2tau",
    id="+",
    is_data=False,
    tags=_default_tags | {"gluglu_hh_2b2tau"},
)


# HH -> b b tau tau production, vector boson fusion
vbf_hh_2b2tau = processes.add(
    name="vbf_hh_2b2tau",
    id="+",
    is_data=False,
    tags=_default_tags | {"vbf_hh_2b2tau"},
)
