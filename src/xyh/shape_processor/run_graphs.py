import cProfile
import io
import itertools
import logging
import pstats
from dataclasses import asdict
from pathlib import Path
from time import time

from omegaconf import DictConfig, OmegaConf

from xyh import ROOT_DIR
from xyh.core.binning import load_binning_overrides
from xyh.core.cli import hydra_cli
from xyh.core.config import load_inventory
from xyh.core.io import dump_json
from xyh.core.specs.dataset import create_dataset_specs
from xyh.core.specs.filters_and_weights import create_filters_and_weights_specs
from xyh.core.specs.graph import create_graph_specs, run_graph
from xyh.core.specs.histogram import create_histogram_specs
from xyh.core.specs.inputs import resolve_processes

logger = logging.getLogger(__name__)


@hydra_cli("run_graphs")
def main(cfg: DictConfig):
    # Set the logging level
    logging.basicConfig(level=cfg["log_level"])

    # Get the profiling settings
    profiling_cfg = cfg.get("profiling", {})
    use_cprofile = bool(profiling_cfg.get("enabled", False)) and bool(
        profiling_cfg.get("cprofile", True)
    )

    if use_cprofile:
        report = _run_with_cprofile(cfg, profiling_cfg)
    else:
        report = _run(cfg, profiling_cfg)

    # Dump the profiling report and print a summary if profiling is enabled
    if report is not None:
        dump_json(report, Path(cfg.get("profiling_report_file")))
        _log_report_summary(report)


def _profiling_options(profiling_cfg: DictConfig) -> dict[str, bool] | None:
    """Return the profiling options or `None` if profiling is disabled."""
    if not bool(profiling_cfg.get("enabled", False)):
        return None
    return {
        "stages": bool(profiling_cfg.get("stages", True)),
        "rdataframe": bool(profiling_cfg.get("rdataframe", True)),
        "memory": bool(profiling_cfg.get("memory", True)),
    }


