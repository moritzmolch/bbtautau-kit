"""
Data and simulation campaigns of the analysis.
"""

from order import Campaign


# 2022preEE, NanoAOD v12
cpn_2022_pre_ee_nano_v12 = Campaign(
    name="2022preEE",
    id="+",
    ecm=13.6,
    lumi=7.9804,  # fb^-1
    aux=dict(
        year=2022,
        postfix="preEE",
        runs={
            "C": [355794, 357486],
            "D": [357487, 359021],
        },
        nano_version="v12",
    ),
)


# 2022postEE, NanoAOD v12
cpn_2022_post_ee_nano_v12 = Campaign(
    analysis,
    name="2022postEE",
    id="+",
    year=2022,
    ecm=13.6,
    lumi=26.6717,  # fb^-1
    aux=dict(
        postfix="postEE",
        runs={
            "E": [359022, 360331],
            "F": [360332, 362180],
            "G": [362350, 362760],
        },
        nano_version="v12",
    ),
)


# 2023preBPix, NanoAOD v12
cpn_2023_pre_bpix_nano_v12 = Campaign(
    analysis,
    name="2023preBPix",
    id="+",
    ecm=13.6,
    lumi=18.063,  # fb^-1
    aux=dict(
        year=2023,
        postfix="preBPix",
        runs={
            "C": [367080, 369802],
        },
        nano_version="v12",
    ),
)


# 2023postBPix, NanoAOD v12 
cpn_2023_post_bpix_nano_v12 = Campaign(
    name="2023postBPix",
    id="+",
    ecm=13.6,
    lumi=9.693,  # fb^-1
    aux=dict(
        year=2023,
        postfix="postBPix",
        runs={
            "D": [369803, 372415],
        },
        nano_version="v12",
    ),
)


# 2024, NanoAOD v15
cpn_2024_nano_v15 = Campaign(
    name="2024",
    id="+",
    ecm=13.6,
    lumi=108.83,  # fb^-1
    aux=dict(
        year=2024,
        postfix=None,
        runs={
            "C": [378971, 379411],
            "D": [379412, 380252],
            "E": [380948, 381943],
            "F": [381944, 383779],
            "G": [383780, 385813],
            "H": [385814, 386408],
            "I": [386409, 387121],
        },
        nano_version="v15",
    ),
)


# Container for all campaigns
campaigns = od.UniqueObjectIndex(
    Campaign,
    [
        cpn_2022_pre_ee_nano_v12,
        cpn_2022_post_ee_nano_v12,
        cpn_2023_pre_bpix_nano_v12,
        cpn_2023_post_bpix_nano_v12,
        cpn_2024_nano_v15,
    ]
)
