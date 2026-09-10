"""
Analysis instance of the X &rarr; YH &rarr; bb&tau;&tau; search.

Attributes
----------

DECAY_MODES: list[tuple[str, str]]
    List of decay mode configurations. The first element defines the Y boson
    decay, the second one the H boson decay.

XY_MASSES: list[tuple[int, int]]
    List of mass combinations. The first element defines the X boson mass, the
    second one the Y boson mass.
"""

from order import Analysis

from xyh.config.campaigns import campaigns
from xyh.config.config import create_xyh_bbtautau_config
from xyh.config.profiles import XYHProfile, get_profile


def create_xyh_analysis(
    profile: XYHProfile,
) -> Analysis:
    """
    Create a new analysis instance of the X &rarr; YH &rarr; bb&tau;&tau;
    analysis for given signal hypothesis.

    The created analysis instance will have the name
    `"xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}"`. The details about
    the signal hypothesis are stored in the `aux` object.

    Parameters
    ----------

    y_decay_mode: str
        Decay mode of the Y boson. Must be `"y2b"` or `"y2tau"`.

    h_decay_mode: str
        Decay mode of the H boson. Must be `"h2b"` or `"h2tau"`.

    m_x: int
        X boson mass of the signal hypothesis.

    m_y: int
        Y boson mass of the signal hypothesis.

    Returns
    -------

    order.Analysis
        The analysis instance.
    """

    # Create the analysis instance
    analysis_inst = Analysis(
        name="xyh",
        id="+",
        aux={
            "xy_masses": profile.xy_masses,
            "decay_modes": profile.decay_modes,
            "missing_signal_samples": profile.missing_signal_samples,
        },
    )

    # Add configuration for all campaigns found in corresponding submodule
    for campaign_inst in campaigns().values():
        create_xyh_bbtautau_config(analysis_inst, campaign_inst)

    return analysis_inst


analysis_inst = create_xyh_analysis(get_profile())
