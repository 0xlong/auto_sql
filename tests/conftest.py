"""
Shared pytest fixtures and configuration for all tests

This file contains:
- Common fixtures used across multiple test files
- Test configuration and setup
- Shared mock objects and test data

Pytest automatically discovers and uses fixtures defined here
in all test files without needing explicit imports.
"""

import pytest
import json
import sys
import types
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock

# Mock google package hierarchy before any test modules are imported
# This prevents ImportError when modules try to import google.* packages
# We do this at the module level so it's available before any imports
# Python imports work hierarchically: google -> google.cloud -> google.cloud.bigquery
# We need to mock all levels of the import path using ModuleType for proper package behavior

def _create_mock_module(name):
    """Create a proper module object that can be used in sys.modules"""
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module

# Create proper module objects (not MagicMock) so Python can traverse them as packages
# This allows imports like "from google.ai import ..." to work

# Mock the google module as a proper module
if 'google' not in sys.modules:
    _create_mock_module('google')

# Mock google.ai module (needed by langchain_google_genai)
if 'google.ai' not in sys.modules:
    mock_google_ai = _create_mock_module('google.ai')
    # Set it as an attribute on google module
    sys.modules['google'].ai = mock_google_ai

# Mock google.ai.generativelanguage_v1beta (needed by langchain_google_genai)
if 'google.ai.generativelanguage_v1beta' not in sys.modules:
    mock_genai = _create_mock_module('google.ai.generativelanguage_v1beta')
    sys.modules['google.ai'].generativelanguage_v1beta = mock_genai

# Mock google.cloud module
if 'google.cloud' not in sys.modules:
    mock_google_cloud = _create_mock_module('google.cloud')
    sys.modules['google'].cloud = mock_google_cloud
else:
    mock_google_cloud = sys.modules['google.cloud']

# Mock google.cloud.bigquery module
if 'google.cloud.bigquery' not in sys.modules:
    mock_bigquery = _create_mock_module('google.cloud.bigquery')
    # Add Client class as a MagicMock since it's a class, not a module
    mock_bigquery.Client = MagicMock()
    sys.modules['google.cloud'].bigquery = mock_bigquery
else:
    mock_bigquery = sys.modules['google.cloud.bigquery']
    if not hasattr(mock_bigquery, 'Client'):
        mock_bigquery.Client = MagicMock()

# Mock google.oauth2 for service account credentials
if 'google.oauth2' not in sys.modules:
    mock_google_oauth2 = _create_mock_module('google.oauth2')
    sys.modules['google'].oauth2 = mock_google_oauth2
else:
    mock_google_oauth2 = sys.modules['google.oauth2']

if 'google.oauth2.service_account' not in sys.modules:
    mock_service_account = _create_mock_module('google.oauth2.service_account')
    # Add Credentials class
    mock_service_account.Credentials = MagicMock()
    sys.modules['google.oauth2'].service_account = mock_service_account
else:
    mock_service_account = sys.modules['google.oauth2.service_account']
    if not hasattr(mock_service_account, 'Credentials'):
        mock_service_account.Credentials = MagicMock()


@pytest.fixture
def sample_dataframe():
    """
    Fixture that provides a sample pandas DataFrame for testing.
    
    This DataFrame simulates query results from BigQuery with common
    Ethereum blockchain fields.
    
    Usage in tests:
        def test_something(sample_dataframe):
            # sample_dataframe is automatically provided
            assert len(sample_dataframe) == 3
    
    Returns:
        pd.DataFrame: Sample DataFrame with transaction data
    """
    return pd.DataFrame({
        'transaction_hash': ['0xabc123', '0xdef456', '0xghi789'],
        'block_number': [1000, 1001, 1002],
        'value': [100, 200, 300],
        'gas_price': [20, 25, 30]
    })


