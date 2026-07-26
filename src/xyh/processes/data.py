from order import Process


# ------------------------------------------------------------------------------
# Observed data
# ------------------------------------------------------------------------------


# General data process (mainly needed for statistical inference)
data = Process(
    name="data",
    id="+",
    is_data=True,
)


# EGamma streams
egamma = data.add_process(
    name="egamma",
    id="+",
    is_data=True,
)


# Muon streams
muon = data.add_process(
    name="muon",
    id="+",
    is_data=True,
)


# Tau streams
tau = data.add_process(
    name="tau",
    id="+",
    is_data=True,
)
