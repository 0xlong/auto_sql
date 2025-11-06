import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import os
import json
import yaml
import pandas as pd
from dotenv import load_dotenv
from utils import llm_utils as llm_engine
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
st.set_page_config(page_title="Anylitics AI", layout="wide")

# Initialize session state variables for results and errors
if "results_df" not in st.session_state:
    # Remember the most recent query results across reruns so the table stays visible
    st.session_state["results_df"] = None

if "query_error" not in st.session_state:
    # Track the latest error so we can surface it inside the results column without crashing
    st.session_state["query_error"] = None

if "generated_query" not in st.session_state:
    st.session_state.generated_query = None


# QUERY SECTION
# Only show this section if we have a valid connection (client is not None)

# Build a responsive two-column layout where the left column hosts inputs and the right column shows results
col_inputs, col_results = st.columns((1, 2.5), gap="medium")

with col_inputs:
    client = authenticate_to_bigquery(GOOGLE_BIGQUERY_CREDENTIALS)
    if client is not None:  
        st.success(f"Connected to BigQuery Ethereum database! Project: {client.project}")
        # Collect the natural language intent so we can let the LLM transform it later (currently informational)
        
        st.text("What would you like to find on Ethereum Mainnet blockchain?")
        prompt = st.chat_input("I want to know the number of transactions in the last 30 days")
        
        
        with st.container(border=True):
            user_query = st.text_area(
            "What would you like to find on Ethereum Mainnet blockchain?",
            value="I want to know the number of transactions in the last 30 days",
            height=112,
        )

            user_input_clicked = st.button("Translate to SQL", type="primary", use_container_width=True, key="user_input_button")
            if user_input_clicked:
                try:
                    generated_query = llm_engine.generate_response(user_query, GOOGLE_LLM_API_KEY, db_schema=db_schema, few_shot_examples=few_shot_examples)
                    st.session_state.generated_query = generated_query
                except Exception as e:
                    st.error(f"❌ Error generating query: {str(e)}")
        
        if st.session_state.generated_query:
            with st.status("Generated Query", expanded=True) as status_box:
                query = st.text_area(label="Generated Query", value=st.session_state.generated_query, height=300, label_visibility="collapsed")

                # Execute button to run the query
                # type="primary" makes it blue and prominent
                execute_clicked = st.button("Execute Query", type="primary", use_container_width=True, key="execute_query_button")

            if execute_clicked:
                # Reset previous result state so stale data does not linger if the next run fails
                st.session_state["query_error"] = None

                # Check if user actually entered a query (not just whitespace)
                if query.strip():
                    try:
                        # Show loading spinner while query runs
                        # This gives user feedback that something is happening
                        with col_results:
                            with st.status("Running query...", expanded=True) as status_box:
                                status_box.update(label="Executing query", state="running")

                                # Execute the SQL query using the BigQuery client
                                # This sends the query to BigQuery servers
                                query_job = client.query(query)

                                # Print comprehensive query job details to console for debugging and monitoring
                                # This shows all important metrics including cost, performance, and execution details
                                bigquery_sqlrun_details(query_job)

                                # Fetch results and convert to pandas DataFrame
                                # DataFrame is a table-like data structure that's easy to display
                                results_df = query_job.to_dataframe()

                                # Persist results so the second column can render them even after Streamlit reruns
                                st.session_state["results_df"] = results_df
                                status_box.update(label="Query finished", state="complete")

                                if st.session_state["query_error"]:
                                    # Show any stored error feedback where users expect the table to appear
                                    st.error(f"❌ {st.session_state['query_error']}")

                                elif st.session_state["results_df"] is not None and not st.session_state["results_df"].empty:
                                    st.dataframe(st.session_state["results_df"], use_container_width=True, height=500)

                                else:
                                    # Placeholder message to guide users before they run a query
                                    st.info("Run a query to see results here. The table will appear automatically when data is available.")
                            
                            with st.expander("Query AI answer"):
                                st.info("Query Results AI answer")
                    except Exception as e:
                        # If query fails (syntax error, permission issue, etc.)
                        # Store error so the results column can surface it and ensure we clear old tables
                        st.session_state["results_df"] = None
                        st.session_state["query_error"] = str(e)
                        st.error(f"❌ Query failed: {str(e)}")
                else:
                    # Warn user if they clicked button without entering a query
                    st.warning("⚠️ Please enter a query first.")
    else:
        # If not connected, show message prompting user to fix credentials setup
        st.warning(
            "⚠️ Could not connect to BigQuery. Please ensure that:\n"
            "1. The service-account JSON file exists and is readable.\n"
            "2. The GOOGLE_APPLICATION_CREDENTIALS environment variable points to that file.\n"
            "3. The associated Google Cloud project has BigQuery enabled and billing configured."
        )