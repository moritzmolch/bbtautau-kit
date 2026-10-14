"""
C++ helper functions to evaluate correctionlib corrections in RDataFrame
expressions.

The functions are declared lazily in the ROOT interpreter, once per process,
by calling `ensure_declared` with an expression that uses them. Each function
takes the path of the correctionlib file as its first argument, so that the
expressions are self-contained. The files are loaded once and cached.
"""

from pathlib import Path

import correctionlib
import ROOT

# Preamble that loads the correctionlib library and defines the file cache
_PREAMBLE = """
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include "correction.h"

namespace xyh {
inline const correction::Correction::Ref& get_correction(
    const std::string& file, const std::string& name) {
  static std::mutex mutex;
  static std::map<std::string, std::unique_ptr<correction::CorrectionSet>> sets;
  static std::map<std::string, correction::Correction::Ref> refs;
  std::lock_guard<std::mutex> lock(mutex);
  auto key = file + "::" + name;
  auto it = refs.find(key);
  if (it != refs.end()) return it->second;
  auto set_it = sets.find(file);
  if (set_it == sets.end()) {
    set_it = sets.emplace(file, correction::CorrectionSet::from_file(file)).first;
  }
  return refs.emplace(key, set_it->second->at(name)).first->second;
}
}  // namespace xyh
"""

# Registered functions: name -> declaration code
_FUNCTIONS = {
    "xyh_z_normalization": """
inline double xyh_z_normalization(
    const std::string& file, int n_jets, int n_bjets) {
  return xyh::get_correction(file, "z_normalization")->evaluate(
      {n_jets, n_bjets});
}
""",
    "xyh_z_pt_correction": """
inline double xyh_z_pt_correction(
    const std::string& file, int n_jets, int n_bjets, double genboson_pt) {
  return xyh::get_correction(file, "z_pt_correction")->evaluate(
      {n_jets, n_bjets, genboson_pt});
}
""",
}

_declared: set[str] = set()
_preamble_declared = False


def _declare_preamble():
    global _preamble_declared
    if _preamble_declared:
        return
    package_dir = Path(correctionlib.__file__).parent
    ROOT.gInterpreter.AddIncludePath(str(package_dir / "include"))
    if ROOT.gSystem.Load(str(package_dir / "lib" / "libcorrectionlib.so")) < 0:
        raise RuntimeError("Cannot load libcorrectionlib")
    if not ROOT.gInterpreter.Declare(_PREAMBLE):
        raise RuntimeError("Cannot declare correctionlib helpers")
    _preamble_declared = True


def ensure_declared(expression: str) -> None:
    """Declare all registered functions that are used in the expression."""
    for name, code in _FUNCTIONS.items():
        if name in _declared or name not in expression:
            continue
        _declare_preamble()
        if not ROOT.gInterpreter.Declare(code):
            raise RuntimeError(f"Cannot declare function '{name}'")
        _declared.add(name)
