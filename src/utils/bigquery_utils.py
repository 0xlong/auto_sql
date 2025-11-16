import logging
import os
import json
import re
from google.oauth2 import service_account
from google.cloud import bigquery

# Create logger for this module using standard pattern
# Logging is centrally configured in config.py - this just creates a module-specific logger
# All log messages from this module will be prefixed with "utils.bigquery_utils"
logger = logging.getLogger(__name__)

def _fix_json_control_characters(json_string):
    """
    Attempt to fix common JSON issues with control characters, especially in private_key fields.
    
    This function handles the common problem where literal newlines in the private_key field
    break JSON parsing. It tries to escape them properly.
    
    Args:
        json_string: The JSON string that may contain control characters
        
    Returns:
        str: The fixed JSON string, or original if no fixes were needed
    """
    # Common issue: literal newlines in private_key field need to be escaped
    # Pattern matches: "private_key": "-----BEGIN...\n...\n...-----END..."
    # We need to replace literal \n (actual newline characters) with escaped \n (the string "\n")
    
    # First, try to find the private_key field and fix newlines within it
    # This regex finds the private_key value and replaces literal newlines with escaped ones
    # Pattern explanation:
    # - "private_key"\s*:\s*" - matches "private_key": "
    # - (.*?) - captures the key content (non-greedy)
    # - " - matches the closing quote
    pattern = r'("private_key"\s*:\s*")(.*?)(")'
    
    def replace_newlines(match):
        # match.group(1) is the opening: "private_key": "
        # match.group(2) is the key content
        # match.group(3) is the closing "
        key_content = match.group(2)
        # Replace literal newlines with escaped newlines
        # Also replace literal carriage returns and tabs
        key_content = key_content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return match.group(1) + key_content + match.group(3)
    
    # Apply the fix to the private_key field
    fixed_json = re.sub(pattern, replace_newlines, json_string, flags=re.DOTALL)
    
    return fixed_json

def authenticate_to_bigquery():
    """
    Authenticate to BigQuery using credentials from environment variable.
    
    This function loads BigQuery service account credentials from the GOOGLE_BIGQUERY_CREDENTIALS environment variable.
    The credentials should be stored as a JSON string in the environment variable.
    
    Why this approach:
    - Keeps sensitive credentials out of the codebase
    - Ensures credentials are loaded from a secure environment variable source
    
    Returns:
        bigquery.Client: Authenticated BigQuery client object, or None if authentication fails
    """
    try:
        # Load the credentials JSON string from environment variable
        # os.getenv() safely retrieves environment variables without crashing if they don't exist
        bigquery_credentials = os.getenv('GOOGLE_BIGQUERY_CREDENTIALS')
        
        # Check if the environment variable exists and has content
        # This prevents cryptic errors later if credentials are missing
        if not bigquery_credentials:
            logger.error("❌ GOOGLE_BIGQUERY_CREDENTIALS environment variable is not set")
            return None
        
        # Clean the credentials string to handle common issues
        # Strip leading/trailing whitespace that might have been accidentally added
        # This is important because extra spaces can break JSON parsing
        bigquery_credentials = bigquery_credentials.strip()
        
        # Parse the JSON string into a Python dictionary
        # json.loads() converts the string representation into a real dictionary object
        # that we can use with the Google Cloud SDK
        try:
            # First attempt: try parsing the JSON as-is
            credentials_dict = json.loads(bigquery_credentials)
        except json.JSONDecodeError as json_error:
            # If parsing fails, check if it's a control character error
            # Control character errors often happen when literal newlines exist in private_key
            error_msg = str(json_error).lower()
            if 'control character' in error_msg or 'invalid' in error_msg:
                # Try to fix common control character issues
                logger.warning("⚠️ Detected control character issue, attempting to fix...")
                try:
                    # Fix literal newlines in private_key field
                    fixed_credentials = _fix_json_control_characters(bigquery_credentials)
                    # Try parsing again with the fixed JSON
                    credentials_dict = json.loads(fixed_credentials)
                    logger.info("✅ Successfully fixed JSON control character issues")
                except json.JSONDecodeError as fix_error:
                    # If fixing didn't work, provide detailed error information
                    error_pos = getattr(json_error, 'pos', None)
                    if error_pos:
                        # Show context around the error position to help debug
                        start = max(0, error_pos - 50)
                        end = min(len(bigquery_credentials), error_pos + 50)
                        context = bigquery_credentials[start:end]
                        # Replace actual newlines in context with \n for display
                        context_display = context.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                        logger.error(f"❌ Invalid JSON in credentials at position {error_pos}: {str(json_error)}")
                        logger.error(f"   Context around error: ...{context_display}...")
                        logger.error("   Common fixes:")
                        logger.error("   1. Ensure all newlines in private_key are escaped as \\n")
                        logger.error("   2. In Windows PowerShell, use: $env:GOOGLE_BIGQUERY_CREDENTIALS = (Get-Content 'path\\to\\key.json' -Raw)")
                        logger.error("   3. Or use a .env file with the JSON on a single line (newlines escaped as \\n)")
                        logger.error("   4. Check for unescaped quotes or special characters")
                    else:
                        logger.error(f"❌ Invalid JSON in credentials: {str(json_error)}")
                    return None
            else:
                # For other JSON errors, provide standard error message
                error_pos = getattr(json_error, 'pos', None)
                if error_pos:
                    start = max(0, error_pos - 50)
                    end = min(len(bigquery_credentials), error_pos + 50)
                    context = bigquery_credentials[start:end]
                    context_display = context.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    logger.error(f"❌ Invalid JSON in credentials at position {error_pos}: {str(json_error)}")
                    logger.error(f"   Context around error: ...{context_display}...")
                else:
                    logger.error(f"❌ Invalid JSON in credentials: {str(json_error)}")
                return None
        
        # Create Google Cloud credentials object from the dictionary
        # service_account.Credentials is the Google Cloud SDK class that handles authentication
        # from_service_account_info() takes a dictionary (rather than a file path)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        
        # Create the BigQuery client using the credentials
        # The client object is what you use to run queries, list datasets, etc.
        # We pass the credentials explicitly so it knows which service account to use
        client = bigquery.Client(credentials=credentials, project=credentials_dict['project_id'])
        
        # Show success message with the project ID so user knows which project they're connected to
        logger.info(f"✅ Connected to BigQuery! Project: {client.project}")
        return client
        
    except json.JSONDecodeError as e:
        # This catch block handles any remaining JSON decode errors that weren't caught above
        # This happens if the credentials string is not valid JSON
        # Common causes: missing quotes, extra commas, incorrectly escaped characters
        logger.error(f"❌ Invalid JSON in credentials: {str(e)}")
        return None
        
    except Exception as e:
        # Catch any other errors (network issues, invalid credentials, etc.)
        # This prevents the entire app from crashing if authentication fails
        logger.error(f"❌ Authentication failed: {str(e)}")
        return None

