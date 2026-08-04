"""
Integration tests for campaigns.
"""

from xyh.config.campaigns.util import DatasetProxy


# =============================================================================
# Integration tests for single campaigns
# =============================================================================


class TestCpn2022PreEENanoV12Integration:
    """Tests for cpn_2022_pre_ee_nano_v12 campaign."""

    def test_import(self):
        """Test that the campaign can be imported and executed."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2022_pre_ee_nano_v12

        # Verify the campaign object exists
        assert cpn_2022_pre_ee_nano_v12 is not None

    def test_campaign_attributes(self):
        """Test that campaign has expected attributes."""
        from xyh.config.campaigns import cpn_2022_pre_ee_nano_v12 as campaign_inst

        # Check basic attributes exist
        assert hasattr(campaign_inst, 'name')
        assert hasattr(campaign_inst, 'id')
        assert hasattr(campaign_inst, 'ecm')
        assert hasattr(campaign_inst, 'aux')
        
        # Verify name is set correctly
        assert campaign_inst.name == "2022_pre_ee_nano_v12"
        assert campaign_inst.x.nano_version == "v12"

        # Verify aux contains expected keys
        assert 'year' in campaign_inst.aux
        assert 'postfix' in campaign_inst.aux
        assert 'lumi' in campaign_inst.aux
        assert 'runs' in campaign_inst.aux
        assert 'nano_version' in campaign_inst.aux

    def test_data_available(self):
        """Test that the campaign file contains the expected data samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2022_pre_ee_nano_v12
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        for dataset_name in [
            "egamma_2022_cd",
            "muon_2022_cd",
            "tau_2022_cd",
        ]:
            dataset_inst = cpn_2022_pre_ee_nano_v12.get_dataset(dataset_name, None)

            # Check base attributes of the dataset instance
            assert dataset_inst is not None
            assert dataset_inst.is_data

            # Check that cross sections and generator weights are set to 1
            assert dataset_inst.x.xsec == 1.0
            assert dataset_inst.x.generator_weight == 1.0

    def test_signal_available(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2022_pre_ee_nano_v12
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        dataset_inst = cpn_2022_pre_ee_nano_v12.get_dataset("xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph", None)

        # Check base attributes of the dataset instance
        assert dataset_inst is not None
        assert not dataset_inst.is_data

    def test_mc_xsec_and_generator_weight_set(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2022_pre_ee_nano_v12

        for dataset in cpn_2022_pre_ee_nano_v12.datasets.values():
            if not dataset.is_data and not isinstance(dataset, DatasetProxy):
                # Check that cross sections are set to reasonable values (not
                # None and not 0)
                assert dataset.x.xsec is not None
                assert dataset.x.xsec > 0
                assert dataset.x.generator_weight is not None
                assert dataset.x.generator_weight > 0


class TestCpn2022PostEENanoV12Integration:
    """Tests for cpn_2022_post_ee_nano_v12 campaign."""

    def test_import(self):
        """Test that the campaign can be imported and executed."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2022_post_ee_nano_v12

        # Verify the campaign object exists
        assert cpn_2022_post_ee_nano_v12 is not None

    def test_campaign_attributes(self):
        """Test that campaign has expected attributes."""
        from xyh.config.campaigns import cpn_2022_post_ee_nano_v12 as campaign_inst

        # Check basic attributes exist
        assert hasattr(campaign_inst, 'name')
        assert hasattr(campaign_inst, 'id')
        assert hasattr(campaign_inst, 'ecm')
        assert hasattr(campaign_inst, 'aux')
        
        # Verify name and nanoAOD version are set correctly
        assert campaign_inst.name == "2022_post_ee_nano_v12"
        assert campaign_inst.x.nano_version == "v12"
        
        # Verify aux contains expected keys
        assert 'year' in campaign_inst.aux
        assert 'postfix' in campaign_inst.aux
        assert 'lumi' in campaign_inst.aux
        assert 'runs' in campaign_inst.aux
        assert 'nano_version' in campaign_inst.aux

    def test_data_available(self):
        """Test that the campaign file contains the expected data samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2022_post_ee_nano_v12
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        for dataset_name in [
            "egamma_2022_efg",
            "muon_2022_efg",
            "tau_2022_efg",
        ]:
            dataset_inst = cpn_2022_post_ee_nano_v12.get_dataset(dataset_name, None)

            # Check base attributes of the dataset instance
            assert dataset_inst is not None
            assert dataset_inst.is_data

            # Check that cross sections and generator weights are set to 1
            assert dataset_inst.x.xsec == 1.0
            assert dataset_inst.x.generator_weight == 1.0

    def test_signal_available(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2022_post_ee_nano_v12
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        dataset_inst = cpn_2022_post_ee_nano_v12.get_dataset("xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph", None)

        # Check base attributes of the dataset instance
        assert dataset_inst is not None
        assert not dataset_inst.is_data

    def test_mc_xsec_and_generator_weight_set(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2022_post_ee_nano_v12

        for dataset in cpn_2022_post_ee_nano_v12.datasets.values():
            if not dataset.is_data and not isinstance(dataset, DatasetProxy):
                # Check that cross sections are set to reasonable values (not
                # None and not 0)
                assert dataset.x.xsec is not None
                assert dataset.x.xsec > 0
                assert dataset.x.generator_weight is not None
                assert dataset.x.generator_weight > 0


class TestCpn2023PreBPixNanoV12Integration:
    """Tests for cpn_2023_pre_bpix_nano_v12 campaign."""

    def test_import(self):
        """Test that the campaign can be imported and executed."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2023_pre_bpix_nano_v12

        # Verify the campaign object exists
        assert cpn_2023_pre_bpix_nano_v12 is not None

    def test_campaign_attributes(self):
        """Test that campaign has expected attributes."""
        from xyh.config.campaigns import cpn_2023_pre_bpix_nano_v12 as campaign_inst

        # Check basic attributes exist
        assert hasattr(campaign_inst, 'name')
        assert hasattr(campaign_inst, 'id')
        assert hasattr(campaign_inst, 'ecm')
        assert hasattr(campaign_inst, 'aux')
        
        # Verify name and nanoAOD version are set correctly
        assert campaign_inst.name == "2023_pre_bpix_nano_v12"
        assert campaign_inst.x.nano_version == "v12"
        
        # Verify aux contains expected keys
        assert 'year' in campaign_inst.aux
        assert 'postfix' in campaign_inst.aux
        assert 'lumi' in campaign_inst.aux
        assert 'runs' in campaign_inst.aux
        assert 'nano_version' in campaign_inst.aux

    def test_data_available(self):
        """Test that the campaign file contains the expected data samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2023_pre_bpix_nano_v12
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        for dataset_name in [
            "egamma_2023_c",
            "muon_2023_c",
            "tau_2023_c",
        ]:
            dataset_inst = cpn_2023_pre_bpix_nano_v12.get_dataset(dataset_name, None)

            # Check base attributes of the dataset instance
            assert dataset_inst is not None
            assert dataset_inst.is_data

            # Check that cross sections and generator weights are set to 1
            assert dataset_inst.x.xsec == 1.0
            assert dataset_inst.x.generator_weight == 1.0

    def test_signal_available(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2023_pre_bpix_nano_v12
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        dataset_inst = cpn_2023_pre_bpix_nano_v12.get_dataset("xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph", None)

        # Check base attributes of the dataset instance
        assert dataset_inst is not None
        assert not dataset_inst.is_data

    def test_mc_xsec_and_generator_weight_set(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2023_pre_bpix_nano_v12

        for dataset in cpn_2023_pre_bpix_nano_v12.datasets.values():
            if not dataset.is_data and not isinstance(dataset, DatasetProxy):
                # Check that cross sections are set to reasonable values (not
                # None and not 0)
                assert dataset.x.xsec is not None
                assert dataset.x.xsec > 0
                assert dataset.x.generator_weight is not None
                assert dataset.x.generator_weight > 0


class TestCpn2023PostBPixNanoV12Integration:
    """Tests for cpn_2023_post_bpix_nano_v12 campaign."""

    def test_import(self):
        """Test that the campaign can be imported and executed."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2023_post_bpix_nano_v12

        # Verify the campaign object exists
        assert cpn_2023_post_bpix_nano_v12 is not None

    def test_campaign_attributes(self):
        """Test that campaign has expected attributes."""
        from xyh.config.campaigns import cpn_2023_post_bpix_nano_v12 as campaign_inst

        # Check basic attributes exist
        assert hasattr(campaign_inst, 'name')
        assert hasattr(campaign_inst, 'id')
        assert hasattr(campaign_inst, 'ecm')
        assert hasattr(campaign_inst, 'aux')
        
        # Verify name and nanoAOD version are set correctly
        assert campaign_inst.name == "2023_post_bpix_nano_v12"
        assert campaign_inst.x.nano_version == "v12"
        
        # Verify aux contains expected keys
        assert 'year' in campaign_inst.aux
        assert 'postfix' in campaign_inst.aux
        assert 'lumi' in campaign_inst.aux
        assert 'runs' in campaign_inst.aux
        assert 'nano_version' in campaign_inst.aux

    def test_data_available(self):
        """Test that the campaign file contains the expected data samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2023_post_bpix_nano_v12
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        for dataset_name in [
            "egamma_2023_d",
            "muon_2023_d",
            "tau_2023_d",
        ]:
            dataset_inst = cpn_2023_post_bpix_nano_v12.get_dataset(dataset_name, None)

            # Check base attributes of the dataset instance
            assert dataset_inst is not None
            assert dataset_inst.is_data

            # Check that cross sections and generator weights are set to 1
            assert dataset_inst.x.xsec == 1.0
            assert dataset_inst.x.generator_weight == 1.0

    def test_signal_available(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2023_post_bpix_nano_v12
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        dataset_inst = cpn_2023_post_bpix_nano_v12.get_dataset("xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph", None)

        # Check base attributes of the dataset instance
        assert dataset_inst is not None
        assert not dataset_inst.is_data

    def test_mc_xsec_and_generator_weight_set(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2023_post_bpix_nano_v12

        for dataset in cpn_2023_post_bpix_nano_v12.datasets.values():
            if not dataset.is_data and not isinstance(dataset, DatasetProxy):
                # Check that cross sections are set to reasonable values (not
                # None and not 0)
                assert dataset.x.xsec is not None
                assert dataset.x.xsec > 0
                assert dataset.x.generator_weight is not None
                assert dataset.x.generator_weight > 0


class TestCpn2024NanoV15Integration:
    """Tests for cpn_2024_nano_v15 campaign."""

    def test_import(self):
        """Test that the campaign can be imported and executed."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2024_nano_v15

        # Verify the campaign object exists
        assert cpn_2024_nano_v15 is not None

    def test_campaign_attributes(self):
        """Test that campaign has expected attributes."""
        from xyh.config.campaigns import cpn_2024_nano_v15 as campaign_inst

        # Check basic attributes exist
        assert hasattr(campaign_inst, 'name')
        assert hasattr(campaign_inst, 'id')
        assert hasattr(campaign_inst, 'ecm')
        assert hasattr(campaign_inst, 'aux')
        
        # Verify name and nanoAOD version are set correctly
        assert campaign_inst.name == "2024_nano_v15"
        assert campaign_inst.x.nano_version == "v15"
        
        # Verify aux contains expected keys
        assert 'year' in campaign_inst.aux
        assert 'postfix' in campaign_inst.aux
        assert 'lumi' in campaign_inst.aux
        assert 'runs' in campaign_inst.aux
        assert 'nano_version' in campaign_inst.aux

    def test_data_available(self):
        """Test that the campaign file contains the expected data samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2024_nano_v15
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        for dataset_name in [
            "egamma_2024_cdefghi",
            "muon_2024_cdefghi",
            "tau_2024_cdefghi",
        ]:
            dataset_inst = cpn_2024_nano_v15.get_dataset(dataset_name, None)

            # Check base attributes of the dataset instance
            assert dataset_inst is not None
            assert dataset_inst.is_data

            # Check that cross sections and generator weights are set to 1
            assert dataset_inst.x.xsec == 1.0
            assert dataset_inst.x.generator_weight == 1.0

    def test_signal_available(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2024_nano_v15
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        dataset_inst = cpn_2024_nano_v15.get_dataset("xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph", None)

        # Check base attributes of the dataset instance
        assert dataset_inst is not None
        assert not dataset_inst.is_data

    def test_mc_xsec_and_generator_weight_set(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2024_nano_v15

        for dataset in cpn_2024_nano_v15.datasets.values():
            if not dataset.is_data and not isinstance(dataset, DatasetProxy):
                # Check that cross sections are set to reasonable values (not
                # None and not 0)
                assert dataset.x.xsec is not None
                assert dataset.x.xsec > 0
                assert dataset.x.generator_weight is not None
                assert dataset.x.generator_weight > 0


class TestCpn2025NanoV15Integration:
    """Tests for cpn_2025_nano_v15 campaign."""

    def test_import(self):
        """Test that the campaign can be imported and executed."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2025_nano_v15

        # Verify the campaign object exists
        assert cpn_2025_nano_v15 is not None

    def test_campaign_attributes(self):
        """Test that campaign has expected attributes."""
        from xyh.config.campaigns import cpn_2025_nano_v15 as campaign_inst

        # Check basic attributes exist
        assert hasattr(campaign_inst, 'name')
        assert hasattr(campaign_inst, 'id')
        assert hasattr(campaign_inst, 'ecm')
        assert hasattr(campaign_inst, 'aux')
        
        # Verify name and nanoAOD version are set correctly
        assert campaign_inst.name == "2025_nano_v15"
        assert campaign_inst.x.nano_version == "v15"
        
        # Verify aux contains expected keys
        assert 'year' in campaign_inst.aux
        assert 'postfix' in campaign_inst.aux
        assert 'lumi' in campaign_inst.aux
        assert 'runs' in campaign_inst.aux
        assert 'nano_version' in campaign_inst.aux

    def test_data_available(self):
        """Test that the campaign file contains the expected data samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2025_nano_v15
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        for dataset_name in [
            "egamma_2025_cdefg",
            "muon_2025_cdefg",
            "tau_2025_cdefg",
        ]:
            dataset_inst = cpn_2025_nano_v15.get_dataset(dataset_name, None)

            # Check base attributes of the dataset instance
            assert dataset_inst is not None
            assert dataset_inst.is_data

            # Check that cross sections and generator weights are set to 1
            assert dataset_inst.x.xsec == 1.0
            assert dataset_inst.x.generator_weight == 1.0

    def test_signal_available(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2025_nano_v15
        
        # Verify the data samples have been added and that they have the
        # expected attributes
        dataset_inst = cpn_2025_nano_v15.get_dataset("xyh_{y_decay_mode}_{h_decay_mode}_mx{m_x}_my{m_y}_madgraph", None)

        # Check base attributes of the dataset instance
        assert dataset_inst is not None
        assert not dataset_inst.is_data

    def test_mc_xsec_and_generator_weight_set(self):
        """Test that the campaign file contains the expected signal samples."""
        # Import should not raise any errors
        from xyh.config.campaigns import cpn_2025_nano_v15

        for dataset in cpn_2025_nano_v15.datasets.values():
            if not dataset.is_data and not isinstance(dataset, DatasetProxy):
                # Check that cross sections are set to reasonable values (not
                # None and not 0)
                assert dataset.x.xsec is not None
                assert dataset.x.xsec > 0
                assert dataset.x.generator_weight is not None
                assert dataset.x.generator_weight > 0
