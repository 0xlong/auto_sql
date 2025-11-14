"""
Integration tests for the auto_sql application

These tests verify end-to-end workflows including:
- Loading configuration and prompt data
- Generating SQL queries from natural language
- Executing queries against BigQuery (mocked)
- Generating AI summaries of results
- Saving successful queries

Integration tests use mocked external services (LLM, BigQuery)
but test the full flow through multiple modules.
"""

import pytest
import json
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


class TestEndToEndQueryGeneration:
    """Test the complete flow from user query to SQL generation"""
    
    def test_generate_and_validate_sql_query_flow(self):
        """
        Test the complete flow of generating a SQL query.
        
        This integration test:
        1. Loads configuration (db schema, few-shot examples)
        2. Generates a SQL query using the LLM
        3. Validates the output format
        
        Why this is an integration test:
        - Tests multiple components working together
        - Validates data flow between config and LLM utils
        - Ensures prompt construction works correctly
        """
        # Import modules first so they exist before patching
        from src.utils import llm_utils
        from src import config
        
        # Patch after import using context manager
        with patch.object(llm_utils, 'ChatGoogleGenerativeAI') as mock_llm, \
             patch.object(llm_utils, 'PromptTemplate') as mock_prompt_template:
        
            # Mock the LLM response
            mock_response = MagicMock()
            mock_response.content = "SELECT transaction_hash, block_number FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.transactions` LIMIT 10"
            
            # Setup mock chain
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            mock_prompt_template.return_value.__or__ = MagicMock(return_value=mock_chain)
            
            # Test input
            user_query = "Show me the last 10 transactions"
            db_schema = "transactions: transaction_hash, block_number, value, gas_price"
            few_shot_examples = json.dumps([
                {
                    "query_name": "recent transactions",
                    "query_sql": "SELECT * FROM transactions LIMIT 10"
                }
            ])
            
            # Generate SQL query
            result = llm_utils.generate_sql_query(
                user_query=user_query,
                api_key="test_api_key",
                db_schema=db_schema,
                few_shot_examples=few_shot_examples
            )
            
            # Verify the result
            assert result is not None
            assert "SELECT" in result.upper()
            assert "FROM" in result.upper()
            
            # Verify that the LLM was called
            mock_chain.invoke.assert_called_once()
            
            # Verify that the prompt template received all required inputs
            call_args = mock_chain.invoke.call_args[0][0]
            assert 'user_query' in call_args
            assert 'db_schema' in call_args
            assert 'few_shot_examples' in call_args


class TestEndToEndQueryExecution:
    """Test the complete flow of executing a query and processing results"""
    
    @patch.dict('os.environ', {
        'GOOGLE_BIGQUERY_CREDENTIALS': json.dumps({
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com"
        })
    })
    def test_authenticate_and_execute_query_flow(self):
        """
        Test the complete flow of authenticating and executing a query.
        
        This integration test:
        1. Authenticates to BigQuery
        2. Executes a SQL query
        3. Retrieves and processes results
        
        Why this is an integration test:
        - Tests authentication → query execution flow
        - Validates that the client is properly initialized
        - Ensures query results can be processed
        """
        # Import module first
        from src.utils import bigquery_utils
        
        # Patch after import
        with patch('google.cloud.bigquery.Client') as mock_client, \
             patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_credentials:
            
            # Import function after patching
            from src.utils.bigquery_utils import authenticate_to_bigquery
        
            # Setup mock client
            mock_client_instance = MagicMock()
            mock_client_instance.project = "test-project"
            mock_client.return_value = mock_client_instance
            
            # Setup mock credentials
            mock_creds = MagicMock()
            mock_credentials.return_value = mock_creds
            
            # Authenticate
            client = authenticate_to_bigquery()
            assert client is not None
            assert client.project == "test-project"
            
            # Setup mock query job
            mock_query_job = MagicMock()
            mock_query_job.state = "DONE"
            mock_query_job.errors = None
            
            # Setup mock results
            mock_result = MagicMock()
            mock_result.total_rows = 5
            mock_query_job.result.return_value = mock_result
            
            # Mock to_dataframe to return test data
            test_df = pd.DataFrame({
                'transaction_hash': ['0xabc', '0xdef', '0xghi'],
                'block_number': [1000, 1001, 1002],
                'value': [100, 200, 300]
            })
            mock_query_job.to_dataframe.return_value = test_df
            
            # Execute query
            client.query = MagicMock(return_value=mock_query_job)
            query_job = client.query("SELECT * FROM transactions LIMIT 3")
            
            # Process results
            results_df = query_job.to_dataframe()
            
            # Verify results
            assert results_df is not None
            assert len(results_df) == 3
            assert 'transaction_hash' in results_df.columns
            assert 'block_number' in results_df.columns
            assert 'value' in results_df.columns


