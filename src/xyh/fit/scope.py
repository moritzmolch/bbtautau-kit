"""Fit scope: the campaigns and channels combined in one fit."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from xyh.fit.mass_points import CLASSES, MassPoint

ALL = "all"


def short_campaign_name(campaign: str) -> str:
    """Strip the NanoAOD version, e.g. ``2024_nano_v15`` -> ``2024``."""
    return re.sub(r"_nano_v\d+$", "", campaign)


def _resolve(
    requested: str | Sequence[str],
    available: Sequence[str],
    short=lambda name: name,
) -> tuple[tuple[str, ...], bool]:
    """Resolve requested names; returns the names and the `all` flag."""
    # Hydra parses e.g. `2024` as an integer
    if isinstance(requested, str | int):
        requested = [requested]
    requested = [str(r) for r in requested]
    if not requested:
        raise ValueError("Empty selection, use 'all' to select everything")
    if ALL in requested:
        return tuple(available), True
    resolved = []
    for req in requested:
        matches = [n for n in available if req in (n, short(n))]
        if not matches:
            raise ValueError(
                f"{req!r} is not available, choose from {list(available)}"
            )
        resolved.extend(m for m in matches if m not in resolved)
    return tuple(resolved), set(resolved) == set(available)


@dataclass(frozen=True)
class FitBin:
    """One Combine bin: a campaign, a channel and an output class."""

    campaign: str
    channel: str
    cls: str

    @property
    def name(self) -> str:
        # Combine rejects bin names starting with a digit, so the campaign
        # (e.g. 2024_nano_v15) goes last.
        return f"{self.channel}_{self.cls}_{self.campaign}"

    def category(self, point: MassPoint) -> str:
        return point.category(self.channel, self.cls)


@dataclass(frozen=True)
class FitScope:
    """Campaigns times channels entering one fit."""

    campaigns: tuple[str, ...]
    channels: tuple[str, ...]
    all_campaigns: bool = False
    all_channels: bool = False

    @property
    def tag(self) -> str:
        """Directory name of the scope, e.g. ``2024_tt`` or ``all_all``."""
        camp = (
            ALL
            if self.all_campaigns
            else "-".join(short_campaign_name(c) for c in self.campaigns)
        )
        chan = ALL if self.all_channels else "-".join(self.channels)
        return f"{camp}_{chan}"

    def bins(self) -> list[FitBin]:
        return [
            FitBin(campaign, channel, cls)
            for campaign in self.campaigns
            for channel in self.channels
            for cls in CLASSES
        ]


def resolve_scope(
    campaigns: str | Sequence[str],
    channels: str | Sequence[str],
    available_campaigns: Sequence[str],
    available_channels: Sequence[str],
) -> FitScope:
    """Build the scope from the config values (`all` selects everything).

    Campaigns may be given by full name or short name (``2024``).
    """
    camps, all_camps = _resolve(
        campaigns, available_campaigns, short_campaign_name
    )
    chans, all_chans = _resolve(channels, available_channels)
    return FitScope(camps, chans, all_camps, all_chans)
