from order import Process, UniqueObjectIndex

# Index of jetfakes processes
processes = UniqueObjectIndex(Process, [])


# ------------------------------------------------------------------------------
# jet -> tau_h misidentification (estimated from data)
# ------------------------------------------------------------------------------


# jet -> tau_h misidentification
jetfakes = processes.add(
    name="jetfakes",
    id="+",
    is_data=False,
    tags={"background", "tautau_jetfakes"},
)
