# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`bbtautau-kit` is the shape-production framework for the XYH → bbττ analysis. It reads CROWN ntuples with ROOT RDataFrame, builds per-dataset computation graphs (filters, weights, variations), fills histograms/snapshots, merges them, and plots shapes/control plots. Python 3.12, managed with pixi; the package is `src/xyh` (installed editable).

## Commands

```bash
pixi run -e dev ruff check src/ tests/     # lint (what CI runs; line length 80, py312)
pixi run -e dev pytest                      # all tests (testpaths = tests/)
pixi run -e dev pytest tests/core/test_graph.py::test_name   # single test
pixi run -e dev basedpyright                # type check (standard mode, src only)
```

Production chains are wrapper scripts in `bin/` that call `python3 -m xyh.shape_processor.<stage>`; every extra argument is a Hydra override:

```bash
bin/shapes_no_ff [overrides]        # run_graphs -> merge_histograms -> plot_shapes
bin/shapes_ff [overrides]           # same chain including fake-factor histograms
bin/derive_z_pt_weights [overrides] # data-driven Z pT corrections
bin/run_btag_renormalization        # b-tag weight normalization corrections
bin/shapes_no_ff graph_processing.mode=binning binning.n_bins=60   # derive data-driven binning
```

Orchestration with law: `law run xyh.Shapes --overrides "tags.shapes_tag=foo"` (tasks in `src/xyh/workflow/`, `law.cfg` registers the module).

## Architecture

**Hydra is the single source of truth for configuration.** Each stage in `src/xyh/shape_processor/` has a same-named top-level file in `hydra_config/` (composed from `hydra_config/base/*` and an `inventory/*` choice) and is decorated with `@hydra_cli("<stage>")` (`xyh.core.cli`). The law tasks (`xyh.workflow.base.HydraTask`) take only an `overrides` string, compose the same Hydra config to compute their outputs, and invoke the stage — never duplicate parameters in law tasks. Outputs land under `data/output/<tags.shapes_tag>/` (specs, histograms, snapshots, binning, z_pt_weights); paths come from `hydra_config/base/artifacts.yaml`.

**Physics configuration (`src/xyh/config/`)** is built on the `order` library: `campaigns/` (one module per era/NanoAOD version), `processes/`, `channels/` (channels plus category definitions), `variables/`, plus `inventory.py` / `process_sets.py` / `process_datasets_map.py` tying them together. The Hydra `inventory/*.yaml` files select which campaigns, channels, categories, processes and variables a production covers (e.g. `control_regions_z_pt`, `bjet_norm_*`). `XYH_PROFILE` (`BKG_ONLY`/`BENCHMARK`/`FULL`) and `XYH_SAMPLE_DATABASE` are set via `hydra.job.env_set` in `base/global.yaml`.

**Graph processing (`src/xyh/core/`)**: `run_graphs` first creates and dumps spec objects (`core/specs/`: dataset, histogram, filters_and_weights, graph), then `specs/graph.py` builds a `networkx` DAG per dataset and runs it in a process pool (`parallel.py`, `graph_processing.num_workers/num_threads`). Filter and weight building blocks live in `src/xyh/filters/` and `src/xyh/weights/` (their `__init__` re-exports are intentional, hence the ruff F401 ignore); systematic variations in `variations/` and `core/variations.py`. Correctionlib files are loaded via C++ declarations (`include/correctionlib.hxx`, `core/correctionlib_cpp.py`). `graph_processing.mode` selects output: `histogram`, `snapshot`, or `binning`.

**Data-driven corrections** are produced by separate stages and consumed by later productions through directories configured in `base/global.yaml` (`z_pt_weights.input_dir`, `btag_renorm_weights.input_dir`, `binning_overrides.file`). Setting `z_pt_weights.tag` makes the law workflow first produce the derivation production, derive the weights, then apply them.

`xyh.settings.Settings` is a singleton reading `config/config.yaml`; `bin/browse_graphs`, `plot_*`, `compare_campaigns` and `src/xyh/scripts/` are inspection/plotting helpers.

## Conventions

- Tests mirror the source layout under `tests/` (pytest, isolated unit tests mocking external deps; names like `test_<function>_<scenario>_<expected>`).
- Branches: `feature/`, `fix/`, `refactor/`, `docs/`, `test/` prefixes. PR descriptions need Overview, Key Changes, Testing and Checklist sections (see `.github/instructions/`).
- Git: commit only your own changes by path, in logical chunks, with the co-author trailer; do not push unless asked.
- The README documents the data-driven binning workflow and `bin/build_control_plot_dashboard` (needs the `plot-dashboard` skill, or `PLOT_DASHBOARD_DIR`).
