import json
import logging
from typing import Any

import pandas as pd
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from config import FEWSHOT_FILE

# Create logger for llm_utils information
logger = logging.getLogger(__name__)


def generate_sql_query(
    user_query: str, 
    api_key: str, 
    db_schema: str, 
    few_shot_examples: str
) -> str:
    """
    Simple LLM generation function using LangChain with prompt template.
    
    Args:
        user_query (str): The natural language input text from the user
        api_key (str): Your Google AI API key for authentication
        db_schema (str): The database schema definition (tables, columns, types)
        few_shot_examples (str): JSON string containing example queries for context
        
    Returns:
        str: Generated SQL query string from the LLM
        
    Raises:
        ValueError: If any required parameter is None, empty, or invalid
        json.JSONDecodeError: If few_shot_examples is not valid JSON
    """
    # ========== INPUT VALIDATION ==========
    # Validate that all required parameters are provided and not None
    # This prevents cryptic errors later in the function execution
    if user_query is None:
        raise ValueError("user_query parameter cannot be None")
    if api_key is None:
        raise ValueError("api_key parameter cannot be None")
    if db_schema is None:
        raise ValueError("db_schema parameter cannot be None")
    if few_shot_examples is None:
        raise ValueError("few_shot_examples parameter cannot be None")
    
    # Validate that string parameters are not empty or just whitespace
    # strip() removes leading/trailing whitespace, then we check if anything remains
    if not user_query.strip():
        raise ValueError("user_query cannot be empty or contain only whitespace")
    if not api_key.strip():
        raise ValueError("api_key cannot be empty or contain only whitespace")
    if not db_schema.strip():
        raise ValueError("db_schema cannot be empty or contain only whitespace")
    if not few_shot_examples.strip():
        raise ValueError("few_shot_examples cannot be empty or contain only whitespace")
    
    # Validate that few_shot_examples is valid JSON
    # This catches malformed JSON early before it causes issues in the prompt
    try:
        # Attempt to parse the JSON string to verify it's valid
        json.loads(few_shot_examples)
    except json.JSONDecodeError as e:
        # If JSON parsing fails, raise a descriptive error with details
        raise ValueError(f"few_shot_examples must be valid JSON string. Error: {str(e)}")
    
    # Additional validation: Check that user_query has reasonable length
    # Prevents excessively long queries that could cause performance issues
    MAX_QUERY_LENGTH = 5000  # Maximum characters allowed in user query
    if len(user_query) > MAX_QUERY_LENGTH:
        raise ValueError(f"user_query exceeds maximum length of {MAX_QUERY_LENGTH} characters")
    
    # Additional validation: Check that db_schema has reasonable length
    MAX_SCHEMA_LENGTH = 100000  # Maximum characters allowed in schema
    if len(db_schema) > MAX_SCHEMA_LENGTH:
        raise ValueError(f"db_schema exceeds maximum length of {MAX_SCHEMA_LENGTH} characters")
    
    # Log successful validation for debugging and monitoring
    logger.debug(f"Input validation passed for user_query: '{user_query[:50]}...'")
    # ========== END INPUT VALIDATION ==========
    
    # Create a new LLM instance for generating the SQL query
    # Model: gemini-2.5-flash-lite - Fast and efficient for SQL generation
    # Temperature: 0.5 - Balanced between deterministic and creative responses
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=api_key,
        temperature=0.5
    )
    
    # Create a prompt template string with placeholders for LangChain variables
    # We use a raw string here (not an f-string) to avoid Python interpreting the curly braces
    # LangChain's PromptTemplate will handle the variable substitution
    # The curly braces {db_schema}, {few_shot_examples}, {user_query} are LangChain template variables
    prompt = """
    You are a crypto data analyst. You have experience and knowledge in blockchain data analysis and you are expert in BigQuery SQL.
    You are given a database schema and a user query. You need to generate a SQL query that will answer the user query.
    The SQL query should be in BigQuery SQL syntax.
    The SQL query should be efficient and will not take too long to execute.
    The SQL query should be secure and will not expose any sensitive data.
    The SQL query should be optimized for the database schema.
    The SQL query should be optimized for the user query.
    If user query does not make sense, return an message "Please provide more specific request".
    If user query does not explicitly contain dates, assume the most recent date period that makes sense for the query.
    Add an explicit alias for every selected expression. Never return unnamed columns. Alias cannot be named "hash".
    Access tables or view with bigquery-public-data.goog_blockchain_ethereum_mainnet_us.XXX where XXX is the table or view name.
    TIMESTAMP_SUB function does not directly support subtracting MONTH intervals from a TIMESTAMP.

    IMPORTANT: Return ONLY the SQL query text. Do NOT include markdown code blocks (```sql or ```).
    Do NOT wrap the query in any formatting. Return the raw SQL query only.
    
    Database schema: {db_schema}
    Few shot examples: {few_shot_examples}
    User query: {user_query}
    """
    
    # Create a prompt template with placeholders for user input
    # The {db_schema}, {few_shot_examples}, {user_query} will be replaced with actual values
    # Note: few_shot_examples should have its curly braces escaped (done in app.py) 
    # to prevent LangChain from interpreting JSON structure as template variables
    prompt_template = PromptTemplate(
        input_variables=["db_schema", "few_shot_examples", "user_query"],
        template=prompt
    )
    
    # Create a chain by combining prompt template and LLM using the pipe operator
    # This means: prompt_template outputs formatted text → LLM processes it
    chain = prompt_template | llm
    
    # Execute the chain: format prompt with user_input, then generate response
    response = chain.invoke({"db_schema": db_schema, "few_shot_examples": few_shot_examples, "user_query": user_query})

    logger.info(f"Generated SQL query: {response}")

    return response.content


