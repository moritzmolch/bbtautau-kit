from xyh.core.graph.node import Node
from xyh.core.specs.specs import Context, WeightProduct
from xyh.core.specs.storage import SpecsStorage

# Name of the total weight
TOTAL_WEIGHT_NAME = "__total_weight"


def _build_context_nodes_for_filters_and_weights_operations(
    context: Context,
    specs_storage: SpecsStorage,
):
    """
    Build chain of nodes from input file loading, filter operations, and weight
    calculations for a given `context`.

    The function returns the last node of the constructed chain, which can be
    used as parent for subsequent steps.

    Parameters
    ----------
    context : Context
        The context of the graph, including campaign, channel, category,
        dataset, process, and variation.

    specs_storage : SpecsStorage
        The storage containing specifications for datasets, filters, weights,
        and histograms.

    Returns
    -------
    Node
        The last node in the chain of operations, which can be used as a parent
        for subsequent nodes in the graph.
    """

    # Create the input file node
    dataset_spec = specs_storage.get_dataset_spec(context)
    n = Node(
        operation="input_files",
        data=dataset_spec,
    )

    # Create filter nodes
    for filter_spec in specs_storage.get_filters_specs(context):
        n = Node(
            operation="filter",
            data=filter_spec,
            parents=(n,),
        )

    # Create the weight nodes
    weights_spec = specs_storage.get_weights_specs(context)
    for weight_spec in weights_spec:
        n = Node(
            operation="weight",
            data=weight_spec,
            parents=(n,),
        )

    # Create the total weight multiplication node
    n = Node(
        operation="weight_product",
        data=WeightProduct(name=TOTAL_WEIGHT_NAME, weights=weights_spec),
        parents=(n,),
    )

    return n
