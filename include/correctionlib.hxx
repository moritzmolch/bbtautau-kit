#ifndef INCLUDE_CLIB_HXX
#define INCLUDE_CLIB_HXX

/**
 * C++ helper functions to evaluate correctionlib corrections in RDataFrame
 * expressions.
 *
 * The functions are declared lazily in the ROOT interpreter, once per process,
 * by calling `ensure_declared` with an expression that uses them. Each function
 * takes the path of the correctionlib file as its first argument, so that the
 * expressions are self-contained. Each file is loaded only once per process and
 * the lookup during the event loop does not lock or allocate.
 *
 * Preamble with the cache of correction sets. Loading happens once per file
 * and correction under a lock. The per-event lookup is lock-free: each function
 * remembers, per thread, the last file pointer it has resolved. The pointer is
 * that of the string literal in the weight expression, which is stable for the
 * lifetime of the compiled expression. A different pointer (e.g. another data
 * frame) falls back to the slow lookup by file name.
 */

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


inline double xyh_z_normalization(
    const char* file, int n_jets, int n_bjets) {
  static thread_local xyh::CorrectionCache cache;
  return xyh::get_correction(cache, file, "z_normalization")->evaluate(
      {n_jets, n_bjets});
}


inline double xyh_z_pt_correction(
    const char* file, int n_jets, double genboson_pt) {
  static thread_local xyh::CorrectionCache cache;
  return xyh::get_correction(cache, file, "z_pt_correction")->evaluate(
      {n_jets, genboson_pt});
}


inline double xyh_bjet_normalization(
    const char* file, const std::string& channel,
    const std::string& process, int n_jets) {
  static thread_local xyh::CorrectionCache cache;
  return xyh::get_correction(cache, file, "bjet_normalization")->evaluate(
      {channel, process, n_jets});
}

#endif