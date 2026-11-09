"""Signal mass points and their discovery from category names."""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

# Output classes of the classifier, each of which is one category per point
CLASSES: tuple[str, ...] = ("xyh", "t_tt", "z2tau", "jetfakes")

# Prefix of all signal process names
SIGNAL_PREFIX = "xyh_"

# Names of the classifier categories, see `_categories_clf.py`
_CATEGORY_RE = re.compile(
    r"^(?P<channel>[a-z]+)_clf_(?P<cls>"
    + "|".join(CLASSES)
    + r")_xyh_(?P<decay_mode>y2[^_]+_h2[^_]+)_mx(?P<m_x>\d+)_my(?P<m_y>\d+)$"
)

# Mass point given as a string, e.g. "2000_500" or "mx2000_my500"
_POINT_RE = re.compile(r"^(?:mx)?(?P<m_x>\d+)_(?:my)?(?P<m_y>\d+)$")


@dataclass(frozen=True, order=True)
class MassPoint:
    """One signal hypothesis (decay modes and masses)."""

    decay_mode: str
    m_x: int
    m_y: int

    @property
    def mass_label(self) -> str:
        return f"mx{self.m_x}_my{self.m_y}"

    @property
    def signal_process(self) -> str:
        """Name of the signal process of this point in the merged file."""
        return f"{SIGNAL_PREFIX}{self.decay_mode}_{self.mass_label}"

    def category(self, channel: str, cls: str) -> str:
        """Name of the classifier category of a channel and class."""
        if cls not in CLASSES:
            raise ValueError(f"Unknown class {cls!r}, expected {CLASSES}")
        return f"{channel}_clf_{cls}_xyh_{self.decay_mode}_{self.mass_label}"


def parse_category_name(name: str) -> tuple[str, str, MassPoint] | None:
    """Split a classifier category name into channel, class and point.

    Returns
    -------
    tuple[str, str, MassPoint] | None
        ``(channel, cls, point)`` or `None` if `name` is not a classifier
        category.
    """
    match = _CATEGORY_RE.match(name)
    if match is None:
        return None
    point = MassPoint(
        decay_mode=match["decay_mode"],
        m_x=int(match["m_x"]),
        m_y=int(match["m_y"]),
    )
    return match["channel"], match["cls"], point


def discover_mass_points(categories: Iterable[str]) -> list[MassPoint]:
    """Collect the sorted, unique mass points of classifier categories."""
    points = set()
    for name in categories:
        parsed = parse_category_name(name)
        if parsed is not None:
            points.add(parsed[2])
    return sorted(points)


def parse_mass_pair(spec: str | Sequence[int | str]) -> tuple[int, int]:
    """Parse ``(m_x, m_y)`` from ``[m_x, m_y]`` or ``"{m_x}_{m_y}"`` strings."""
    if isinstance(spec, str):
        match = _POINT_RE.match(spec)
        if match is None:
            raise ValueError(
                f"Cannot parse mass point {spec!r}, expected e.g. '2000_500'"
            )
        return int(match["m_x"]), int(match["m_y"])
    if len(spec) != 2:
        raise ValueError(f"Mass point {spec!r} must have two entries")
    return int(spec[0]), int(spec[1])


def select_mass_points(
    available: Iterable[MassPoint],
    mass_points: Sequence[str | Sequence[int | str]] | None = None,
    decay_modes: Sequence[str] | None = None,
) -> list[MassPoint]:
    """Select points by masses and decay modes (`None` selects all).

    Raises
    ------
    ValueError
        If a requested mass pair is not available or nothing is selected.
    """
    available = sorted(set(available))
    selected = [
        p
        for p in available
        if (decay_modes is None or p.decay_mode in decay_modes)
    ]
    if mass_points is not None:
        pairs = {parse_mass_pair(m) for m in mass_points}
        missing = pairs - {(p.m_x, p.m_y) for p in selected}
        if missing:
            raise ValueError(
                f"Requested mass points not available: {sorted(missing)}"
            )
        selected = [p for p in selected if (p.m_x, p.m_y) in pairs]
    if not selected:
        raise ValueError("No mass points selected")
    return selected
