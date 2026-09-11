import itertools
import logging
import re

from xyh.core.config import load_inventory
from xyh.core.specs.specs import Histogram

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
            c.strip() for c in ",".split(channels) if len(c.strip()) > 0
        ]

    return name, channels


def create_histogram_spec(
    campaign_inst,
    channel_inst,
    category_inst,
    variable_inst,
) -> Histogram:
    """
    Create `Histogram` specification for a given configuration, channel,
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
        The variable instance.

    Returns
    -------
    Histogram
        The histogram specification.
    """
    # Create dictionary with variable information needed to produce the
    # histogram

    return Histogram(
        campaign=campaign_inst.name,
        channel=channel_inst.name,
        category=category_inst.name,
        variable=variable_inst.name,
        expression=(
            variable_inst.expression
            if variable_inst.expression is not None
            else variable_inst.name
        ),
        bin_edges=variable_inst.bin_edges,
    )


def create_histogram_specs(
    inventory_factory_fn_path: str,
    campaigns: list[str],
    channels: list[str],
    categories: list[str],
    variables: list[str],
):
    """
    Create histogram specs for a given subset of the analysis concerning
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
        List of category names to consider.

    variables : dict[str, list[str]]
        Dictionary of variable groups and variable names to consider.

    Returns
    -------
    list[Histogram]
        List of histogram specs for the given subset of the analysis.
    """

    # Container of histogram specs for each variable
    histogram_specs = []

    for campaign, channel in itertools.product(campaigns, channels):
        # Load the analysis inventory for this campaign and channel
        inventory = load_inventory(
            inventory_factory_fn_path,
            campaign,
            channel,
        )

        # Get the campaign and channel instances
        campaign_inst = inventory.campaign
        channel_inst = inventory.channel
        variable_insts = inventory.variables

        # Iterate through categories of this channel
        for category_inst in (
            channel_inst.get_category(c)
            for c in categories
            if channel_inst.has_category(c)
        ):
            # Iterate through all selected variables
            for variable in variables:
                # Parse the variable name to extract 'pure' name and channels
                name, channels = _parse_variable_name(variable)

                # If channels is 'None', no constraint is put on the variable.
                # If channels is a list of channel names, it needs to be checked
                # whether the variable is assigned to be processed in the
                # currently considered channel.
                if channels is not None and channel_inst.name not in channels:
                    logger.info(
                        f"Skipping variable {name} in channel "
                        + channel_inst.name
                    )
                    continue

                # Get the variable instance
                variable_inst = variable_insts.get(name)

                # Create the histogram spec
                logger.info(
                    "\n".join(
                        [
                            "Creating histogram specs for",
                            f"    campaign: {campaign_inst.name}",
                            f"    channel:  {channel_inst.name}",
                            f"    category: {category_inst.name}",
                            f"    variable: {variable_inst.name}",
                        ],
                    ),
                )
                histogram_specs.append(
                    create_histogram_spec(
                        campaign_inst,
                        channel_inst,
                        category_inst,
                        variable_inst,
                    )
                )

    return histogram_specs
