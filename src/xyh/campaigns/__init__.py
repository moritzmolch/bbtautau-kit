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
    name="2022_post_ee_nano_v12",
    id="+",
    ecm=13.6,
    lumi=26.674924045,  # fb^-1
    aux=dict(
        year=2022,
        postfix="postEE",
        runs={
            "E": [359022, 360331],
            "F": [360332, 362180],
            "G": [362350, 362760],
        },
        nano_version="v12",
    ),
)
add_datasets(
    cpn_2022_post_ee_nano_v12,
    samples_2022_post_ee_nano_v12,
)


# 2023preBPix, NanoAOD v12
cpn_2023_pre_bpix_nano_v12 = Campaign(
    name="2023_pre_bpix_nano_v12",
    id="+",
    ecm=13.6,
    lumi=17.964217998,  # fb^-1
    aux=dict(
        year=2023,
        postfix="preBPix",
        runs={
            "C": [367080, 369802],
        },
        nano_version="v12",
    ),
)
add_datasets(
    cpn_2023_pre_bpix_nano_v12,
    samples_2023_pre_bpix_nano_v12,
)


# 2023postBPix, NanoAOD v12
cpn_2023_post_bpix_nano_v12 = Campaign(
    name="2023_post_bpix_nano_v12",
    id="+",
    ecm=13.6,
    lumi=9.676737966,  # fb^-1
    aux=dict(
        year=2023,
        postfix="postBPix",
        runs={
            "D": [369803, 372415],
        },
        nano_version="v12",
    ),
)
add_datasets(
    cpn_2023_post_bpix_nano_v12,
    samples_2023_post_bpix_nano_v12,
)


# 2024, NanoAOD v15
cpn_2024_nano_v15 = Campaign(
    name="2024_nano_v15",
    id="+",
    ecm=13.6,
    lumi=109.816515335,  # fb^-1
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
add_datasets(
    cpn_2024_nano_v15,
    samples_2024_nano_v15,
)


# 2025, NanoAOD v15
cpn_2025_nano_v15 = Campaign(
    name="2025_nano_v15",
    id="+",
    ecm=13.6,
    lumi=109.898115287,  # fb^-1
    aux=dict(
        year=2025,
        postfix=None,
        runs={
            "C": [392159, 393609],
            "D": [394286, 395967],
            "E": [395968, 396597],
            "F": [396598, 397853],
            "G": [397854, 398903],
        },
        nano_version="v15",
    ),
)
add_datasets(
    cpn_2025_nano_v15,
    samples_2025_nano_v15,
)


# Container for all campaigns
campaigns = UniqueObjectIndex(
    Campaign,
    [
        cpn_2022_pre_ee_nano_v12,
        cpn_2022_post_ee_nano_v12,
        cpn_2023_pre_bpix_nano_v12,
        cpn_2023_post_bpix_nano_v12,
        cpn_2024_nano_v15,
        cpn_2025_nano_v15,
    ],
)
