"""
C++ helper functions to evaluate correctionlib corrections in RDataFrame
expressions.

The functions are defined in ``include/correctionlib.hxx`` and are declared in
the ROOT interpreter once per process, by calling `ensure_declared` with an
expression that uses them. Each function takes the path of the correctionlib
file as its first argument, so that the expressions are self-contained. Each
file is loaded only once per process and the lookup during the event loop does
not lock or allocate.
"""

from pathlib import Path

import correctionlib
import ROOT

from .. import ROOT_DIR

# Header with the correction-set cache and the correction functions. Declared
# once per process the first time an expression uses one of the functions.
_HEADER = ROOT_DIR / "include" / "correctionlib.hxx"

# Functions provided by the header, declared lazily on first use.
_FUNCTIONS = (
    "xyh_z_normalization",
    "xyh_z_pt_correction",
    "xyh_bjet_normalization",
)

_declared: set[str] = set()
_header_declared = False


def _declare_header() -> None:
    global _header_declared
    if _header_declared:
        return
    package_dir = Path(correctionlib.__file__).parent
    ROOT.gInterpreter.AddIncludePath(str(package_dir / "include"))
    if ROOT.gSystem.Load(str(package_dir / "lib" / "libcorrectionlib.so")) < 0:
        raise RuntimeError("Cannot load libcorrectionlib")
    ROOT.gInterpreter.AddIncludePath(str(_HEADER.parent))
    if not ROOT.gInterpreter.Declare(f'#include "{_HEADER.name}"'):
        raise RuntimeError("Cannot declare correctionlib helpers")
    _header_declared = True


def ensure_declared(expression: str) -> None:
    """Declare all registered functions that are used in the expression."""
    for name in _FUNCTIONS:
        if name in _declared or name not in expression:
            continue
        _declare_header()
        _declared.update(_FUNCTIONS)
        return
