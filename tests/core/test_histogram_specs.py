"""Unit tests for the histogram specs, channel restriction and overrides."""

from xyh.core.specs.histogram import create_histogram_specs

KWARGS = {
    "inventory_factory_fn_path": "xyh.config.inventory.create_inventory",
    "inventory_factory_kwargs": {"process_set": "default"},
    "campaigns": ["2024_nano_v15"],
    "channels": ["tt"],
    "categories": ["tt_base"],
    "variables": ["pt_1", "mass_1[tt]", "mass_1[et]"],
}


def test_channel_restriction():
    specs = create_histogram_specs(**KWARGS)
    assert [s.variable for s in specs] == ["pt_1", "mass_1"]


def test_binning_override():
    overrides = {"2024_nano_v15": {"tt": {"tt_base": {"pt_1": [0, 1, 2]}}}}
    specs = create_histogram_specs(**KWARGS, binning_overrides=overrides)
    assert specs[0].bin_edges == [0, 1, 2]
    assert specs[1].bin_edges != [0, 1, 2]
