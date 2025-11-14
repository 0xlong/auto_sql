import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# LOGGING CONFIGURATION - Configure once for entire application
# All modules will inherit this configuration via logging.getLogger(__name__)
# ============================================================================
# Configure the root logger with basicConfig (only call this ONCE in the entire app)
# This sets up the default logging behavior for all loggers created with getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,  # Log level: INFO shows general application flow, change to DEBUG for detailed diagnostics
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format: timestamp - module - level - message
    datefmt='%Y-%m-%d %H:%M:%S'  # Timestamp format: YYYY-MM-DD HH:MM:SS
)

# API KEYS (from environment variables)
GOOGLE_LLM_API_KEY = os.getenv("GOOGLE_LLM_API_KEY")
GOOGLE_BIGQUERY_CREDENTIALS = os.getenv("GOOGLE_BIGQUERY_CREDENTIALS")

# BIGQUERY CONFIGURATION
BIGQUERY_QUERY_TIMEOUT = 60       # Seconds before query times out
BIGQUERY_MAX_RESULTS = 1000       # Maximum rows to return (safety limit)
BIGQUERY_PROJECT_ID = os.getenv("BIGQUERY_PROJECT_ID", "bigquery-public-data")
BIGQUERY_DATASET = "goog_blockchain_ethereum_mainnet_us"

# FILE PATHS
PROJECT_ROOT = Path(__file__).parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
PROMPT_DIR = DATA_DIR / "prompt"
SQL_QUERY_RESULTS_DIR = DATA_DIR / "sql_query_results"

# Create sql_query_results directory if it doesn't exist
# This ensures the directory is available for saving CSV exports
# exist_ok=True prevents errors if directory already exists
SQL_QUERY_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Specific files
SCHEMA_FILE = PROMPT_DIR / "eth_mainnet_db_schema.yaml" # YAML file containing the database schema
FEWSHOT_FILE = PROMPT_DIR / "eth_mainnet_sql_fewshots.json" # JSON file containing example queries for context



