"""
Process sets that define groups of processes for plots and for statistical
inference.
"""

from order import Campaign, Channel

from xyh.config.profiles import get_profile
from xyh.core.config import ProcessGroup, ProcessSet

# Only expose the process sets function
__all__ = ["get_process_set"]


# ------------------------------------------------------------------------------
# Generic process groups
# ------------------------------------------------------------------------------

data = ProcessGroup(
    name="data",
    processes=["data"],
    label="Data",
    color="#000000",
)


def xyh(y_decay_mode, h_decay_mode, m_x, m_y) -> ProcessGroup:
    return ProcessGroup(
        name=f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}",
        processes=[f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}"],
        label="X $\\to$ HY",
        color="#bd1f01",
    )


tt = ProcessGroup(
    name="tt",
    processes=["tt_tautau", "tt_rem"],
    label="$\\text{t}\\bar{\\text{t}}$",
    color="#3f90da",
)

tt_jetfakes = ProcessGroup(
    name="tt_jetfakes",
    processes=["tt_jetfakes"],
    label="$\\text{t}\\bar{\\text{t}}$ ($\\text{j} \\to \\tau_{\\text{h}}$)",
    color="#6da4daff",
)

z_2l = ProcessGroup(
    name="z_2l",
    processes=[
        "z_2e_2mu_tautau",
        "z_2e_2mu_rem",
        "z_2tau_tautau",
        "z_2tau_rem",
    ],
    label="DY",
    color="#ffa90e",
)

z_2l_jetfakes = ProcessGroup(
    name="z_2l_jetfakes",
    processes=["z_2e_2mu_jetfakes", "z_2tau_jetfakes"],
    label="DY ($\\text{j} \\to \\tau_{\\text{h}}$)",
    color="#ffebc0",
)

w_lnu = ProcessGroup(
    name="w_lnu",
    processes=["w_lnu_tautau", "w_lnu_rem"],
    label="W",
    color="#92dadd",
)

w_lnu_jetfakes = ProcessGroup(
    name="w_lnu_jetfakes",
    processes=["w_lnu_jetfakes"],
    label="W ($\\text{j} \\to \\tau_{\\text{h}}$)",
    color="#92dadd",
)

single_t = ProcessGroup(
    name="single_t",
    processes=["single_t_tautau", "single_t_rem"],
    label="Single $\\text{t}$",
    color="#e86300",
)

single_t_jetfakes = ProcessGroup(
    name="single_t_jetfakes",
    processes=["single_t_jetfakes"],
    label="Single $\\text{t}$ ($\\text{j} \\to \\tau_{\\text{h}}$)",
    color="#e86300",
)

single_h = ProcessGroup(
    name="single_h",
    processes=[
        # "h_2tau_tautau",
        # "h_2tau_rem",
        "h_2b_tautau",
        "h_2b_rem",
    ],
    label="$\\text{H}$",
    color="#94a4a2",
)

vv = ProcessGroup(
    name="vv",
    processes=["vv_tautau", "vv_rem"],
    label="$\\text{V}\\text{V}$",
    color="#b9ac70",
)

remaining_jetfakes = ProcessGroup(
    name="remaining_jetfakes",
    processes=["h_2tau_jetfakes", "h_2b_jetfakes", "vv_jetfakes"],
    label="$\\text{H}$, $\\text{V}\\text{V}$ ($\\text{j} \\to \\tau_{\\text{h}}$)",
    color="#a96b59",
)

jetfakes = ProcessGroup(
    name="jetfakes",
    processes=["jetfakes"],
    label="Jet $\\to \\tau_{\\text{h}}$",
    color="#a96b59",
)

# -----------------------------------------------------------------------------
# Process sets
# -----------------------------------------------------------------------------


def get_process_set(
    name: str, campaign_inst: Campaign, channel_inst: Channel
) -> ProcessSet:
    # Process set for et, mt, and tt scopes; jet -> tau_h fakes are estimated
    # from data
    process_set_jetfakes = ProcessSet(
        name="default",
        data=[data],
        signals=[
            xyh(y_decay_mode, h_decay_mode, m_x, m_y)
            for (y_decay_mode, h_decay_mode), (
                m_x,
                m_y,
            ) in get_profile().iterate_signal_parameters(
                campaign=campaign_inst.name
            )
        ],
        backgrounds=[
            tt,
            z_2l,
            w_lnu,
            single_t,
            single_h,
            vv,
            jetfakes,
        ],
    )

    # Process set with all processes modelled using MC
    process_set_mc = ProcessSet(
        name="mc",
        data=[data],
        signals=[
            xyh(y_decay_mode, h_decay_mode, m_x, m_y)
            for (y_decay_mode, h_decay_mode), (
                m_x,
                m_y,
            ) in get_profile().iterate_signal_parameters()
        ],
        backgrounds=[
            tt,
            tt_jetfakes,
            z_2l,
            z_2l_jetfakes,
            # w_lnu,
            # w_lnu_jetfakes,
            single_t,
            single_t_jetfakes,
            # single_h,
            # vv,
            # remaining_jetfakes,
        ],
    )

    process_sets = {
        "default": {
            "et": process_set_jetfakes,
            "mt": process_set_jetfakes,
            "tt": process_set_jetfakes,
            "em": process_set_mc,
            "ee": process_set_mc,
            "mm": process_set_mc,
        },
        "mc": {
            "et": process_set_jetfakes,
            "mt": process_set_jetfakes,
            "tt": process_set_jetfakes,
            "em": process_set_mc,
            "ee": process_set_mc,
            "mm": process_set_mc,
        },
    }

    # Get the process set for the given name and channel
    if name not in process_sets:
        raise ValueError(f"Process set '{name}' not found.")
    if channel_inst.name not in process_sets[name]:
        raise ValueError(
            f"Channel '{channel_inst.name}' not found in process set '{name}'."
        )

    return process_sets[name][channel_inst.name]
