import logging
import os
from unittest.mock import MagicMock

import numpy as np
import pytest

from xyh.core.graph import operations
from xyh.core.graph.artifacts import Artifacts
from xyh.core.graph.node import Node, Output
from xyh.core.specs.specs import HistogramsOutput, Snapshot, Spec


@pytest.fixture
def artifacts():
    return {}


def _with_parent(artifacts, make_dataset, df):
    parent = Node(operation="input_files", data=make_dataset())
    artifacts[parent.hash] = Artifacts(data_frame=df)
    return parent


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
        self, root, make_dataset, artifacts
    ):
        files = {"main": ["a.root", "b.root"], "friend": ["c.root"]}
        node = Node(operation="input_files", data=make_dataset(files=files))
        arts = operations.input_files(node, artifacts)
        chains = {c.args[0] for c in root.TChain.call_args_list}
        assert chains == {"ntuple"}
        assert root.TChain.call_count == 2
        main = arts.main_chain
        assert [c.args[0] for c in main.Add.call_args_list] == [
            "a.root",
            "b.root",
        ]
        assert set(arts.friend_chains) == {"friend"}

    def test_input_files_adds_nonempty_friend_only(
        self, root, make_dataset, artifacts
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
        arts = operations.input_files(node, artifacts)
        added = [c.args[0] for c in arts.main_chain.AddFriend.call_args_list]
        assert added == [arts.friend_chains["full"]]

    def test_input_files_creates_dataframe_from_main_chain(
        self, root, make_dataset, artifacts
    ):
        node = Node(operation="input_files", data=make_dataset())
        arts = operations.input_files(node, artifacts)
        root.RDataFrame.assert_called_once_with(arts.main_chain)
        assert arts.data_frame is root.RDataFrame.return_value


class TestFilter:
    def test_filter_applies_expression_and_name(
        self, artifacts, make_dataset, make_filter
    ):
        df = MagicMock()
        parent = _with_parent(artifacts, make_dataset, df)
        node = Node(
            operation="filter",
            data=make_filter(name="cut", expression="pt > 20"),
            parents=(parent,),
        )
        arts = operations.filter(node, artifacts)
        df.Filter.assert_called_once_with("pt > 20", "cut")
        assert arts.data_frame is df.Filter.return_value

    def test_filter_without_parent_raises(self, artifacts, make_filter):
        node = Node(operation="filter", data=make_filter())
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.filter(node, artifacts)


class TestWeight:
    def test_weight_defines_prefixed_column(
        self, artifacts, make_dataset, make_weight
    ):
        df = MagicMock()
        parent = _with_parent(artifacts, make_dataset, df)
        node = Node(
            operation="weight",
            data=make_weight(name="sf", expression="a * b"),
            parents=(parent,),
        )
        arts = operations.weight(node, artifacts)
        df.Define.assert_called_once_with("__weight_sf", "a * b")
        assert arts.data_frame is df.Define.return_value

    def test_weight_declares_helper_functions_of_expression(
        self, artifacts, make_dataset, make_weight, monkeypatch
    ):
        ensure_declared = MagicMock()
        monkeypatch.setattr(operations, "ensure_declared", ensure_declared)
        parent = _with_parent(artifacts, make_dataset, MagicMock())
        node = Node(
            operation="weight",
            data=make_weight(expression="sf(a)"),
            parents=(parent,),
        )
        operations.weight(node, artifacts)
        ensure_declared.assert_called_once_with("sf(a)")

    def test_weight_without_parent_raises(self, artifacts, make_weight):
        node = Node(operation="weight", data=make_weight())
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.weight(node, artifacts)


class TestWeightProduct:
    @staticmethod
    def _node(artifacts, make_dataset, columns, weights):
        from xyh.core.specs.specs import WeightProduct

        df = MagicMock()
        df.GetColumnNames.return_value = columns
        parent = _with_parent(artifacts, make_dataset, df)
        node = Node(
            operation="weight_product",
            data=WeightProduct(weights=weights),
            parents=(parent,),
        )
        return node, df

    def test_weight_product_multiplies_prefixed_columns(
        self, artifacts, make_dataset, make_weight
    ):
        weights = [make_weight(name="a"), make_weight(name="b")]
        node, df = self._node(
            artifacts, make_dataset, ["__weight_a", "__weight_b", "x"], weights
        )
        arts = operations.weight_product(node, artifacts)
        df.Define.assert_called_once_with(
            operations.TOTAL_WEIGHT_NAME, "__weight_a * __weight_b"
        )
        assert arts.data_frame is df.Define.return_value

    def test_weight_product_single_weight_no_operator(
        self, artifacts, make_dataset, make_weight
    ):
        node, df = self._node(
            artifacts, make_dataset, ["__weight_a"], [make_weight(name="a")]
        )
        operations.weight_product(node, artifacts)
        df.Define.assert_called_once_with(
            operations.TOTAL_WEIGHT_NAME, "__weight_a"
        )

    def test_weight_product_no_weights_defines_one(
        self, artifacts, make_dataset, caplog
    ):
        node, df = self._node(artifacts, make_dataset, [], [])
        with caplog.at_level(logging.DEBUG, logger=operations.__name__):
            operations.weight_product(node, artifacts)
        df.Define.assert_called_once_with(operations.TOTAL_WEIGHT_NAME, "1")
        assert "No weight columns found" in caplog.text

    def test_weight_product_missing_columns_raises(
        self, artifacts, make_dataset, make_weight
    ):
        weights = [make_weight(name="a"), make_weight(name="b")]
        node, df = self._node(artifacts, make_dataset, ["__weight_a"], weights)
        with pytest.raises(ValueError, match="__weight_a, __weight_b"):
            operations.weight_product(node, artifacts)
        df.Define.assert_not_called()

    def test_weight_product_unprefixed_column_not_accepted(
        self, artifacts, make_dataset, make_weight
    ):
        node, _ = self._node(
            artifacts, make_dataset, ["a"], [make_weight(name="a")]
        )
        with pytest.raises(ValueError, match="Not all weight columns"):
            operations.weight_product(node, artifacts)

    def test_weight_product_without_parent_raises(self, artifacts):
        from xyh.core.specs.specs import WeightProduct

        node = Node(
            operation="weight_product",
            data=WeightProduct(weights=[]),
        )
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.weight_product(node, artifacts)


class TestHistogram:
    @staticmethod
    def _node(artifacts, make_dataset, spec):
        df = MagicMock()
        parent = _with_parent(artifacts, make_dataset, df)
        node = Node(operation="histogram", data=spec, parents=(parent,))
        return node, df

    def test_histogram_without_expression_uses_variable_column(
        self, artifacts, make_dataset, make_histogram
    ):
        node, df = self._node(artifacts, make_dataset, make_histogram())
        arts = operations.histogram(node, artifacts)
        df.Define.assert_not_called()
        (model, column, weight), _ = df.Histo1D.call_args
        assert model[0] == model[1] == "pt"
        assert model[2] == 2
        np.testing.assert_array_equal(model[3], [0.0, 1.0, 3.0])
        assert column == "pt"
        assert weight == operations.TOTAL_WEIGHT_NAME
        assert arts.lazy_hist is df.Histo1D.return_value
        assert arts.data_frame is df

    def test_histogram_bin_count_is_edges_minus_one(
        self, artifacts, make_dataset, make_histogram
    ):
        spec = make_histogram(bin_edges=range(11))
        node, df = self._node(artifacts, make_dataset, spec)
        operations.histogram(node, artifacts)
        model = df.Histo1D.call_args.args[0]
        assert model[2] == 10

    def test_histogram_bin_edges_passed_as_numpy_array(
        self, artifacts, make_dataset, make_histogram
    ):
        node, df = self._node(artifacts, make_dataset, make_histogram())
        operations.histogram(node, artifacts)
        assert isinstance(df.Histo1D.call_args.args[0][3], np.ndarray)

    def test_histogram_with_expression_defines_private_column(
        self, artifacts, make_dataset, make_histogram
    ):
        spec = make_histogram(expression="a + b")
        node, df = self._node(artifacts, make_dataset, spec)
        arts = operations.histogram(node, artifacts)
        df.Define.assert_called_once_with("__private__pt", "a + b")
        defined = df.Define.return_value
        assert defined.Histo1D.call_args.args[1] == "__private__pt"
        assert arts.data_frame is df.Define.return_value

    def test_histogram_expression_equal_to_variable_defines_no_column(
        self, artifacts, make_dataset, make_histogram
    ):
        spec = make_histogram(expression="pt")
        node, df = self._node(artifacts, make_dataset, spec)
        operations.histogram(node, artifacts)
        df.Define.assert_not_called()
        assert df.Histo1D.call_args.args[1] == "pt"

    def test_histogram_integer_bin_edges_are_converted_to_float(
        self, artifacts, make_dataset, make_histogram
    ):
        spec = make_histogram(bin_edges=[0, 1, 2])
        node, df = self._node(artifacts, make_dataset, spec)
        operations.histogram(node, artifacts)
        edges = df.Histo1D.call_args.args[0][3]
        assert edges.dtype == np.float64

    def test_histogram_without_parent_raises(self, artifacts, make_histogram):
        node = Node(operation="histogram", data=make_histogram())
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.histogram(node, artifacts)


class TestGetOperationFn:
    @pytest.mark.parametrize(
        "name",
        [
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
        ],
    )
    def test_get_operation_fn_known_operation_returns_function(self, name):
        node = MagicMock(operation=name)
        assert operations.get_operation_fn(node) is getattr(operations, name)

    def test_get_operation_fn_real_node_returns_function(self, make_dataset):
        node = Node(operation="input_files", data=make_dataset())
        assert operations.get_operation_fn(node) is operations.input_files

    def test_get_operation_fn_unknown_operation_raises(self):
        node = MagicMock(operation="nope")
        with pytest.raises(ValueError, match="nope"):
            operations.get_operation_fn(node)


BUG_OS_IMPORT = "write_histograms: os is not imported (NameError)"
BUG_WRONG_SPEC = (
    "write_histograms pairs lazy hists with node.data (HistogramsOutput) "
    "instead of parent.data (Histogram)"
)
BUG_RUNGRAPHS = (
    "write_histograms calls RunGraphs once per data frame instead of once "
    "with the list of lazy results"
)
BUG_NO_CD = (
    "write_histograms never cd()s into the directory before hist.Write()"
)
BUG_NO_CLOSE = "write_histograms never closes the TFile"


class TestWriteHistograms:
    @pytest.fixture
    def root(self, monkeypatch):
        mock_root = MagicMock()
        monkeypatch.setattr(
            "xyh.core.graph.operations.ROOT", mock_root, raising=False
        )
        return mock_root

    @pytest.fixture
    def setup(self, artifacts, make_histogram, tmp_path):
        """Build a write node with two histogram parents in artifacts."""
        parents = []
        lazies = []
        dfs = []
        for var in ("pt", "eta"):
            parent = Node(
                operation="histogram", data=make_histogram(variable=var)
            )
            df = MagicMock(name=f"df_{var}")
            lazy = MagicMock(name=f"lazy_{var}")
            artifacts[parent.hash] = Artifacts(data_frame=df, lazy_hist=lazy)
            parents.append(parent)
            dfs.append(df)
            lazies.append(lazy)
        out_path = tmp_path / "hists_abc.root"
        node = Node(
            operation="write_histograms",
            data=HistogramsOutput(
                output_dir=str(tmp_path), subgraph_hash="abc"
            ),
            parents=tuple(parents),
            outputs={"hists_file": Output(path=str(out_path))},
        )
        return node, parents, dfs, lazies

    def test_write_histograms_opens_output_path_with_recreate(
        self, root, artifacts, setup, tmp_path
    ):
        node, *_ = setup
        operations.write_histograms(node, artifacts)
        root.TFile.Open.assert_called_once_with(
            os.path.join(str(tmp_path), "hists_abc.root"), "RECREATE"
        )

    def test_write_histograms_directory_is_campaign_to_process_path(
        self, root, artifacts, setup
    ):
        node, *_ = setup
        operations.write_histograms(node, artifacts)
        root_file = root.TFile.Open.return_value
        root_file.GetDirectory.assert_called_with("c/ch/cat/p/ds")

    def test_write_histograms_sets_name_and_title_from_variable_variation(
        self, root, artifacts, setup
    ):
        node, _, _, lazies = setup
        operations.write_histograms(node, artifacts)
        for lazy, var in zip(lazies, ("pt", "eta"), strict=True):
            hist = lazy.GetValue.return_value
            hist.SetName.assert_called_once_with(f"{var}__nominal")
            hist.SetTitle.assert_called_once_with(f"{var}__nominal")

    def test_write_histograms_runs_graphs_once_with_all_lazy_hists(
        self, root, artifacts, setup
    ):
        node, _, _, lazies = setup
        operations.write_histograms(node, artifacts)
        root.RDF.RunGraphs.assert_called_once_with(lazies)

    def test_write_histograms_writes_into_directory_not_top_level(
        self, root, artifacts, setup
    ):
        node, _, _, lazies = setup
        operations.write_histograms(node, artifacts)
        directory = root.TFile.Open.return_value.GetDirectory.return_value
        wrote_via_dir = directory.WriteObject.called
        assert directory.cd.called or wrote_via_dir

    def test_write_histograms_closes_output_file(self, root, artifacts, setup):
        node, *_ = setup
        operations.write_histograms(node, artifacts)
        root.TFile.Open.return_value.Close.assert_called_once_with()


@pytest.fixture
def root_mock(monkeypatch):
    mock_root = MagicMock()
    monkeypatch.setattr(
        "xyh.core.graph.operations.ROOT", mock_root, raising=False
    )
    return mock_root


class TestSnapshot:
    @staticmethod
    def _node(artifacts, make_dataset, tmp_path, columns=None, df=None):
        df = MagicMock() if df is None else df
        parent = _with_parent(artifacts, make_dataset, df)
        out = tmp_path / "sub" / "dir" / "snap.root"
        node = Node(
            operation="snapshot",
            data=Snapshot(
                campaign="c",
                channel="ch",
                category="cat",
                dataset="ds",
                process="p",
                variation="nominal",
                columns=columns,
            ),
            parents=(parent,),
            outputs={"snapshot_file": Output(path=str(out))},
        )
        return node, df, out

    def test_snapshot_creates_output_directory(
        self, root_mock, artifacts, make_dataset, tmp_path
    ):
        node, df, out = self._node(artifacts, make_dataset, tmp_path)
        df.GetColumnNames.return_value = ["a"]
        operations.snapshot(node, artifacts)
        assert out.parent.is_dir()

    def test_snapshot_is_lazy_and_writes_ntuple_tree(
        self, root_mock, artifacts, make_dataset, tmp_path
    ):
        node, df, out = self._node(artifacts, make_dataset, tmp_path)
        df.GetColumnNames.return_value = ["a", "b"]
        arts = operations.snapshot(node, artifacts)
        options = root_mock.RDF.RSnapshotOptions.return_value
        assert options.fLazy is True
        df.Snapshot.assert_called_once_with(
            "ntuple", str(out), ["a", "b"], options
        )
        assert arts.lazy_snapshot is df.Snapshot.return_value
        assert arts.data_frame is df

    def test_snapshot_columns_none_keeps_all_columns(
        self, root_mock, artifacts, make_dataset, tmp_path
    ):
        node, df, _ = self._node(artifacts, make_dataset, tmp_path)
        df.GetColumnNames.return_value = ["a", "b", "c"]
        operations.snapshot(node, artifacts)
        assert df.Snapshot.call_args.args[2] == ["a", "b", "c"]

    def test_snapshot_columns_patterns_select_matching_columns(
        self, root_mock, artifacts, make_dataset, tmp_path
    ):
        node, df, _ = self._node(
            artifacts, make_dataset, tmp_path, columns=["pt_*", "eta"]
        )
        df.GetColumnNames.return_value = ["pt_1", "pt_2", "eta", "phi"]
        operations.snapshot(node, artifacts)
        assert df.Snapshot.call_args.args[2] == ["pt_1", "pt_2", "eta"]

    def test_snapshot_channel_restricted_column_skipped_in_other_channel(
        self, root_mock, artifacts, make_dataset, tmp_path
    ):
        node, df, _ = self._node(
            artifacts,
            make_dataset,
            tmp_path,
            columns=["a", "b[tt]", "c[ch,mt]"],
        )
        df.GetColumnNames.return_value = ["a", "b", "c"]
        operations.snapshot(node, artifacts)
        assert df.Snapshot.call_args.args[2] == ["a", "c"]

    def test_snapshot_friend_prefix_is_stripped(
        self, root_mock, artifacts, make_dataset, tmp_path
    ):
        node, df, _ = self._node(artifacts, make_dataset, tmp_path)
        df.GetColumnNames.return_value = ["a", "friend.x"]
        operations.snapshot(node, artifacts)
        assert df.Snapshot.call_args.args[2] == ["a", "x"]

    def test_snapshot_friend_prefix_kept_on_name_clash(
        self, root_mock, artifacts, make_dataset, tmp_path
    ):
        node, df, _ = self._node(artifacts, make_dataset, tmp_path)
        df.GetColumnNames.return_value = ["x", "friend.x"]
        operations.snapshot(node, artifacts)
        assert df.Snapshot.call_args.args[2] == ["x", "friend.x"]

    def test_snapshot_unavailable_columns_are_dropped_with_warning(
        self, root_mock, artifacts, make_dataset, tmp_path, caplog
    ):
        node, df, _ = self._node(artifacts, make_dataset, tmp_path)
        df.GetColumnNames.return_value = ["a", "b"]
        df.HasColumn.side_effect = lambda c: c != "b"
        with caplog.at_level(logging.WARNING, logger=operations.__name__):
            operations.snapshot(node, artifacts)
        assert df.Snapshot.call_args.args[2] == ["a"]
        assert "Ignoring column b" in caplog.text

    def test_snapshot_without_parent_raises(self, artifacts, tmp_path):
        node = Node(
            operation="snapshot",
            data=Snapshot(
                campaign="c",
                channel="ch",
                category="cat",
                dataset="ds",
                process="p",
                variation="nominal",
            ),
            outputs={"snapshot_file": Output(path=str(tmp_path / "s.root"))},
        )
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.snapshot(node, artifacts)


class TestWriteSnapshots:
    def test_write_snapshots_runs_all_lazy_snapshots_once(
        self, root_mock, artifacts, make_dataset
    ):
        parents = []
        lazies = []
        for name in ("a", "b"):
            parent = Node(operation="input_files", data=make_dataset(name))
            lazy = MagicMock(name=f"lazy_{name}")
            artifacts[parent.hash] = Artifacts(lazy_snapshot=lazy)
            parents.append(parent)
            lazies.append(lazy)
        node = Node(
            operation="write_snapshots", data=Spec(), parents=tuple(parents)
        )
        result = operations.write_snapshots(node, artifacts)
        root_mock.RDF.RunGraphs.assert_called_once_with(lazies)
        assert result == {}


class TestBinning:
    @staticmethod
    def _node(artifacts, make_dataset, spec):
        df = MagicMock()
        parent = _with_parent(artifacts, make_dataset, df)
        return Node(operation="binning", data=spec, parents=(parent,)), df

    def test_binning_defines_double_column_from_variable(
        self, artifacts, make_dataset, make_histogram
    ):
        node, df = self._node(artifacts, make_dataset, make_histogram())
        operations.binning(node, artifacts)
        df.Define.assert_called_once_with(
            "__binning_pt", "static_cast<double>(pt)"
        )

    def test_binning_uses_expression_when_given(
        self, artifacts, make_dataset, make_histogram
    ):
        spec = make_histogram(expression="a + b")
        node, df = self._node(artifacts, make_dataset, spec)
        operations.binning(node, artifacts)
        df.Define.assert_called_once_with(
            "__binning_pt", "static_cast<double>(a + b)"
        )

    def test_binning_takes_lazy_values_of_defined_column(
        self, artifacts, make_dataset, make_histogram
    ):
        node, df = self._node(artifacts, make_dataset, make_histogram())
        arts = operations.binning(node, artifacts)
        defined = df.Define.return_value
        defined.Take.__getitem__.assert_called_once_with("double")
        defined.Take.__getitem__.return_value.assert_called_once_with(
            "__binning_pt"
        )
        assert arts.lazy_values is (
            defined.Take.__getitem__.return_value.return_value
        )
        assert arts.data_frame is defined

    def test_binning_declares_helpers_of_expression(
        self, artifacts, make_dataset, make_histogram, monkeypatch
    ):
        ensure_declared = MagicMock()
        monkeypatch.setattr(operations, "ensure_declared", ensure_declared)
        node, _ = self._node(
            artifacts, make_dataset, make_histogram(expression="f(a)")
        )
        operations.binning(node, artifacts)
        ensure_declared.assert_called_once_with("f(a)")

    def test_binning_without_parent_raises(self, artifacts, make_histogram):
        node = Node(operation="binning", data=make_histogram())
        with pytest.raises(ValueError, match="exactly one parent"):
            operations.binning(node, artifacts)


class TestWriteBinning:
    @pytest.fixture
    def setup(self, root_mock, artifacts, make_dataset, tmp_path):
        parents = []
        outputs = {}
        for name, values in (("a", [1, 2, 3]), ("b", [])):
            parent = Node(operation="input_files", data=make_dataset(name))
            lazy = MagicMock(name=f"lazy_{name}")
            lazy.GetValue.return_value = values
            artifacts[parent.hash] = Artifacts(lazy_values=lazy)
            parents.append(parent)
            outputs[parent.hash] = Output(
                path=str(tmp_path / "deep" / name / f"{name}.npz")
            )
        node = Node(
            operation="write_binning",
            data=Spec(),
            parents=tuple(parents),
            outputs=outputs,
        )
        return node, parents, outputs

    def test_write_binning_runs_all_lazy_values_once(
        self, root_mock, artifacts, setup
    ):
        node, parents, _ = setup
        operations.write_binning(node, artifacts)
        root_mock.RDF.RunGraphs.assert_called_once_with(
            [artifacts[p.hash].lazy_values for p in parents]
        )

    def test_write_binning_writes_values_to_output_of_each_parent(
        self, root_mock, artifacts, setup
    ):
        node, parents, outputs = setup
        result = operations.write_binning(node, artifacts)
        assert result == {}
        with np.load(outputs[parents[0].hash].path) as f:
            np.testing.assert_array_equal(f["values"], [1.0, 2.0, 3.0])
            assert f["values"].dtype == np.float64
        with np.load(outputs[parents[1].hash].path) as f:
            assert f["values"].shape == (0,)

    def test_write_binning_creates_missing_directories(
        self, root_mock, artifacts, setup
    ):
        node, _, outputs = setup
        operations.write_binning(node, artifacts)
        assert all(os.path.isfile(o.path) for o in outputs.values())

    def test_write_binning_missing_output_for_parent_raises(
        self, root_mock, artifacts, setup
    ):
        node, parents, outputs = setup
        node = Node(
            operation="write_binning",
            data=Spec(),
            parents=node.parents,
            outputs={parents[0].hash: outputs[parents[0].hash]},
        )
        with pytest.raises(KeyError):
            operations.write_binning(node, artifacts)
