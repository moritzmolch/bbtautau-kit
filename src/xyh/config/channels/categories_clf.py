from order import Channel

from xyh.config.channels.util import CategoryProxy


def add_clf_category(
    channel_inst: Channel,
):

    # Classification category, containing events after categorization/classification
    for name, label in [
        ("jetfakes", r"$\text{j} \to \tau_{\text{h}}$"),
        ("tt", r"$\text{t}\bar{\text{t}}$"),
        ("xyh", r"$\text{X} \to \text{H}\text{Y}$"),
        ("ztt", r"$\text{Z}(\tau\tau)$"),
    ]:
        category_inst = channel_inst.add_category(
            CategoryProxy(
                name=f"{channel_inst.name}_clf_{name}_xyh_{{y_decay_mode}}_{{h_decay_mode}}_mx{{m_x}}_my{{m_y}}",
                id="+",
                label=f"{channel_inst.name}, {label} category",
                label_short=f"{channel_inst.name}, {label}",
            )
        )

    return category_inst
