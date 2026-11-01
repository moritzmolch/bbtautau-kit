import pytest

from xyh.core.graph import builder, executor
from xyh.core.graph.artifacts import Artifacts
from xyh.core.graph.node import Node, Output


@pytest.fixture
def make_node(make_dataset, make_filter):
    """Factory for filter/input nodes with optional file outputs."""

    def _make(name, parents=(), out_path=None, exists=False):
        outputs = {}
        if out_path is not None:
            outputs = {"out": Output(path=str(out_path))}
            if exists:
                out_path.write_text("x")
        if not parents:
            return Node(
                operation="input_files",
                data=make_dataset(dataset=name),
                outputs=outputs,
            )
        return Node(
            operation="filter",
            data=make_filter(name=name),
            parents=tuple(parents),
            outputs=outputs,
        )

    return _make


class TestPruneGraph:
    def test_prune_graph_all_outputs_exist_returns_empty_graph(
        self, make_node, tmp_path
    ):
        root = make_node("root")
        leaf = make_node(
            "leaf", (root,), out_path=tmp_path / "leaf.root", exists=True
        )
        graph = builder.build_graph_from_leaf_nodes([leaf])
        assert len(executor._prune_graph(graph)) == 0

    def test_prune_graph_no_outputs_exist_keeps_all_nodes(
        self, make_node, tmp_path
    ):
        root = make_node("root")
        mid = make_node("mid", (root,))
        leaf = make_node("leaf", (mid,), out_path=tmp_path / "leaf.root")
        graph = builder.build_graph_from_leaf_nodes([leaf])
        pruned = executor._prune_graph(graph)
        assert set(pruned.nodes) == set(graph.nodes)
        assert set(pruned.edges) == set(graph.edges)

    def test_prune_graph_two_sinks_one_done_keeps_missing_branch_and_prefix(
        self, make_node, tmp_path
    ):
        root = make_node("root")
        shared = make_node("shared", (root,))
        done = make_node(
            "done", (shared,), out_path=tmp_path / "done.root", exists=True
        )
        todo_mid = make_node("todo_mid", (shared,))
        todo = make_node("todo", (todo_mid,), out_path=tmp_path / "todo.root")
        graph = builder.build_graph_from_leaf_nodes([done, todo])
        pruned = executor._prune_graph(graph)
        assert set(pruned.nodes) == {
            root.hash,
            shared.hash,
            todo_mid.hash,
            todo.hash,
        }
        assert done.hash not in pruned

    def test_prune_graph_leaf_without_outputs_is_kept(self, make_node):
        root = make_node("root")
        leaf = make_node("leaf", (root,))
        graph = builder.build_graph_from_leaf_nodes([leaf])
        assert set(executor._prune_graph(graph).nodes) == {
            root.hash,
            leaf.hash,
        }

    def test_prune_graph_intermediate_with_existing_output_kept_if_needed(
        self, make_node, tmp_path
    ):
        root = make_node("root")
        mid = make_node(
            "mid", (root,), out_path=tmp_path / "mid.root", exists=True
        )
        leaf = make_node("leaf", (mid,), out_path=tmp_path / "leaf.root")
        graph = builder.build_graph_from_leaf_nodes([leaf])
        assert set(executor._prune_graph(graph).nodes) == {
            root.hash,
            mid.hash,
            leaf.hash,
        }

    def test_prune_graph_returns_copy_with_node_data(self, make_node):
        root = make_node("root")
        graph = builder.build_graph_from_leaf_nodes([root])
        pruned = executor._prune_graph(graph)
        assert pruned is not graph
        assert pruned.nodes[root.hash]["node"] is root


class TestExecuteGraph:
    @pytest.fixture
    def calls(self, monkeypatch):
        """Install a recording fake operation resolver."""
        calls = []

        def fake_get_operation_fn(node):
            def op(n, input_artifacts):
                calls.append((n, dict(input_artifacts)))
                return Artifacts(
                    name=n.data.dataset
                    if n.operation == "input_files"
                    else n.data.name
                )

            return op

        monkeypatch.setattr(executor, "get_operation_fn", fake_get_operation_fn)
        return calls

    def test_execute_graph_runs_in_topological_order(self, calls, make_node):
        root = make_node("root")
        mid = make_node("mid", (root,))
        leaf = make_node("leaf", (mid,))
        graph = builder.build_graph_from_leaf_nodes([leaf])
        executor._execute_graph(graph)
        assert [c[0] for c in calls] == [root, mid, leaf]

    def test_execute_graph_passes_exactly_parent_artifacts(
        self, calls, make_node
    ):
        a = make_node("a")
        b = make_node("b")
        join = make_node("join", (a, b))
        unrelated = make_node("unrelated", (a,))
        graph = builder.build_graph_from_leaf_nodes([join, unrelated])
        executor._execute_graph(graph)
        inputs = {c[0].hash: c[1] for c in calls}
        assert inputs[a.hash] == {}
        assert set(inputs[join.hash]) == {a.hash, b.hash}
        assert inputs[join.hash][a.hash].name == "a"
        assert inputs[join.hash][b.hash].name == "b"
        assert set(inputs[unrelated.hash]) == {a.hash}

    def test_execute_graph_returns_leaf_artifacts(self, calls, make_node):
        root = make_node("root")
        l1 = make_node("l1", (root,))
        l2 = make_node("l2", (root,))
        graph = builder.build_graph_from_leaf_nodes([l1, l2])
        result = executor._execute_graph(graph)
        assert sorted(a.name for a in result) == ["l1", "l2"]

    def test_execute_graph_empty_graph_returns_empty_list(self, calls):
        from networkx import DiGraph

        assert executor._execute_graph(DiGraph()) == []
        assert calls == []


class TestExecute:
    @pytest.fixture
    def calls(self, monkeypatch):
        calls = []

        def fake_get_operation_fn(node):
            def op(n, input_artifacts):
                calls.append(n)
                return Artifacts(hash=n.hash)

            return op

        monkeypatch.setattr(executor, "get_operation_fn", fake_get_operation_fn)
        return calls

    def test_execute_all_outputs_present_runs_no_operation(
        self, calls, make_node, tmp_path
    ):
        root = make_node("root")
        leaf = make_node(
            "leaf", (root,), out_path=tmp_path / "leaf.root", exists=True
        )
        graph = builder.build_graph_from_leaf_nodes([leaf])
        assert executor.execute([graph]) == []
        assert calls == []

    def test_execute_runs_only_required_nodes(self, calls, make_node, tmp_path):
        root = make_node("root")
        done = make_node(
            "done", (root,), out_path=tmp_path / "d.root", exists=True
        )
        todo = make_node("todo", (root,), out_path=tmp_path / "t.root")
        graph = builder.build_graph_from_leaf_nodes([done, todo])
        result = executor.execute([graph])
        assert calls == [root, todo]
        assert [a.hash for a in result] == [todo.hash]

    def test_execute_concatenates_leaf_artifacts_of_all_graphs(
        self, calls, make_node
    ):
        g1 = builder.build_graph_from_leaf_nodes(
            [make_node("l1", (make_node("r1"),))]
        )
        g2 = builder.build_graph_from_leaf_nodes(
            [make_node("l2", (make_node("r2"),))]
        )
        result = executor.execute([g1, g2])
        leaves = [n for n in calls if n.operation == "filter"]
        assert [a.hash for a in result] == [n.hash for n in leaves]
        assert len(result) == 2

    def test_execute_no_graphs_returns_empty_list(self, calls):
        assert executor.execute([]) == []
