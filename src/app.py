import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv
from utils import llm_utils
from utils.bigquery_utils import bigquery_sqlrun_details, authenticate_to_bigquery


# Load environment variables from .env file
load_dotenv()
GOOGLE_BIGQUERY_CREDENTIALS = os.getenv('GOOGLE_BIGQUERY_CREDENTIALS')
GOOGLE_LLM_API_KEY = os.getenv("GOOGLE_LLM_API_KEY")

# Get the absolute path to the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load database schema and few shot examples for prompt template for LLM
with open(os.path.join(PROJECT_ROOT, "data", "prompt", "eth_mainnet_db_schema.yaml"), "r") as file:
    db_schema = file.read()
with open(os.path.join(PROJECT_ROOT, "data", "prompt", "eth_mainnet_sql_fewshots.json"), "r") as file:
    few_shot_examples = file.read()

# Configure the Streamlit page with minimal settings and title
st.set_page_config(page_title="DataAnyone")

# Initialize session state variables for results and errors
if "results_df" not in st.session_state:
    # Remember the most recent query results across reruns so the table stays visible
    st.session_state["results_df"] = None

if "query_error" not in st.session_state:
    # Track the latest error so we can surface it inside the results column without crashing
    st.session_state["query_error"] = None

if "generated_query" not in st.session_state:
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
    st.session_state.client = None

# QUERY SECTION
# Only show this section if we have a valid connection (client is not None)

# BIGQUERY CONNECTION
if st.session_state.client is None:
    client = authenticate_to_bigquery(GOOGLE_BIGQUERY_CREDENTIALS)
    st.session_state.client = client
else:
    # Reuse the existing client from session_state instead of creating a new one
    client = st.session_state.client

# if bigquery connection is successful, show the query section
if st.session_state.client is not None:

    with st.container():
        user_input_example = st.pills(label="", options=["show me the number of transactions in the last 30 days", 
                                                        "show me the average gas price by day for october", 
                                                        "show me the number of blocks created by day for october",
                                                        "show me the last 10 transactions in August 2025"], key="user_input_example")
        user_query = st.text_input(label="What would you like to find on Ethereum blockchain?", value=user_input_example, label_visibility="collapsed")
        st.session_state.user_query = user_query
        st.session_state.results_df = None

    if user_query:
        try:
            generated_query = llm_utils.generate_sql_query(user_query, GOOGLE_LLM_API_KEY, db_schema=db_schema, few_shot_examples=few_shot_examples)
            st.session_state.generated_query = generated_query
        except Exception as e:
            st.error(f"❌ Error generating query: {str(e)}")
    
    if st.session_state.generated_query:
        with st.status("Generated Query") as status_box:
            query = st.text_area(label="Generated Query", value=st.session_state.generated_query, height=250, label_visibility="collapsed")

            # Execute button to run the query
            execute_clicked = st.button("Execute Query", type="primary", use_container_width=True, key="execute_query_button")

        # EXECUTION BLOCK: This block only handles executing the query and storing results
        if execute_clicked:
            # Reset previous result state so stale data does not linger if the next run fails
            st.session_state["query_error"] = None
            
            # Reset feedback_processed flag when executing a new query so user can provide feedback again
            st.session_state.feedback_processed = False

            # Check if user actually entered a query (not just whitespace)
            if query.strip():
                try:
                    # Execute the SQL query using the BigQuery client. This sends the query to BigQuery servers
                    query_job = client.query(query)

                    # Print all important query job details including cost, performance, and execution details
                    bigquery_sqlrun_details(query_job)

                    # Fetch results and convert to pandas DataFrame. DataFrame is a table-like data structure that's easy to display
                    results_df = query_job.to_dataframe()

                    # Persist results so the table can render them even after Streamlit reruns
                    st.session_state["results_df"] = results_df
                    
                    # Store the executed SQL query for later use in saving examples
                    st.session_state["executed_query"] = query

                except Exception as e:
                    # If query fails (syntax error, permission issue, etc.)
                    # Store error so the results column can surface it and ensure we clear old tables
                    st.session_state["results_df"] = None
                    st.session_state["query_error"] = str(e)
                    st.error(f"❌ Query failed: {str(e)}")
            else:
                # Warn user if they clicked button without entering a query
                st.warning("⚠️ Please enter a query first.")

    # DISPLAY BLOCK: This block displays results whenever they exist in session state
    if st.session_state["query_error"]:
        # Show any stored error feedback where users expect the table to appear
        st.error(f"❌ {st.session_state['query_error']}")

    if st.session_state["results_df"] is not None and not st.session_state["results_df"].empty:
        
        # Results summary section - always visible when results exist
        with st.status("Results Summary") as status_box_3:
            st.dataframe(st.session_state["results_df"], use_container_width=True, height=500, hide_index=True)
            
            # Save results to csv file
            export_to_csv_clicked = st.button("Export to CSV", type="primary", use_container_width=True, key="export_to_csv_button")
            if export_to_csv_clicked:
                st.session_state["results_df"].to_csv(f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)
                st.success("Results exported to CSV file")
        
        # Query AI answer section - always visible when results exist
        with st.status("Summary", expanded=True) as status_box_2:
            # Generate AI answer using the stored user_query from session state
            ai_answer = llm_utils.generate_ai_answer(
                st.session_state.get("user_query", ""), 
                st.session_state["results_df"], 
                GOOGLE_LLM_API_KEY
            )
            st.write(ai_answer)
        
        # Feedback section - always visible when results exist        
        # Get the current feedback selection (1 for thumbs up, 0 for thumbs down, None if not clicked)
        selected = st.feedback("thumbs")
        
        # Only process feedback if:
        # 1. A thumb was clicked (selected is 1)
        # 2. We haven't already processed this feedback (prevents duplicate saves on reruns)
        if selected == 1 and not st.session_state.feedback_processed:
            # Mark feedback as processed so we don't save it again on the next rerun
            st.session_state.feedback_processed = True
            
            st.write(f"Query name: {st.session_state.get('user_query', '')}")
            llm_utils.save_successful_query(
                query_name=st.session_state.get("user_query", ""),
                query_sql=st.session_state.get("executed_query", ""),
                expected_result=st.session_state["results_df"],
                notes=ai_answer
            )

else:
    # If not connected, show message prompting user to fix credentials setup
    st.warning(
        "⚠️ Could not connect to BigQuery. Please ensure that:\n"
        "1. The service-account JSON file exists and is readable.\n"
        "2. The GOOGLE_APPLICATION_CREDENTIALS environment variable points to that file.\n"
        "3. The associated Google Cloud project has BigQuery enabled and billing configured."
    )