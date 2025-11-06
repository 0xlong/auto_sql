from datetime import datetime
import logging
import os
import json
from google.oauth2 import service_account
from google.cloud import bigquery
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format=' %(asctime)s - %(message)s')
logging.Formatter.converter = time.gmtime # Set the timezone to UTC
logger = logging.getLogger(__name__)

def authenticate_to_bigquery(credentials_json: str):
    """
    Authenticate to BigQuery using credentials from environment variables.
    
    This function loads BigQuery service account credentials from the credentials_json parameter. The credentials should be stored as a JSON string.
    
    Why this approach:
    - Keeps sensitive credentials out of the codebase
    
    Returns:
        bigquery.Client: Authenticated BigQuery client object, or None if authentication fails
    """
    try:
        # Load the credentials JSON string from environment variable
        # os.getenv() safely retrieves environment variables without crashing if they don't exist
        credentials_json = os.getenv('GOOGLE_BIGQUERY_CREDENTIALS')
        
        # Check if the environment variable exists and has content
        # This prevents cryptic errors later if credentials are missing
        if not credentials_json:
            logger.error("❌ GOOGLE_BIGQUERY_CREDENTIALS environment variable is not set")
            return None
        
        # Parse the JSON string into a Python dictionary
        # json.loads() converts the string representation into a real dictionary object
        # that we can use with the Google Cloud SDK
        credentials_dict = json.loads(credentials_json)
        
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
    # Get the current timestamp when this function is called
    # This helps track when the analysis was performed
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    logger.info("\n" + "="*80)
    logger.info(f"{current_timestamp} - BIGQUERY QUERY JOB ANALYSIS - Generated at: ")
    logger.info("\n" + "="*80)
    
    # ============================================================================
    # SECTION 1: JOB IDENTIFICATION
    # These fields uniquely identify this specific query execution
    # ============================================================================
    print("\n=== JOB IDENTIFICATION ===")
    logger.info(f"{current_timestamp} - Job ID: {query_job.job_id}")
    logger.info(f"{current_timestamp} - Location: {query_job.location}")
    logger.info(f"{current_timestamp} - User Email: {query_job.user_email}")
    logger.info(f"{current_timestamp} - State: {query_job.state}")
    
    # ============================================================================
    # SECTION 2: TIMING INFORMATION
    # Track when the job was created, started, and completed
    # All timestamps are in UTC timezone from BigQuery
    # ============================================================================
    print("\n=== TIMING INFORMATION ===")
    logger.info(f"{current_timestamp} - Created At: {query_job.created}")
    logger.info(f"{current_timestamp} - Started At: {query_job.started}")
    logger.info(f"{current_timestamp} - Ended At: {query_job.ended}")
    
    # Calculate total execution time if job has completed
    # This is the wall-clock time from start to finish
    if query_job.started and query_job.ended:
        execution_time = (query_job.ended - query_job.started).total_seconds()
        logger.info(f"{current_timestamp} - Execution Time: {execution_time:.2f} seconds")
    
    # ============================================================================
    # SECTION 3: STATISTICS (COST & PERFORMANCE)
    # These metrics determine billing and query efficiency
    # ============================================================================
    print("\n=== STATISTICS ===")
    
    # total_bytes_processed: Actual amount of data scanned by BigQuery
    # This is the primary factor in query cost (BigQuery charges per TB scanned)
    bytes_processed = query_job.total_bytes_processed or 0
    logger.info(f"{current_timestamp} - Total Bytes Processed: {bytes_processed:,} bytes")
    logger.info(f"{current_timestamp} -  └─ In GB: {bytes_processed / (1024**3):.4f} GB")
    logger.info(f"{current_timestamp} -  └─ In TB: {bytes_processed / (1024**4):.6f} TB")
    
    # total_bytes_billed: What you actually get charged for
    # BigQuery has a minimum of 10MB per query, so small queries might be billed more than processed
    bytes_billed = query_job.total_bytes_billed or 0
    logger.info(f"{current_timestamp} - Total Bytes Billed: {bytes_billed:,} bytes")
    logger.info(f"{current_timestamp} -  └─ In GB: {bytes_billed / (1024**3):.4f} GB")
    logger.info(f"{current_timestamp} -  └─ In TB: {bytes_billed / (1024**4):.6f} TB")
    
    # cache_hit: If True, results came from BigQuery's cache (no charge!)
    # BigQuery caches query results for 24 hours
    cache_status = "Yes ✓ (Free!)" if query_job.cache_hit else "No ✗ (Billed)"
    logger.info(f"{current_timestamp} - Cache Hit: {cache_status}")
    
    # slot_millis: Computational resources used (slot-milliseconds)
    # A slot is a unit of computational capacity in BigQuery
    # Higher values indicate more complex queries or larger datasets
    if query_job.slot_millis:
        logger.info(f"{current_timestamp} - Slot Milliseconds: {query_job.slot_millis:,}")
        logger.info(f"{current_timestamp} -  └─ Slot Seconds: {query_job.slot_millis / 1000:.2f}")
    else:
        logger.info(f"{current_timestamp} - Slot Milliseconds: N/A")
    
    # ============================================================================
    # SECTION 4: QUERY DETAILS
    # Information about the SQL query itself
    # ============================================================================
    print("\n=== QUERY DETAILS ===")
    logger.info(f"{current_timestamp} - Query SQL:\n{query_job.query} \n")
    logger.info(f"\n{current_timestamp} - Destination Table: {query_job.destination}")
    logger.info(f"{current_timestamp} - Priority: {query_job.priority}")
    
    # ============================================================================
    # SECTION 5: RESULTS INFORMATION
    # Details about the data returned by the query
    # ============================================================================
    print("\n=== RESULTS INFORMATION ===")
    
    # Get the result object which contains row data and metadata
    # This triggers waiting for the query to complete if not already done
    result = query_job.result()
    
    # total_rows: Number of rows returned by the query
    logger.info(f"{current_timestamp} - Total Rows Returned: {result.total_rows:,}")
    
    # schema: Structure of the result table (column names and data types)
    logger.info(f"{current_timestamp} - Schema (Column Definitions):")
    for i, field in enumerate(result.schema, 1):
        # field.name: column name
        # field.field_type: data type (STRING, INTEGER, FLOAT, TIMESTAMP, etc.)
        # field.mode: NULLABLE, REQUIRED, or REPEATED
        logger.info(f"{current_timestamp} -   {i}. {field.name} ({field.field_type}, {field.mode})")
    
    logger.info("\n" + "="*80)
    logger.info(f"{current_timestamp} - END OF QUERY JOB ANALYSIS")
    logger.info("="*80 + "\n")

