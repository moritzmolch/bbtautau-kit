"""Datacard specification and the launcher of the CombineHarvester script.

`DatacardSpec` is a pure description of the datacard. It is dumped to JSON
and read by `ch_scripts/write_datacard.py`, which runs in the CMSSW
environment and does not import `xyh`.
"""

import json
import logging
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from xyh.fit.mass_points import MassPoint
from xyh.fit.scope import FitBin
from xyh.fit.shapes import SIGNAL_NAME, BinShapes

logger = logging.getLogger(__name__)

CH_SCRIPT = Path(__file__).parent / "ch_scripts" / "write_datacard.py"


@dataclass(frozen=True)
class BinSpec:
    """One datacard bin; era is the campaign, channel the channel."""

    name: str
    era: str
    channel: str
    signals: tuple[str, ...]
    backgrounds: tuple[str, ...]


@dataclass(frozen=True)
class DatacardSpec:
    """Everything needed to write a datacard with CombineHarvester.

    All file names are relative to the directory the script runs in.
    """

    analysis: str
    mass: int
    bins: tuple[BinSpec, ...]
    shapes_in_file: str = "shapes_in.root"
    datacard_file: str = "datacard.txt"
    shapes_out_file: str = "shapes.root"
    # Threshold of autoMCStats, `None` disables it
    auto_mc_stats: float | None = None
    # Reserved for systematics, passed through to the script
    systematics: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DatacardSpec":
        data = dict(data)
        data["bins"] = tuple(
            BinSpec(
                **{
                    **b,
                    "signals": tuple(b["signals"]),
                    "backgrounds": tuple(b["backgrounds"]),
                }
            )
            for b in data["bins"]
        )
        data["systematics"] = tuple(data.get("systematics", ()))
        return cls(**data)


def build_datacard_spec(
    point: MassPoint,
    bins: Mapping[FitBin, BinShapes],
    auto_mc_stats: float | None = None,
    analysis: str = "xyh",
) -> DatacardSpec:
    """Build the spec from the shapes of a point's bins."""
    bin_specs = tuple(
        BinSpec(
            name=fit_bin.name,
            era=fit_bin.campaign,
            channel=fit_bin.channel,
            signals=(SIGNAL_NAME,) if shapes.signal is not None else (),
            backgrounds=tuple(sorted(shapes.backgrounds)),
        )
        for fit_bin, shapes in bins.items()
    )
    return DatacardSpec(
        analysis=analysis,
        mass=point.mx,
        bins=bin_specs,
        auto_mc_stats=auto_mc_stats,
    )


def write_spec(spec: DatacardSpec, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec.to_dict(), indent=2) + "\n")


def read_spec(path: Path) -> DatacardSpec:
    return DatacardSpec.from_dict(json.loads(path.read_text()))


def datacard_script_command(
    prefix: str,
    spec_file: str,
    script: Path = CH_SCRIPT,
) -> list[str]:
    """Shell command running the CH script inside the CMSSW environment."""
    inner = f"python3 {script} {spec_file}"
    return ["bash", "-c", f"{prefix} && {inner}" if prefix else inner]


def run_datacard_script(prefix: str, spec_file: Path, workdir: Path) -> None:
    """Write datacard and shapes with CombineHarvester in `workdir`."""
    command = datacard_script_command(prefix, spec_file.name)
    logger.info(f"Write datacard in {workdir}")
    result = subprocess.run(
        command, cwd=workdir, capture_output=True, text=True, check=False
    )
    (workdir / "write_datacard.log").write_text(result.stdout + result.stderr)
    if result.returncode != 0:
        raise RuntimeError(
            f"Datacard script failed ({result.returncode}), see "
            f"{workdir / 'write_datacard.log'}:\n{result.stderr[-2000:]}"
        )


__all__: Sequence[str] = [
    "BinSpec",
    "DatacardSpec",
    "build_datacard_spec",
    "datacard_script_command",
    "read_spec",
    "run_datacard_script",
    "write_spec",
]
