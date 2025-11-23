import streamlit as st
import logging
from datetime import datetime

from config import SCHEMA_FILE, FEWSHOT_FILE, GOOGLE_LLM_API_KEY, SQL_QUERY_RESULTS_DIR
from utils import llm_utils
from utils.bigquery_utils import bigquery_sqlrun_details, authenticate_to_bigquery

# Create logger for app information
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(page_title="DataAnyone")

# Cache the prompt data so it is read only once across all user sessions
@st.cache_data
def load_prompt_data():
    """
    Load both database schema and few-shot examples from files.
    This function is cached, so both files are read only once across all user sessions.
    The cached result (a dictionary containing both values) is reused for all subsequent calls.
    
    Returns:
        dict: Dictionary with keys 'db_schema' and 'few_shot_examples'
    """
    logger.info("Loading database schema and few-shot examples from files")
    
    # Read the database schema YAML file via centralized config path to keep single source of truth
    with SCHEMA_FILE.open("r", encoding="utf-8") as file:
        db_schema = file.read()
    
    # Read the few-shot examples JSON file using the same config-managed path
    with FEWSHOT_FILE.open("r", encoding="utf-8") as file:
        few_shot_examples = file.read()
    
    logger.info("Successfully loaded prompt data")
    
    # Return both values in a dictionary for easy access
    return {
        "db_schema": db_schema,
        "few_shot_examples": few_shot_examples
    }

# Initialize session state for database schema and few-shot examples if not already loaded
if "db_schema" not in st.session_state or "few_shot_examples" not in st.session_state:
    # Call the cached function once to get both values
    # First call reads from files, subsequent calls use cache
    prompt_data = load_prompt_data()
    
    # Store both values in session state
    st.session_state["db_schema"] = prompt_data["db_schema"]
    st.session_state["few_shot_examples"] = prompt_data["few_shot_examples"]

# Initialize session state variables for results and errors
if "results_df" not in st.session_state:
    # Remember the most recent query results across reruns so the table stays visible
    st.session_state["results_df"] = None

if "query_error" not in st.session_state:
    # Track the latest error so we can surface it inside the results column without crashing
    st.session_state["query_error"] = None

if "generated_query" not in st.session_state:
    # Store the generated query to persist across reruns
    st.session_state.generated_query = None

if "user_query" not in st.session_state:
    # Store the user's natural language query to persist across reruns
    st.session_state.user_query = None

if "executed_query" not in st.session_state:
    # Store the executed SQL query to persist across reruns
    st.session_state.executed_query = None

if "feedback_processed" not in st.session_state:
    # Track whether feedback has been processed to prevent duplicate saves on reruns
    st.session_state.feedback_processed = False

if "client" not in st.session_state:
    # Store the BigQuery client to persist across reruns
    st.session_state.client = None


# BIGQUERY CONNECTION
# establish a connection to BigQuery only once per session - If connection fails, client stays None and we show an error message
if st.session_state.client is None:
    logger.info("Attempting to authenticate to BigQuery")
    client = authenticate_to_bigquery() # authenticate to bigquery and create a client
    
    if client is not None:
        st.session_state.client = client # store the client in session state
        logger.info("BigQuery client stored in session state")
    else:
        logger.error("Failed to authenticate to BigQuery")
else:
    # Reuse existing client from session_state - avoids repeated authentication on every rerun
    client = st.session_state.client
    logger.debug("Reusing existing BigQuery client from session state")

# MAIN APP LOGIC
# if bigquery connection is successful, show the query section

