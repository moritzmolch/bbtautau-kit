# bbtautau-kit

## Data-driven binning

A custom equipopulated binning (same number of data events per bin) can be
derived on data with the `binning` output mode of `run_graphs`:

```bash
bin/shapes_no_ff graph_processing.mode=binning binning.n_bins=60
```

The binning is derived for every campaign, channel and category of the
inventory and for the variables of the `binning.variables` configuration (see
`hydra_config/base/binning.yaml`), and written to
`data/output/<tags.shapes_tag>/binning/binning.json` together with control
plots. The number of bins, the edge precision and an optional value range can
be set per variable and, on top of the global defaults, per campaign, channel
and category. The derived binning replaces the inventory binning in a
production by setting its `binning_overrides.file`:

```bash
bin/shapes_no_ff binning_overrides.file=data/output/<tags.shapes_tag>/binning/binning.json
```

## Control plot dashboard

Static dashboard to browse control plots and compare eras side by side
(built with the `plot-dashboard` skill, config in `config/dashboard/control_plots.json`):

```bash
bin/build_control_plot_dashboard OUTDIR [shapes-YYYY-MM-DD ...] [--all] [--mode symlink|copy] [--clean]
```

Without campaign names the newest `data/output/shapes-*` folder is built. Set
`PLOT_DASHBOARD_DIR` if the skill is not in `~/.claude/skills/plot-dashboard`.
