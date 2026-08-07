"""
Channels of the analysis.
"""

from order import Channel

# Channel for electron+hadronic tau final state
ch_et = Channel(
    name="et",
    id="+",
    label=r"$\text{e}\tau_{\text{h}}$",
)


# Channel for muon+hadronic tau final state
ch_mt = Channel(
    name="mt",
    id="+",
    label=r"$\mu\tau_{\text{h}}$",
)


# Channel for hadronic tau+hadronic tau final state
ch_tt = Channel(
    name="tt",
    id="+",
    label=r"$\tau_{\text{h}}\tau_{\text{h}}$",
)


# Channel for electron+muon final state (control channel for tt)
ch_em = Channel(
    name="em",
    id="+",
    label=r"$\text{e}\mu$",
)


# Channel for electron+electron final state (control channel for Z production)
ch_ee = Channel(
    name="ee",
    id="+",
    label=r"$\text{e}\text{e}$",
)


# Channel for electron+muon final state (control channel for Z production)
ch_mm = Channel(
    name="mm",
    id="+",
    label=r"$\mu\mu$",
)
