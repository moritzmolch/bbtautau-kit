"""Limit results: per-point JSON files and the collected CSV."""

import csv
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from xyh.fit.mass_points import MassPoint

LIMITS_JSON = "limits.json"
LIMITS_CSV = "limits.csv"


@dataclass(frozen=True)
class LimitResult:
    """95% CL upper limits on the cross section times branching ratio."""

    decay_mode: str
    mx: int
    my: int
    exp_m2: float
    exp_m1: float
    exp: float
    exp_p1: float
    exp_p2: float
    obs: float
    unit: str = "pb"

    @classmethod
    def from_values(
        cls, point: MassPoint, values: dict[str, float]
    ) -> "LimitResult":
        return cls(
            decay_mode=point.decay_mode,
            mx=point.mx,
            my=point.my,
            exp_m2=values["exp_m2"],
            exp_m1=values["exp_m1"],
            exp=values["exp"],
            exp_p1=values["exp_p1"],
            exp_p2=values["exp_p2"],
            obs=values["obs"],
        )

    def to_dict(self) -> dict:
        return asdict(self)


def write_limits_json(result: LimitResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), indent=2) + "\n")


def read_limits_json(path: Path) -> LimitResult:
    return LimitResult(**json.loads(path.read_text()))


def find_limit_files(data_mode_dir: Path) -> list[Path]:
    """All per-point ``limits.json`` below a data-mode directory."""
    return sorted(data_mode_dir.glob(f"*/mx*_my*/{LIMITS_JSON}"))


def collect_limits(data_mode_dir: Path) -> list[LimitResult]:
    """Load all per-point results, sorted by decay modes and masses."""
    results = [read_limits_json(p) for p in find_limit_files(data_mode_dir)]
    return sorted(results, key=lambda r: (r.decay_mode, r.mx, r.my))


def write_limits_csv(results: Iterable[LimitResult], path: Path) -> None:
    """Write one row per point; columns follow `LimitResult`."""
    names = [f.name for f in fields(LimitResult)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        for result in results:
            writer.writerow(result.to_dict())
