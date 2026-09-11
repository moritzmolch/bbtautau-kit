from order import Process

from xyh.config.profiles import get_profile

from ._util import add_process


def get_xyh_processes() -> list[Process]:
    """
    X -> HY -> b b tau tau signal processes
    """

    # List of processes
    processes = []

    for (y_decay_mode, h_decay_mode), (
        m_x,
        m_y,
    ) in get_profile().iterate_signal_parameters():
        # Add the process for this specific hypothesis to the X -> HY parent
        # processs
        add_process(
            name=f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}",
            id="+",
            is_data=False,
            tags=xyh.tags,
            aux={
                "is_signal": True,
                "y_decay_mode": y_decay_mode,
                "h_decay_mode": h_decay_mode,
                "m_x": m_x,
                "m_y": m_y,
            },
        )
