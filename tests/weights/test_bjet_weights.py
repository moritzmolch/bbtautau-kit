"""Tests for the application of the b-tag weight normalization as weight."""

from types import SimpleNamespace

import pytest

from xyh.weights.jets import (
    BTAG_RENORM_WEIGHTS_DIR_ENV,
    b_jet_weights,
)


def _kwargs(campaign="2022_pre_ee_nano_v12", channel="et"):
    return {
        "campaign_inst": SimpleNamespace(
            name=campaign,
            x=SimpleNamespace(year=2022, postfix="preEE"),
        ),
        "channel_inst": SimpleNamespace(name=channel),
        "category_inst": SimpleNamespace(name=f"{channel}_base"),
        "dataset_inst": SimpleNamespace(),
        "process_inst": SimpleNamespace(
            is_data=False, name="z_2tau_tautau"
        ),
    }


@pytest.fixture
def corrections_dir(tmp_path, monkeypatch):
    (tmp_path / "btag_renormalization_weights_2022preEE_et.json").write_text(
        "{}"
    )
    monkeypatch.setenv(BTAG_RENORM_WEIGHTS_DIR_ENV, str(tmp_path))
    return tmp_path


def test_raw_weight_without_environment_variable(monkeypatch):
    monkeypatch.delenv(BTAG_RENORM_WEIGHTS_DIR_ENV, raising=False)
    assert b_jet_weights(**_kwargs()).nominal() == {
        "id_wgt_bjet_shape": "id_wgt_bjet"
    }
    monkeypatch.setenv(BTAG_RENORM_WEIGHTS_DIR_ENV, "")
    assert b_jet_weights(**_kwargs()).nominal() == {
        "id_wgt_bjet_shape": "id_wgt_bjet"
    }


def test_compensated_weight_with_corrections_dir(corrections_dir):
    path = str(
        corrections_dir / "btag_renormalization_weights_2022preEE_et.json"
    )
    assert b_jet_weights(**_kwargs()).nominal() == {
        "id_wgt_bjet_shape": (
            f'id_wgt_bjet * xyh_bjet_normalization("{path}", "et", '
            '"z_2tau_tautau", n_jets)'
        )
    }


def test_no_weight_for_data(corrections_dir):
    kwargs = _kwargs()
    kwargs["process_inst"] = SimpleNamespace(is_data=True, name="data_obs")
    assert b_jet_weights(**kwargs).nominal() == {}


def test_channel_specific_file(corrections_dir, tmp_path):
    # The channel enters the file name, so each channel needs its own file
    (tmp_path / "btag_renormalization_weights_2022preEE_tt.json").write_text(
        "{}"
    )
    path = str(
        tmp_path / "btag_renormalization_weights_2022preEE_tt.json"
    )
    assert b_jet_weights(**_kwargs(channel="tt")).nominal() == {
        "id_wgt_bjet_shape": (
            f'id_wgt_bjet * xyh_bjet_normalization("{path}", "tt", '
            '"z_2tau_tautau", n_jets)'
        )
    }


def test_missing_file_raises(corrections_dir):
    with pytest.raises(FileNotFoundError):
        b_jet_weights(**_kwargs(channel="mt")).nominal()
