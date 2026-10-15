"""
C++ helper functions to evaluate correctionlib corrections in RDataFrame
expressions.

The functions are declared lazily in the ROOT interpreter, once per process,
by calling `ensure_declared` with an expression that uses them. Each function
takes the path of the correctionlib file as its first argument, so that the
expressions are self-contained. Each file is loaded only once per process and
the lookup during the event loop does not lock or allocate.
"""

from pathlib import Path

import correctionlib
import ROOT

# Preamble with the cache of correction sets. Loading happens once per file
# and correction under a lock. The per-event lookup is lock-free: each function
# remembers, per thread, the last file pointer it has resolved. The pointer is
# that of the string literal in the weight expression, which is stable for the
# lifetime of the compiled expression. A different pointer (e.g. another data
# frame) falls back to the slow lookup by file name.
_PREAMBLE = """
#include <atomic>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include "correction.h"

namespace xyh {
inline std::atomic<int> n_correction_sets_loaded{0};

inline const correction::Correction* get_correction_slow(
    const char* file, const char* name) {
  static std::mutex mutex;
  static std::map<std::string, std::unique_ptr<correction::CorrectionSet>> sets;
  std::lock_guard<std::mutex> lock(mutex);
  auto set_it = sets.find(file);
  if (set_it == sets.end()) {
    set_it = sets.emplace(
        file, correction::CorrectionSet::from_file(file)).first;
    ++n_correction_sets_loaded;
  }
  return set_it->second->at(name).get();
}

struct CorrectionCache {
  const char* file = nullptr;
  const correction::Correction* correction = nullptr;
};

inline const correction::Correction* get_correction(
    CorrectionCache& cache, const char* file, const char* name) {
  if (file != cache.file) {
    cache.correction = get_correction_slow(file, name);
    cache.file = file;
  }
  return cache.correction;
}
}  // namespace xyh

inline int xyh_n_correction_sets_loaded() {
  return xyh::n_correction_sets_loaded.load();
}
"""

# Registered functions: name -> declaration code
_FUNCTIONS = {
    "xyh_z_normalization": """
inline double xyh_z_normalization(
    const char* file, int n_jets, int n_bjets) {
  static thread_local xyh::CorrectionCache cache;
  return xyh::get_correction(cache, file, "z_normalization")->evaluate(
      {n_jets, n_bjets});
}
""",
    "xyh_z_pt_correction": """
inline double xyh_z_pt_correction(
    const char* file, int n_jets, double genboson_pt) {
  static thread_local xyh::CorrectionCache cache;
  return xyh::get_correction(cache, file, "z_pt_correction")->evaluate(
      {n_jets, genboson_pt});
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
