from itertools import product

from order import Process, UniqueObjectIndex

from xyh.config.analysis import DECAY_MODES, XY_MASSES

# Index of signal processes
processes = UniqueObjectIndex(Process, [])


# ------------------------------------------------------------------------------
# X -> HY -> b b tau tau signal processes
# ------------------------------------------------------------------------------


# X -> HY -> b b tau tau parent process
xyh = processes.add(
    name="xyh",
    id="+",
    is_data=False,
    tags={"signal"},
    aux={
        "is_signal": True,
        "parameter_names": ["y_decay_mode", "h_decay_mode", "m_x", "m_y"],
        "parameter_values": [
            (dy, dh, x, y)
            for (dy, dh), (x, y) in product(DECAY_MODES, XY_MASSES)
        ],
    },
)


for (y_decay_mode, h_decay_mode), (m_x, m_y) in product(DECAY_MODES, XY_MASSES):
    # TODO Some samples seem to be missing in the production. Request production
    # of them.
    if (
        y_decay_mode == "y2b"
        and h_decay_mode == "h2tau"
        and m_x == 2500
        and m_y == 800
    ):
        continue
    if (
        y_decay_mode == "y2tau"
        and h_decay_mode == "h2b"
        and m_x == 2500
        and m_y == 90
    ):
        continue

    # Add the process for this specific hypothesis to the X -> HY parent
    # processs
    name = f"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}"
    locals()[name] = processes.add(
        name=name,
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
