"""
Channels and categories the analysis is split into.
"""

from order import Channel, UniqueObjectIndex

from ._channels import ch_ee, ch_em, ch_et, ch_mm, ch_mt, ch_tt

# Only expose the channels index
__all__ = ["channels"]

# ------------------------------------------------------------------------------
# Index of all channels of this analysis
# ------------------------------------------------------------------------------

channels = UniqueObjectIndex(
    Channel,
    [
        ch_et,
        ch_mt,
        ch_tt,
        ch_em,
        ch_ee,
        ch_mm,
    ],
)
