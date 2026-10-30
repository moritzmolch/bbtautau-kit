import pytest

from xyh.core.graph.node import Node


def test_node_init_invalid_operation_raises_value_error(make_filter):
    with pytest.raises(ValueError, match="Invalid operation: bogus"):
        Node(operation="bogus", data=make_filter())


@pytest.mark.parametrize(
    "operation",
    ["input_files", "filter", "weight", "weight_product", "histogram"],
)
def test_node_init_valid_operation_accepted(operation, make_filter):
    node = Node(operation=operation, data=make_filter())
    assert node.operation == operation
    assert node.parents == ()


def test_node_hash_same_inputs_is_deterministic(make_filter):
    a = Node(operation="filter", data=make_filter())
    b = Node(operation="filter", data=make_filter())
    assert a is not b
    assert a.hash == b.hash
    assert hash(a) == hash(b)


def test_node_hash_is_sha256_hex(make_filter):
    h = Node(operation="filter", data=make_filter()).hash
    assert len(h) == 64
    int(h, 16)


def test_node_hash_different_data_differs(make_filter):
    a = Node(operation="filter", data=make_filter(expression="x > 0"))
    b = Node(operation="filter", data=make_filter(expression="x > 1"))
    assert a.hash != b.hash


def test_node_hash_different_operation_differs(make_filter):
    data = make_filter()
    a = Node(operation="filter", data=data)
    b = Node(operation="weight", data=data)
    assert a.hash != b.hash


def test_node_hash_different_parents_differs(make_filter, make_dataset):
    p1 = Node(operation="input_files", data=make_dataset(dataset="a"))
    p2 = Node(operation="input_files", data=make_dataset(dataset="b"))
    a = Node(operation="filter", data=make_filter(), parents=(p1,))
    b = Node(operation="filter", data=make_filter(), parents=(p2,))
    c = Node(operation="filter", data=make_filter())
    assert len({a.hash, b.hash, c.hash}) == 3


def test_node_hash_parent_order_matters(make_filter, make_dataset):
    p1 = Node(operation="input_files", data=make_dataset(dataset="a"))
    p2 = Node(operation="input_files", data=make_dataset(dataset="b"))
    a = Node(operation="filter", data=make_filter(), parents=(p1, p2))
    b = Node(operation="filter", data=make_filter(), parents=(p2, p1))
    assert a.hash != b.hash


def test_node_hash_is_cached(make_filter):
    node = Node(operation="filter", data=make_filter())
    assert node.hash is node.hash


def test_node_dunder_hash_usable_in_set(make_filter):
    a = Node(operation="filter", data=make_filter())
    b = Node(operation="filter", data=make_filter())
    # eq=False: identity equality, so equal-hash nodes stay distinct entries
    assert len({a, b}) == 2
    assert a in {a}
