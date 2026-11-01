"""Unit tests for the entry points of the thin shape_processor stages.

The mains are wrapped by `hydra_cli`. The tests call the undecorated function
(`__wrapped__`) which takes the composed config, so no Hydra run is started.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from omegaconf import OmegaConf

from xyh.shape_processor import (
    merge_histograms,
    plot_shapes,
    run_fake_factor_histograms,
)
from xyh.workflow.hydra_utils import compose_cfg

INVENTORY = {
    "factory_fn": "pkg:inv",
    "factory_fn_kwargs": {"opt": 1},
    "campaigns": ["c1", "c2"],
    "channels": ["tt", "et"],
    "categories": ["cat"],
    "variables": ["pt", "mass[tt]"],
}


def _call(module, cfg):
    return module.main.__wrapped__(OmegaConf.create(cfg))


@pytest.fixture(autouse=True)
def restore_environment(monkeypatch):
    # The Hydra wrapper may export correction directories into the environment
    monkeypatch.delenv("XYH_Z_PT_WEIGHTS_DIR", raising=False)
    monkeypatch.delenv("XYH_BTAG_RENORM_WEIGHTS_DIR", raising=False)


@pytest.fixture
def inventory_kwargs():
    return {
        "inventory_factory_fn_path": "pkg:inv",
        "inventory_factory_kwargs": {"opt": 1},
        "campaigns": ["c1", "c2"],
        "channels": ["tt", "et"],
        "categories": ["cat"],
        "variables": ["pt", "mass[tt]"],
    }


class TestMergeHistogramsMain:
    def test_forwards_inventory_and_paths(self, monkeypatch, inventory_kwargs):
        mock = MagicMock()
        monkeypatch.setattr(merge_histograms, "merge_histograms", mock)
        _call(
            merge_histograms,
            {
                "inventory": INVENTORY,
                "histograms_dir": "hist",
                "merged_histograms_file": "hist/merged.root",
            },
        )
        mock.assert_called_once_with(
            **inventory_kwargs,
            histograms_dir=Path("hist"),
            output_file=Path("hist/merged.root"),
        )

    def test_composed_config_provides_all_arguments(self, monkeypatch):
        mock = MagicMock()
        monkeypatch.setattr(merge_histograms, "merge_histograms", mock)
        cfg = compose_cfg("merge_histograms", ["tags.shapes_tag=foo"])
        merge_histograms.main.__wrapped__(cfg)
        kwargs = mock.call_args.kwargs
        assert kwargs["histograms_dir"] == Path("data/output/foo/histograms")
        assert kwargs["output_file"] == Path(
            "data/output/foo/histograms/merged_histograms.root"
        )
        assert set(kwargs) == {
            "inventory_factory_fn_path",
            "inventory_factory_kwargs",
            "campaigns",
            "channels",
            "categories",
            "variables",
            "histograms_dir",
            "output_file",
        }


class TestPlotShapesMain:
    def _cfg(self, **extra):
        cfg = {
            "inventory": INVENTORY,
            "merged_histograms_file": "hist/merged.root",
            "output_dir": "plots",
            "control_plots": {"extensions": ["png", "pdf"]},
        }
        cfg.update(extra)
        return cfg

    def test_forwards_plain_python_objects(self, monkeypatch, inventory_kwargs):
        mock = MagicMock()
        monkeypatch.setattr(plot_shapes, "plot_shapes", mock)
        _call(plot_shapes, self._cfg(num_workers=4))
        mock.assert_called_once_with(
            **inventory_kwargs,
            merged_histograms_file=Path("hist/merged.root"),
            output_dir=Path("plots"),
            extensions=["png", "pdf"],
            num_workers=4,
        )
        kwargs = mock.call_args.kwargs
        assert type(kwargs["inventory_factory_kwargs"]) is dict
        for key in ("campaigns", "channels", "categories", "variables"):
            assert type(kwargs[key]) is list
        assert type(kwargs["extensions"]) is list

    def test_num_workers_defaults_to_one(self, monkeypatch):
        mock = MagicMock()
        monkeypatch.setattr(plot_shapes, "plot_shapes", mock)
        _call(plot_shapes, self._cfg())
        assert mock.call_args.kwargs["num_workers"] == 1

    def test_interpolations_in_inventory_are_resolved(self, monkeypatch):
        mock = MagicMock()
        monkeypatch.setattr(plot_shapes, "plot_shapes", mock)
        inventory = dict(INVENTORY, categories=["${inventory.channels.0}_cat"])
        _call(plot_shapes, self._cfg(inventory=inventory))
        assert mock.call_args.kwargs["categories"] == ["tt_cat"]

    def test_composed_config_gives_picklable_arguments(self, monkeypatch):
        import pickle

        mock = MagicMock()
        monkeypatch.setattr(plot_shapes, "plot_shapes", mock)
        cfg = compose_cfg("plot_shapes", ["tags.shapes_tag=foo"])
        plot_shapes.main.__wrapped__(cfg)
        kwargs = mock.call_args.kwargs
        assert pickle.loads(pickle.dumps(kwargs)) == kwargs
        assert kwargs["merged_histograms_file"] == Path(
            "data/output/foo/histograms/merged_histograms.root"
        )
        assert kwargs["output_dir"] == Path("data/output/foo/control_plots")
        assert kwargs["num_workers"] == 8
        assert kwargs["extensions"] == ["png", "pdf"]


class TestRunFakeFactorHistogramsMain:
    def test_forwards_inventory_and_histograms_dir(
        self, monkeypatch, inventory_kwargs
    ):
        mock = MagicMock()
        monkeypatch.setattr(
            run_fake_factor_histograms, "run_fake_factor_histograms", mock
        )
        _call(
            run_fake_factor_histograms,
            {"inventory": INVENTORY, "histograms_dir": "hist"},
        )
        mock.assert_called_once_with(
            **inventory_kwargs, histograms_dir=Path("hist")
        )

    def test_composed_config_provides_all_arguments(self, monkeypatch):
        mock = MagicMock()
        monkeypatch.setattr(
            run_fake_factor_histograms, "run_fake_factor_histograms", mock
        )
        cfg = compose_cfg("run_fake_factor_histograms", ["tags.shapes_tag=foo"])
        run_fake_factor_histograms.main.__wrapped__(cfg)
        assert mock.call_args.kwargs["histograms_dir"] == Path(
            "data/output/foo/histograms"
        )
