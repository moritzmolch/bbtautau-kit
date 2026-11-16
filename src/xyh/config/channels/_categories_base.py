from order import Channel


def add_base_category(channel_inst: Channel):
    # Base category, containing all events before categorization/classification
    channel_inst.add_category(
        name=f"{channel_inst.name}_base",
        label=f"{channel_inst.label} (base selection)",
        label_short=f"{channel_inst.label}",
    )


def add_ff_presel_category(channel_inst: Channel):
    # Loose preselection category for the TauFakeFactors framework (loose
    # tau-vs-jet ID, no b jet requirements); only used by the
    # `fake_factors` inventory
    channel_inst.add_category(
        name=f"{channel_inst.name}_ff_presel",
        label=f"{channel_inst.label} (fake factor preselection)",
        label_short=f"{channel_inst.label}",
    )
