import os
from collections.abc import Generator
from dataclasses import dataclass
from functools import cache
from itertools import product

# Decay modes of the Y and H bosons
DECAY_MODES = [
    # (<Y decay mode>, <H decay mode>)
    ("y2b", "h2tau"),
    ("y2tau", "h2b"),
]


# Masses of the X and Y bosons
XY_MASSES = [
    # (m_x, m_y)
    (300, 60),
    (300, 70),
    (300, 80),
    (300, 90),
    (300, 95),
    (300, 100),
    (300, 150),
    (400, 60),
    (400, 70),
    (400, 80),
    (400, 90),
    (400, 95),
    (400, 100),
    (400, 150),
    (400, 200),
    (500, 60),
    (500, 70),
    (500, 80),
    (500, 90),
    (500, 95),
    (500, 100),
    (500, 150),
    (500, 200),
    (500, 300),
    (550, 60),
    (550, 70),
    (550, 80),
    (550, 90),
    (550, 95),
    (550, 100),
    (550, 150),
    (550, 200),
    (550, 300),
    (550, 400),
    (600, 60),
    (600, 70),
    (600, 80),
    (600, 90),
    (600, 95),
    (600, 100),
    (600, 150),
    (600, 200),
    (600, 300),
    (600, 400),
    (650, 60),
    (650, 70),
    (650, 80),
    (650, 90),
    (650, 95),
    (650, 100),
    (650, 150),
    (650, 200),
    (650, 300),
    (650, 400),
    (650, 500),
    (700, 60),
    (700, 70),
    (700, 80),
    (700, 90),
    (700, 95),
    (700, 100),
    (700, 150),
    (700, 200),
    (700, 300),
    (700, 400),
    (700, 500),
    (800, 60),
    (800, 70),
    (800, 80),
    (800, 90),
    (800, 95),
    (800, 100),
    (800, 150),
    (800, 200),
    (800, 300),
    (800, 400),
    (800, 500),
    (800, 600),
    (900, 60),
    (900, 70),
    (900, 80),
    (900, 90),
    (900, 95),
    (900, 100),
    (900, 150),
    (900, 200),
    (900, 300),
    (900, 400),
    (900, 500),
    (900, 600),
    (1000, 60),
    (1000, 70),
    (1000, 80),
    (1000, 90),
    (1000, 95),
    (1000, 100),
    (1000, 150),
    (1000, 200),
    (1000, 300),
    (1000, 400),
    (1000, 500),
    (1000, 600),
    (1000, 800),
    (1200, 60),
    (1200, 70),
    (1200, 80),
    (1200, 90),
    (1200, 95),
    (1200, 100),
    (1200, 150),
    (1200, 200),
    (1200, 300),
    (1200, 400),
    (1200, 500),
    (1200, 600),
    (1200, 800),
    (1200, 1000),
    (1400, 60),
    (1400, 70),
    (1400, 80),
    (1400, 90),
    (1400, 95),
    (1400, 100),
    (1400, 150),
    (1400, 200),
    (1400, 300),
    (1400, 400),
    (1400, 500),
    (1400, 600),
    (1400, 800),
    (1400, 1000),
    (1400, 1200),
    (1600, 60),
    (1600, 70),
    (1600, 80),
    (1600, 90),
    (1600, 95),
    (1600, 100),
    (1600, 150),
    (1600, 200),
    (1600, 300),
    (1600, 400),
    (1600, 500),
    (1600, 600),
    (1600, 800),
    (1600, 1000),
    (1600, 1200),
    (1600, 1400),
    (1800, 60),
    (1800, 70),
    (1800, 80),
    (1800, 90),
    (1800, 95),
    (1800, 100),
    (1800, 150),
    (1800, 200),
    (1800, 300),
    (1800, 400),
    (1800, 500),
    (1800, 600),
    (1800, 800),
    (1800, 1000),
    (1800, 1200),
    (1800, 1400),
    (1800, 1600),
    (2000, 60),
    (2000, 70),
    (2000, 80),
    (2000, 90),
    (2000, 95),
    (2000, 100),
    (2000, 150),
    (2000, 200),
    (2000, 300),
    (2000, 400),
    (2000, 500),
    (2000, 600),
    (2000, 800),
    (2000, 1000),
    (2000, 1200),
    (2000, 1400),
    (2000, 1600),
    (2000, 1800),
    (2500, 60),
    (2500, 70),
    (2500, 80),
    (2500, 90),
    (2500, 95),
    (2500, 100),
    (2500, 150),
    (2500, 200),
    (2500, 300),
    (2500, 400),
    (2500, 500),
    (2500, 600),
    (2500, 800),
    (2500, 1000),
    (2500, 1200),
    (2500, 1400),
    (2500, 1600),
    (2500, 1800),
    (2500, 2000),
    (3000, 60),
    (3000, 70),
    (3000, 80),
    (3000, 90),
    (3000, 95),
    (3000, 100),
    (3000, 150),
    (3000, 200),
    (3000, 300),
    (3000, 400),
    (3000, 500),
    (3000, 600),
    (3000, 800),
    (3000, 1000),
    (3000, 1200),
    (3000, 1400),
    (3000, 1600),
    (3000, 1800),
    (3000, 2000),
    (3000, 2600),
    (3500, 60),
    (3500, 70),
    (3500, 80),
    (3500, 90),
    (3500, 95),
    (3500, 100),
    (3500, 150),
    (3500, 200),
    (3500, 300),
    (3500, 400),
    (3500, 500),
    (3500, 600),
    (3500, 800),
    (3500, 1000),
    (3500, 1200),
    (3500, 1400),
    (3500, 1600),
    (3500, 1800),
    (3500, 2000),
    (3500, 2600),
    (3500, 3000),
    (4000, 60),
    (4000, 70),
    (4000, 80),
    (4000, 90),
    (4000, 95),
    (4000, 100),
    (4000, 150),
    (4000, 200),
    (4000, 300),
    (4000, 400),
    (4000, 500),
    (4000, 600),
    (4000, 800),
    (4000, 1000),
    (4000, 1200),
    (4000, 1400),
    (4000, 1600),
    (4000, 1800),
    (4000, 2000),
    (4000, 2600),
    (4000, 3000),
    (4000, 3500),
]


