import re
from itertools import product
from operator import eq, ge

from order import Channel


def _get_operator_and_selection(object_multiplicity: str, selection: str):
    # Parse the selection
    match = re.match(r"^(eq|geq)(\d)$", selection)
    if not match:
        raise ValueError(f"Could not parse selection '{selection}'")

    # Convert binary operators into symbols
    operator = {"eq": eq, "geq": ge}[match.group(1)]
    number = match.group(2)

    return operator, number


def _get_label(object_multiplicity: str, selection: str):
    # Parse the selection
    match = re.match(r"^(eq|geq)(\d)$", selection)
    if not match:
        raise ValueError(f"Could not parse selection '{selection}'")

    # Convert binary operators into symbols
    symbol = {"eq": "=", "geq": r"\geq"}[match.group(1)]
    number = match.group(2)

    return f"{object_multiplicity} ${symbol}$ {number}"


def _get_root_selection(variable: str, selection: str):
    # Parse the selection
    match = re.match(r"^(eq|geq)(\d)$", selection)
    if not match:
        raise ValueError(f"Could not parse selection '{selection}'")

    # Convert binary operators into symbols
    symbol = {"eq": "==", "geq": ">="}[match.group(1)]
    number: str = match.group(2)

    return f"{variable} {symbol} {number}"


def add_jet_categories(channel_inst: Channel):
    # Base category, containing all events before categorization/classification

    # Categories in n_jets space
    for n_jets_sel in [
        "eq0",
        "eq1",
        "eq2",
        "eq3",
        "geq3",
        "eq4",
        "geq4",
        "geq5",
    ]:
        # Get the labels for n_jets and n_bjets selection
        label_n_jets = _get_label(r"$n_{\text{jets}}$", n_jets_sel)

        # Get the ROOT expression for the selection
        selection_n_jets = _get_root_selection("n_jets", n_jets_sel)

        # Get operator and number for n_jets selection
        operator_n_jets, n_jets = _get_operator_and_selection(
            "n_jets", n_jets_sel
        )

        # Add the category instance to the channel
        channel_inst.add_category(
            name=f"{channel_inst.name}_{n_jets_sel}j",
            label=f"{channel_inst.label} ({label_n_jets})",
            label_short=f"{channel_inst.name}",
            tags={"jet_cat"},
            aux={
                "n_jets_selection": selection_n_jets,
                "n_jets_operator": operator_n_jets,
                "n_jets": n_jets,
            },
        )

    # Categories in (n_jets, n_bjets) space
    for n_jets_sel, n_bjets_sel in product(
        ["eq0", "eq1", "eq2", "eq3", "geq3", "eq4", "geq4", "geq5"],
        ["eq0", "eq1", "eq2", "geq2", "eq3", "geq3", "geq4"],
    ):
        # Get the labels for n_jets and n_bjets selection
        label_n_jets = _get_label(r"$n_{\text{jets}}$", n_jets_sel)
        label_n_bjets = _get_label(r"$n_{\text{b-jets}}$", n_bjets_sel)

        # Get the ROOT expression for the selection
        selection_n_jets = _get_root_selection("n_jets", n_jets_sel)
        selection_nbjets = _get_root_selection("n_bjets", n_bjets_sel)

        # Get operator and number for n_bjets selection
        operator_n_jets, n_jets = _get_operator_and_selection(
            "n_jets", n_jets_sel
        )
        operator_n_bjets, n_bjets = _get_operator_and_selection(
            "n_bjets", n_bjets_sel
        )

        # Add the category instance to the channel
        channel_inst.add_category(
            name=f"{channel_inst.name}_{n_jets_sel}j_{n_bjets_sel}b",
            label=f"{channel_inst.label} ({label_n_jets}, {label_n_bjets})",
            label_short=f"{channel_inst.name}",
            tags={"jet_bjet_cat"},
            aux={
                "n_jets_selection": selection_n_jets,
                "n_bjets_selection": selection_nbjets,
                "n_jets": n_jets,
                "n_jets_operator": operator_n_jets,
                "n_bjets": n_bjets,
                "n_bjets_operator": operator_n_bjets,
            },
        )
