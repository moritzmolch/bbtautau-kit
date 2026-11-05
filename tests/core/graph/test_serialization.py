import json
import os

import pytest

from xyh.core.graph import builder, serialization
from xyh.core.specs.specs import (
    Binning,
    Context,
    Dataset,
    FiltersAndWeights,
)
from xyh.core.specs.storage import SpecsStorage


def _context(dataset="ds", process="p", variation="nominal"):
    return Context(
        campaign="c",
        channel="ch",
        category="cat",
        dataset=dataset,
        process=process,
        variation=variation,
    )


@pytest.fixture
def storage(make_filter, make_weight):
    datasets = [
        Dataset(
            campaign="c",
            channel="ch",
            dataset=name,
            files={"main": [f"{name}.root"]},
        )
        for name in ("ds1", "ds2")
    ]
    faw = [
        FiltersAndWeights(
            campaign="c",
            channel="ch",
            category="cat",
            process="p",
            dataset=name,
            variation=variation,
            filters=[make_filter(name="f", expression="x > 0")],
            weights=[make_weight(name="w", expression="2.0")],
        )
        for name in ("ds1", "ds2")
        for variation in ("nominal", "up")
    ]
    binnings = [
        Binning(
            campaign="c",
            channel="ch",
            category="cat",
            variable="pt",
            expression="a + b",
            bin_edges=[0, 1, 2],
        ),
        Binning(
            campaign="c",
            channel="ch",
            category="cat",
            variable="eta",
            bin_edges=[-1.0, 1.0],
        ),
    ]
    return SpecsStorage(datasets, faw, binnings)


@pytest.fixture
def hist_graphs(storage, tmp_path):
    return builder.build_histograms_graph(
        [
            _context("ds1"),
            _context("ds1", variation="up"),
            _context("ds2"),
        ],
        None,
        storage,
        tmp_path,
    )


def _specs_by_type(specs):
    result = {}
    for node in specs["nodes"]:
        result.setdefault(node["type"], []).append(node)
    return result


class TestGraphsToSpecs:
    def test_graphs_to_specs_empty_list_gives_empty_node_link_graph(self):
        specs = serialization.graphs_to_specs([])
        assert specs["nodes"] == []
        assert specs["edges"] == []

    def test_graphs_to_specs_is_json_serializable(self, hist_graphs):
        specs = serialization.graphs_to_specs(hist_graphs)
        assert json.loads(json.dumps(specs)) == specs

    def test_graphs_to_specs_node_types_match_operations(self, hist_graphs):
        specs = serialization.graphs_to_specs(hist_graphs)
        by_type = _specs_by_type(specs)
        assert set(by_type) == {
            "InputFilesNode",
            "FilterNode",
            "WeightNode",
            "WeightProductNode",
            "HistogramNode",
            "WriteHistogramsNode",
        }
        assert len(by_type["InputFilesNode"]) == 2
        assert len(by_type["HistogramNode"]) == 6
        assert len(by_type["WriteHistogramsNode"]) == 2

    def test_graphs_to_specs_links_match_graph_edges(self, hist_graphs):
        specs = serialization.graphs_to_specs(hist_graphs)
        links = {(link["source"], link["target"]) for link in specs["edges"]}
        edges = {e for g in hist_graphs for e in g.edges}
        assert links == edges
        assert specs["directed"] is True

    def test_graphs_to_specs_node_ids_are_node_hashes(self, hist_graphs):
        specs = serialization.graphs_to_specs(hist_graphs)
        assert {n["id"] for n in specs["nodes"]} == {
            h for g in hist_graphs for h in g.nodes
        }

    def test_graphs_to_specs_input_files_spec_is_dataset(self, hist_graphs):
        by_type = _specs_by_type(serialization.graphs_to_specs(hist_graphs))
        specs = sorted(
            (n["spec"] for n in by_type["InputFilesNode"]),
            key=lambda s: s["dataset"],
        )
        assert specs[0] == {
            "campaign": "c",
            "channel": "ch",
            "dataset": "ds1",
            "files": {"main": ["ds1.root"]},
        }

    def test_graphs_to_specs_filter_weight_and_product_specs(self, hist_graphs):
        by_type = _specs_by_type(serialization.graphs_to_specs(hist_graphs))
        assert by_type["FilterNode"][0]["spec"] == {
            "name": "f",
            "expression": "x > 0",
        }
        assert by_type["WeightNode"][0]["spec"] == {
            "name": "w",
            "expression": "2.0",
        }
        assert by_type["WeightProductNode"][0]["spec"] == {"weights": ["w"]}

    def test_graphs_to_specs_histogram_spec_content(
        self, hist_graphs, tmp_path
    ):
        by_type = _specs_by_type(serialization.graphs_to_specs(hist_graphs))
        pt_nominal = next(
            n["spec"]
            for n in by_type["HistogramNode"]
            if n["spec"]["variable"] == "pt"
            and n["spec"]["dataset"] == "ds1"
            and n["spec"]["variation"] == "nominal"
        )
        assert {k: v for k, v in pt_nominal.items() if k != "output_file"} == {
            "campaign": "c",
            "channel": "ch",
            "category": "cat",
            "dataset": "ds1",
            "process": "p",
            "variation": "nominal",
            "variable": "pt",
            "expression": "a + b",
            "bin_edges": [0, 1, 2],
            "hist_path": "c/ch/cat/p/ds1/pt__nominal",
        }

    def test_graphs_to_specs_histogram_output_file_relative_to_write_dir(
        self, hist_graphs, tmp_path
    ):
        specs = serialization.graphs_to_specs(hist_graphs)
        by_type = _specs_by_type(specs)
        write_files = {
            os.path.relpath(n["spec"]["outputs"]["hists_file"], str(tmp_path))
            for n in by_type["WriteHistogramsNode"]
        }
        hist_files = {
            n["spec"]["output_file"] for n in by_type["HistogramNode"]
        }
        assert hist_files == write_files
        assert all(
            f.startswith("histograms_") and f.endswith(".root")
            for f in hist_files
        )

    def test_graphs_to_specs_write_node_spec_lists_output_paths(
        self, hist_graphs
    ):
        by_type = _specs_by_type(serialization.graphs_to_specs(hist_graphs))
        for node in by_type["WriteHistogramsNode"]:
            assert set(node["spec"]["outputs"]) == {"hists_file"}

    def test_graphs_to_specs_snapshot_and_write_snapshots(
        self, storage, tmp_path
    ):
        graphs = builder.build_snapshots_graph(
            [_context("ds1")], ["pt"], storage, tmp_path
        )
        by_type = _specs_by_type(serialization.graphs_to_specs(graphs))
        (snap,) = by_type["SnapshotNode"]
        assert snap["spec"]["columns"] == ["pt"]
        assert snap["spec"]["dataset"] == "ds1"
        assert snap["spec"]["output_file"] == os.path.join(
            str(tmp_path), "c", "ch__cat", "p__ds1__nominal.root"
        )
        (write,) = by_type["WriteSnapshotsNode"]
        assert list(write["spec"]["outputs"].values()) == [
            snap["spec"]["output_file"]
        ]

    def test_graphs_to_specs_binning_nodes(self, storage, tmp_path):
        graphs = builder.build_binning_graph(
            [_context("ds1")], storage, tmp_path, variables=["pt"]
        )
        by_type = _specs_by_type(serialization.graphs_to_specs(graphs))
        (binning,) = by_type["BinningNode"]
        assert binning["spec"]["variable"] == "pt"
        assert binning["spec"]["output_file"] == os.path.join(
            str(tmp_path), "c", "ch__cat", "pt", "ds1.npz"
        )
        assert "hist_path" not in binning["spec"]
        assert len(by_type["WriteBinningNode"]) == 1


