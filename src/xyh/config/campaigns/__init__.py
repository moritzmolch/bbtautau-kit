"""
Data-taking campaigns of the analysis, including corresponding data and
simulation sample metadata.
"""

from order import Campaign, UniqueObjectIndex

from .cpn_2022_post_ee_nano_v12 import cpn_2022_post_ee_nano_v12
from .cpn_2022_pre_ee_nano_v12 import cpn_2022_pre_ee_nano_v12
from .cpn_2023_post_bpix_nano_v12 import cpn_2023_post_bpix_nano_v12
from .cpn_2023_pre_bpix_nano_v12 import cpn_2023_pre_bpix_nano_v12
from .cpn_2024_nano_v15 import cpn_2024_nano_v15
from .cpn_2025_nano_v15 import cpn_2025_nano_v15

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
