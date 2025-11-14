"""
Unit tests for llm_utils.py module

These tests verify the LLM utility functions including:
- SQL query generation
- AI answer generation
- Successful query saving

All LLM calls are mocked to avoid actual API calls during testing.
"""

import pytest
import json
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


class TestGenerateSQLQuery:
    """Test the generate_sql_query function"""
    
    def test_generate_sql_query_with_valid_inputs(self, mocker):
        """
        Test that generate_sql_query works correctly with valid inputs.
        
        This test:
        1. Mocks the LangChain LLM to avoid actual API calls
        2. Provides valid input parameters
        3. Verifies that the function returns the expected SQL query
        
        Why mock the LLM:
        - Avoids actual API calls (faster tests, no API costs)
        - Makes tests deterministic (same output every time)
        - Allows testing without API credentials
        """
        from src.utils import llm_utils
        
        # Mock the ChatGoogleGenerativeAI class to avoid real API calls
        # mocker.patch replaces the real class with a mock during this test
        mock_llm = mocker.patch('src.utils.llm_utils.ChatGoogleGenerativeAI')
        
        # Create a mock response object that mimics the real LLM response
        # The mock response has a 'content' attribute with our test SQL
        mock_response = MagicMock()
        mock_response.content = "SELECT * FROM table"
        
        # Configure the mock LLM instance to return our mock response
        # When the chain's invoke() method is called, it returns mock_response
        mock_llm_instance = mock_llm.return_value
        
        # Mock the chain's invoke method directly
        # We need to mock the chain because LangChain uses the pipe operator
        mocker.patch('src.utils.llm_utils.PromptTemplate.__or__', 
                    return_value=MagicMock(invoke=MagicMock(return_value=mock_response)))
        
        # Call the function with valid test inputs
        result = llm_utils.generate_sql_query(
            user_query="Show me transactions",
            api_key="test_api_key",
            db_schema="table1: column1, column2",
            few_shot_examples='[{"query": "test"}]'
        )
        
        # Verify that the function returned the mocked SQL query
        assert result == "SELECT * FROM table"
    
    def test_generate_sql_query_raises_error_for_none_user_query(self):
        """
        Test that generate_sql_query raises ValueError when user_query is None.
        
        Why test None values:
        - Ensures the function validates inputs before processing
        - Prevents cryptic errors from being passed to downstream code
        - Documents the expected behavior for invalid inputs
        """
        from src.utils import llm_utils
        
        # Attempt to call the function with None user_query
        # This should raise a ValueError with a descriptive message
        with pytest.raises(ValueError, match="user_query parameter cannot be None"):
            llm_utils.generate_sql_query(
                user_query=None,
                api_key="test_key",
                db_schema="schema",
                few_shot_examples='[]'
            )
    
    def test_generate_sql_query_raises_error_for_empty_user_query(self):
        """
        Test that generate_sql_query raises ValueError when user_query is empty.
        
        An empty string (or whitespace-only) is not a valid query.
        The function should detect this early and raise a clear error.
        """
        from src.utils import llm_utils
        
        # Test with empty string
        with pytest.raises(ValueError, match="user_query cannot be empty"):
            llm_utils.generate_sql_query(
                user_query="",
                api_key="test_key",
                db_schema="schema",
                few_shot_examples='[]'
            )
        
        # Test with whitespace-only string
        with pytest.raises(ValueError, match="user_query cannot be empty"):
            llm_utils.generate_sql_query(
                user_query="   ",
                api_key="test_key",
                db_schema="schema",
                few_shot_examples='[]'
            )
    
    def test_generate_sql_query_raises_error_for_none_api_key(self):
        """
        Test that generate_sql_query raises ValueError when api_key is None.
        
        An API key is required to authenticate with the LLM service.
        The function should validate this before attempting to create the LLM client.
        """
        from src.utils import llm_utils
        
        with pytest.raises(ValueError, match="api_key parameter cannot be None"):
            llm_utils.generate_sql_query(
                user_query="test query",
                api_key=None,
                db_schema="schema",
                few_shot_examples='[]'
            )
    
    def test_generate_sql_query_raises_error_for_empty_api_key(self):
        """
        Test that generate_sql_query raises ValueError when api_key is empty.
        """
        from src.utils import llm_utils
        
        with pytest.raises(ValueError, match="api_key cannot be empty"):
            llm_utils.generate_sql_query(
                user_query="test query",
                api_key="",
                db_schema="schema",
                few_shot_examples='[]'
            )
    
    def test_generate_sql_query_raises_error_for_invalid_json_few_shots(self):
        """
        Test that generate_sql_query raises ValueError when few_shot_examples is invalid JSON.
        
        The few_shot_examples parameter must be valid JSON because it's used
        in the prompt template. Invalid JSON would cause errors during processing.
        
        Why validate JSON early:
        - Provides clear error messages to developers
        - Prevents cryptic JSON parsing errors later in the pipeline
        - Ensures data integrity before expensive LLM calls
        """
        from src.utils import llm_utils
        
        # Test with invalid JSON (missing closing bracket)
        with pytest.raises(ValueError, match="few_shot_examples must be valid JSON"):
            llm_utils.generate_sql_query(
                user_query="test query",
                api_key="test_key",
                db_schema="schema",
                few_shot_examples='[{"query": "test"'  # Invalid JSON
            )
    
    def test_generate_sql_query_raises_error_for_excessively_long_query(self):
        """
        Test that generate_sql_query raises ValueError when user_query exceeds maximum length.
        
        Excessively long queries can:
        - Cause performance issues
        - Exceed LLM token limits
        - Indicate a problem with the user input
        
        The function enforces a reasonable maximum length (5000 characters).
        """
        from src.utils import llm_utils
        
        # Create a query that exceeds the maximum length (5000 characters)
        long_query = "a" * 5001
        
        with pytest.raises(ValueError, match="user_query exceeds maximum length"):
            llm_utils.generate_sql_query(
                user_query=long_query,
                api_key="test_key",
                db_schema="schema",
                few_shot_examples='[]'
            )


