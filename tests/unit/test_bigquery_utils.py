"""
Unit tests for bigquery_utils.py module

These tests verify the BigQuery utility functions including:
- Authentication to BigQuery
- Query job details extraction and logging

All BigQuery client calls are mocked to avoid actual cloud connections.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, call
from datetime import datetime


class TestAuthenticateToBigQuery:
    """Test the authenticate_to_bigquery function"""
    
    @patch.dict('os.environ', {
        'GOOGLE_BIGQUERY_CREDENTIALS': json.dumps({
            "type": "service_account",
            "project_id": "test-project-123",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        })
    })
    def test_authenticate_to_bigquery_success(self):
        """
        Test successful authentication to BigQuery.
        
        This test:
        1. Mocks the environment variable with valid credentials JSON
        2. Mocks the Google Cloud authentication and client creation
        3. Calls the authenticate_to_bigquery function
        4. Verifies that authentication succeeds and returns a client
        
        Why mock the entire authentication flow:
        - Avoids requiring actual GCP credentials for testing
        - Tests the function logic without external dependencies
        - Makes tests fast and deterministic
        """
        # Mock the service account credentials and BigQuery Client before importing
        # We patch at the location where they're used (in the imported module)
        with patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_credentials, \
             patch('google.cloud.bigquery.Client') as mock_client:
            
            # Import after patching to ensure mocks are in place
            from src.utils.bigquery_utils import authenticate_to_bigquery
            
            # Create a mock BigQuery client that will be returned
            mock_client_instance = MagicMock()
            mock_client_instance.project = "test-project-123"
            mock_client.return_value = mock_client_instance
            
            # Create mock credentials
            mock_creds = MagicMock()
            mock_credentials.return_value = mock_creds
            
            # Call the function
            result = authenticate_to_bigquery()
            
            # Verify that a client was returned
            assert result is not None
            assert result == mock_client_instance
            
            # Verify that the credentials were loaded correctly
            # from_service_account_info should be called with the credentials dict
            mock_credentials.assert_called_once()
            
            # Verify that the BigQuery client was created with correct parameters
            # The function uses project_id from the credentials dict
            mock_client.assert_called_once()
            # Check that credentials and project_id were passed
            call_args = mock_client.call_args
            assert call_args[1]['credentials'] == mock_creds
            assert call_args[1]['project'] == "test-project-123"
    
    @patch.dict('os.environ', {}, clear=True)
    def test_authenticate_to_bigquery_missing_env_variable(self):
        """
        Test authentication fails when GOOGLE_BIGQUERY_CREDENTIALS is not set.
        
        When the environment variable is missing:
        - The function should detect this early
        - Return None instead of crashing
        - Log an error message explaining the issue
        
        Why this test is important:
        - Ensures graceful failure when credentials are missing
        - Provides clear error feedback to developers
        - Prevents cryptic errors from propagating
        """
        # Import after mocking to avoid import errors
        from src.utils.bigquery_utils import authenticate_to_bigquery
        
        # Call the function with no environment variable set
        result = authenticate_to_bigquery()
        
        # Verify that the function returns None (authentication failed)
        assert result is None
    
    @patch.dict('os.environ', {
        'GOOGLE_BIGQUERY_CREDENTIALS': 'invalid json{{'  # Invalid JSON
    })
    def test_authenticate_to_bigquery_invalid_json(self):
        """
        Test authentication fails when credentials JSON is malformed.
        
        If the JSON is invalid (missing quotes, extra commas, etc.):
        - json.loads() will raise JSONDecodeError
        - The function should catch this exception
        - Return None with an appropriate error message
        
        Why catch JSON errors:
        - Provides clear feedback about what went wrong
        - Prevents the app from crashing on startup
        - Helps developers debug credential issues quickly
        """
        # Import after mocking to avoid import errors
        from src.utils.bigquery_utils import authenticate_to_bigquery
        
        # Call the function with invalid JSON in environment variable
        result = authenticate_to_bigquery()
        
        # Verify that the function returns None (authentication failed)
        assert result is None
    
    @patch.dict('os.environ', {
        'GOOGLE_BIGQUERY_CREDENTIALS': json.dumps({
            "type": "service_account",
            "project_id": "test-project"
        })
    })
    def test_authenticate_to_bigquery_authentication_error(self):
        """
        Test authentication fails when Google Cloud SDK raises an exception.
        
        Even with valid JSON, authentication can fail due to:
        - Invalid credentials
        - Network issues
        - Insufficient permissions
        - Expired credentials
        
        The function should catch these errors and return None gracefully.
        """
        # Mock the credentials to raise an exception
        with patch('google.oauth2.service_account.Credentials.from_service_account_info') as mock_credentials:
            from src.utils.bigquery_utils import authenticate_to_bigquery
            
            # Make the credentials creation raise an exception
            mock_credentials.side_effect = Exception("Authentication failed: Invalid credentials")
            
            # Call the function
            result = authenticate_to_bigquery()
            
            # Verify that the function returns None (caught the exception)
            assert result is None


class TestBigQuerySQLRunDetails:
    """Test the bigquery_sqlrun_details function"""
    
    def test_bigquery_sqlrun_details_successful_query(self, mocker):
        """
        Test that bigquery_sqlrun_details correctly logs information for a successful query.
        
        This test:
        1. Creates a mock QueryJob object with success status
        2. Calls the function to extract and log details
        3. Verifies that all expected information is logged
        
        Why test logging:
        - Ensures developers get visibility into query execution
        - Validates that all important metrics are extracted
        - Documents what information should be logged
        """
        # Import the module first so it exists before patching
        from src.utils import bigquery_utils
        
        # Create a mock QueryJob object representing a successful query
        mock_query_job = MagicMock()
        
        # Set basic job identification
        mock_query_job.job_id = "test-job-123"
        mock_query_job.location = "US"
        mock_query_job.user_email = "test@example.com"
        
        # Set execution status to successful (DONE with no errors)
        mock_query_job.state = "DONE"
        mock_query_job.errors = None  # No errors means success
        
        # Set timing information
        mock_query_job.created = datetime(2024, 1, 1, 10, 0, 0)
        mock_query_job.started = datetime(2024, 1, 1, 10, 0, 5)
        mock_query_job.ended = datetime(2024, 1, 1, 10, 0, 15)
        
        # Set performance statistics
        mock_query_job.total_bytes_processed = 1024 * 1024 * 100  # 100 MB
        mock_query_job.total_bytes_billed = 1024 * 1024 * 100  # 100 MB
        mock_query_job.cache_hit = False
        mock_query_job.slot_millis = 5000
        
        # Set query details
        mock_query_job.query = "SELECT * FROM test_table"
        mock_query_job.destination = "project.dataset.table"
        mock_query_job.priority = "INTERACTIVE"
        
        # Mock the result() method to return query results
        mock_result = MagicMock()
        mock_result.total_rows = 100
        
        # Create mock schema (column definitions)
        mock_field1 = MagicMock()
        mock_field1.name = "id"
        mock_field1.field_type = "INTEGER"
        mock_field1.mode = "REQUIRED"
        
        mock_field2 = MagicMock()
        mock_field2.name = "name"
        mock_field2.field_type = "STRING"
        mock_field2.mode = "NULLABLE"
        
        mock_result.schema = [mock_field1, mock_field2]
        mock_query_job.result.return_value = mock_result
        
        # Mock the logger to capture log calls (patch after import)
        mock_logger = mocker.patch.object(bigquery_utils, 'logger')
        
        # Call the function
        bigquery_utils.bigquery_sqlrun_details(mock_query_job)
        
        # Verify that logging methods were called
        # The function should log job identification, status, timing, statistics, etc.
        assert mock_logger.info.call_count > 0
        
        # Verify specific log messages were created
        # Check that the job ID was logged
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("test-job-123" in str(call) for call in log_calls)
    
    def test_bigquery_sqlrun_details_failed_query(self, mocker):
        """
        Test that bigquery_sqlrun_details correctly logs information for a failed query.
        
        When a query fails:
        - state is "DONE" but errors list is not empty
        - The function should log error details
        - Error count, messages, reasons, and locations should be logged
        """
        # Import the module first so it exists before patching
        from src.utils import bigquery_utils
        
        # Create a mock QueryJob object representing a failed query
        mock_query_job = MagicMock()
        
        # Set basic job identification
        mock_query_job.job_id = "failed-job-456"
        mock_query_job.location = "US"
        mock_query_job.user_email = "test@example.com"
        
        # Set execution status to failed (DONE with errors)
        mock_query_job.state = "DONE"
        mock_query_job.errors = [
            {
                'message': 'Syntax error: Unexpected token SELECT',
                'reason': 'invalidQuery',
                'location': 'line 1, column 5'
            }
        ]
        
        # Set timing information
        mock_query_job.created = datetime(2024, 1, 1, 10, 0, 0)
        mock_query_job.started = datetime(2024, 1, 1, 10, 0, 5)
        mock_query_job.ended = datetime(2024, 1, 1, 10, 0, 6)
        
        # Set performance statistics (even failed queries have some stats)
        mock_query_job.total_bytes_processed = 0
        mock_query_job.total_bytes_billed = 0
        mock_query_job.cache_hit = False
        mock_query_job.slot_millis = 0
        
        # Set query details
        mock_query_job.query = "SELECT * FORM test_table"  # Typo: FORM instead of FROM
        mock_query_job.destination = None
        mock_query_job.priority = "INTERACTIVE"
        
        # Mock the logger to capture log calls (patch after import)
        mock_logger = mocker.patch.object(bigquery_utils, 'logger')
        
        # Call the function
        bigquery_utils.bigquery_sqlrun_details(mock_query_job)
        
        # Verify that error logging was called
        assert mock_logger.error.call_count > 0
        
        # Verify that the error message was logged
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any("Syntax error" in str(call) for call in error_calls)
    
    def test_bigquery_sqlrun_details_pending_query(self, mocker):
        """
        Test that bigquery_sqlrun_details handles queries that are still pending.
        
        When a query is still running:
        - state is "PENDING" or "RUNNING"
        - Results are not yet available
        - The function should log basic info without trying to access results
        """
        # Import the module first so it exists before patching
        from src.utils import bigquery_utils
        
        # Create a mock QueryJob object representing a pending query
        mock_query_job = MagicMock()
        
        # Set basic job identification
        mock_query_job.job_id = "pending-job-789"
        mock_query_job.location = "US"
        mock_query_job.user_email = "test@example.com"
        
        # Set execution status to pending
        mock_query_job.state = "RUNNING"
        mock_query_job.errors = None
        
        # Set partial timing information (not yet completed)
        mock_query_job.created = datetime(2024, 1, 1, 10, 0, 0)
        mock_query_job.started = datetime(2024, 1, 1, 10, 0, 5)
        mock_query_job.ended = None  # Not yet ended
        
        # Set query details
        mock_query_job.query = "SELECT * FROM large_table"
        mock_query_job.destination = None
        mock_query_job.priority = "INTERACTIVE"
        
        # Mock partial statistics
        mock_query_job.total_bytes_processed = None
        mock_query_job.total_bytes_billed = None
        mock_query_job.cache_hit = False
        mock_query_job.slot_millis = None
        
        # Mock the logger to capture log calls (patch after import)
        mock_logger = mocker.patch.object(bigquery_utils, 'logger')
        
        # Call the function
        bigquery_utils.bigquery_sqlrun_details(mock_query_job)
        
        # Verify that the function handled the pending state
        # It should log the status without trying to access results
        assert mock_logger.info.call_count > 0
        
        # Verify that a warning was logged about results not being available
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any("Results not available" in str(call) for call in warning_calls)
    
    def test_bigquery_sqlrun_details_cache_hit(self, mocker):
        """
        Test that bigquery_sqlrun_details correctly identifies cache hits.
        
        When cache_hit is True:
        - Results came from BigQuery's cache
        - No bytes were billed (free!)
        - The function should log this clearly
        
        Why test cache hits:
        - Cache hits save money (no billing)
        - Important for developers to know when caching is working
        - Validates the cost-tracking functionality
        """
        # Import the module first so it exists before patching
        from src.utils import bigquery_utils
        
        # Create a mock QueryJob with a cache hit
        mock_query_job = MagicMock()
        
        mock_query_job.job_id = "cached-job-999"
        mock_query_job.location = "US"
        mock_query_job.user_email = "test@example.com"
        mock_query_job.state = "DONE"
        mock_query_job.errors = None
        
        # Cache hit means results came from cache (free!)
        mock_query_job.cache_hit = True
        mock_query_job.total_bytes_processed = 0
        mock_query_job.total_bytes_billed = 0  # No billing for cache hits
        
        mock_query_job.created = datetime(2024, 1, 1, 10, 0, 0)
        mock_query_job.started = datetime(2024, 1, 1, 10, 0, 1)
        mock_query_job.ended = datetime(2024, 1, 1, 10, 0, 2)
        mock_query_job.slot_millis = 0
        
        mock_query_job.query = "SELECT * FROM test_table"
        mock_query_job.destination = None
        mock_query_job.priority = "INTERACTIVE"
        
        # Mock result
        mock_result = MagicMock()
        mock_result.total_rows = 50
        mock_result.schema = []
        mock_query_job.result.return_value = mock_result
        
        # Mock the logger (patch after import)
        mock_logger = mocker.patch.object(bigquery_utils, 'logger')
        
        # Call the function
        bigquery_utils.bigquery_sqlrun_details(mock_query_job)
        
        # Verify that the cache hit was logged
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Yes" in str(call) and "Free" in str(call) for call in info_calls)

