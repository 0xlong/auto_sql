from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import re


def clean_sql_response(response: str) -> str:
    """
    Removes markdown code block markers from SQL response.
    
    LLMs sometimes wrap SQL queries in markdown code blocks like:
    ```sql
    SELECT * FROM table;
    ```
    
    This function strips those markers and returns just the SQL query.
    
    Args:
        response: Raw response string that may contain markdown formatting
        
    Returns:
        Clean SQL query string without markdown code block markers
    """
    # Remove markdown code block markers (```sql, ```SQL, ```, etc.)
    # This regex pattern matches:
    # - Triple backticks (```)
    # - Optional language identifier (sql, SQL, etc.) - case insensitive
    # - Optional whitespace and newline
    # Then captures everything (non-greedy) until the closing triple backticks
    # The pattern uses non-greedy matching (.*?) to capture only the content between markers
    # re.DOTALL flag makes . match newlines too, so multi-line SQL queries work correctly
    
    # Pattern explanation:
    # ```(?:sql|SQL)? - matches opening ``` with optional sql/SQL identifier
    # \s*\n? - matches optional whitespace and optional newline after opening marker
    # (.*?) - captures the SQL content (non-greedy, so it stops at first closing marker)
    # \n?\s*``` - matches optional newline, optional whitespace, and closing ```
    pattern = r'```(?:sql|SQL)?\s*\n?(.*?)\n?\s*```'
    
    # Replace the entire code block with just the captured content
    cleaned = re.sub(pattern, r'\1', response, flags=re.DOTALL)
    
    # Strip any leading/trailing whitespace that might remain
    cleaned = cleaned.strip()
    
    return cleaned


def generate_response(user_query: str, api_key: str, db_schema: str, few_shot_examples: str) -> str:
    """
    Simple LLM generation function using LangChain with prompt template.
    
    Args:
        user_input: The input text from the user
        api_key: Your Google AI API key
        
    Returns:
        Generated response string from the LLM
    """
    # Initialize the LLM model (using Google's Gemini as it's free and simple)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
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
    
    # Clean the response to remove any markdown code block markers
    # This is a safety measure in case the LLM still includes them despite the prompt instructions
    cleaned_response = clean_sql_response(response.content)
    
    return response.content
