from collections import OrderedDict

from xyh.core.wrapper import Wrapper


@Wrapper.wrap
def jet_categories(self) -> OrderedDict[str, str]:
    """
    Selections to form jet categories.

    These selections are only applied to categories which have the `jet_cat`
    tag.
    """

    # Storage for all bb pair selections
    selections = OrderedDict()

    # Skip categories which do not have the "jet_cat" tag
    if not self.category_inst.has_tag("jet_cat"):
        return selections

    # Add selections for jets and b jets, taken from the category metadata
    selections["n_jets_selection"] = self.category_inst.x.n_jets_selection
    if self.category_inst.has_aux("n_bjets_selection"):
        selections["n_bjets_selection"] = self.category_inst.x.n_bjets_selection

    return selections
