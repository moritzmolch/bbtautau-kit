from itertools import product

from xyh.analysis import DECAY_MODES, XY_MASSES


for (y_decay_mode, h_decay_mode), (m_x, m_y) in product(DECAY_MODES, XY_MASSES):

    # Some samples seem to be missing in the production
    # TODO request production of these samples
    if (
        y_decay_mode == "2b"
        and h_decay_mode == "2tau"
        and m_x == 2500
        and m_y == 800
    ):
        continue

    if (
        y_decay_mode == "2tau"
        and h_decay_mode == "2b"
        and m_x == 2500
        and m_y == 90
    ):
        continue

    # Construct the process name
    name = f"xyh_y{y_decay_mode}_h{h_decay_mode}_mx{m_x}_my{m_y}"

    # Create variable dynamically
    locals()[name] = Process(
        name=name,
        id="+",
        is_data=False,
        tags={"signal"},
        aux={
            "is_signal": True,
            "m_x": m_x,
            "m_y": m_y,
            "y_decay_mode": y_decay_mode,
            "h_decay_mode": h_decay_mode,
        },
    )