@pytest.fixture
def sample_few_shot_examples():
    """
    Fixture that provides sample few-shot examples as JSON string.
    
    These examples simulate the format used in eth_mainnet_sql_fewshots.json
    for providing context to the LLM.
    
    Returns:
        str: JSON string containing example queries
    """
    examples = [
        {
            "query_name": "recent transactions",
            "query_sql": "SELECT transaction_hash, block_number FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.transactions` LIMIT 10",
            "expected_result": {
                "columns": ["transaction_hash", "block_number"],
                "rows": [
                    ["0xabc123", "1000"],
                    ["0xdef456", "1001"]
                ],
                "notes": "Shows the most recent transactions"
            }
        },
        {
            "query_name": "average gas price",
            "query_sql": "SELECT AVG(gas_price) as avg_gas_price FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.transactions`",
            "expected_result": {
                "columns": ["avg_gas_price"],
                "rows": [["25.5"]],
                "notes": "Calculates the average gas price"
            }
        }
    ]
    return json.dumps(examples)


@pytest.fixture
def sample_db_schema():
    """
    Fixture that provides a sample database schema string.
    
    This simulates the content of eth_mainnet_db_schema.yaml
    with common Ethereum blockchain table definitions.
    
    Returns:
        str: Database schema in YAML-like format
    """
    return """
    tables:
      - name: transactions
        columns:
          - transaction_hash: STRING (unique identifier)
          - block_number: INTEGER (block containing transaction)
          - value: INTEGER (amount transferred in wei)
          - gas_price: INTEGER (gas price in wei)
          - from_address: STRING (sender address)
          - to_address: STRING (recipient address)
          
      - name: blocks
        columns:
          - block_number: INTEGER (unique block identifier)
          - timestamp: TIMESTAMP (when block was mined)
          - miner: STRING (address of miner)
          - difficulty: INTEGER (mining difficulty)
    """


@pytest.fixture
def mock_bigquery_client():
    """
    Fixture that provides a mocked BigQuery client.
    
    This mock client simulates BigQuery operations without
    requiring actual GCP credentials or making real API calls.
    
    Returns:
        MagicMock: Mocked BigQuery client with common methods
    """
    client = MagicMock()
    client.project = "test-project-123"
    
    # Mock query method to return a query job
    query_job = MagicMock()
    query_job.state = "DONE"
    query_job.errors = None
    query_job.job_id = "test-job-123"
    
    # Mock to_dataframe to return test data
    query_job.to_dataframe.return_value = pd.DataFrame({
        'result': ['test1', 'test2', 'test3']
    })
    
    client.query.return_value = query_job
    
    return client


@pytest.fixture
def mock_llm_response():
    """
    Fixture that provides a mocked LLM response.
    
    This simulates the response structure from ChatGoogleGenerativeAI
    without making actual API calls.
    
    Returns:
        MagicMock: Mocked LLM response with content attribute
    """
    response = MagicMock()
    response.content = "SELECT * FROM test_table LIMIT 10"
    return response


@pytest.fixture
def temp_fewshot_file(tmp_path):
    """
    Fixture that creates a temporary few-shot examples file.
    
    This allows tests to read/write few-shot examples without
    modifying the actual project files.
    
    Args:
        tmp_path: Pytest's built-in fixture for temporary directories
    
    Returns:
        Path: Path to the temporary few-shot JSON file
    """
    # Create temporary file with initial data
    file_path = tmp_path / "test_fewshots.json"
    initial_data = [
        {
            "query_name": "test query",
            "query_sql": "SELECT 1",
            "expected_result": {
                "columns": ["col1"],
                "rows": [["val1"]],
                "notes": "test"
            }
        }
    ]
    
    # Write initial data to file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f)
    
    return file_path


@pytest.fixture
def sample_user_queries():
    """
    Fixture that provides a list of sample user queries.
    
    These represent typical natural language queries that users
    might ask the application.
    
    Returns:
        list: List of sample user query strings
    """
    return [
        "Show me the last 10 transactions",
        "What is the average gas price in October?",
        "How many blocks were created yesterday?",
        "Show me transactions with value greater than 1 ETH",
        "What are the top 5 most active addresses?"
    ]


