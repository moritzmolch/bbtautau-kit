import re
from collections.abc import Generator, Iterable
from itertools import chain

from order import Category, Channel, Dataset, Process

from ._inventory import Inventory


def gen_process_insts(
    inventory: Inventory,
) -> Generator[Process, None, None]:
    """
    Collect all processes associated with the inventory's `process_set`.

    Parameters
    ----------
    inventory : Inventory
        The analysis inventory.

    Yields
    ------
    Process
        Process instance.
    """

    for process in chain.from_iterable(
        g.processes for g in inventory.process_set.process_groups
    ):
        yield inventory.processes.get(process)


def gen_category_insts(
    channel_inst: Channel,
    patterns: Iterable[str],
) -> Generator[Category, None, None]:
    """
    Collect the categories of a channel whose names match regular expressions.

    Each pattern is matched in full (`re.fullmatch`) against the names of all
    categories of the channel, including nested categories. Plain category
    names are valid patterns that match themselves. A pattern that matches no
    category of this channel yields nothing, since not every category exists in
    every channel.

    Parameters
    ----------
    channel_inst : Channel
        The channel instance.

    patterns : Iterable[str]
        Regular expressions for the category names.

    Yields
    ------
    Category
        Category instance. Every category is yielded once, ordered by the
        first matching pattern and then by declaration order.

    Raises
    ------
    ValueError
        If an entry of `patterns` is not a valid regular expression.
    """

    # Compile all patterns first, so that malformed ones are reported
    # independently of the channel
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as e:
            raise ValueError(
                f"Category pattern '{pattern}' is not a valid regular "
                f"expression: {e}"
            ) from e

    # All categories of the channel including nested ones
    category_insts = [c for c, _, _ in channel_inst.walk_categories()]

    seen = set()
    for pattern in compiled:
        for category_inst in category_insts:
            if category_inst.name in seen:
                continue
            if pattern.fullmatch(category_inst.name):
                seen.add(category_inst.name)
                yield category_inst


def skip_process_in_category(
    category_inst: Category,
    process_inst: Process,
) -> bool:
    """
    Check whether a process is to be skipped in a category.

    The decision is delegated to the optional auxiliary function
    `skip_process_inst` of the category.

    Parameters
    ----------
    category_inst : Category
        The category instance.

    process_inst : Process
        The process instance.

    Returns
    -------
    bool
        `True` if the process is skipped in this category, `False` otherwise
        (also if the category does not define `skip_process_inst`).
    """

    if category_inst.has_aux("skip_process_inst"):
        return bool(category_inst.x.skip_process_inst(process_inst))
    return False


def gen_dataset_insts(
    inventory: Inventory,
    process: Process | str | None = None,
) -> Generator[Dataset, None, None]:
    """
    Collect all datasets associated with processes in the inventory's
    `process_set`.

    Parameters
    ----------
    inventory : Inventory
        The analysis inventory.

    process : Process | str | None, optional
        A process instance or the name of a process. If `None`, all datasets
        associated with all processes in the inventory's `process_set` are
        collected.

    Yields
    ------
    Dataset
        Dataset instance.

    Raises
    ------
    TypeError
        If `process` is not of type `str`, `Process`, or `None`.
    """

    # Select processes iterable depending on the `process` argument
    processes = []
    if process is None:
        processes = chain.from_iterable(
            g.processes for g in inventory.process_set.process_groups
        )
    elif isinstance(process, str):
        processes = [process]
    elif isinstance(process, Process):
        processes = [process.name]
    else:
        raise TypeError(
            f"Argument `process` must be of type `str`, `Process`, or `None`, "
            f"but got {type(process)}"
        )

    for process in processes:
        for dataset in chain(inventory.process_datasets_map[process]):
            yield inventory.campaign.datasets.get(dataset)


def gen_process_and_dataset_insts(
    inventory: Inventory,
) -> Generator[tuple[Process, Dataset], None, None]:
    """
    Collect all `(process, dataset)` pairs associated with a process in the
    inventory's `process_set`.

    Parameters
    ----------
    inventory : Inventory
        The analysis inventory.

    Yields
    ------
    tuple[Process, Dataset]
        Tuple of a process and a dataset instance.
    """

    for process in chain.from_iterable(
        g.processes for g in inventory.process_set.process_groups
    ):
        process_inst = inventory.processes.get(process)
        for dataset in chain(inventory.process_datasets_map[process]):
            yield process_inst, inventory.campaign.datasets.get(dataset)
