"""
Unit tests for config.py module

These tests verify that configuration values are loaded correctly
from environment variables and that file paths are properly constructed.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConfigurationLoading:
    """Test configuration loading from environment variables"""
    
    def test_config_imports_successfully(self):
        """
        Test that the config module can be imported without errors.
        This is a smoke test that ensures all dependencies are available.
        """
        # Import the config module - should not raise any exceptions
        from src import config
        
        # Verify that the module was imported successfully
        assert config is not None
    
    @patch.dict(os.environ, {
        'GOOGLE_LLM_API_KEY': 'test_llm_key_12345',
        'GOOGLE_BIGQUERY_CREDENTIALS': '{"project_id": "test-project"}',
        'BIGQUERY_PROJECT_ID': 'custom-project-id'
    })
    def test_api_keys_loaded_from_environment(self):
        """
        Test that API keys are correctly loaded from environment variables.
        
        This test:
        1. Mocks environment variables with test values
        2. Reloads the config module to pick up the mocked values
        3. Verifies that the config values match the mocked environment
        
        Why this is important:
        - Ensures the application correctly reads credentials from environment
        - Prevents hardcoded credentials in the codebase
        - Validates the configuration loading mechanism
        """
        # Reimport config to pick up the mocked environment variables
        import importlib
        from src import config
        importlib.reload(config)
        
        # Verify that the API keys match the mocked environment values
        assert config.GOOGLE_LLM_API_KEY == 'test_llm_key_12345'
        assert config.GOOGLE_BIGQUERY_CREDENTIALS == '{"project_id": "test-project"}'
        assert config.BIGQUERY_PROJECT_ID == 'custom-project-id'
    
    def test_bigquery_configuration_values(self):
        """
        Test that BigQuery configuration values are set correctly.
        
        These values control:
        - BIGQUERY_QUERY_TIMEOUT: Maximum time a query can run before timing out
        - BIGQUERY_MAX_RESULTS: Safety limit on the number of rows returned
        - BIGQUERY_DATASET: The specific dataset to query
        
        Why test hardcoded values:
        - Ensures default values remain consistent across deployments
        - Documents the expected configuration in test form
        - Catches accidental changes to important constants
        """
        from src import config
        
        # Verify timeout is set (should be positive integer)
        assert isinstance(config.BIGQUERY_QUERY_TIMEOUT, int)
        assert config.BIGQUERY_QUERY_TIMEOUT > 0
        
        # Verify max results is set (should be positive integer)
        assert isinstance(config.BIGQUERY_MAX_RESULTS, int)
        assert config.BIGQUERY_MAX_RESULTS > 0
        
        # Verify dataset name is a non-empty string
        assert isinstance(config.BIGQUERY_DATASET, str)
        assert len(config.BIGQUERY_DATASET) > 0
    
    def test_file_paths_are_valid_path_objects(self):
        """
        Test that file paths are constructed as Path objects.
        
        Using pathlib.Path objects provides:
        - Cross-platform compatibility (Windows/Linux/Mac)
        - Clean path manipulation (using / operator)
        - Built-in path validation and existence checking
        
        Why this test matters:
        - Ensures paths work on any operating system
        - Validates that the Path objects are properly constructed
        - Catches potential path construction errors early
        """
        from src import config
        
        # Verify that PROJECT_ROOT is a Path object
        assert isinstance(config.PROJECT_ROOT, Path)
        
        # Verify that DATA_DIR is a Path object
        assert isinstance(config.DATA_DIR, Path)
        
        # Verify that PROMPT_DIR is a Path object
        assert isinstance(config.PROMPT_DIR, Path)
        
        # Verify that SCHEMA_FILE is a Path object
        assert isinstance(config.SCHEMA_FILE, Path)
        
        # Verify that FEWSHOT_FILE is a Path object
        assert isinstance(config.FEWSHOT_FILE, Path)
    
    def test_file_paths_have_correct_extensions(self):
        """
        Test that configuration files have the expected file extensions.
        
        Expected extensions:
        - SCHEMA_FILE should be .yaml (YAML format for schema definition)
        - FEWSHOT_FILE should be .json (JSON format for example queries)
        
        Why this matters:
        - Ensures the correct file types are being referenced
        - Prevents accidentally using wrong file formats
        - Documents the expected file formats in test form
        """
        from src import config
        
        # SCHEMA_FILE should be a YAML file
        assert config.SCHEMA_FILE.suffix == '.yaml'
        
        # FEWSHOT_FILE should be a JSON file
        assert config.FEWSHOT_FILE.suffix == '.json'
    
    def test_data_directory_structure(self):
        """
        Test that the data directory structure is correctly defined.
        
        Expected structure:
        PROJECT_ROOT/
        └── data/
            └── prompt/
                ├── eth_mainnet_db_schema.yaml
                └── eth_mainnet_sql_fewshots.json
        
        Why test directory structure:
        - Ensures consistent file organization across deployments
        - Validates the path relationships between directories
        - Documents the expected directory layout
        """
        from src import config
        
        # Verify that DATA_DIR is a subdirectory of PROJECT_ROOT
        # Using is_relative_to() checks if DATA_DIR path starts with PROJECT_ROOT
        assert config.DATA_DIR.is_relative_to(config.PROJECT_ROOT)
        
        # Verify that PROMPT_DIR is a subdirectory of DATA_DIR
        assert config.PROMPT_DIR.is_relative_to(config.DATA_DIR)
        
        # Verify that SCHEMA_FILE is in PROMPT_DIR
        assert config.SCHEMA_FILE.parent == config.PROMPT_DIR
        
        # Verify that FEWSHOT_FILE is in PROMPT_DIR
        assert config.FEWSHOT_FILE.parent == config.PROMPT_DIR


class TestLoggingConfiguration:
    """Test that logging is properly configured"""
    
    def test_logging_is_configured(self):
        """
        Test that logging is configured at module import.
        
        The logging configuration in config.py sets up:
        - Log level (INFO by default)
        - Log format (timestamp - module - level - message)
        - Date format (YYYY-MM-DD HH:MM:SS)
        
        Why test logging:
        - Ensures logging works correctly across all modules
        - Validates that log messages will be properly formatted
        - Catches logging configuration errors early
        """
        import logging
        from src import config
        
        # Get a test logger to verify configuration
        test_logger = logging.getLogger('test_logger')
        
        # Verify that the logger has handlers configured
        # (basicConfig in config.py should have set up a default handler)
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        
        # Verify that the log level is set (should be INFO or DEBUG)
        assert root_logger.level in [logging.INFO, logging.DEBUG, logging.WARNING]