def _run(cfg: DictConfig, profiling_cfg: DictConfig, cprofile: bool = False):
    """Run the graph processing and return the profiling report, if any.

    Parameters
    ----------
    cfg : DictConfig
        The composed hydra configuration.

    profiling_cfg : DictConfig
        The `profiling` section of the configuration.

    cprofile : bool
        Whether the whole entry point was run under `cProfile`. Only affects
        the metadata stored in the profiling report.
    """
    # Determine which profiling components are activated
    profiling_options = _profiling_options(profiling_cfg)

    # Initialize the profiling report
    report = None
    if profiling_options is not None:
        report = {
            "python": {
                "cprofile": cprofile,
                "mode": cfg["graph_processing"].get("mode", "n/a"),
                "num_workers": cfg["graph_processing"]["num_workers"],
                "num_threads": cfg["graph_processing"].get("num_threads", 1),
            },
            "subgraphs": [],
        }

    wall_start = time()

    # Create the dataset specs
    dataset_specs = create_dataset_specs(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        inventory_factory_kwargs=cfg["inventory"]["factory_fn_kwargs"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        xrootd_server=cfg["ntuples"]["xrootd_server"],
        ntuple_base_dir=Path(cfg["ntuples"]["base_dir"]),
        ntuple_tag=cfg["tags"]["ntuple_tag"],
        ntuple_friends=cfg["ntuples"]["friends"],
    )

    # Graph processing mode and whether the binning is derived in this run
    mode = cfg["graph_processing"]["mode"]
    is_binning = mode == "binning"

    # In binning mode, optionally limit the ntuple files per dataset
    n_files = cfg["binning"].get("n_files") if is_binning else None
    if n_files:
        for dataset_spec in dataset_specs:
            dataset_spec.files = {
                key: files[:n_files]
                for key, files in dataset_spec.files.items()
            }

    # Load the binning that overrides the one of the inventory, if configured
    binning_overrides = None
    binning_file = cfg.get("binning_overrides", {}).get("file")
    if binning_file:
        binning_overrides = load_binning_overrides(ROOT_DIR / binning_file)

    # Create the histogram specs. In binning mode, only the variables of the
    # `binning` configuration are considered.
    histogram_specs = create_histogram_specs(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        inventory_factory_kwargs=cfg["inventory"]["factory_fn_kwargs"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        categories=cfg["inventory"]["categories"],
        variables=(
            list(cfg["binning"].get("variables", {}).keys())
            if is_binning
            else cfg["inventory"]["variables"]
        ),
        binning_overrides=binning_overrides,
    )

    # Create the filter and weight specs
    filters_and_weights_specs = create_filters_and_weights_specs(
        inventory_factory_fn_path=cfg["inventory"]["factory_fn"],
        inventory_factory_kwargs=cfg["inventory"]["factory_fn_kwargs"],
        campaigns=cfg["inventory"]["campaigns"],
        channels=cfg["inventory"]["channels"],
        categories=cfg["inventory"]["categories"],
        filters_fn_path=cfg["inventory"]["filters_fn"],
        weights_fn_path=cfg["inventory"]["weights_fn"],
    )

    # In binning mode, keep only the nominal data events: the equipopulated
    # binning is optimized on data only. The axes labels of the variables are
    # collected for the control plots.
    binning_labels: dict[tuple[str, str], str] = {}
    if is_binning:
        data_processes = set()
        for campaign, channel in itertools.product(
            cfg["inventory"]["campaigns"],
            cfg["inventory"]["channels"],
        ):
            inventory = load_inventory(
                cfg["inventory"]["factory_fn"],
                campaign,
                channel,
                **cfg["inventory"]["factory_fn_kwargs"],
            )
            data_processes.update(
                resolve_processes(
                    inventory, cfg["binning"]["data_process_group"]
                )
            )
            for variable in inventory.variables:
                binning_labels[(channel, variable.name)] = (
                    variable.x_title or variable.name
                )
        filters_and_weights_specs = [
            spec
            for spec in filters_and_weights_specs
            if spec.variation == "nominal" and spec.process in data_processes
        ]

    # Build the graph from the individual specs
    graph_specs = create_graph_specs(
        dataset_specs,
        histogram_specs,
        filters_and_weights_specs,
        mode,
        columns=cfg["snapshots"].get("columns"),
    )

    # Dump specs to output file
    dump_json(
        [asdict(d) for d in dataset_specs],
        Path(cfg["dataset_specs_file"]),
    )
    dump_json(
        [asdict(h) for h in histogram_specs],
        Path(cfg["histogram_specs_file"]),
    )
    dump_json(
        [asdict(fw) for fw in filters_and_weights_specs],
        Path(cfg["filters_and_weights_specs_file"]),
    )
    dump_json(graph_specs, Path(cfg["graph_specs_file"]))

    # Set output dir based on mode
    output_dir = None
    if mode == "histogram":
        output_dir = cfg["histograms_output_dir"]
    elif mode == "snapshot":
        output_dir = cfg["snapshots_output_dir"]
    elif mode == "binning":
        output_dir = cfg["binning_output_dir"]
    else:
        raise ValueError(f"Invalid graph processing mode: {mode}")

    # Run graph processing and production of output files
    graph_report = run_graph(
        graph_specs,
        Path(output_dir),
        cfg["graph_processing"]["num_workers"],
        cfg["graph_processing"]["num_threads"],
        profiling_options,
    )

    # In binning mode, derive the equipopulated binning from the values that
    # were written by the graphs and store it as binning overrides
    if is_binning:
        from xyh.binning import derive_binning

        derive_binning(
            Path(output_dir),
            ROOT_DIR / Path(cfg["binning"]["output_file"]),
            ROOT_DIR / Path(cfg["binning"]["plots_dir"]),
            OmegaConf.to_container(cfg["binning"], resolve=True),
            labels=binning_labels,
        )

    # Finalize the profiling report
    if report is not None and graph_report is not None:
        report["subgraphs"] = graph_report["subgraphs"]
        report["subgraphs_wall_s"] = graph_report["wall_s"]
        report["memory"] = graph_report["memory"]
        report["totals"] = graph_report["totals"]
        report["python"]["total_wall_s"] = round(time() - wall_start, 3)

    return report


def _summarize_cprofile_stats(cprofile_file: Path) -> str | None:
    """Return a text summary of a cProfile statistics file.

    The summary is generated from the marshalled statistics file on disk
    rather than from a `cProfile.Profile` instance, so it does not depend
    on the internal state of the profiler object. All failures are
    swallowed and `None` is returned, such that profiling output can never
    break the processing.
    """
    try:
        summary = io.StringIO()
        stats = pstats.Stats(str(cprofile_file), stream=summary)
        stats.strip_dirs()
        stats.sort_stats("cumulative")
        stats.print_stats(30)
        return summary.getvalue()
    except Exception:
        logger.warning(
            "Failed to summarize cProfile output %s",
            cprofile_file,
            exc_info=True,
        )
        return None


def _run_with_cprofile(cfg: DictConfig, profiling_cfg: DictConfig):
    """Run `_run` under `cProfile` and store the profiling data.

    The profiler only covers the Python code executed in the main process of
    the entry point. The heavy lifting happens inside ROOT and, for
    `num_workers > 1`, inside the worker subprocesses; both are reflected in
    the per-subgraph profiling report.
    """
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        report = _run(cfg, profiling_cfg, cprofile=True)
    finally:
        profiler.disable()

    # Store the raw profiling data
    cprofile_file = Path(cfg.get("cprofile_file", "profile_output.prof"))
    cprofile_file.parent.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(str(cprofile_file))

    # Summarize the most time-consuming functions from the dumped file
    summary_text = _summarize_cprofile_stats(cprofile_file)
    if summary_text is not None:
        logger.info("cProfile summary (top 30, cumulative):\n%s", summary_text)

    if report is not None:
        report["python"]["cprofile_file"] = str(cprofile_file)
        report["python"]["cprofile_summary"] = summary_text

    return report


def _log_report_summary(report):
    """Print a summary of the profiling report to the log."""
    totals = report.get("totals", {})
    memory = report.get("memory", {})
    logger.info(
        "Profiling report: %d subgraphs, %d nodes declared, %d leaf outputs, "
        "%d events processed, subgraph processing %.2f s, peak RSS %.1f MB",
        totals.get("subgraphs", 0),
        totals.get("nodes_declared", 0),
        totals.get("leaf_nodes", 0),
        totals.get("events_processed", 0),
        totals.get("run_s", 0.0),
        memory.get("peak_rss_mb", -1.0),
    )

    for profile in report.get("subgraphs", []):
        times = profile.get("times_s", {})
        memory = profile.get("memory", {})
        leaf_nodes = profile.get("leaf_nodes", [])
        if leaf_nodes:
            first = leaf_nodes[0]
            name = "__".join(
                str(first.get(key, "?"))
                for key in (
                    "campaign",
                    "channel",
                    "category",
                    "dataset",
                    "process",
                    "variation",
                )
            )
        else:
            name = "no leaf outputs"

        logger.info(
            "Subgraph %s: declare %.2f s, run %.2f s, write %.2f s, total %.2f s, "
            "events %d, rss %.1f MB",
            name,
            times.get("declare", 0.0),
            times.get("run", 0.0),
            times.get("write", 0.0),
            times.get("total", times.get("declare", 0.0)),
            profile.get("events_processed", 0),
            memory.get("rss_mb_end", -1.0),
        )


if __name__ == "__main__":
    main()
