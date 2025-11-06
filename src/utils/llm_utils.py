from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import re
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def generate_sql_query(user_query: str, api_key: str, db_schema: str, few_shot_examples: str) -> str:
    """
    Simple LLM generation function using LangChain with prompt template.
    
    Args:
        user_query: The input text from the user
        api_key: Your Google AI API key
        
    Returns:
        Generated response string from the LLM
    """
    # Initialize the LLM model (using Google's Gemini as it's free and simple)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=api_key,
        temperature=0.5  # Controls randomness (0=deterministic, 1=creative)
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
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.5
    )
    
    prompt = """
    You are a crypto data analyst. You have experience and knowledge in blockchain data analysis.
    You are given a user query and a results dataframe. You need to summarize results take into account user query and results.
    User query: {user_query}
    Results: {results_df}
    The answer should be in a natural language format. 
    Be specific and to the point.
    Do not present data from result_df in the answer.
    Use markdown formatting for tables and lists."""

    prompt_template = PromptTemplate(
        input_variables=["user_query", "results_df"],
        template=prompt
    )
    
    chain = prompt_template | llm
    
    response = chain.invoke({"user_query": user_query, "results_df": results_df})
    
    return response.content