class TestGenerateAIAnswer:
    """Test the generate_ai_answer function"""
    
    def test_generate_ai_answer_with_valid_inputs(self, mocker):
        """
        Test that generate_ai_answer works correctly with valid inputs.
        
        This function takes query results and generates a natural language summary.
        We mock the LLM to avoid actual API calls while testing the logic.
        """
        from src.utils import llm_utils
        
        # Mock the LLM to avoid real API calls
        mock_llm = mocker.patch('src.utils.llm_utils.ChatGoogleGenerativeAI')
        
        # Create a mock response with a test summary
        mock_response = MagicMock()
        mock_response.content = "The results show 10 transactions"
        
        # Configure the mock to return our response
        mocker.patch('src.utils.llm_utils.PromptTemplate.__or__', 
                    return_value=MagicMock(invoke=MagicMock(return_value=mock_response)))
        
        # Create a test DataFrame with sample data
        # This simulates the results from a BigQuery query
        test_df = pd.DataFrame({
            'transaction_id': [1, 2, 3],
            'amount': [100, 200, 300]
        })
        
        # Call the function with valid inputs
        result = llm_utils.generate_ai_answer(
            user_query="Show me transactions",
            results_df=test_df,
            api_key="test_api_key"
        )
        
        # Verify that the function returned the mocked summary
        assert result == "The results show 10 transactions"
    
    def test_generate_ai_answer_raises_error_for_none_user_query(self):
        """
        Test that generate_ai_answer raises ValueError when user_query is None.
        """
        from src.utils import llm_utils
        
        test_df = pd.DataFrame({'col': [1, 2, 3]})
        
        with pytest.raises(ValueError, match="user_query parameter cannot be None"):
            llm_utils.generate_ai_answer(
                user_query=None,
                results_df=test_df,
                api_key="test_key"
            )
    
    def test_generate_ai_answer_raises_error_for_none_dataframe(self):
        """
        Test that generate_ai_answer raises ValueError when results_df is None.
        """
        from src.utils import llm_utils
        
        with pytest.raises(ValueError, match="results_df parameter cannot be None"):
            llm_utils.generate_ai_answer(
                user_query="test query",
                results_df=None,
                api_key="test_key"
            )
    
    def test_generate_ai_answer_raises_error_for_invalid_dataframe_type(self):
        """
        Test that generate_ai_answer raises TypeError when results_df is not a DataFrame.
        
        The function expects a pandas DataFrame specifically.
        Passing other types (list, dict, etc.) should raise a clear error.
        """
        from src.utils import llm_utils
        
        # Test with a list instead of DataFrame
        with pytest.raises(TypeError, match="results_df must be a pandas DataFrame"):
            llm_utils.generate_ai_answer(
                user_query="test query",
                results_df=[1, 2, 3],  # Not a DataFrame
                api_key="test_key"
            )
    
    def test_generate_ai_answer_raises_error_for_empty_dataframe(self):
        """
        Test that generate_ai_answer raises ValueError when results_df is empty.
        
        An empty DataFrame has no data to summarize.
        The function should detect this and raise a clear error.
        """
        from src.utils import llm_utils
        
        # Create an empty DataFrame (no rows)
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="results_df cannot be an empty DataFrame"):
            llm_utils.generate_ai_answer(
                user_query="test query",
                results_df=empty_df,
                api_key="test_key"
            )


