import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import os
import json
import pandas as pd
from dotenv import load_dotenv


def authenticate_to_bigquery():
    try:
        client = bigquery.Client()
        st.info(f"✅ Connected to BigQuery! Project: {client.project}")
        return client
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        return None

# Load environment variables from .env file if it exists
# This allows us to configure credentials path without hardcoding
# The .env file should be in the same directory as app.py
load_dotenv()
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Configure the Streamlit page with minimal settings
st.set_page_config(page_title="BigQuery Query", layout="wide")

if "results_df" not in st.session_state:
    # Remember the most recent query results across reruns so the table stays visible
    st.session_state["results_df"] = None

if "query_error" not in st.session_state:
    # Track the latest error so we can surface it inside the results column without crashing
    st.session_state["query_error"] = None

# QUERY SECTION
# Only show this section if we have a valid connection (client is not None)

# Build a responsive two-column layout where the left column hosts inputs and the right column shows results
col_inputs, col_results = st.columns((1, 3), gap="large")

with col_inputs:
    client = authenticate_to_bigquery()
    if client:  
        # Collect the natural language intent so we can let the LLM transform it later (currently informational)
        with st.container(border=True):
            user_query = st.text_area(
            "What would you like to find in ethereum database?",
            value="I want to know the number of transactions in the last 30 days",
            height=112,
        )

        user_input_clicked = st.button("Translate to SQL", type="primary", use_container_width=True, key="user_input_button")

        # Text input field for SQL query
        # text_area creates a multi-line input box
        # height parameter controls how tall the box is (in pixels)
        # placeholder shows example text when field is empty
        with st.container(border=True):
            query = st.text_area(
            "Enter your SQL query:",
            value="SELECT * FROM `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.logs` LIMIT 10",
            height=160,
        )

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
                    with st.status("Running query...", expanded=True) as status_box:
                        status_box.update(label="Contacting BigQuery", state="running")

                        # Execute the SQL query using the BigQuery client
                        # This sends the query to BigQuery servers
                        query_job = client.query(query)

                        # Fetch results and convert to pandas DataFrame
                        # DataFrame is a table-like data structure that's easy to display
                        results_df = query_job.to_dataframe()

                        # Persist results so the second column can render them even after Streamlit reruns
                        st.session_state["results_df"] = results_df
                        status_box.update(label="Query finished", state="complete")

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

with col_results:
    
    if st.session_state["query_error"]:
        # Show any stored error feedback where users expect the table to appear
        st.error(f"❌ {st.session_state['query_error']}")

    elif st.session_state["results_df"] is not None and not st.session_state["results_df"].empty:
        # Display the results as an interactive table
        # use_container_width makes table expand to fill available space
        with st.status("Query Results", expanded=True) as status_box:
            st.dataframe(st.session_state["results_df"], use_container_width=True, height=500)
            status_box.update(label="Query Results", state="complete")

    else:
        # Placeholder message to guide users before they run a query
        st.info("Run a query to see results here. The table will appear automatically when data is available.")


