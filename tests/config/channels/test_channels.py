"""
Unit tests for xyh.config.channels.channels module.
"""

import pytest

# =============================================================================
# Tests for channel definitions
# =============================================================================


@pytest.mark.skip(reason="Tests are outdated")
class TestChannelDefinitions:
    """Tests for the channel definitions."""

    def test_all_channels_exist(self):
        """Verify that all analysis channels are defined."""
        from xyh.config.channels.channels import (
            ch_ee,
            ch_em,
            ch_et,
            ch_mm,
            ch_mt,
            ch_tt,
        )

        for channel_inst in [ch_et, ch_mt, ch_tt, ch_em, ch_ee, ch_mm]:
            assert channel_inst is not None

    def test_channels_with_electrons_name_and_labels(self):
        """Verify that electron labels are properly formatted in channels with electrons."""
        from xyh.config.channels.channels import ch_ee, ch_em, ch_et

        for channel in [ch_et, ch_em, ch_ee]:
            assert "e" in channel.name
            assert r"\text{e}" in channel.label

    def test_channels_with_muons_name_and_labels(self):
        """Verify that muon labels are properly formatted in channels with muons."""
        from xyh.config.channels.channels import ch_em, ch_mm, ch_mt

        for channel in [ch_mt, ch_em, ch_mm]:
            assert "m" in channel.name
            assert r"\mu" in channel.label

    def test_channels_with_hadronic_taus_name_and_labels(self):
        """Verify that muon labels are properly formatted in channels with muons."""
        from xyh.config.channels.channels import ch_et, ch_mt, ch_tt

        for channel in [ch_et, ch_mt, ch_tt]:
            assert "t" in channel.name
            assert r"\tau_{\text{h}}" in channel.label