class TestSaveSuccessfulQuery:
    """Test the save_successful_query function"""
    
    def test_save_successful_query_with_valid_inputs(self, mocker, tmp_path):
        """
        Test that save_successful_query correctly saves a query to the JSON file.
        
        This test:
        1. Creates a temporary JSON file with existing data
        2. Calls the function to add a new query
        3. Verifies the new query was appended to the file
        4. Checks that the JSON structure is correct
        
        Why use tmp_path:
        - pytest provides tmp_path fixture for temporary test files
        - Avoids modifying actual project files during tests
        - Automatically cleaned up after test completes
        """
        from src.utils import llm_utils
        
        # Create a temporary JSON file to simulate the few-shot examples file
        test_file = tmp_path / "test_fewshots.json"
        
        # Start with an existing query in the file
        existing_data = [
            {
                "query_name": "existing query",
                "query_sql": "SELECT 1",
                "expected_result": {"columns": ["col1"], "rows": [["val1"]], "notes": "test"}
            }
        ]
        
        # Write the existing data to the test file
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f)
        
        # Mock the FEWSHOT_FILE config to use our test file
        mocker.patch('src.utils.llm_utils.FEWSHOT_FILE', test_file)
        
        # Create a test DataFrame with sample results
        test_df = pd.DataFrame({
            'transaction_id': [1, 2, 3],
            'amount': [100, 200, 300]
        })
        
        # Call the function to save a new query
        llm_utils.save_successful_query(
            query_name="new query",
            query_sql="SELECT * FROM transactions",
            expected_result=test_df,
            notes="This is a test query"
        )
        
        # Read the file to verify the new query was added
        with open(test_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        # Verify that we now have 2 queries (original + new)
        assert len(saved_data) == 2
        
        # Verify the new query was added correctly
        new_query = saved_data[1]
        assert new_query['query_name'] == "new query"
        assert new_query['query_sql'] == "SELECT * FROM transactions"
        assert new_query['expected_result']['notes'] == "This is a test query"
        
        # Verify the columns and rows were saved correctly
        assert new_query['expected_result']['columns'] == ['transaction_id', 'amount']
        assert len(new_query['expected_result']['rows']) == 3
    
    def test_save_successful_query_prevents_duplicates(self, mocker, tmp_path):
        """
        Test that save_successful_query does not save duplicate queries.
        
        If a query with the same name already exists, the function should:
        1. Detect the duplicate
        2. Skip saving (return early)
        3. Log an informational message
        
        Why prevent duplicates:
        - Avoids polluting the few-shot examples file
        - Prevents the same query from being added multiple times
        - Maintains data quality in the examples file
        """
        from src.utils import llm_utils
        
        # Create a temporary JSON file with an existing query
        test_file = tmp_path / "test_fewshots.json"
        
        existing_data = [
            {
                "query_name": "duplicate query",
                "query_sql": "SELECT 1",
                "expected_result": {"columns": ["col1"], "rows": [["val1"]], "notes": "test"}
            }
        ]
        
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f)
        
        # Mock the FEWSHOT_FILE config
        mocker.patch('src.utils.llm_utils.FEWSHOT_FILE', test_file)
        
        # Create a test DataFrame
        test_df = pd.DataFrame({'col': [1, 2, 3]})
        
        # Try to save a query with the same name
        llm_utils.save_successful_query(
            query_name="duplicate query",  # Same name as existing
            query_sql="SELECT 2",  # Different SQL
            expected_result=test_df,
            notes="This should not be saved"
        )
        
        # Read the file to verify no duplicate was added
        with open(test_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        # Verify that we still have only 1 query (no duplicate added)
        assert len(saved_data) == 1
        
        # Verify the original query is unchanged
        assert saved_data[0]['query_name'] == "duplicate query"
        assert saved_data[0]['query_sql'] == "SELECT 1"  # Original SQL unchanged
    
    def test_save_successful_query_raises_error_for_none_inputs(self):
        """
        Test that save_successful_query raises ValueError for None inputs.
        
        All parameters are required for saving a query.
        The function should validate this before attempting file operations.
        """
        from src.utils import llm_utils
        
        test_df = pd.DataFrame({'col': [1]})
        
        # Test None query_name
        with pytest.raises(ValueError, match="query_name parameter cannot be None"):
            llm_utils.save_successful_query(
                query_name=None,
                query_sql="SELECT 1",
                expected_result=test_df,
                notes="test"
            )
        
        # Test None query_sql
        with pytest.raises(ValueError, match="query_sql parameter cannot be None"):
            llm_utils.save_successful_query(
                query_name="test",
                query_sql=None,
                expected_result=test_df,
                notes="test"
            )
        
        # Test None expected_result
        with pytest.raises(ValueError, match="expected_result parameter cannot be None"):
            llm_utils.save_successful_query(
                query_name="test",
                query_sql="SELECT 1",
                expected_result=None,
                notes="test"
            )
        
        # Test None notes
        with pytest.raises(ValueError, match="notes parameter cannot be None"):
            llm_utils.save_successful_query(
                query_name="test",
                query_sql="SELECT 1",
                expected_result=test_df,
                notes=None
            )
    
    def test_save_successful_query_raises_error_for_empty_dataframe(self):
        """
        Test that save_successful_query raises ValueError for empty DataFrame.
        
        An empty DataFrame has no data to save as an example.
        This should be caught and reported clearly.
        """
        from src.utils import llm_utils
        
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="expected_result cannot be an empty DataFrame"):
            llm_utils.save_successful_query(
                query_name="test",
                query_sql="SELECT 1",
                expected_result=empty_df,
                notes="test"
            )