# Missing signal samples
MISSING_SIGNAL_SAMPLES = {
    "2024_nano_v15": [
        # ((y_decay_mode, h_decay_mode), (m_x, m_y))
        (("y2b", "h2tau"), (2500, 800)),
        (("y2tau", "h2b"), (2500, 90)),
    ],
    "2025_nano_v15": [
        # ((y_decay_mode, h_decay_mode), (m_x, m_y))
        (("y2b", "h2tau"), (2500, 800)),
        (("y2tau", "h2b"), (2500, 90)),
    ],
}


@dataclass
class XYHProfile:
    decay_modes: list[tuple[str, str]]
    xy_masses: list[tuple[int, int]]
    missing_signal_samples: dict[
        str, list[tuple[tuple[str, str], tuple[int, int]]]
    ]


FULL = XYHProfile(
    decay_modes=DECAY_MODES,
    xy_masses=XY_MASSES,
    missing_signal_samples=MISSING_SIGNAL_SAMPLES,
)


BENCHMARK = XYHProfile(
    decay_modes=[("y2b", "h2tau")],
    xy_masses=[(2000, 500)],
    missing_signal_samples=MISSING_SIGNAL_SAMPLES,
)


BKG_ONLY = XYHProfile(
    decay_modes=[],
    xy_masses=[],
    missing_signal_samples=MISSING_SIGNAL_SAMPLES,
)


@cache
def get_profile():
    """
    Get the analysis profile.

    The analysis profile is inferred from the `XYH_PROFILE` environment
    variable. The default profile is `BENCHMARK`.

    Returns
    -------
    XYHProfile
        The analysis profile.
    """

    # Get the profile name from the environment variable
    name = os.environ.get("XYH_PROFILE", None)
    if name is None:
        name = "BENCHMARK"

    # Load the profile
    profile = globals().get(name)
    if not isinstance(profile, XYHProfile):
        raise ValueError(
            f"Profile {name} not found or not of correct type XYHProfile."
        )

    return profile


def iterate_signal_parameters(
    profile: XYHProfile,
    campaign: str | None = None,
) -> Generator[tuple[tuple[str, str], tuple[int, int]], None, None]:
    """
    Yield the signal parameters for the given analysis profile.

    If the `campaign` argument is provided, the missing signal samples for the
    campaign will be excluded from the iteration.

    Parameters
    ----------
    profile : XYHProfile
        The analysis profile.

    campaign : str | None
        The campaign name. If provided, the missing signal samples for the
        campaign will be excluded from the iteration.

    Yields
    ------
    tuple[tuple[str, str], tuple[int, int]]
        A tuple of ((y_decay_mode, h_decay_mode), (m_x, m_y)).
    """

    for (y_decay_mode, h_decay_mode), (m_x, m_y) in product(
        profile.decay_modes, profile.xy_masses
    ):
        # Skip signals which are missing for certain campaigns
        if campaign is not None:
            if (
                (y_decay_mode, h_decay_mode),
                (m_x, m_y),
            ) in profile.missing_signal_samples.get(campaign, []):
                continue

        # Yield the signal parameters
        yield (y_decay_mode, h_decay_mode), (m_x, m_y)
