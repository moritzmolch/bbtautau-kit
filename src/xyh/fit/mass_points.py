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
    + r")_xyh_(?P<ydm>[^_]+)_(?P<hdm>[^_]+)_mx(?P<mx>\d+)_my(?P<my>\d+)$"
)

# Mass point given as a string, e.g. "2000_500" or "mx2000_my500"
_POINT_RE = re.compile(r"^(?:mx)?(?P<mx>\d+)_(?:my)?(?P<my>\d+)$")


@dataclass(frozen=True, order=True)
class MassPoint:
    """One signal hypothesis (decay modes and masses)."""

    ydm: str
    hdm: str
    mx: int
    my: int

    @property
    def decay_label(self) -> str:
        return f"{self.ydm}_{self.hdm}"

    @property
    def mass_label(self) -> str:
        return f"mx{self.mx}_my{self.my}"

    @property
    def signal_process(self) -> str:
        """Name of the signal process of this point in the merged file."""
        return f"{SIGNAL_PREFIX}{self.ydm}_{self.hdm}_{self.mass_label}"

    def category(self, channel: str, cls: str) -> str:
        """Name of the classifier category of a channel and class."""
        if cls not in CLASSES:
            raise ValueError(f"Unknown class {cls!r}, expected {CLASSES}")
        return (
            f"{channel}_clf_{cls}_xyh_{self.ydm}_{self.hdm}_{self.mass_label}"
        )


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
        ydm=match["ydm"],
        hdm=match["hdm"],
        mx=int(match["mx"]),
        my=int(match["my"]),
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
    """Parse ``(mx, my)`` from ``[mx, my]`` or ``"mx_my"`` strings."""
    if isinstance(spec, str):
        match = _POINT_RE.match(spec)
        if match is None:
            raise ValueError(
                f"Cannot parse mass point {spec!r}, expected e.g. '2000_500'"
            )
        return int(match["mx"]), int(match["my"])
    if len(spec) != 2:
        raise ValueError(f"Mass point {spec!r} must have two entries")
    return int(spec[0]), int(spec[1])


def select_mass_points(
    available: Iterable[MassPoint],
    mass_points: Sequence[str | Sequence[int | str]] | None = None,
    ydm: Sequence[str] | None = None,
    hdm: Sequence[str] | None = None,
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
        if (ydm is None or p.ydm in ydm) and (hdm is None or p.hdm in hdm)
    ]
    if mass_points is not None:
        pairs = {parse_mass_pair(m) for m in mass_points}
        missing = pairs - {(p.mx, p.my) for p in selected}
        if missing:
            raise ValueError(
                f"Requested mass points not available: {sorted(missing)}"
            )
        selected = [p for p in selected if (p.mx, p.my) in pairs]
    if not selected:
        raise ValueError("No mass points selected")
    return selected
