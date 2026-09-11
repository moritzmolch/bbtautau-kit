"""
Process sets that define groups of processes for plots and for statistical
inference.
"""

from dataclasses import dataclass, field

from xyh.config.profiles import get_profile

# Only expose the process sets dictionary and the interface definitions
__all__ = ["process_sets", "ProcessGroup", "ProcessSet"]


@dataclass
class ProcessGroup:
    name: str
    processes: list[str]
    label: str
    color: str
    scale_factor: float | None = field(default=None)


@dataclass
class ProcessSet:
    name: str
    data: list[ProcessGroup] = field(default_factory=list)
    signals: list[ProcessGroup] = field(default_factory=list)
    backgrounds: list[ProcessGroup] = field(default_factory=list)


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
        name=f"xyh_y{y_decay_mode}_h{h_decay_mode}_mx{m_x}_my{m_y}",
        processes=[f"xyh_y{y_decay_mode}_h{h_decay_mode}_mx{m_x}_my{m_y}"],
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

dy_2l = ProcessGroup(
    name="dy_2l",
    processes=[
        "dy_2e_2mu_tautau",
        "dy_2e_2mu_rem",
        "dy_2tau_tautau",
        "dy_2tau_rem",
    ],
    label="DY",
    color="#ffa90e",
)

dy_2l_jetfakes = ProcessGroup(
    name="dy_2l_jetfakes",
    processes=["dy_2e_2mu_jetfakes", "dy_2tau_jetfakes"],
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
    processes=["single_h_tautau", "single_h_rem"],
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
    processes=["single_h_jetfakes", "vv_jetfakes"],
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

process_sets = {
    "default": ProcessSet(
        name="default",
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
            dy_2l,
            w_lnu,
            single_t,
            single_h,
            vv,
            jetfakes,
        ],
    ),
    "mc": ProcessSet(
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
            dy_2l,
            dy_2l_jetfakes,
            w_lnu,
            w_lnu_jetfakes,
            single_t,
            single_t_jetfakes,
            single_h,
            vv,
            remaining_jetfakes,
        ],
    ),
}
