from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

COMBINE_M_H = 120


@dataclass(kw_only=True)
class Environment:
    """Settings for the combine environment."""

    # Relative paths refer to the repository root, see bin/setup_combine
    cmssw_dir: str | Path = field(default="external/combine/CMSSW_16_0_0")
    scram_arch: str = field(default="el9_amd64_gcc13")
    setup_cmd: str | None = field(default=None)

    def __post_init__(self):
        self.cmssw_dir = Path(self.cmssw_dir).resolve()


@dataclass(frozen=True, kw_only=True)
class DefaultArguments:
    """Default arguments for combine modules."""

    verbosity: int = field(default=1)
    mass: int = field(default=COMBINE_M_H)
    cmin_default_minimizer_strategy: int = field(default=0)
    cmin_default_minimizer_tolerance: float = field(default=0.000001)
    fallback_algo: str = field(default="Minuit2,Migrad,2:0.000001")
    x_rtd: str = field(default="MINIMIZER_no_analytic")

    def to_args_list(self) -> list[str]:
        return [
            "-v",
            str(self.verbosity),
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
    r_abs_acc: float = field(default=1.0e-6)
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
            "--rAbsAcc",
            str(self.r_abs_acc),
            "--run",
            self.mode,
        ] + asimov_args


@dataclass(frozen=True, kw_only=True)
class FitDiagnostics:
    """Arguments for the `FitDiagnostics` combine module."""

    r_min: float = field(default=-1)
    r_max: float = field(default=3)
    robust_fit: bool = field(default=True)
    asimov: bool = field(default=True)
    expect_signal: float = field(default=0.001)
    save_shapes: bool = field(default=True)
    save_overall_shapes: bool = field(default=True)
    save_nll: bool = field(default=True)
    save_with_uncertainties: bool = field(default=True)
    skip_b_only_fit: bool = field(default=False)
    skip_sb_fit: bool = field(default=False)

    def to_args_list(self) -> list[str]:
        # Construct arguments for tests on Asimov dataset
        asimov_args = []
        if self.asimov:
            asimov_args = [
                "-t",
                "-1",
                "--expectSignal",
                str(self.expect_signal),
            ]

        # Construct optional fit setup arguments
        robust_fit_args = []
        if self.robust_fit:
            robust_fit_args = ["--robustFit", "1"]

        # Construct save arguments
        save_args = []
        if self.save_nll:
            save_args.append("--saveNLL")
        if self.save_shapes:
            save_args.append("--saveShapes")
        if self.save_overall_shapes:
            save_args.append("--saveOverallShapes")
        if self.save_with_uncertainties:
            save_args.append("--saveWithUncertainties")

        # Construct skip arguments
        skip_args = []
        if self.skip_b_only_fit:
            skip_args.append("--skipBOnlyFit")
        if self.skip_sb_fit:
            skip_args.append("--skipSBFit")

        return (
            [
                "--rMin",
                str(self.r_min),
                "--rMax",
                str(self.r_max),
            ]
            + asimov_args
            + robust_fit_args
            + save_args
            + skip_args
        )


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
    fit_diagnostics: FitDiagnostics = field(default_factory=FitDiagnostics)
