"""Tests for the application of the data-driven Z corrections as weights."""

from types import SimpleNamespace

import pytest

from xyh.weights.processes import (
    Z_CORRECTIONS_DIR_ENV,
    z_normalization,
    z_pt_reweighting,
)


def _kwargs(tags=("z",), campaign="2024_nano_v15", channel="mm"):
    return {
        "campaign_inst": SimpleNamespace(name=campaign),
        "channel_inst": SimpleNamespace(name=channel),
        "category_inst": SimpleNamespace(name=f"{channel}_base"),
        "dataset_inst": SimpleNamespace(),
        "process_inst": SimpleNamespace(
            is_data=False, has_tag=lambda tag: tag in tags
        ),
    }


@pytest.fixture
def corrections_dir(tmp_path, monkeypatch):
    (tmp_path / "2024_nano_v15.json").write_text("{}")
    monkeypatch.setenv(Z_CORRECTIONS_DIR_ENV, str(tmp_path))
    return tmp_path


def test_disabled_without_environment_variable(monkeypatch):
    monkeypatch.delenv(Z_CORRECTIONS_DIR_ENV, raising=False)
    assert z_normalization(**_kwargs()).nominal() == {}
    assert z_pt_reweighting(**_kwargs()).nominal() == {}
    monkeypatch.setenv(Z_CORRECTIONS_DIR_ENV, "")
    assert z_normalization(**_kwargs()).nominal() == {}


def test_weights_for_z_processes(corrections_dir):
    path = str(corrections_dir / "2024_nano_v15.json")
    assert z_normalization(**_kwargs()).nominal() == {
        "z_normalization_weight": f'xyh_z_normalization("{path}", n_jets, n_bjets)'
    }
    assert z_pt_reweighting(**_kwargs()).nominal() == {
        "z_pt_weight": (
            f'xyh_z_pt_correction("{path}", n_jets, n_bjets, gen_boson_p4.Pt())'
        )
    }


def test_no_weights_for_other_processes(corrections_dir):
    kwargs = _kwargs(tags=("tt",))
    assert z_normalization(**kwargs).nominal() == {}
    assert z_pt_reweighting(**kwargs).nominal() == {}


def test_missing_file_raises(corrections_dir):
    with pytest.raises(FileNotFoundError):
        z_normalization(**_kwargs(campaign="2025_nano_v15")).nominal()