@pytest.fixture
def sample_sql_queries():
    """
    Fixture that provides a list of sample SQL queries.
    
    These represent valid BigQuery SQL queries that the LLM
    might generate from user queries.
    
    Returns:
        list: List of sample SQL query strings
    """
    return [
        "SELECT transaction_hash, block_number FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.transactions` LIMIT 10",
        "SELECT AVG(gas_price) as avg_gas FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.transactions` WHERE EXTRACT(MONTH FROM block_timestamp) = 10",
        "SELECT COUNT(*) as block_count FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.blocks` WHERE DATE(timestamp) = CURRENT_DATE() - 1",
        "SELECT * FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.transactions` WHERE value > 1000000000000000000",
        "SELECT from_address, COUNT(*) as tx_count FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.transactions` GROUP BY from_address ORDER BY tx_count DESC LIMIT 5"
    ]


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """
    Fixture that runs automatically before each test to reset environment.
    
    This ensures that each test starts with a clean environment and
    doesn't affect other tests through shared state.
    
    Args:
        monkeypatch: Pytest's built-in fixture for modifying environment
    
    The autouse=True parameter means this fixture runs automatically
    for every test without needing to be explicitly requested.
    """
    # This fixture doesn't do anything by default
    # But it can be extended to reset specific environment variables
    # or clean up shared state between tests
    pass


@pytest.fixture
def mock_successful_query_job():
    """
    Fixture that provides a mocked successful BigQuery query job.
    
    This includes all the attributes that bigquery_sqlrun_details expects
    for a successfully completed query.
    
    Returns:
        MagicMock: Fully configured mock query job
    """
    from datetime import datetime
    
    query_job = MagicMock()
    
    # Job identification
    query_job.job_id = "successful-job-123"
    query_job.location = "US"
    query_job.user_email = "test@example.com"
    
    # Execution status (successful)
    query_job.state = "DONE"
    query_job.errors = None
    
    # Timing information
    query_job.created = datetime(2024, 1, 1, 10, 0, 0)
    query_job.started = datetime(2024, 1, 1, 10, 0, 5)
    query_job.ended = datetime(2024, 1, 1, 10, 0, 15)
    
    # Performance statistics
    query_job.total_bytes_processed = 1024 * 1024 * 100  # 100 MB
    query_job.total_bytes_billed = 1024 * 1024 * 100  # 100 MB
    query_job.cache_hit = False
    query_job.slot_millis = 5000
    
    # Query details
    query_job.query = "SELECT * FROM test_table"
    query_job.destination = "project.dataset.table"
    query_job.priority = "INTERACTIVE"
    
    # Results
    mock_result = MagicMock()
    mock_result.total_rows = 100
    
    # Schema
    mock_field = MagicMock()
    mock_field.name = "test_column"
    mock_field.field_type = "STRING"
    mock_field.mode = "NULLABLE"
    mock_result.schema = [mock_field]
    
    query_job.result.return_value = mock_result
    
    return query_job


# Pytest configuration hooks
def pytest_configure(config):
    """
    Pytest hook that runs once before any tests start.
    
    Used to register custom markers and configure test behavior.
    
    Args:
        config: Pytest configuration object
    """
    # Register custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """
    Pytest hook that modifies test collection.
    
    Automatically adds markers to tests based on their location:
    - Tests in tests/unit/ get the 'unit' marker
    - Tests in tests/integration/ get the 'integration' marker
    
    This allows filtering tests by type without manually adding
    markers to every test function.
    
    Args:
        config: Pytest configuration object
        items: List of collected test items
    """
    for item in items:
        # Get the test file path
        test_path = str(item.fspath)
        
        # Add unit marker to tests in unit directory
        if "tests\\unit\\" in test_path or "tests/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in integration directory
        if "tests\\integration\\" in test_path or "tests/integration/" in test_path:
            item.add_marker(pytest.mark.integration)

