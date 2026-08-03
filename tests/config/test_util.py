"""
Unit tests for xyh.config.campaigns.util module.

These tests are completely isolated and use mocks for all external dependencies.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from dataclasses import fields


# =============================================================================
# Dummy classes for external dependencies
# =============================================================================

class DummyCampaign:
    """Dummy Campaign class for testing."""
    
    def __init__(self):
        self.x = Mock()
        self._datasets = []
    
    def add_dataset(self, **kwargs):
        """Mock method to add a dataset."""
        dataset = DummyDataset(**kwargs)
        self._datasets.append(dataset)
        return dataset


class DummyDataset:
    """Dummy Dataset class for testing."""
    
    def __init__(self, name, id, campaign=None, info=None, processes=None,
                 label=None, label_short=None, is_data=False, tags=None,
                 aux=None, n_events=None, n_files=None, **kwargs):
        self.name = name
        self.id = id
        self.campaign = campaign
        self.info = info
        self.processes = processes
        self.label = label
        self.label_short = label_short
        self.is_data = is_data
        self.tags = tags or []
        self.aux = aux or {}
        self.n_events = n_events
        self.n_files = n_files


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_settings():
    """Fixture to mock Settings class."""
    with patch('xyh.config.campaigns.util.Settings') as mock:
        instance = Mock()
        instance.get.return_value = Path('/mock/sample/database')
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_campaign():
    """Fixture to create a mock campaign instance."""
    campaign = DummyCampaign()
    campaign.x.nanoaod_version = 'v12'
    return campaign


@pytest.fixture
def sample_data():
    """Fixture providing sample data for tests."""
    return {
        'sample1': {
            'nick': 'sample1',
            'era': '2022',
            'nevents': 1000,
            'nfiles': 10,
            'sample_type': 'mc',
            'dbs': '/A/B/C',
            'filelist': ['file1.root', 'file2.root'],
            'instance': 'prod',
            'xsec': 1.5,
            'generator_weight': 0.9
        },
        'sample2': {
            'nick': 'sample2',
            'era': '2022',
            'nevents': 2000,
            'nfiles': 20,
            'sample_type': 'mc',
            'dbs': '/D/E/F',
            'filelist': ['file3.root'],
            'instance': 'prod',
            'xsec': 1.5,
            'generator_weight': 0.9
        },
        'data_sample': {
            'nick': 'data_sample',
            'era': '2023',
            'nevents': 5000,
            'nfiles': 50,
            'sample_type': 'data',
            'dbs': None,
            'filelist': None,
            'instance': None,
            'xsec': None,
            'generator_weight': None
        }
    }


# =============================================================================
# Tests for Sample dataclass
# =============================================================================

class TestSample:
    """Tests for the Sample dataclass."""
    
    def test_sample_creation_with_all_fields(self):
        """Test creating a Sample with all fields populated."""
        from xyh.config.campaigns.util import Sample
        
        sample = Sample(
            nick='test_nick',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            dbs='/A/B/C',
            filelist=['file1.root'],
            instance='prod',
            xsec=1.5,
            generator_weight=0.9
        )
        
        assert sample.nick == 'test_nick'
        assert sample.era == '2022'
        assert sample.nevents == 1000
        assert sample.nfiles == 10
        assert sample.sample_type == 'mc'
        assert sample.dbs == '/A/B/C'
        assert sample.filelist == ['file1.root']
        assert sample.instance == 'prod'
        assert sample.xsec == 1.5
        assert sample.generator_weight == 0.9
    
    def test_sample_creation_with_defaults(self):
        """Test creating a Sample with default values for optional fields."""
        from xyh.config.campaigns.util import Sample
        
        sample = Sample(
            nick='test_nick',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='data'
        )
        
        assert sample.nick == 'test_nick'
        assert sample.era == '2022'
        assert sample.nevents == 1000
        assert sample.nfiles == 10
        assert sample.sample_type == 'data'
        assert sample.dbs is None
        assert sample.filelist is None
        assert sample.instance is None
        assert sample.xsec is None
        assert sample.generator_weight is None


# =============================================================================
# Tests for load_database function
# =============================================================================

class TestLoadDatabase:
    """Tests for the load_database function."""
    
    def test_load_database_success(self, sample_data):
        """Test successful loading of sample database."""
        from xyh.config.campaigns.util import load_database, Sample
        
        # Mock the JSON file content
        mock_json_content = json.dumps(sample_data)
        
        with patch('xyh.config.campaigns.util.json.load') as mock_json_load:
            mock_json_load.return_value = sample_data
            
            with patch('builtins.open', mock_open(read_data=mock_json_content)):
                result = load_database(
                    sample_database_dir=Path('/mock/path'),
                    nanoaod_version='v12'
                )
        
        # Verify the result
        assert isinstance(result, dict)
        assert 'sample1' in result
        assert 'sample2' in result
        assert isinstance(result['sample1'], Sample)
        assert result['sample1'].nick == 'sample1'
        assert result['sample1'].nevents == 1000
    
    def test_load_database_uses_cache(self, sample_data):
        """Test that load_database uses caching."""
        from xyh.config.campaigns.util import load_database
        
        # Clear cache before test
        load_database.cache_clear()
        
        mock_json_content = json.dumps(sample_data)
        
        with patch('xyh.config.campaigns.util.json.load') as mock_json_load:
            mock_json_load.return_value = sample_data
            
            with patch('builtins.open', mock_open(read_data=mock_json_content)):
                # Call twice
                result1 = load_database(Path('/mock/path'), 'v12')
                result2 = load_database(Path('/mock/path'), 'v12')
                
                # json.load should only be called once due to caching
                assert mock_json_load.call_count == 1
                
                # Results should be identical
                assert result1 is result2
    
    def test_load_database_file_path_construction(self, sample_data):
        """Test that load_database constructs correct file path."""
        from xyh.config.campaigns.util import load_database
        
        mock_json_content = json.dumps(sample_data)
        
        with patch('xyh.config.campaigns.util.json.load') as mock_json_load:
            mock_json_load.return_value = sample_data
            
            with patch('builtins.open', mock_open(read_data=mock_json_content)) as mock_file:
                load_database(Path('/base/path'), 'v15')
                
                # Verify the file path was constructed correctly
                expected_path = Path('/base/path/nanoAOD_v15/datasets.json')
                mock_file.assert_called_once()
                call_args = mock_file.call_args[0][0]
                assert str(call_args).endswith('nanoAOD_v15/datasets.json')
    
    def test_load_database_empty_file(self):
        """Test loading an empty sample database."""
        from xyh.config.campaigns.util import load_database
        
        with patch('xyh.config.campaigns.util.json.load') as mock_json_load:
            mock_json_load.return_value = {}
            
            with patch('builtins.open', mock_open(read_data='{}')):
                result = load_database(Path('/mock/path'), 'v12')
                
                assert result == {}
    
    def test_load_database_cache_clear(self):
        """Test that cache can be cleared."""
        from xyh.config.campaigns.util import load_database
        
        load_database.cache_clear()
        # Should not raise an error
        assert load_database.cache_info().hits == 0


# =============================================================================
# Tests for get_format_string_parameters function
# =============================================================================

class TestGetFormatStringParameters:
    """Tests for the get_format_string_parameters function."""
    
    def test_extract_single_parameter(self):
        """Test extracting a single parameter from format string."""
        from xyh.config.campaigns.util import get_format_string_parameters
        
        result = get_format_string_parameters('sample_{mass}_test')
        assert result == {'mass'}
    
    def test_extract_multiple_parameters(self):
        """Test extracting multiple parameters from format string."""
        from xyh.config.campaigns.util import get_format_string_parameters
        
        result = get_format_string_parameters('sample_{mass}_{coupling}_test')
        assert result == {'mass', 'coupling'}
    
    def test_no_parameters(self):
        """Test format string with no parameters."""
        from xyh.config.campaigns.util import get_format_string_parameters
        
        result = get_format_string_parameters('sample_fixed_name')
        assert result == set()
    
    def test_empty_string(self):
        """Test empty format string."""
        from xyh.config.campaigns.util import get_format_string_parameters
        
        result = get_format_string_parameters('')
        assert result == set()
    
    def test_duplicate_parameters(self):
        """Test format string with duplicate parameters returns unique set."""
        from xyh.config.campaigns.util import get_format_string_parameters
        
        result = get_format_string_parameters('{mass}_{mass}_{mass}')
        assert result == {'mass'}
    
    def test_complex_format_string(self):
        """Test complex format string with various parameter names."""
        from xyh.config.campaigns.util import get_format_string_parameters
        
        result = get_format_string_parameters(
            'signal_m{mass}_pt{pt}_eta{eta}_phi{phi}'
        )
        assert result == {'mass', 'pt', 'eta', 'phi'}
    
    def test_format_with_literal_braces(self):
        """Test format string with escaped braces."""
        from xyh.config.campaigns.util import get_format_string_parameters
        
        # Double braces represent literal braces in format strings
        result = get_format_string_parameters('{{literal}}_{param}')
        assert result == {'param'}


# =============================================================================
# Tests for add_dataset function (str version)
# =============================================================================

class TestAddDatasetStr:
    """Tests for add_dataset with string nick parameter."""
    
    def test_add_dataset_single_nick(self, mock_campaign, mock_settings, sample_data):
        """Test adding a dataset with a single nick."""
        from xyh.config.campaigns.util import add_dataset, load_database
        
        # Mock the load_database to return sample data
        with patch.object(load_database, 'cache_clear'):
            with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
                mock_load_db.return_value = {
                    'sample1': type('Sample', (), sample_data['sample1'])()
                }
                
                # Create proper Sample object
                from xyh.config.campaigns.util import Sample
                mock_sample = Sample(**sample_data['sample1'])
                mock_load_db.return_value = {'sample1': mock_sample}
                
                dataset = add_dataset(mock_campaign, 'test_dataset', 'sample1')
        
        assert dataset is not None
        assert dataset.name == 'test_dataset'
        assert dataset.aux['nicks'] == ['sample1']
        assert dataset.n_events == 1000
        assert dataset.n_files == 10
        assert dataset.aux['xsec'] == 1.5
        assert dataset.aux['generator_weight'] == 0.9
        assert dataset.is_data is False
    
    def test_add_dataset_data_sample(self, mock_campaign, mock_settings):
        """Test adding a data dataset (is_data=True)."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        data_sample = Sample(
            nick='data_sample',
            era='2023',
            nevents=5000,
            nfiles=50,
            sample_type='data'
        )
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = {'data_sample': data_sample}
            
            dataset = add_dataset(mock_campaign, 'data_dataset', 'data_sample')
        
        assert dataset.is_data is True
        assert dataset.aux['xsec'] is None
        assert dataset.aux['generator_weight'] is None
    
    def test_add_dataset_none_values(self, mock_campaign, mock_settings):
        """Test adding a dataset with None xsec and generator_weight."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        sample = Sample(
            nick='test_nick',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=None,
            generator_weight=None
        )
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = {'test_nick': sample}
            
            dataset = add_dataset(mock_campaign, 'test_dataset', 'test_nick')
        
        assert dataset.aux['xsec'] is None
        assert dataset.aux['generator_weight'] is None


# =============================================================================
# Tests for add_dataset function (list version)
# =============================================================================

class TestAddDatasetList:
    """Tests for add_dataset with list of nicks parameter."""
    
    def test_add_dataset_multiple_nicks(self, mock_campaign, mock_settings):
        """Test adding a dataset with multiple nicks."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        sample1 = Sample(
            nick='sample1',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        sample2 = Sample(
            nick='sample2',
            era='2022',
            nevents=2000,
            nfiles=20,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        samples = {'sample1': sample1, 'sample2': sample2}
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = samples
            
            dataset = add_dataset(
                mock_campaign, 
                'combined_dataset', 
                ['sample1', 'sample2']
            )
        
        assert dataset.name == 'combined_dataset'
        assert dataset.aux['nicks'] == ['sample1', 'sample2']
        # Events and files should be summed
        assert dataset.n_events == 3000
        assert dataset.n_files == 30
        # Cross sections should match (not summed)
        assert dataset.aux['xsec'] == 1.5
        assert dataset.aux['generator_weight'] == 0.9
    
    def test_add_dataset_xsec_tolerance_check(self, mock_campaign, mock_settings):
        """Test that cross sections within tolerance are accepted."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        # Cross sections differ by less than 1e-3 relative tolerance
        sample1 = Sample(
            nick='sample1',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        sample2 = Sample(
            nick='sample2',
            era='2022',
            nevents=2000,
            nfiles=20,
            sample_type='mc',
            xsec=1.5001,  # Within 1e-3 relative tolerance
            generator_weight=0.9
        )
        
        samples = {'sample1': sample1, 'sample2': sample2}
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = samples
            
            dataset = add_dataset(
                mock_campaign,
                'combined_dataset',
                ['sample1', 'sample2']
            )
        
        assert dataset is not None
        assert dataset.aux['xsec'] == 1.5  # First value used
    
    def test_add_dataset_xsec_mismatch_raises_error(self, mock_campaign, mock_settings):
        """Test that mismatched cross sections raise ValueError."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        sample1 = Sample(
            nick='sample1',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        sample2 = Sample(
            nick='sample2',
            era='2022',
            nevents=2000,
            nfiles=20,
            sample_type='mc',
            xsec=2.0,  # Significantly different
            generator_weight=0.9
        )
        
        samples = {'sample1': sample1, 'sample2': sample2}
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = samples
            
            with pytest.raises(ValueError, match="Values of 'xsec' not equal"):
                add_dataset(mock_campaign, 'combined_dataset', ['sample1', 'sample2'])
    
    def test_add_dataset_generator_weight_mismatch_raises_error(self, mock_campaign, mock_settings):
        """Test that mismatched generator weights raise ValueError."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        sample1 = Sample(
            nick='sample1',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        sample2 = Sample(
            nick='sample2',
            era='2022',
            nevents=2000,
            nfiles=20,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.5  # Significantly different
        )
        
        samples = {'sample1': sample1, 'sample2': sample2}
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = samples
            
            with pytest.raises(ValueError, match="Values of 'generator_weight' not equal"):
                add_dataset(mock_campaign, 'combined_dataset', ['sample1', 'sample2'])
    
    def test_add_dataset_era_mismatch_raises_error(self, mock_campaign, mock_settings):
        """Test that mismatched eras raise ValueError."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        sample1 = Sample(
            nick='sample1',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        sample2 = Sample(
            nick='sample2',
            era='2023',  # Different era
            nevents=2000,
            nfiles=20,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        samples = {'sample1': sample1, 'sample2': sample2}
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = samples
            
            with pytest.raises(ValueError, match="Values of 'era' not equal"):
                add_dataset(mock_campaign, 'combined_dataset', ['sample1', 'sample2'])
    
    def test_add_dataset_sample_type_mismatch_raises_error(self, mock_campaign, mock_settings):
        """Test that mismatched sample types raise ValueError."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        sample1 = Sample(
            nick='sample1',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        sample2 = Sample(
            nick='sample2',
            era='2022',
            nevents=2000,
            nfiles=20,
            sample_type='data',  # Different sample type
            xsec=None,
            generator_weight=None
        )
        
        samples = {'sample1': sample1, 'sample2': sample2}
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = samples
            
            with pytest.raises(ValueError, match="Values of 'sample_type' not equal"):
                add_dataset(mock_campaign, 'combined_dataset', ['sample1', 'sample2'])
    
    def test_add_dataset_all_none_xsec(self, mock_campaign, mock_settings):
        """Test adding datasets where all have None xsec."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        sample1 = Sample(
            nick='sample1',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=None,
            generator_weight=None
        )
        
        sample2 = Sample(
            nick='sample2',
            era='2022',
            nevents=2000,
            nfiles=20,
            sample_type='mc',
            xsec=None,
            generator_weight=None
        )
        
        samples = {'sample1': sample1, 'sample2': sample2}
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = samples
            
            dataset = add_dataset(
                mock_campaign,
                'combined_dataset',
                ['sample1', 'sample2']
            )
        
        assert dataset.aux['xsec'] is None
        assert dataset.aux['generator_weight'] is None


# =============================================================================
# Tests for add_dataset function (generic/Any version)
# =============================================================================

class TestAddDatasetGeneric:
    """Tests for add_dataset with generic Any parameter (format strings)."""
    
    def test_add_dataset_with_format_string_name(self, mock_campaign):
        """Test adding a dataset with format string in name."""
        from xyh.config.campaigns.util import add_dataset
        
        # When name has format parameters, should return DatasetProxy
        dataset = add_dataset(
            mock_campaign,
            'signal_mass{mass}',
            'nick_template_{mass}'
        )
        
        # Should create a DatasetProxy
        assert dataset is not None
        assert hasattr(dataset, '_parameters')
        assert 'mass' in dataset._parameters
    
    def test_add_dataset_without_format_string(self, mock_campaign, mock_settings):
        """Test that regular names fall through to other handlers."""
        from xyh.config.campaigns.util import add_dataset, Sample
        
        sample = Sample(
            nick='regular_nick',
            era='2022',
            nevents=1000,
            nfiles=10,
            sample_type='mc',
            xsec=1.5,
            generator_weight=0.9
        )
        
        with patch('xyh.config.campaigns.util.load_database') as mock_load_db:
            mock_load_db.return_value = {'regular_nick': sample}
            
            # This should use the str handler, not the generic one
            dataset = add_dataset(mock_campaign, 'regular_name', 'regular_nick')
        
        assert dataset.name == 'regular_name'
        assert not hasattr(dataset, '_parameters')


# =============================================================================
# Tests for DatasetProxy class
# =============================================================================

class TestDatasetProxy:
    """Tests for the DatasetProxy class."""
    
    def test_dataset_proxy_creation_with_string_nicks(self):
        """Test creating DatasetProxy with string nicks."""
        from xyh.config.campaigns.util import DatasetProxy
        
        proxy = DatasetProxy(
            name='signal_mass{mass}',
            id='+',
            aux={'nicks': ['nick_{mass}']}
        )
        
        assert proxy.name == 'signal_mass{mass}'
        assert proxy.id == '+'
        assert 'mass' in proxy._parameters
    
    def test_dataset_proxy_creation_with_callable_nicks(self):
        """Test creating DatasetProxy with callable nicks."""
        from xyh.config.campaigns.util import DatasetProxy
        
        def nick_func(mass):
            return f'nick_{mass}'
        
        proxy = DatasetProxy(
            name='signal_mass{mass}',
            id='+',
            aux={'nicks': [nick_func]}
        )
        
        assert proxy.name == 'signal_mass{mass}'
        assert 'mass' in proxy._parameters
    
    def test_dataset_proxy_parameter_mismatch_string(self):
        """Test that parameter mismatch in string nicks raises ValueError."""
        from xyh.config.campaigns.util import DatasetProxy
        
        # Nick has 'coupling' but name only has 'mass'
        with pytest.raises(ValueError, match="Nick.*contains parameters.*which are not present"):
            DatasetProxy(
                name='signal_mass{mass}',
                id='+',
                aux={'nicks': ['nick_{coupling}']}
            )
    
    def test_dataset_proxy_parameter_mismatch_callable(self):
        """Test that parameter mismatch in callable nicks raises ValueError."""
        from xyh.config.campaigns.util import DatasetProxy
        
        def nick_func(coupling):
            return f'nick_{coupling}'
        
        # Nick has 'coupling' but name only has 'mass'
        with pytest.raises(ValueError, match="Nick.*contains parameters.*which are not present"):
            DatasetProxy(
                name='signal_mass{mass}',
                id='+',
                aux={'nicks': [nick_func]}
            )
    
    def test_dataset_proxy_unsupported_nick_type(self):
        """Test that unsupported nick type raises TypeError."""
        from xyh.config.campaigns.util import DatasetProxy
        
        with pytest.raises(TypeError, match="Unsupported type for nick"):
            DatasetProxy(
                name='signal_mass{mass}',
                id='+',
                aux={'nicks': [123]}  # Integer is not supported
            )
    
    def test_dataset_proxy_multiple_parameters(self):
        """Test DatasetProxy with multiple parameters."""
        from xyh.config.campaigns.util import DatasetProxy
        
        proxy = DatasetProxy(
            name='signal_mass{mass}_pt{pt}',
            id='+',
            aux={'nicks': ['nick_{mass}_{pt}']}
        )
        
        assert 'mass' in proxy._parameters
        assert 'pt' in proxy._parameters
        assert len(proxy._parameters) == 2
    
    def test_dataset_proxy_subset_parameters(self):
        """Test that nick parameters can be a subset of name parameters."""
        from xyh.config.campaigns.util import DatasetProxy
        
        # Name has mass and pt, nick only uses mass (this is allowed)
        proxy = DatasetProxy(
            name='signal_mass{mass}_pt{pt}',
            id='+',
            aux={'nicks': ['nick_{mass}']}
        )
        
        assert proxy is not None
    
    def test_dataset_proxy_empty_nicks(self):
        """Test DatasetProxy with empty nicks list."""
        from xyh.config.campaigns.util import DatasetProxy
        
        proxy = DatasetProxy(
            name='signal_mass{mass}',
            id='+',
            aux={'nicks': []}
        )
        
        assert proxy is not None
        assert 'mass' in proxy._parameters
    
    def test_dataset_proxy_no_nicks_in_aux(self):
        """Test DatasetProxy without nicks in aux."""
        from xyh.config.campaigns.util import DatasetProxy
        
        proxy = DatasetProxy(
            name='signal_mass{mass}',
            id='+',
            aux={}
        )
        
        assert proxy is not None
        assert 'mass' in proxy._parameters
    
    def test_dataset_proxy_inherits_from_dataset(self):
        """Test that DatasetProxy inherits from Dataset."""
        from xyh.config.campaigns.util import DatasetProxy
        
        proxy = DatasetProxy(
            name='test',
            id='+',
            aux={}
        )
        
        # Should have Dataset attributes
        assert hasattr(proxy, 'name')
        assert hasattr(proxy, 'id')
        assert hasattr(proxy, 'aux')
        assert hasattr(proxy, 'is_data')
        assert proxy.is_data is False  # Default value
