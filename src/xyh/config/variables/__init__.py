"""
Variables relevant for this analysis.
"""

from itertools import chain

from order import Channel, UniqueObjectIndex, Variable

from ._control_plots import get_control_plot_variables

# Only expose the get_variables function
__all__ = ["get_variables"]


def get_variables(
    channel_inst: Channel,
) -> UniqueObjectIndex:
    """
    Get the variables for a given channel.

    Parameters
    ----------
    channel_inst: Channel
        The channel instance.

    Returns
    -------
    UniqueObjectIndex
        Index of `Variable` objects for the given channel.
    """

    # Create the variable index
    variable_insts = UniqueObjectIndex(
        Variable,
        # Control plot variables
        get_control_plot_variables(channel_inst),
    )

    return variable_insts
