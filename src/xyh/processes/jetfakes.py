from order import Process


# ------------------------------------------------------------------------------
# jet -> tau_h misidentification (estimated from data)
# ------------------------------------------------------------------------------


# jet -> tau_h misidentification
jetfakes = Process(
    name="jetfakes",
    id="+",
    is_data=False,
    tags={"background", "tautau_jetfakes"},
)
