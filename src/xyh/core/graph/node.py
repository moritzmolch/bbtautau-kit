import hashlib
import json
from dataclasses import asdict, dataclass, field
from functools import cached_property

from xyh.core.specs import Spec

_operations = {
    "input_files",
    "filter",
    "weight",
    "weight_product",
    "histogram",
}


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
                },
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()

    def __hash__(self):
        return hash(self.hash)
