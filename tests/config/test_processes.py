"""
Integration tests for xyh.config.processes module.

These tests verify that all physics process modules integrate correctly
and that the combined process index has the expected structure and properties.
"""

import pytest

# =============================================================================
# Tests for combined process index
# =============================================================================


@pytest.mark.skip(reason="Tests are outdated")
class TestCombinedProcessIndex:
    """Tests for the combined processes index."""

    def test_combined_index_creation(self):
        """Test that combined process index is created."""
        from xyh.config.processes import processes

        assert processes is not None
        assert len(processes) > 0

    def test_combined_index_contains_all_categories(self):
        """Test that combined index contains processes from all categories."""
        from xyh.config.processes import processes

        process_names = processes.names()

        # Check for representative processes from each category
        assert "data" in process_names  # Data
        assert "tt_tautau" in process_names  # Top
        assert "z_2e_2mu_tautau" in process_names  # EWK
        assert "h_2tau_tautau" in process_names  # Higgs
        assert "jetfakes" in process_names  # Jet fakes
        assert "tt_tautau" in process_names  # Top
        assert "xyh_y2b_h2tau_mx2000_my500" in process_names  # Signal


# =============================================================================
# Tests for process properties
# =============================================================================


@pytest.mark.skip(reason="Tests are outdated")
class TestProcessProperties:
    """Test for properties of process classes in the combined index."""

    def test_all_processes_have_is_data(self):
        """Test that all processes have the is_data property set to a boolean value."""
        from xyh.config.processes import processes

        for process_inst in processes.values():
            assert hasattr(process_inst, "is_data")
            assert isinstance(process_inst.is_data, bool)

    def test_data_processes_properties(self):
        """Test that data processes have correct properties."""
        from xyh.config.processes import processes

        # Check that all data processes are present in the combined index
        process_inst = processes.get("data", None)
        assert process_inst is not None
        assert process_inst.is_data

    def test_signal_processes_properties(self):
        """Test that signal processes have correct properties."""
        from xyh.config.processes import processes

        # Check that all data processes are present in the combined index
        for process_inst in processes.values():
            # Skip non-X -> HY signal processes
            if not process_inst.name.startswith("xyh_"):
                continue

            # Verify that process is not marked as data and has signal tag
            assert not process_inst.is_data
            assert process_inst.has_tag("signal")

            # Verify that process has auxiliary parameters for decay mode and masses
            assert "y_decay_mode" in process_inst.aux
            assert "h_decay_mode" in process_inst.aux
            assert "m_x" in process_inst.aux
            assert "m_y" in process_inst.aux

    def test_background_processes_properties(self):
        """Test that background processes have correct properties."""
        from xyh.config.processes import processes

        # Check that all data processes are present in the combined index
        for process_inst in processes.values():
            # Skip data processes and X -> HY signal processes
            if any(
                process_inst.name.startswith(match)
                for match in [
                    "data",
                    "egamma",
                    "muon",
                    "tau",
                    "xyh",
                ]
            ):
                continue

            # Verify that process is not marked as data and has background tag
            assert not process_inst.is_data
            assert process_inst.has_tag("background")

    def test_genuine_tautau_processes_properties(self):
        """Test that processes with generator matching to genuine tau tau pairs have correct properties."""
        from xyh.config.processes import processes

        # Check that all data processes are present in the combined index
        for process_inst in processes.values():
            # Only consider processes that end with "_tautau"
            if not process_inst.name.endswith("tautau"):
                continue

            # Process must have the correct tag
            assert process_inst.has_tag("tautau_genuine")

    def test_jetfakes_processes_properties(self):
        """Test that processes with generator matching to tau &rarr; jet fake have correct properties."""
        from xyh.config.processes import processes

        # Check that all data processes are present in the combined index
        for process_inst in processes.values():
            # Only consider processes that end with "_tautau"
            if not process_inst.name.endswith("jetfakes"):
                continue

            # Process must have the correct tag
            assert process_inst.has_tag("tautau_jetfakes")

    def test_remaining_processes_properties(self):
        """Test that processes with generator matching to remaining class have correct properties."""
        from xyh.config.processes import processes

        # Check that all data processes are present in the combined index
        for process_inst in processes.values():
            # Only consider processes that end with "_tautau"
            if not process_inst.name.endswith("rem"):
                continue

            # Process must have the correct tag
            assert process_inst.has_tag("tautau_remaining")