def generate_ai_answer(
    user_query: str, 
    results_df: pd.DataFrame, 
    api_key: str
) -> str:
    """
    Generate an AI answer including user query and query results context.
    
    Args:
        user_query (str): The original natural language query from the user
        results_df (pd.DataFrame): The query results as a pandas DataFrame
        api_key (str): Your Google AI API key for authentication
    
    Returns:
        str: Natural language summary of the query results
        
    Raises:
        ValueError: If any required parameter is None, empty, or invalid
        TypeError: If results_df is not a pandas DataFrame
    """
    # ========== INPUT VALIDATION ==========
    # Validate that all required parameters are provided and not None
    if user_query is None:
        raise ValueError("user_query parameter cannot be None")
    if results_df is None:
        raise ValueError("results_df parameter cannot be None")
    if api_key is None:
        raise ValueError("api_key parameter cannot be None")
    
    # Validate that string parameters are not empty or just whitespace
    if not user_query.strip():
        raise ValueError("user_query cannot be empty or contain only whitespace")
    if not api_key.strip():
        raise ValueError("api_key cannot be empty or contain only whitespace")
    
    # Validate that results_df is actually a pandas DataFrame
    # Using isinstance() to ensure type safety
    if not isinstance(results_df, pd.DataFrame):
        raise TypeError(f"results_df must be a pandas DataFrame, got {type(results_df).__name__}")
    
    # Validate that the DataFrame is not empty
    # An empty DataFrame would not provide meaningful context for the AI
    if results_df.empty:
        raise ValueError("results_df cannot be an empty DataFrame")
    
    # Additional validation: Check that user_query has reasonable length
    MAX_QUERY_LENGTH = 5000  # Maximum characters allowed in user query
    if len(user_query) > MAX_QUERY_LENGTH:
        raise ValueError(f"user_query exceeds maximum length of {MAX_QUERY_LENGTH} characters")
    
    # Log successful validation for debugging
    logger.debug(f"Input validation passed for generate_ai_answer function")
    # ========== END INPUT VALIDATION ==========
    
    # Create a new LLM instance for generating the natural language answer
    # Model: gemini-2.5-flash-lite - Fast and efficient for text summarization
    # Temperature: 0.5 - Balanced between deterministic and creative responses
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=api_key,
        temperature=0.5
    )
    
    prompt = """
    You are a crypto data analyst. You have experience and domain knowledge in blockchain data analysis.
    You are given a user query and a results dataframe. You need to summarize results take into account user query and results.
    User query: {user_query}
    Results: {results_df}
    The answer should be in a natural language format. 
    No introduction sentence.
    Be specific and to the point.
    Do not rewrite results, but summarize them in a natural language format. Add some insights and observations based on the results if possible.
    If date was not specified in user query, assume the most recent date period that makes sense for the query and write in answer that date was not specified so latest date period was used.
    """

    prompt_template = PromptTemplate(
        input_variables=["user_query", "results_df"],
        template=prompt
    )
    
    chain = prompt_template | llm
    
    response = chain.invoke({"user_query": user_query, "results_df": results_df})
    
    return response.content

