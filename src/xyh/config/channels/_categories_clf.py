from functools import partial

from order import Category, Channel, Process

from xyh.config.profiles import get_profile


def add_clf_categories(channel_inst: Channel):
    # Filter for processes to only consider signals which are relevant for this
    # category
    def _skip_signal_process(category_inst: Category, process_inst: Process):
        return process_inst.has_tag("signal") and not (
            process_inst.x.y_decay_mode == category_inst.x.y_decay_mode
            and process_inst.x.h_decay_mode == category_inst.x.h_decay_mode
            and process_inst.x.m_x == category_inst.x.m_x
            and process_inst.x.m_y == category_inst.x.m_y
        )

    # Classification category, containing events after categorization/classification
    for (y_decay_mode, h_decay_mode), (
        m_x,
        m_y,
    ) in get_profile().iterate_signal_parameters():
        for i, (name, label) in enumerate(
            [
                ("xyh", r"$\text{X} \to \text{H}\text{Y}$"),
                ("t_tt", r"$\text{t}+\text{t}\bar{\text{t}}$"),
                ("z2tau", r"$\text{Z}(\tau\tau)$"),
                ("jetfakes", r"$\text{j} \to \tau_{\text{h}}$"),
            ]
        ):
            # Create the classifier category
            category_inst = channel_inst.add_category(
                name=f"{channel_inst.name}_clf_{name}_xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}",
                id="+",
                label=f"{channel_inst.label} channel, {label} class",
                label_short=f"{channel_inst.label}, {label}",
                tags={"clf"},
            )

            # Add process filter and metadata
            category_inst.aux = {
                "skip_process_inst": partial(
                    _skip_signal_process, category_inst
                ),
                "output_class": name,
                "output_class_index": i,
                "m_x": m_x,
                "m_y": m_y,
                "y_decay_mode": y_decay_mode,
                "h_decay_mode": h_decay_mode,
            }