class TestHistogramKeys:
    def test_histogram_keys_empty_graph_list_gives_empty_dict(self):
        assert serialization.histogram_keys([]) == {}

    def test_histogram_keys_maps_file_basename_to_sorted_keys(
        self, storage, tmp_path
    ):
        (graph,) = builder.build_histograms_graph(
            [_context("ds1"), _context("ds1", variation="up")],
            ["pt", "eta"],
            storage,
            tmp_path,
        )
        keys = serialization.histogram_keys([graph])
        (writer,) = (
            d["node"]
            for _, d in graph.nodes(data=True)
            if d["node"].operation == "write_histograms"
        )
        assert keys == {
            os.path.basename(writer.outputs["hists_file"].path): [
                "c/ch/cat/p/ds1/eta__nominal",
                "c/ch/cat/p/ds1/eta__up",
                "c/ch/cat/p/ds1/pt__nominal",
                "c/ch/cat/p/ds1/pt__up",
            ]
        }

    def test_histogram_keys_one_entry_per_graph_sorted_by_file(
        self, hist_graphs
    ):
        keys = serialization.histogram_keys(hist_graphs)
        assert len(keys) == 2
        assert list(keys) == sorted(keys)
        for hist_keys in keys.values():
            assert hist_keys == sorted(hist_keys)
        assert sum(len(v) for v in keys.values()) == 6

    def test_histogram_keys_ignore_existing_outputs(self, storage, tmp_path):
        (graph,) = builder.build_histograms_graph(
            [_context("ds1")], ["pt"], storage, tmp_path
        )
        before = serialization.histogram_keys([graph])
        # Pretend the output file already exists, i.e. would be pruned
        (out_name,) = before
        (tmp_path / out_name).write_text("x")
        assert serialization.histogram_keys([graph]) == before

    def test_histogram_keys_graphs_without_write_nodes_are_ignored(
        self, storage, tmp_path
    ):
        graphs = builder.build_snapshots_graph(
            [_context("ds1")], None, storage, tmp_path
        )
        assert serialization.histogram_keys(graphs) == {}
