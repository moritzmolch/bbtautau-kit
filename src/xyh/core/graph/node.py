import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from functools import cached_property

from xyh.core.specs.specs import Spec

_operations = {
    "input_files",
    "filter",
    "weight",
    "weight_product",
    "histogram",
    "write_histograms",
    "snapshot",
    "write_snapshots",
    "binning",
    "write_binning",
}


@dataclass(frozen=True, eq=False, kw_only=True)
class Output:
    path: str

    def exists(self) -> bool:
        """
        Check if the output file exists.

        Returns
        -------
        bool
            True if the output file exists, False otherwise.
        """
        return os.path.exists(self.path)

    def isfile(self) -> bool:
        """
        Check if the output path is a file.

        Returns
        -------
        bool
            True if the output path is a file, False otherwise.
        """
        return os.path.isfile(self.path)

    def isdir(self) -> bool:
        """
        Check if the output path is a directory.

        Returns
        -------
        bool
            True if the output path is a directory, False otherwise.
        """
        return os.path.isdir(self.path)


@dataclass(frozen=True, eq=False, kw_only=True)
class Node:
    """
    Node in a computational graph.

    The node encapsulates the operation type and the associated data for that
    operation. It also keeps track of the parent nodes for graph construction.

    Attributes
    ----------

    operation : str
        The type of operation this node represents. Must be one of the predefined
        operations in the `_operations` set.

    data : Spec
        The data associated with the operation. This should be an instance of a
        subclass of `Spec`.

    parents : tuple[Node, ...] (optional)
        A tuple of parent nodes to this node. Default: `()`.
    """

    operation: str
    data: Spec
    parents: tuple["Node", ...] = field(default_factory=tuple)
    outputs: dict[str, Output] = field(default_factory=dict)

    def __post_init__(self):
        # Validate that the operation is one of the allowed operations
        if self.operation not in _operations:
            raise ValueError(f"Invalid operation: {self.operation}")

    @cached_property
    def hash(self):
        """
        Calculate the hash of the node.

        The hash allows to identify deduplicate nodes by including the
        operation, data, and hashes of parent nodes into the hash calculation.
        The hash is computed using SHA-256.

        Returns
        -------
        str
            The hash of the node.
        """
        return hashlib.sha256(
            json.dumps(
                {
                    "operation": self.operation,
                    "data": asdict(self.data),
                    "parents": [p.hash for p in self.parents],
                    "outputs": {k: asdict(v) for k, v in self.outputs.items()},
                },
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()

    def __hash__(self):
        return hash(self.hash)
