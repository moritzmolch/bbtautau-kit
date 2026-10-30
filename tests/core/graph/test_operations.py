import logging
from unittest.mock import MagicMock

import numpy as np
import pytest

from xyh.core.graph import operations
from xyh.core.graph.node import Node
from xyh.core.graph.operations import (
    Artifacts,
    ArtifactsStore,
    OutputFiles,
)


@pytest.fixture
def store():
    return ArtifactsStore()


def _with_parent(store, make_dataset, df):
    parent = Node(operation="input_files", data=make_dataset())
    store.put(parent.hash, Artifacts(data_frame=df))
    return parent


class TestContainers:
    def test_artifacts_getattr_returns_item(self):
        assert Artifacts(a=1).a == 1

    def test_artifacts_getattr_missing_raises_key_error(self):
        with pytest.raises(KeyError):
            _ = Artifacts().missing

    def test_output_files_getattr_returns_item(self):
        assert OutputFiles(f="x").f == "x"

    def test_store_put_get_roundtrip(self, store):
        arts = Artifacts(a=1)
        store.put("id", arts)
        assert store.get("id") is arts

    def test_store_get_unknown_raises_key_error(self, store):
        with pytest.raises(KeyError):
            store.get("nope")


class TestGetSingleParent:
    def test_get_single_parent_one_parent_returns_it(
        self, make_dataset, make_filter
    ):
        p = Node(operation="input_files", data=make_dataset())
        n = Node(operation="filter", data=make_filter(), parents=(p,))
        assert operations._get_single_parent(n) is p

    def test_get_single_parent_no_parent_raises(self, make_filter):
        n = Node(operation="filter", data=make_filter())
        with pytest.raises(ValueError, match="exactly one parent.*has 0"):
            operations._get_single_parent(n)

    def test_get_single_parent_two_parents_raises(
        self, make_dataset, make_filter
    ):
        p1 = Node(operation="input_files", data=make_dataset(dataset="a"))
        p2 = Node(operation="input_files", data=make_dataset(dataset="b"))
        n = Node(operation="filter", data=make_filter(), parents=(p1, p2))
        with pytest.raises(ValueError, match="exactly one parent.*has 2"):
            operations._get_single_parent(n)


class TestInputFiles:
    @pytest.fixture
    def root(self, monkeypatch):
        mock_root = MagicMock()

        def tchain(name):
            c = MagicMock()
            c.GetListOfFiles.return_value.GetEntries.return_value = 1
            return c

        mock_root.TChain.side_effect = tchain
        monkeypatch.setattr(
            "xyh.core.graph.operations.ROOT", mock_root, raising=False
        )
        return mock_root

    def test_input_files_builds_chains_and_adds_files(
        self, root, make_dataset, store
    ):
        files = {"main": ["a.root", "b.root"], "friend": ["c.root"]}
        node = Node(operation="input_files", data=make_dataset(files=files))
        arts, out = operations.input_files(node, store)
        chains = {c.args[0] for c in root.TChain.call_args_list}
        assert chains == {"ntuple"}
        assert root.TChain.call_count == 2
        main = arts.main_chain
        assert [c.args[0] for c in main.Add.call_args_list] == [
            "a.root",
            "b.root",
        ]
        assert set(arts.friend_chains) == {"friend"}
        assert out == {}

    def test_input_files_adds_nonempty_friend_only(
        self, root, make_dataset, store
    ):
        entries = {"main": 1, "full": 1, "empty": 0}
        created = []

        def tchain(name):
            c = MagicMock()
            c.GetListOfFiles.return_value.GetEntries.return_value = entries[
                list(entries)[len(created)]
            ]
            created.append(c)
            return c

        root.TChain.side_effect = tchain
        files = {"main": ["a"], "full": ["b"], "empty": []}
        node = Node(operation="input_files", data=make_dataset(files=files))
        arts, _ = operations.input_files(node, store)
        added = [c.args[0] for c in arts.main_chain.AddFriend.call_args_list]
        assert added == [arts.friend_chains["full"]]

    def test_input_files_creates_dataframe_from_main_chain(
        self, root, make_dataset, store
    ):
        node = Node(operation="input_files", data=make_dataset())
        arts, _ = operations.input_files(node, store)
        root.RDataFrame.assert_called_once_with(arts.main_chain)
        assert arts.data_frame is root.RDataFrame.return_value


class TestFilter:
    def test_filter_applies_expression_and_name(
        self, store, make_dataset, make_filter
    ):
        df = MagicMock()
        parent = _with_parent(store, make_dataset, df)
        node = Node(
            operation="filter",
            data=make_filter(name="cut", expression="pt > 20"),
            parents=(parent,),
        )
        arts, out = operations.filter(node, store)
        df.Filter.assert_called_once_with("pt > 20", "cut")
        assert arts.data_frame is df.Filter.return_value
        assert out == {}

    def test_filter_without_parent_raises(self, store, make_filter):
        node = Node(operation="filter", data=make_filter())
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.filter(node, store)


