"""
Derive an equipopulated binning from data.

For every campaign, channel and category of the inventory, the selection of the
category is applied to the data events (no simulation) and the bin edges are
chosen such that every bin holds the same number of data events. The edges are
written to a JSON file that overrides the binning of the inventory when set as
`binning_overrides.file` in `run_graphs`, see `xyh.core.binning`.

The selections and ntuple file lists are taken from the specs of an existing
production (`binning.specs_tag`).
"""

import logging
from pathlib import Path

import matplotlib
import numpy as np
import ROOT
from omegaconf import DictConfig

from xyh import ROOT_DIR
from xyh.core.binning import (
    dump_binning_overrides,
    equipopulated_edges,
    set_binning,
)
from xyh.core.cli import hydra_cli
from xyh.core.config import load_inventory
from xyh.core.correctionlib_cpp import ensure_declared
from xyh.core.specs.inputs import (
    get_filters_and_weights,
    get_input_files,
    load_specs,
    make_data_frame,
    resolve_processes,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

logger = logging.getLogger(__name__)

ROOT.EnableImplicitMT(16)


def _column(name: str) -> str:
    return f"__binning_{name}"


def _read_values(
    specs: list[dict],
    graph_specs: dict,
    campaign: str,
    channel: str,
    expressions: dict[str, str],
    n_files: int | None,
) -> dict[str, np.ndarray]:
    """Read the variables of all events passing the selection of the specs."""
    chunks = {name: [] for name in expressions}
    for spec in specs:
        files = get_input_files(
            graph_specs, campaign, channel, spec["dataset"], n_files
        )
        data_frame = make_data_frame(files)
        for filter_name, expression in spec["filters"].items():
            data_frame = data_frame.Filter(expression, filter_name)
        for name, expression in expressions.items():
            ensure_declared(expression)
            data_frame = data_frame.Define(
                _column(name), f"static_cast<double>({expression})"
            )
        arrays = data_frame.AsNumpy(
            columns=[_column(name) for name in expressions]
        )
        for name in expressions:
            chunks[name].append(arrays[_column(name)])
    return {name: np.concatenate(c) for name, c in chunks.items()}


def _plot(values, edges, label, x_title, output_file: Path) -> None:
    counts, _ = np.histogram(values, bins=edges)
    fig, ax = plt.subplots()
    ax.stairs(counts, edges, linewidth=2)
    ax.set_xlabel(x_title)
    ax.set_ylabel("Data events")
    ax.set_ylim(0, 1.3 * counts.max())
    ax.text(0.02, 0.95, label, transform=ax.transAxes, va="top")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file)
    plt.close(fig)


@hydra_cli("derive_binning")
def main(cfg: DictConfig):
    ROOT.TH1.AddDirectory(0)
    settings = cfg["binning"]

    filters_and_weights_specs = load_specs(
        settings["specs_tag"], "filters_and_weights"
    )
    graph_specs = load_specs(settings["specs_tag"], "graphs")
    output_file = ROOT_DIR / settings["output_file"]
    plots_dir = ROOT_DIR / settings["plots_dir"]

    overrides = {}
    for campaign in cfg["inventory"]["campaigns"]:
        for channel in cfg["inventory"]["channels"]:
            inventory = load_inventory(
                cfg["inventory"]["factory_fn"],
                campaign,
                channel,
                **cfg["inventory"]["factory_fn_kwargs"],
            )
            processes = resolve_processes(
                inventory, settings["data_process_group"]
            )

            # Variables with a binning in this channel
            variables = {}
            for name, variable_settings in settings["variables"].items():
                variable_inst = (
                    inventory.variables.get(name)
                    if inventory.variables.has(name)
                    else None
                )
                if variable_inst is None or len(variable_inst.bin_edges) < 2:
                    logger.warning(f"Skipping {name} in channel {channel}")
                    continue
                variables[name] = (
                    variable_inst,
                    {**settings, **(variable_settings or {})},
                )
            if not variables:
                continue

            for category in cfg["inventory"]["categories"]:
                if not inventory.channel.has_category(category):
                    continue
                specs = get_filters_and_weights(
                    filters_and_weights_specs,
                    campaign,
                    channel,
                    category,
                    processes,
                )
                values = _read_values(
                    specs,
                    graph_specs,
                    campaign,
                    channel,
                    {
                        name: inst.expression or name
                        for name, (inst, _) in variables.items()
                    },
                    settings["n_files"],
                )
                for name, (inst, var_settings) in variables.items():
                    edges = equipopulated_edges(
                        values[name],
                        var_settings["n_bins"],
                        range=var_settings.get("range"),
                        precision=var_settings["precision"],
                    )
                    set_binning(
                        overrides, campaign, channel, category, name, edges
                    )
                    logger.info(
                        f"{campaign}/{channel}/{category}/{name}: "
                        f"{len(values[name])} events, {len(edges) - 1} bins"
                    )
                    _plot(
                        values[name],
                        edges,
                        f"{campaign} {category}",
                        inst.x_title,
                        plots_dir / campaign / f"{category}__{name}.png",
                    )

    dump_binning_overrides(overrides, output_file)
    logger.info(f"Wrote binning to {output_file}")


if __name__ == "__main__":
    main()
