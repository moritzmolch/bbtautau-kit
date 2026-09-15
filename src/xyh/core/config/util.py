from collections.abc import Generator
from itertools import chain

from order import Dataset, Process

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