def bigquery_sqlrun_details(query_job):
    """
    Print comprehensive details about a BigQuery query job execution.
    
    This function extracts and displays all important information about a query job including:
    - Job identification and metadata (job_id, location, user)
    - Timing information (when job was created, started, ended)
    - Performance statistics (bytes processed, billed, cache usage)
    - Query details (SQL, destination, priority)
    - Results information (row count, schema)
    
    Args:
        query_job: A google.cloud.bigquery.job.QueryJob object returned from client.query()
    
    Returns:
        None (prints to console)
    """
    
    logger.info("\n" + "="*80)
    logger.info("BIGQUERY QUERY JOB ANALYSIS")
    logger.info("\n" + "="*80)
    
    # ============================================================================
    # SECTION 1: JOB IDENTIFICATION & EXECUTION STATUS
    # These fields uniquely identify this specific query execution
    # ============================================================================
    logger.info("\n=== JOB IDENTIFICATION ===")
    logger.info(f"Job ID: {query_job.job_id}")
    logger.info(f"Location: {query_job.location}")
    logger.info(f"User Email: {query_job.user_email}")
    
    # ============================================================================
    # EXECUTION STATUS CHECK - This is where BigQuery tells us if query succeeded
    # ============================================================================
    # query_job.state: BigQuery job state from the QueryJob object
    # Possible values: "PENDING", "RUNNING", "DONE" (success or failure)
    # State comes directly from BigQuery's job status API response
    job_state = query_job.state
    logger.info(f"State: {job_state}")
    
    # query_job.errors: List of error dictionaries if query failed
    # This is the PRIMARY source of failure information from BigQuery
    # If errors list is empty/None, query succeeded; if it has items, query failed
    # Errors come from BigQuery's job status response when state is "DONE" with errors
    query_errors = query_job.errors or []
    
    # Determine execution status based on state and errors
    # "DONE" state can mean success OR failure - we check errors to know which
    if job_state == "DONE" and len(query_errors) == 0:
        # Query completed successfully - no errors in the errors list
        execution_status = "✅ SUCCESS"
        logger.info(f"Execution Status: {execution_status}")
    elif job_state == "DONE" and len(query_errors) > 0:
        # Query completed but with errors - BigQuery returned error details
        execution_status = "❌ FAILED"
        logger.error(f"Execution Status: {execution_status}")
        logger.error(f"Error Count: {len(query_errors)}")
        # Log each error from BigQuery's error response
        # Each error is a dict with keys like 'message', 'reason', 'location', etc.
        for i, error in enumerate(query_errors, 1):
            error_message = error.get('message', 'Unknown error')
            error_reason = error.get('reason', 'Unknown reason')
            error_location = error.get('location', 'Unknown location')
            logger.error(f"Error #{i}: {error_message}")
            logger.error(f"  Reason: {error_reason}")
            logger.error(f"  Location: {error_location}")
    elif job_state in ["PENDING", "RUNNING"]:
        # Query is still running - status is intermediate
        execution_status = f"⏳ {job_state}"
        logger.info(f"Execution Status: {execution_status}")
    else:
        # Unknown state
        execution_status = f"⚠️ UNKNOWN STATE: {job_state}"
        logger.warning(f"Execution Status: {execution_status}")
    
    # ============================================================================
    # SECTION 2: TIMING INFORMATION
    # Track when the job was created, started, and completed
    # All timestamps are in UTC timezone from BigQuery
    # ============================================================================
    logger.info("\n=== TIMING INFORMATION ===")
    logger.info(f"Created At: {query_job.created}")
    logger.info(f"Started At: {query_job.started}")
    logger.info(f"Ended At: {query_job.ended}")
    
    # Calculate total execution time if job has completed
    # This is the wall-clock time from start to finish
    if query_job.started and query_job.ended:
        execution_time = (query_job.ended - query_job.started).total_seconds()
        logger.info(f"Execution Time: {execution_time:.2f} seconds")
    
    # ============================================================================
    # SECTION 3: STATISTICS (COST & PERFORMANCE)
    # These metrics determine billing and query efficiency
    # ============================================================================
    logger.info("\n=== STATISTICS ===")
    
    # total_bytes_processed: Actual amount of data scanned by BigQuery
    # This is the primary factor in query cost (BigQuery charges per TB scanned)
    bytes_processed = query_job.total_bytes_processed or 0
    logger.info(f"Total Bytes Processed: {bytes_processed:,} bytes")
    logger.info(f" └─ In GB: {bytes_processed / (1024**3):.4f} GB")
    logger.info(f" └─ In TB: {bytes_processed / (1024**4):.6f} TB")
    
    # total_bytes_billed: What you actually get charged for
    # BigQuery has a minimum of 10MB per query, so small queries might be billed more than processed
    bytes_billed = query_job.total_bytes_billed or 0
    logger.info(f"Total Bytes Billed: {bytes_billed:,} bytes")
    logger.info(f" └─ In GB: {bytes_billed / (1024**3):.4f} GB")
    logger.info(f" └─ In TB: {bytes_billed / (1024**4):.6f} TB")
    
    # cache_hit: If True, results came from BigQuery's cache (no charge!)
    # BigQuery caches query results for 24 hours
    cache_status = "Yes ✓ (Free!)" if query_job.cache_hit else "No ✗ (Billed)"
    logger.info(f"Cache Hit: {cache_status}")
    
    # slot_millis: Computational resources used (slot-milliseconds)
    # A slot is a unit of computational capacity in BigQuery
    # Higher values indicate more complex queries or larger datasets
    if query_job.slot_millis:
        logger.info(f"Slot Milliseconds: {query_job.slot_millis:,}")
        logger.info(f" └─ Slot Seconds: {query_job.slot_millis / 1000:.2f}")
    else:
        logger.info(f"Slot Milliseconds: N/A")
    
    # ============================================================================
    # SECTION 4: QUERY DETAILS
    # Information about the SQL query itself
    # ============================================================================
    logger.info("\n=== QUERY DETAILS ===")
    logger.info(f"Query SQL:\n{query_job.query} \n")
    logger.info(f"\nDestination Table: {query_job.destination}")
    logger.info(f"Priority: {query_job.priority}")
    
    # ============================================================================
    # SECTION 5: RESULTS INFORMATION
    # Details about the data returned by the query
    # ============================================================================
    logger.info("\n=== RESULTS INFORMATION ===")
    
    # Only try to get results if query succeeded (no errors)
    # If query failed, query_job.result() will raise an exception
    # We check errors first to avoid unnecessary exception handling
    if job_state == "DONE" and len(query_errors) == 0:
        try:
            # Get the result object which contains row data and metadata
            # This triggers waiting for the query to complete if not already done
            # If query failed, this will raise a google.cloud.exceptions.GoogleCloudError
            result = query_job.result()
            
            # total_rows: Number of rows returned by the query
            # This comes from BigQuery's result metadata after successful execution
            logger.info(f"Total Rows Returned: {result.total_rows:,}")
            
            # schema: Structure of the result table (column names and data types)
            # Schema comes from BigQuery's result metadata - defines what columns were returned
            logger.info(f"Schema (Column Definitions):")
            for i, field in enumerate(result.schema, 1):
                # field.name: column name
                # field.field_type: data type (STRING, INTEGER, FLOAT, TIMESTAMP, etc.)
                # field.mode: NULLABLE, REQUIRED, or REPEATED
                logger.info(f"  {i}. {field.name} ({field.field_type}, {field.mode})")
        except Exception as e:
            # Catch any exceptions raised by query_job.result()
            # This can happen if BigQuery encounters an error during result retrieval
            # The exception object contains error details from BigQuery's API
            logger.error(f"Failed to retrieve results: {str(e)}")
            logger.error(f"Exception Type: {type(e).__name__}")
    else:
        # Query failed or is still running - no results available
        logger.warning(f"Results not available (Status: {execution_status})")
    
    logger.info("\n" + "="*80)
    logger.info("END OF QUERY JOB ANALYSIS")
    logger.info("="*80 + "\n")