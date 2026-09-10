import itertools
import logging
import re

from xyh.core.analysis_config import load_analysis_inst
from xyh.core.specs.specs import Histogram


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
    config_inst,
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
        campaign=config_inst.campaign.name,
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
    analysis,
    campaigns,
    categories,
    variables: dict[str, list[str]],
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
    analysis : str
        The python module path to the analysis instance.

    campaigns : list[str]
        List of campaign names to consider.

    categories : list[str]
        List of category names to consider.

    variables : dict[str, list[str]]
        Dictionary of variable groups and variable names to consider.

    Returns
    -------
    list[Histogram]
        List of histogram specs for the given subset of the analysis.
    """
    # Load the analysis instance
    analysis_inst = load_analysis_inst(analysis)

    # Container of histogram specs for each variable
    histogram_specs = []

    for campaign, category in itertools.product(campaigns, categories):
        # Get the configuration, category and channel instances
        config_inst = analysis_inst.get_config(campaign)
        category_inst = config_inst.get_category(category)
        channel_inst = category_inst.channel

        # Iterate through all selected variables
        for group, variable_names in variables.items():
            # Get list of available variables in this group
            available_variable_insts = config_inst.x.get_variables(
                category_inst, group
            )

            for variable in variable_names:
                # Parse the variable name to extract 'pure' name and channels
                name, channels = _parse_variable_name(variable)

                # If channels is 'None', no constraint is put on the variable.
                # If channels is a list of channel names, it needs to be checked
                # whether the variable is assigned to be processed in the
                # currently considered channel.
                if channels is not None and channel_inst.name not in channels:
                    logging.info(
                        f"Skipping variable {name} in channel "
                        + channel_inst.name
                    )
                    continue

                # Get the variable instance
                variable_inst = available_variable_insts.get(name)

                # Create the histogram spec
                logging.info(
                    "\n".join(
                        [
                            "Creating histogram specs for",
                            f"    campaign: {campaign}",
                            f"    channel:  {channel_inst.name}",
                            f"    category: {category}",
                            f"    variable: {variable_inst.name}",
                        ],
                    ),
                )
                histogram_specs.append(
                    create_histogram_spec(
                        config_inst,
                        channel_inst,
                        category_inst,
                        variable_inst,
                    )
                )

    return histogram_specs
