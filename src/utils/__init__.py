"""
Utils Package - Utility modules for BigQuery and LLM operations.

This package provides two main utility modules:
1. bigquery_utils - Functions for BigQuery authentication and query analysis
2. llm_utils - Functions for LLM-based SQL generation and AI responses

Package-level exports allow convenient imports like:
    from src.utils import authenticate_to_bigquery, generate_sql_query
    
Instead of:
    from src.utils.bigquery_utils import authenticate_to_bigquery
    from src.utils.llm_utils import generate_sql_query
"""

# Import key functions from bigquery_utils module
# These handle BigQuery authentication and query execution details
from .bigquery_utils import (
    authenticate_to_bigquery,  # Authenticates and creates BigQuery client
    bigquery_sqlrun_details    # Analyzes and logs query job execution details
)

# Import key functions from llm_utils module
# These handle LLM-based SQL generation and AI answer generation
from .llm_utils import (
    generate_sql_query,        # Converts natural language to SQL using LLM
    generate_ai_answer,        # Generates natural language summary of query results
    save_successful_query      # Saves successful queries as few-shot examples
)

# Define what gets exported when someone does "from src.utils import *"
# This is explicit control over the public API of this package
# Only these names will be available with wildcard imports
__all__ = [
    # BigQuery utilities
    'authenticate_to_bigquery',
    'bigquery_sqlrun_details',
    
    # LLM utilities  
    'generate_sql_query',
    'generate_ai_answer',
    'save_successful_query'
]

