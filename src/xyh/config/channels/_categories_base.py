from order import Channel


def add_base_category(channel_inst: Channel):
    # Base category, containing all events before categorization/classification
    category_inst = channel_inst.add_category(
        name=f"{channel_inst.name}_base",
        label=f"{channel_inst.name} (base selection)",
        label_short=f"{channel_inst.name}",
    )
