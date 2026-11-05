import itertools
import logging
import re
from typing import Any

from xyh.core.binning import (
    BinningOverrides,
    iter_binning,
    lookup_binning,
)
from xyh.core.config import load_inventory
from xyh.core.config.util import gen_category_insts
from xyh.core.specs.specs import Binning

# Get the logger for this module
logger = logging.getLogger(__name__)


def _parse_variable_name(name):
    # Parse a variable name provided from the command line
    # - The variable name can be the 'pure' name of the variable
    # - The variable name can consist of the 'pure' name and a list of channels
    #   that the variable should be considered in:
    #   '<name>[<channel 1>,<channel 2>,<...>]'
    m = re.match(r"^([^\[]+)(\[([^\]]+)\])?$", name)
    if m is None:
        raise ValueError(
            f"Variable {name} did not match expected pattern. The variable "
            + "name must be provided as the 'pure' name or the name and a "
            + "list of channels that the variable shall be applied to "
            + "('<name>[<channel 1>,<channel 2>,...]')"
        )
    name = m.group(1).strip()
    channels = m.group(3)

    # Preprocess the channel argument: either return 'None' or a list of
    # channel names
    if channels is not None:
        channels = [
            c.strip() for c in channels.split(",") if len(c.strip()) > 0
        ]

    return name, channels


def create_binning_spec(
    campaign_inst,
    channel_inst,
    category_inst,
    variable_inst,
    bin_edges: list[int | float] | None = None,
) -> Binning:
    """
    Create `Binning` specification for a given configuration, channel,
    category, and variable instance.

    Parameters
    ----------
    config_inst : Config
        The configuration instance.

    channel_inst : Channel
        The channel instance.

    category_inst : Category
        The category instance.

    variable_inst : Variable
        The variable instance. Its expression is either a string or a
        callable that takes the category instance and returns the expression
        string, for variables that depend on the category.

    bin_edges : list, optional
        Bin edges that replace the binning of the variable instance.

    Returns
    -------
    Binning
        The binning specification.
    """

    # Resolve the expression of the variable, which can depend on the category
    expression = variable_inst.expression
    if callable(expression):
        expression = expression(category_inst)

    return Binning(
        campaign=campaign_inst.name,
        channel=channel_inst.name,
        category=category_inst.name,
        variable=variable_inst.name,
        expression=expression if expression is not None else variable_inst.name,
        bin_edges=(
            bin_edges if bin_edges is not None else variable_inst.bin_edges
        ),
    )


def create_binning_specs(
    inventory_factory_fn_path: str,
    inventory_factory_kwargs: dict[str, Any],
    campaigns: list[str],
    channels: list[str],
    categories: list[str],
    variables: list[str],
    binning_overrides: BinningOverrides | None = None,
) -> list[Binning]:
    """
    Create binning specs for a given subset of the analysis concerning
    campaigns, categories and variables.

    The `variables` argument is a dictionary of variable groups and variable
    names to consider. The variable names can be provided as the 'pure' name of
    the variable or as the name and a list of channels that the variable should
    be considered in: `<name>[<channel 1>,<channel 2>,...]`

    Parameters
    ----------
    inventory_factory_fn_path : str
        The python module path to the inventory factory function.

    campaigns : list[str]
        List of campaign names to consider.

    channels : list[str]
        List of channel names to consider.

    categories : list[str]
        List of regular expressions that are matched in full against the
        category names (including nested categories) of each channel.
        Plain category names match themselves. Patterns that match nothing in
        a channel are ignored for this channel.

    variables : dict[str, list[str]]
        Dictionary of variable groups and variable names to consider.

    binning_overrides : BinningOverrides, optional
        Bin edges per campaign, channel, category and variable that replace
        the binning defined in the inventory.

    Returns
    -------
    list[Binning]
        List of binning specs for the given subset of the analysis.
    """

    # Container of binning specs for each variable
    binning_specs = []
    used_overrides = set()
    matched_category_patterns = set()

    for campaign, channel in itertools.product(campaigns, channels):
        # Load the analysis inventory for this campaign and channel
        inventory = load_inventory(
            inventory_factory_fn_path,
            campaign,
            channel,
            **inventory_factory_kwargs,
        )

        # Get the campaign and channel instances
        campaign_inst = inventory.campaign
        channel_inst = inventory.channel
        variable_insts = inventory.variables

        # Remember which patterns match a category in any channel
        matched_category_patterns.update(
            pattern
            for pattern in categories
            if next(gen_category_insts(channel_inst, [pattern]), None)
            is not None
        )

        # Iterate through categories of this channel
        for category_inst in gen_category_insts(channel_inst, categories):
            logger.debug(
                "\n".join(
                    [
                        "Creating histogram specs for",
                        f"    campaign: {campaign_inst.name}",
                        f"    channel:  {channel_inst.name}",
                        f"    category: {category_inst.name}",
                        f"    variables: <{len(variables)} items>",
                    ],
                ),
            )

            # Iterate through all selected variables
            for variable in variables:
                # Parse the variable name to extract 'pure' name and channels
                name, variable_channels = _parse_variable_name(variable)

                # If variable_channels is 'None', no constraint is put on the variable.
                # If variable_channels is a list of channel names, it needs to be checked
                # whether the variable is assigned to be processed in the
                # currently considered channel.
                if (
                    variable_channels is not None
                    and channel_inst.name not in variable_channels
                ):
                    logger.debug(
                        f"Skipping variable {name} in channel "
                        + channel_inst.name
                    )
                    continue

                # Get the variable instance
                variable_inst = variable_insts.get(name)
                bin_edges = lookup_binning(
                    binning_overrides,
                    campaign_inst.name,
                    channel_inst.name,
                    category_inst.name,
                    name,
                )
                if bin_edges is not None:
                    used_overrides.add(
                        (
                            campaign_inst.name,
                            channel_inst.name,
                            category_inst.name,
                            name,
                        )
                    )
                binning_specs.append(
                    create_binning_spec(
                        campaign_inst,
                        channel_inst,
                        category_inst,
                        variable_inst,
                        bin_edges,
                    )
                )

    for pattern in categories:
        if pattern not in matched_category_patterns:
            logger.warning(
                f"Category pattern '{pattern}' matches no category in any "
                "channel. Note that classifier categories only exist if "
                "XYH_PROFILE selects signals (the default is BKG_ONLY)."
            )

    if binning_overrides:
        unused = set(iter_binning(binning_overrides)) - used_overrides
        logger.info(f"Overrode the binning of {len(used_overrides)} histograms")
        for key in sorted(unused):
            logger.warning(
                "Binning override matches no histogram: " + "/".join(key)
            )

    return binning_specs
