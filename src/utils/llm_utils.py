from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import os
import json
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Get the absolute path to the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cache for LLM instances to avoid recreating them on every function call
# Dictionary structure: {(model_name, api_key): llm_instance}
# This prevents unnecessary initialization overhead and maintains connection pools
# The cache persists for the lifetime of the Python process (across all Streamlit reruns)
_llm_cache = {}


def _get_llm_instance(model: str, api_key: str, temperature: float) -> ChatGoogleGenerativeAI:
    """
    Get or create a cached LLM instance to avoid recreating clients on every call.
    
    This function implements a simple caching strategy:
    - First call: Creates a new LLM instance and stores it in the cache
    - Subsequent calls: Returns the existing instance from cache
    
    Why this matters:
    - Creating LLM instances has initialization overhead (authentication, config setup)
    - Reusing instances is more efficient and maintains connection pools
    - The cache key uses (model, api_key) to handle different models/credentials
    
    Args:
        model: The model name (e.g., "gemini-2.5-flash-lite")
        api_key: Your Google AI API key
        temperature: Controls randomness (0=deterministic, 1=creative)
        
    Returns:
        ChatGoogleGenerativeAI: Cached or newly created LLM instance
    """
    # Create a cache key based on model and API key to uniquely identify this LLM configuration
    # Temperature is not included in the key as it's typically consistent per model
    cache_key = (model, api_key)
    
    # Check if we already have an instance for this configuration
    if cache_key not in _llm_cache:
        # Cache miss: Create a new LLM instance and store it in the cache
        logger.info(f"Creating new LLM instance for model: {model}")
        _llm_cache[cache_key] = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature
        )
    else:
        # Cache hit: Reuse the existing instance
        logger.debug(f"Reusing cached LLM instance for model: {model}")
    
    return _llm_cache[cache_key]


def generate_sql_query(user_query: str, api_key: str, db_schema: str, few_shot_examples: str) -> str:
    """
    Simple LLM generation function using LangChain with prompt template.
    
    Args:
        user_query: The input text from the user
        api_key: Your Google AI API key
        
    Returns:
        Generated response string from the LLM
    """
    # Get or create a cached LLM instance instead of creating a new one every time
    # This reuses the same client across multiple function calls for better performance
    llm = _get_llm_instance(
        model="gemini-2.5-flash-lite",
        api_key=api_key,
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
    If user query does not make sense, return an message "Please provide a more specific query".
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


def generate_ai_answer(user_query: str, results_df: pd.DataFrame, api_key: str) -> str:
    """
    Generate an AI answer including user query and query results context.
    """
    # Get or create a cached LLM instance to avoid recreating the client
    # This uses the same caching mechanism as generate_sql_query for consistency
    llm = _get_llm_instance(
        model="gemini-2.5-flash",
        api_key=api_key,
        temperature=0.5
    )
    
    prompt = """
    You are a crypto data analyst. You have experience and knowledge in blockchain data analysis.
    You are given a user query and a results dataframe. You need to summarize results take into account user query and results.
    User query: {user_query}
    Results: {results_df}
    The answer should be in a natural language format. 
    No introduction sentence.
    Be specific and to the point.
    If date was not specified in user query, assume the most recent date period that makes sense for the query and write in answer that date was not specified so latest date period was used.
    """

    prompt_template = PromptTemplate(
        input_variables=["user_query", "results_df"],
        template=prompt
    )
    
    chain = prompt_template | llm
    
    response = chain.invoke({"user_query": user_query, "results_df": results_df})
    
    return response.content

def save_successful_query(query_name: str, query_sql: str, expected_result: pd.DataFrame, notes: str) -> str:
    """
    Save successful query as example in eth_mainnet_sql_fewshots.json file
    """
    logger.info(f"Saving successful query: {query_name} to eth_mainnet_sql_fewshots.json file")

    # load few shot examples from file
    with open(os.path.join(PROJECT_ROOT, "data", "prompt", "eth_mainnet_sql_fewshots.json"), "r") as file:
        few_shot_examples = json.load(file)
    
    # check if query already in examples
    if any(example["query_name"] == query_name for example in few_shot_examples):
        logger.info(f"Query {query_name} already exists in few shot examples. Skipping save.")

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
    with open(os.path.join(PROJECT_ROOT, "data", "prompt", "eth_mainnet_sql_fewshots.json"), "w", encoding="utf-8") as file:
        json.dump(few_shot_examples, file, indent=4, ensure_ascii=False)
    
    logger.info(f"Saved successful query: {query_name} to eth_mainnet_sql_fewshots.json file")