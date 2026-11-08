from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(kw_only=True)
class Environment:
    """Settings for the combine environment."""

    # Relative paths refer to the repository root, see bin/setup_combine
    cmssw_dir: str | Path = field(default="external/combine/CMSSW_16_0_0")
    scram_arch: str = field(default="el9_amd64_gcc13")
    setup_cmd: str | None = field(default=None)

    def __post_init__(self):
        self.cmssw_dir = Path(self.cmssw_dir)


@dataclass(frozen=True, kw_only=True)
class DefaultArguments:
    """Default arguments for combine modules."""

    verbosity: int = field(default=1)
    mass: int = field(default=125)
    cmin_default_minimizer_strategy: int = field(default=0)
    cmin_default_minimizer_tolerance: float = field(default=0.0001)
    fallback_algo: str = field(default="Minuit2,Migrad,2:0.0001")
    x_rtd: str = field(default="MINIMIZER_no_analytic")

    def to_args_list(self) -> list[str]:
        return [
            f"-{'v' * self.verbosity}",
            "--mass",
            str(self.mass),
            "--cminDefaultMinimizerStrategy",
            str(self.cmin_default_minimizer_strategy),
            "--cminDefaultMinimizerTolerance",
            str(self.cmin_default_minimizer_tolerance),
            "--cminFallbackAlgo",
            self.fallback_algo,
            "--X-rtd",
            self.x_rtd,
        ]


@dataclass(frozen=True, kw_only=True)
class AsymptoticLimits:
    """Arguments for the `AsymptoticLimits` combine module."""

    r_min: float = field(default=-1)
    r_max: float = field(default=3)
    robust_fit: int = field(default=1)
    asimov: bool = field(default=True)
    mode: Literal["expected", "both"] = field(default="expected")

    def to_args_list(self) -> list[str]:
        # Construct arguments for tests on Asimov dataset
        asimov_args = []
        if self.asimov:
            asimov_args = ["-t", "-1"]

        return [
            "--rMin",
            str(self.r_min),
            "--rMax",
            str(self.r_max),
            "--robustFit",
            str(self.robust_fit),
            "--mode",
            self.mode,
        ] + asimov_args


@dataclass(frozen=True)
class CombineConfig:
    """Settings of the Combine installation and the limit calculation."""

    environment: Environment = field(default_factory=Environment)
    default_arguments: DefaultArguments = field(
        default_factory=DefaultArguments
    )
    asymptotic_limits: AsymptoticLimits = field(
        default_factory=AsymptoticLimits
    )
