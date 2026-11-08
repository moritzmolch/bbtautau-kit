"""Run Combine in a CMSSW environment via subprocess and parse results.

Command and environment builders are pure functions. `run_in_env` and
`read_limit_entries` are the thin I/O wrappers.
"""

import logging
import shlex
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

CMSSET_DEFAULT = "/cvmfs/cms.cern.ch/cmsset_default.sh"

# Quantiles of the expected limits written by AsymptoticLimits
EXPECTED_QUANTILES = {
    0.025: "exp_m2",
    0.16: "exp_m1",
    0.5: "exp",
    0.84: "exp_p1",
    0.975: "exp_p2",
}
OBSERVED_QUANTILE = -1.0


@dataclass(frozen=True)
class CombineConfig:
    """Settings of the Combine installation and the limit calculation."""

    cmssw_dir: str = ""
    scram_arch: str = ""
    setup_cmd: str = ""
    r_range: tuple[float, float] | None = None
    extra_args: tuple[str, ...] = field(default_factory=tuple)


def environment_prefix(
    cmssw_dir: str = "", scram_arch: str = "", setup_cmd: str = ""
) -> str:
    """Shell snippet that sets up the CMSSW environment.

    A non-empty `setup_cmd` replaces the default snippet.

    Raises
    ------
    ValueError
        If neither `setup_cmd` nor `cmssw_dir` is given.
    """
    if setup_cmd:
        return setup_cmd
    if not cmssw_dir:
        raise ValueError("Set fit.combine.cmssw_dir or fit.combine.setup_cmd")
    parts = []
    if scram_arch:
        parts.append(f"export SCRAM_ARCH={shlex.quote(scram_arch)}")
    src = shlex.quote(f"{cmssw_dir}/src")
    parts += [
        f"source {CMSSET_DEFAULT}",
        f"pushd {src} > /dev/null",
        "eval $(scramv1 runtime -sh)",
        "popd > /dev/null",
    ]
    return " && ".join(parts)


def wrap_command(prefix: str, command: Sequence[str]) -> list[str]:
    """Wrap a command so that it runs after the environment `prefix`."""
    inner = shlex.join(command)
    return ["bash", "-c", f"{prefix} && {inner}" if prefix else inner]


def text2workspace_command(
    datacard: str, workspace: str, extra_args: Sequence[str] = ()
) -> list[str]:
    return ["text2workspace.py", datacard, "-o", workspace, *extra_args]


def combine_command(
    workspace: str,
    mass: int,
    name: str = ".fit",
    r_range: tuple[float, float] | None = None,
    extra_args: Sequence[str] = (),
) -> list[str]:
    """Command for the expected and observed asymptotic limits."""
    command = [
        "combine",
        "-M",
        "AsymptoticLimits",
        workspace,
        "--run",
        "both",
        "-m",
        str(mass),
        "-n",
        name,
    ]
    if r_range is not None:
        command += ["--rMin", str(r_range[0]), "--rMax", str(r_range[1])]
    return command + list(extra_args)


def limit_file_name(mass: int, name: str = ".fit") -> str:
    """Name of the file written by `combine_command`."""
    return f"higgsCombine{name}.AsymptoticLimits.mH{mass}.root"


def limits_from_entries(
    entries: Sequence[tuple[float, float]],
) -> dict[str, float]:
    """Map ``(limit, quantile)`` pairs of the limit tree to named values.

    Raises
    ------
    ValueError
        If an expected quantile or the observed limit is missing.
    """
    result: dict[str, float] = {}
    for limit, quantile in entries:
        if abs(quantile - OBSERVED_QUANTILE) < 1e-6:
            result["obs"] = limit
            continue
        for q, name in EXPECTED_QUANTILES.items():
            if abs(quantile - q) < 1e-4:
                result[name] = limit
    expected = {*EXPECTED_QUANTILES.values(), "obs"}
    missing = expected - result.keys()
    if missing:
        raise ValueError(f"Limit tree lacks entries: {sorted(missing)}")
    return result


def read_limit_entries(path: Path) -> list[tuple[float, float]]:
    """Read ``(limit, quantileExpected)`` from the ``limit`` tree."""
    import ROOT

    root_file = ROOT.TFile.Open(str(path), "READ")
    if not root_file or root_file.IsZombie():
        raise FileNotFoundError(f"Cannot open {path}")
    try:
        tree = root_file.Get("limit")
        if not tree:
            raise KeyError(f"No 'limit' tree in {path}")
        return [(float(e.limit), float(e.quantileExpected)) for e in tree]
    finally:
        root_file.Close()


def run_in_env(
    prefix: str,
    command: Sequence[str],
    workdir: Path,
    log_file: Path | None = None,
) -> str:
    """Run a command in the CMSSW environment and return its output.

    Raises
    ------
    RuntimeError
        If the command fails; the message contains the tail of stderr.
    """
    full = wrap_command(prefix, command)
    logger.info(f"Run {shlex.join(command)} in {workdir}")
    result = subprocess.run(
        full, cwd=workdir, capture_output=True, text=True, check=False
    )
    if log_file is not None:
        log_file.write_text(result.stdout + result.stderr)
    if result.returncode != 0:
        raise RuntimeError(
            f"{command[0]} failed ({result.returncode}):\n"
            f"{result.stderr[-2000:]}"
        )
    return result.stdout


def check_environment(prefix: str, workdir: Path) -> None:
    """Fail early if combine, text2workspace or CH are not usable."""
    checks = [
        ["which", "combine"],
        ["which", "text2workspace.py"],
        ["python3", "-c", "import CombineHarvester.CombineTools.ch"],
    ]
    for check in checks:
        try:
            run_in_env(prefix, check, workdir)
        except RuntimeError as err:
            raise RuntimeError(
                "Combine environment check failed for "
                f"{shlex.join(check)}. Run bin/setup_combine and check "
                f"fit.combine.*.\n{err}"
            ) from err
