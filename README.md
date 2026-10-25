# bbtautau-kit

## Control plot dashboard

Static dashboard to browse control plots and compare eras side by side
(built with the `plot-dashboard` skill, config in `config/dashboard/control_plots.json`):

```bash
bin/build_control_plot_dashboard OUTDIR [shapes-YYYY-MM-DD ...] [--all] [--mode symlink|copy] [--clean]
```

Without campaign names the newest `data/output/shapes-*` folder is built. Set
`PLOT_DASHBOARD_DIR` if the skill is not in `~/.claude/skills/plot-dashboard`.
