"""Tests for the application of the data-driven Z corrections as weights."""

from types import SimpleNamespace

import pytest

from xyh.weights.processes import (
    Z_CORRECTIONS_DIR_ENV,
    Z_PT_WEIGHTS_DIR_ENV,
    z_normalization,
    z_pt_reweighting,
)

CAMPAIGN = "2024_nano_v15"


def _kwargs(tags=("z",), campaign=CAMPAIGN, channel="mm"):
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
def norm_dir(tmp_path, monkeypatch):
    directory = tmp_path / "norm"
    directory.mkdir()
    (directory / f"z_norm_{CAMPAIGN}.json").write_text("{}")
    monkeypatch.setenv(Z_CORRECTIONS_DIR_ENV, str(directory))
    return directory


@pytest.fixture
def pt_dir(tmp_path, monkeypatch):
    directory = tmp_path / "pt"
    directory.mkdir()
    (directory / f"z_pt_{CAMPAIGN}.json").write_text("{}")
    monkeypatch.setenv(Z_PT_WEIGHTS_DIR_ENV, str(directory))
    return directory


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.delenv(Z_CORRECTIONS_DIR_ENV, raising=False)
    monkeypatch.delenv(Z_PT_WEIGHTS_DIR_ENV, raising=False)


@pytest.mark.parametrize("value", [None, ""], ids=["unset", "empty"])
def test_normalization_disabled_without_directory(monkeypatch, value):
    if value is not None:
        monkeypatch.setenv(Z_CORRECTIONS_DIR_ENV, value)
    assert z_normalization(**_kwargs()).nominal() == {}


@pytest.mark.parametrize("value", [None, ""], ids=["unset", "empty"])
def test_pt_weight_disabled_without_directory(monkeypatch, value):
    if value is not None:
        monkeypatch.setenv(Z_PT_WEIGHTS_DIR_ENV, value)
    assert z_pt_reweighting(**_kwargs()).nominal() == {}


def test_normalization_for_z_process(norm_dir):
    path = str((norm_dir / f"z_norm_{CAMPAIGN}.json").resolve())
    assert z_normalization(**_kwargs()).nominal() == {
        "z_normalization_weight": (
            f'xyh_z_normalization("{path}", n_jets, n_bjets, "nominal")'
        )
    }


def test_pt_weight_for_z_process(pt_dir):
    path = str((pt_dir / f"z_pt_{CAMPAIGN}.json").resolve())
    assert z_pt_reweighting(**_kwargs()).nominal() == {
        "z_pt_weight": (
            f'xyh_z_pt_correction("{path}", n_jets, gen_boson_p4.Pt(), '
            '"nominal")'
        )
    }


def test_no_weights_for_other_processes(norm_dir, pt_dir):
    kwargs = _kwargs(tags=("tt",))
    assert z_normalization(**kwargs).nominal() == {}
    assert z_pt_reweighting(**kwargs).nominal() == {}


def test_normalization_missing_file_raises(norm_dir):
    with pytest.raises(FileNotFoundError, match="z_norm_2025_nano_v15"):
        z_normalization(**_kwargs(campaign="2025_nano_v15")).nominal()


def test_pt_weight_missing_file_raises(pt_dir):
    with pytest.raises(FileNotFoundError, match="z_pt_2025_nano_v15"):
        z_pt_reweighting(**_kwargs(campaign="2025_nano_v15")).nominal()


def test_pt_weight_ignores_normalization_directory(norm_dir):
    # Only the normalization directory is set: pt weight stays disabled
    assert z_pt_reweighting(**_kwargs()).nominal() == {}
    assert z_normalization(**_kwargs()).nominal() != {}


def test_normalization_ignores_pt_directory(pt_dir):
    assert z_normalization(**_kwargs()).nominal() == {}
    assert z_pt_reweighting(**_kwargs()).nominal() != {}