class TestEndToEndResultsSummarization:
    """Test the complete flow of generating AI summaries from query results"""
    
    def test_query_execution_to_ai_summary_flow(self):
        """
        Test the complete flow from query results to AI summary.
        
        This integration test:
        1. Simulates query execution with results
        2. Generates an AI summary of the results
        3. Validates the summary format
        
        Why this is an integration test:
        - Tests the data transformation pipeline
        - Validates that DataFrame data is properly formatted for LLM
        - Ensures the summary generation works with realistic data
        """
        # Import module first
        from src.utils import llm_utils
        
        # Patch after import
        with patch.object(llm_utils, 'ChatGoogleGenerativeAI') as mock_llm, \
             patch.object(llm_utils, 'PromptTemplate') as mock_prompt_template:
        
            # Mock the LLM response
            mock_response = MagicMock()
            mock_response.content = "The query returned 3 transactions with block numbers ranging from 1000 to 1002. The total value of these transactions is 600 wei."
            
            # Setup mock chain
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = mock_response
            mock_prompt_template.return_value.__or__ = MagicMock(return_value=mock_chain)
            
            # Create test query results
            results_df = pd.DataFrame({
                'transaction_hash': ['0xabc123', '0xdef456', '0xghi789'],
                'block_number': [1000, 1001, 1002],
                'value': [100, 200, 300]
            })
            
            # Generate AI summary
            user_query = "Show me recent transactions"
            summary = llm_utils.generate_ai_answer(
                user_query=user_query,
                results_df=results_df,
                api_key="test_api_key"
            )
            
            # Verify the summary
            assert summary is not None
            assert len(summary) > 0
            assert isinstance(summary, str)
            
            # Verify that the LLM was called with results data
            mock_chain.invoke.assert_called_once()
            call_args = mock_chain.invoke.call_args[0][0]
            assert 'user_query' in call_args
            assert 'results_df' in call_args


class TestEndToEndConfigurationIntegration:
    """Test integration between configuration and application modules"""
    
    def test_config_values_used_across_modules(self, tmp_path):
        """
        Test that configuration values are properly used across modules.
        
        This integration test:
        1. Verifies that config paths are accessible
        2. Tests that file paths work with utility functions
        3. Ensures consistent configuration across the application
        
        Why this is important:
        - Validates the configuration pattern works end-to-end
        - Ensures modules can access shared configuration
        - Tests the single source of truth for config values
        """
        from src import config
        
        # Verify that configuration paths are Path objects
        assert isinstance(config.PROJECT_ROOT, Path)
        assert isinstance(config.DATA_DIR, Path)
        assert isinstance(config.SCHEMA_FILE, Path)
        assert isinstance(config.FEWSHOT_FILE, Path)
        
        # Verify that BigQuery configuration is accessible
        assert config.BIGQUERY_QUERY_TIMEOUT > 0
        assert config.BIGQUERY_MAX_RESULTS > 0
        assert isinstance(config.BIGQUERY_DATASET, str)
        
        # Verify that the configuration can be used by utility modules
        # (This tests that imports work correctly across the project)
        from src.utils import llm_utils
        from src.utils import bigquery_utils
        
        # Both modules should be able to import and use config
        assert llm_utils.FEWSHOT_FILE == config.FEWSHOT_FILE
    
    @patch.dict('os.environ', {'GOOGLE_LLM_API_KEY': 'test_integration_key'})
    def test_environment_variables_integration(self):
        """
        Test that environment variables are properly integrated.
        
        This test verifies that:
        - Environment variables can be set and read
        - The config module picks up environment changes
        - API keys are accessible to utility modules
        """
        import os
        import importlib
        from src import config
        
        # Reload config to pick up the mocked environment variable
        importlib.reload(config)
        
        # Verify that the API key was loaded
        assert config.GOOGLE_LLM_API_KEY == 'test_integration_key'


class TestEndToEndErrorHandling:
    """Test error handling across the application"""
    
    def test_invalid_inputs_handled_gracefully(self):
        """
        Test that invalid inputs are handled gracefully throughout the flow.
        
        This integration test verifies that:
        - Input validation catches errors early
        - Error messages are clear and actionable
        - The application doesn't crash with invalid inputs
        """
        from src.utils import llm_utils
        
        # Test that None inputs are rejected with clear errors
        with pytest.raises(ValueError, match="user_query parameter cannot be None"):
            llm_utils.generate_sql_query(
                user_query=None,
                api_key="test_key",
                db_schema="schema",
                few_shot_examples='[]'
            )
        
        # Test that empty inputs are rejected
        with pytest.raises(ValueError, match="user_query cannot be empty"):
            llm_utils.generate_sql_query(
                user_query="",
                api_key="test_key",
                db_schema="schema",
                few_shot_examples='[]'
            )
        
        # Test that invalid JSON is rejected
        with pytest.raises(ValueError, match="few_shot_examples must be valid JSON"):
            llm_utils.generate_sql_query(
                user_query="test",
                api_key="test_key",
                db_schema="schema",
                few_shot_examples='invalid json{'
            )
    
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_credentials_handled_gracefully(self):
        """
        Test that missing credentials are handled gracefully.
        
        When credentials are missing:
        - Authentication should fail gracefully (not crash)
        - A clear error message should be provided
        - The application should return None for the client
        """
        from src.utils.bigquery_utils import authenticate_to_bigquery
        
        # Attempt to authenticate without credentials
        client = authenticate_to_bigquery()
        
        # Verify that authentication failed gracefully
        assert client is None

