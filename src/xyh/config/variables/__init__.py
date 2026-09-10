import importlib

from order import Analysis, Campaign, Category, UniqueObjectIndex


def get_variables(
    analysis_inst: Analysis,
    campaign_inst: Campaign,
    category_inst: Category,
    group: str,
) -> UniqueObjectIndex:
    """
    Get the variables for a given campaign, category and group.

    Parameters
    ----------
    analysis_inst: Analysis
        The analysis instance.

    campaign_inst: Campaign
        The campaign instance.

    category_inst: Category
        The category instance.

    group: str
        The group name (corresponds to a submodule in this package).

    Returns
    -------
    UniqueObjectIndex
        The variables for the given campaign, category and group.
    """

    # Get module for the given group
    variable_group = importlib.import_module(f".{group}", package=__package__)

    return variable_group.get_variables(
        analysis_inst, campaign_inst, category_inst
    )