class TestWeight:
    def test_weight_defines_prefixed_column(
        self, store, make_dataset, make_weight
    ):
        df = MagicMock()
        parent = _with_parent(store, make_dataset, df)
        node = Node(
            operation="weight",
            data=make_weight(name="sf", expression="a * b"),
            parents=(parent,),
        )
        arts, out = operations.weight(node, store)
        df.Define.assert_called_once_with("__weight_sf", "a * b")
        assert arts.data_frame is df.Define.return_value
        assert out == {}

    def test_weight_without_parent_raises(self, store, make_weight):
        node = Node(operation="weight", data=make_weight())
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.weight(node, store)


class TestWeightProduct:
    @staticmethod
    def _node(store, make_dataset, columns, weights):
        from xyh.core.specs.specs import WeightProduct

        df = MagicMock()
        df.GetColumnNames.return_value = columns
        parent = _with_parent(store, make_dataset, df)
        node = Node(
            operation="weight_product",
            data=WeightProduct(weights=weights),
            parents=(parent,),
        )
        return node, df

    def test_weight_product_multiplies_prefixed_columns(
        self, store, make_dataset, make_weight
    ):
        weights = [make_weight(name="a"), make_weight(name="b")]
        node, df = self._node(
            store, make_dataset, ["__weight_a", "__weight_b", "x"], weights
        )
        arts, out = operations.weight_product(node, store)
        df.Define.assert_called_once_with(
            operations.TOTAL_WEIGHT_NAME, "__weight_a * __weight_b"
        )
        assert arts.data_frame is df.Define.return_value
        assert out == {}

    def test_weight_product_single_weight_no_operator(
        self, store, make_dataset, make_weight
    ):
        node, df = self._node(
            store, make_dataset, ["__weight_a"], [make_weight(name="a")]
        )
        operations.weight_product(node, store)
        df.Define.assert_called_once_with(
            operations.TOTAL_WEIGHT_NAME, "__weight_a"
        )

    def test_weight_product_no_weights_defines_one(
        self, store, make_dataset, caplog
    ):
        node, df = self._node(store, make_dataset, [], [])
        with caplog.at_level(logging.DEBUG, logger=operations.__name__):
            operations.weight_product(node, store)
        df.Define.assert_called_once_with(operations.TOTAL_WEIGHT_NAME, "1")
        assert "No weight columns found" in caplog.text

    def test_weight_product_missing_columns_raises(
        self, store, make_dataset, make_weight
    ):
        weights = [make_weight(name="a"), make_weight(name="b")]
        node, df = self._node(store, make_dataset, ["__weight_a"], weights)
        with pytest.raises(ValueError, match="__weight_a, __weight_b"):
            operations.weight_product(node, store)
        df.Define.assert_not_called()

    def test_weight_product_unprefixed_column_not_accepted(
        self, store, make_dataset, make_weight
    ):
        node, _ = self._node(
            store, make_dataset, ["a"], [make_weight(name="a")]
        )
        with pytest.raises(ValueError, match="Not all weight columns"):
            operations.weight_product(node, store)

    def test_weight_product_without_parent_raises(self, store):
        from xyh.core.specs.specs import WeightProduct

        node = Node(
            operation="weight_product",
            data=WeightProduct(weights=[]),
        )
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.weight_product(node, store)


class TestHistogram:
    @staticmethod
    def _node(store, make_dataset, spec):
        df = MagicMock()
        parent = _with_parent(store, make_dataset, df)
        node = Node(operation="histogram", data=spec, parents=(parent,))
        return node, df

    def test_histogram_without_expression_uses_variable_column(
        self, store, make_dataset, make_histogram
    ):
        node, df = self._node(store, make_dataset, make_histogram())
        arts, out = operations.histogram(node, store)
        df.Define.assert_not_called()
        (model, column, weight), _ = df.Histo1D.call_args
        assert model[0] == model[1] == "pt"
        assert model[2] == 2
        np.testing.assert_array_equal(model[3], [0.0, 1.0, 3.0])
        assert column == "pt"
        assert weight == operations.TOTAL_WEIGHT_NAME
        assert arts.lazy_hist is df.Histo1D.return_value
        assert arts.data_frame is df
        assert out == {}

    def test_histogram_bin_count_is_edges_minus_one(
        self, store, make_dataset, make_histogram
    ):
        spec = make_histogram(bin_edges=range(11))
        node, df = self._node(store, make_dataset, spec)
        operations.histogram(node, store)
        model = df.Histo1D.call_args.args[0]
        assert model[2] == 10

    def test_histogram_bin_edges_passed_as_numpy_array(
        self, store, make_dataset, make_histogram
    ):
        node, df = self._node(store, make_dataset, make_histogram())
        operations.histogram(node, store)
        assert isinstance(df.Histo1D.call_args.args[0][3], np.ndarray)

    def test_histogram_with_expression_defines_private_column(
        self, store, make_dataset, make_histogram
    ):
        spec = make_histogram(expression="a + b")
        node, df = self._node(store, make_dataset, spec)
        arts, _ = operations.histogram(node, store)
        df.Define.assert_called_once_with("__private__pt", "a + b")
        defined = df.Define.return_value
        assert defined.Histo1D.call_args.args[1] == "__private__pt"
        assert arts.data_frame is df.Define.return_value

    def test_histogram_without_parent_raises(self, store, make_histogram):
        node = Node(operation="histogram", data=make_histogram())
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.histogram(node, store)
