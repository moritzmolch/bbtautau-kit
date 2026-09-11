from order import Process, UniqueObjectIndex

# Index of data processes
processes = UniqueObjectIndex(Process, [])


# ------------------------------------------------------------------------------
# Observed data
# ------------------------------------------------------------------------------


def get_data_processes() -> list[Process]:
    # General data process (mainly needed for statistical inference)
    data = processes.add(
        name="data",
        id="+",
        is_data=True,
        tags={"data"},
    )

    # # EGamma streams
    # egamma = data.add_process(
    #     name="egamma",
    #     id="+",
    #     is_data=True,
    # )

    # # Muon streams
    # muon = data.add_process(
    #     name="muon",
    #     id="+",
    #     is_data=True,
    # )

    # # Tau streams
    # tau = data.add_process(
    #     name="tau",
    #     id="+",
    #     is_data=True,
    # )

    return [data]