if st.session_state.client is not None:

    with st.container():
        user_input_example = st.pills(label="", options=["show me the number of transactions in the last 30 days", 
                                                        "show me the average gas price by day for october", 
                                                        "show me the number of blocks created by day for october",
                                                        "show me the last 10 transactions in August 2025"], key="user_input_example")
        st.write("")
        user_query = st.text_input(label="What would you like to find on Ethereum blockchain?", value=user_input_example, label_visibility="collapsed")
        st.session_state.user_query = user_query
        st.session_state.results_df = None

    if user_query:
        try:
            logger.info(f"User query received: {user_query[:100]}...")  # Log first 100 chars to avoid excessive logging
            
            # Use the centralized API key from config so every module reads the same credential source
            generated_query = llm_utils.generate_sql_query(
                user_query,
                GOOGLE_LLM_API_KEY,
                db_schema=st.session_state["db_schema"],
                few_shot_examples=st.session_state["few_shot_examples"]
            )
            st.session_state.generated_query = generated_query
            logger.info("SQL query generated successfully")
        except Exception as e:
            logger.error(f"Error generating query: {str(e)}", exc_info=True)  # exc_info=True includes stack trace
            st.error(f"❌ Error generating query: {str(e)}")
    
    if st.session_state.generated_query and user_query:
        with st.status("Generated Query") as status_box:
            
            # generated query is stored in session state and displayed in text area, user can edit the query and click run button to run the query
            query = st.text_area(label="Generated Query", value=st.session_state.generated_query, height=250, label_visibility="collapsed", key="query_editor")

            # Execute button to run the query
            run_query_button_clicked = st.button("Run Query", type="primary", use_container_width=True, key="execute_query_button")

        # EXECUTION BLOCK: This block only handles executing the query and storing results
        if run_query_button_clicked:
            logger.info("Execute query button clicked")
            
            # Reset previous result state so stale data does not linger if the next run fails
            st.session_state["query_error"] = None
            
            # Reset feedback_processed flag when executing a new query so user can provide feedback again
            st.session_state.feedback_processed = False

            # Check if user actually entered a query (not just whitespace)
            # Use st.session_state["query_editor"] to access the edited query from the text_area widget
            # This ensures we get the user's edited version, not the original generated query
            if st.session_state["query_editor"].strip():
                try:
                    logger.info(f"Executing SQL query: {st.session_state['query_editor'][:20]}...")
                    
                    # Execute the SQL query using the BigQuery client. This sends the query to BigQuery servers
                    # Use st.session_state["query_editor"] to get the edited version from the text_area widget
                    query_job = client.query(st.session_state["query_editor"])

                    # Print all important query job details including cost, performance, and execution details
                    bigquery_sqlrun_details(query_job)

                    # Fetch results and convert to pandas DataFrame. DataFrame is a table-like data structure that's easy to display
                    results_df = query_job.to_dataframe()
                    
                    logger.info(f"Query executed successfully, returned {len(results_df)} rows")

                    # Persist results so the table can render them even after Streamlit reruns
                    st.session_state["results_df"] = results_df
                    
                    # Store the executed SQL query for later use in saving examples
                    # Store the edited query, not the original generated one
                    st.session_state["executed_query"] = st.session_state["query_editor"]

                except Exception as e:
                    # If query fails (syntax error, permission issue, etc.)
                    # Store error so the results column can surface it and ensure we clear old tables
                    logger.error(f"Query execution failed: {str(e)}", exc_info=True)  # Include stack trace for debugging
                    st.session_state["results_df"] = None
                    st.session_state["query_error"] = str(e)
                    st.error(f"❌ Query failed: {str(e)}")
            else:
                logger.warning("User clicked execute button without entering a query")
                # Warn user if they clicked button without entering a query
                st.warning("⚠️ Please enter a query first.")

    # DISPLAY BLOCK: This block displays results whenever they exist in session state
    if st.session_state["query_error"]:
        # Show any stored error feedback where users expect the table to appear
        st.error(f"❌ {st.session_state['query_error']}")

    if st.session_state["results_df"] is not None and not st.session_state["results_df"].empty:
        
        # Results summary section - always visible when results exist
        with st.status("Data Summary") as status_box_3:
            st.dataframe(st.session_state["results_df"], use_container_width=True, height=500, hide_index=True)
            
            # Save results to csv file in data/sql_query_results directory
            def export_to_csv():
                filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = SQL_QUERY_RESULTS_DIR / filename
                st.session_state["results_df"].to_csv(filepath, index=False)
            st.button("Export to CSV", type="primary", use_container_width=True, key="export_to_csv_button", on_click=export_to_csv)
            
        
        # Query AI answer section - always visible when results exist
        with st.status("AI Summary", expanded=True) as status_box_2:
            # Generate AI answer using the stored user_query from session state
            # Reuse the same config-managed API key to keep AI calls consistent with query generation
            ai_answer = llm_utils.generate_ai_answer(
                st.session_state.get("user_query", ""), 
                st.session_state["results_df"], 
                GOOGLE_LLM_API_KEY
            )
            st.write(ai_answer)
            
            # Store ai_answer in session state so the callback function can access it
            # Callbacks execute before the main script reruns, so they need data from session state
            st.session_state["ai_answer"] = ai_answer
        
            # Callback function that executes immediately when feedback is clicked, before the script reruns
            def handle_feedback():
                
                if st.session_state.feedback_widget == 1: # if thumbs up was clicked (value is 1)
                    logger.info("User provided positive feedback, saving query as example")
                    
                    # Save the successful query with all relevant data from session state
                    llm_utils.save_successful_query(
                        query_name=st.session_state.get("user_query", ""),
                        query_sql=st.session_state.get("executed_query", ""),
                        expected_result=st.session_state["results_df"],
                        notes=st.session_state.get("ai_answer", "")
                    )
                    # Mark as processed so we can show a success message on the rerun
                    st.session_state.feedback_processed = True
                    logger.info("Query example saved successfully")
                    user_query = "" # make user_query empty so the user can ask a new question
                else:
                    logger.info("User provided negative feedback")
            selected = st.feedback("thumbs", key="feedback_widget", on_change=handle_feedback)

else:
    # If not connected, show message prompting user to fix credentials setup
    st.warning(
        "⚠️ Could not connect to BigQuery. Please ensure that:\n"
        "1. The service-account JSON file exists and is readable.\n"
        "2. The GOOGLE_APPLICATION_CREDENTIALS environment variable points to that file.\n"
        "3. The associated Google Cloud project has BigQuery enabled and billing configured."
    )
