from collections.abc import Generator
from itertools import chain

from order import Dataset

from ._inventory import Inventory


def gen_dataset_insts(
    inventory: Inventory,
) -> Generator[Dataset, None, None]:
    """
    Collect all datasets associated with a process in the inventory's
    `process_set`.

    Parameters
    ----------
    inventory : Inventory
        The analysis inventory.

    Yields
    ------
    Dataset
        Dataset instance.
    """

    for process in chain.from_iterable(
        g.processes for g in inventory.process_set.process_groups
    ):
        print(process)
        for dataset in chain(inventory.process_datasets_map[process]):
            print("   ", dataset)
            yield inventory.campaign.datasets.get(dataset)
