from functools import partial
from itertools import product

from order import Category, Channel, Process

from xyh.config.profiles import get_profile


def add_clf_categories(channel_inst: Channel):
    # Filter for processes to only consider signals which are relevant for this
    # category
    def _filter_signal_process(category_inst: Category, process_inst: Process):
        return not process_inst.has_tag("is_signal") or (
            process_inst.x.y_decay_mode == category_inst.x.y_decay_mode
            and process_inst.x.h_decay_mode == category_inst.x.h_decay_mode
            and process_inst.x.m_x == category_inst.x.m_x
            and process_inst.x.m_y == category_inst.x.m_y
        )

    # Classification category, containing events after categorization/classification
    for (y_decay_mode, h_decay_mode), (m_x, m_y) in product(
        get_profile().decay_modes,
        get_profile().xy_masses,
    ):
        for name, label in [
            ("jetfakes", r"$\text{j} \to \tau_{\text{h}}$"),
            ("tt", r"$\text{t}\bar{\text{t}}$"),
            ("xyh", r"$\text{X} \to \text{H}\text{Y}$"),
            ("ztt", r"$\text{Z}(\tau\tau)$"),
        ]:
            # Create the classifier category
            category_inst = channel_inst.add_category(
                name=f"{channel_inst.name}_clf_{name}_xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}",
                id="+",
                label=f"{channel_inst.label} channel, {label} category",
                label_short=f"{channel_inst.label}, {label}",
            )

            # Add process filter
            category_inst.set_aux(
                "filter_process_inst",
                partial(_filter_signal_process, category_inst=category_inst),
            )