def save_successful_query(
    query_name: str, 
    query_sql: str, 
    expected_result: pd.DataFrame, 
    notes: str
) -> None:
    """
    Save successful query as example in eth_mainnet_sql_fewshots.json file.
    
    Args:
        query_name (str): Descriptive name for the query (user's natural language query)
        query_sql (str): The SQL query that was successfully executed
        expected_result (pd.DataFrame): DataFrame containing the query results (first 5 rows saved)
        notes (str): Additional notes or context about the query (AI-generated summary)
    
    Returns:
        None: This function saves to file and does not return a value
        
    Raises:
        ValueError: If any required parameter is None, empty, or invalid
        TypeError: If expected_result is not a pandas DataFrame
    """
    # ========== INPUT VALIDATION ==========
    # Validate that all required parameters are provided and not None
    if query_name is None:
        raise ValueError("query_name parameter cannot be None")
    if query_sql is None:
        raise ValueError("query_sql parameter cannot be None")
    if expected_result is None:
        raise ValueError("expected_result parameter cannot be None")
    if notes is None:
        raise ValueError("notes parameter cannot be None")
    
    # Validate that string parameters are not empty or just whitespace
    if not query_name.strip():
        raise ValueError("query_name cannot be empty or contain only whitespace")
    if not query_sql.strip():
        raise ValueError("query_sql cannot be empty or contain only whitespace")
    if not notes.strip():
        raise ValueError("notes cannot be empty or contain only whitespace")
    
    # Validate that expected_result is actually a pandas DataFrame
    if not isinstance(expected_result, pd.DataFrame):
        raise TypeError(f"expected_result must be a pandas DataFrame, got {type(expected_result).__name__}")
    
    # Validate that the DataFrame is not empty
    # We need at least some data to save as an example
    if expected_result.empty:
        raise ValueError("expected_result cannot be an empty DataFrame")
    
    # Validate that the DataFrame has at least one column
    # A DataFrame without columns wouldn't be a meaningful example
    if len(expected_result.columns) == 0:
        raise ValueError("expected_result must have at least one column")
    
    # Additional validation: Check string lengths to prevent unreasonably large data
    MAX_NAME_LENGTH = 500  # Maximum characters for query name
    MAX_SQL_LENGTH = 50000  # Maximum characters for SQL query
    MAX_NOTES_LENGTH = 5000  # Maximum characters for notes
    
    if len(query_name) > MAX_NAME_LENGTH:
        raise ValueError(f"query_name exceeds maximum length of {MAX_NAME_LENGTH} characters")
    if len(query_sql) > MAX_SQL_LENGTH:
        raise ValueError(f"query_sql exceeds maximum length of {MAX_SQL_LENGTH} characters")
    if len(notes) > MAX_NOTES_LENGTH:
        raise ValueError(f"notes exceeds maximum length of {MAX_NOTES_LENGTH} characters")
    
    # Log successful validation
    logger.debug(f"Input validation passed for save_successful_query: '{query_name}'")
    # ========== END INPUT VALIDATION ==========
    
    logger.info(f"Saving successful query: {query_name} to eth_mainnet_sql_fewshots.json file")

    # load few shot examples from the centralized config path so every module reads the same source
    with FEWSHOT_FILE.open("r", encoding="utf-8") as file:
        few_shot_examples = json.load(file)
    
    # check if query already in examples
    if any(example["query_name"] == query_name for example in few_shot_examples):
        logger.info(f"Query {query_name} already exists in few shot examples. Skipping save.")
        return  # Return early to prevent duplicate from being appended

    # Get column names as a list of strings
    columns = expected_result.columns.tolist()
    
    # Convert DataFrame rows to list of lists with native Python types
    rows = expected_result.head(5).astype(str).values.tolist()
    
    # add new query to few shot examples
    few_shot_examples.append({
        "query_name": query_name,
        "query_sql": query_sql,
        "expected_result": {
            "columns": columns, 
            "rows": rows,
            "notes": notes
        }
    })
    
    # save few shot examples to file with indentation for readability
    with FEWSHOT_FILE.open("w", encoding="utf-8") as file:
        json.dump(few_shot_examples, file, indent=4, ensure_ascii=False)
    
    logger.info(f"Saved successful query: {query_name} to eth_mainnet_sql_fewshots.json file")