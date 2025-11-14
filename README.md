# Auto SQL - Natural Language to BigQuery SQL (NL2SQL)

Web app that converts natural language queries into SQL using [BigQuery Ethereum blockchain database](https://docs.cloud.google.com/blockchain-analytics/docs/example-ethereum) with Google Gemini LLM models.

## Features

- Natural language to SQL conversion
- Query Ethereum mainnet data on BigQuery dataset
- AI-generated result summaries (with chosen LLMs)
- Automatic query learning (few-shot examples)
- CSV export

# Architecture Design sources

- https://arxiv.org/pdf/2408.05109v5
- https://bird-bench.github.io/
- https://spider2-sql.github.io/

## Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Project with BigQuery API enabled
- BigQuery service account (read-only access)
- Google AI API key

### Installation

```bash
# Create virtual environment (Windows PowerShell)
python -m venv auto_sql
auto_sql\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
GOOGLE_BIGQUERY_CREDENTIALS={"type":"service_account","project_id":"your-project-id",...}
GOOGLE_LLM_API_KEY=your-google-ai-api-key-here
```

**Note**: `GOOGLE_BIGQUERY_CREDENTIALS` must be the entire JSON as a single-line string.

### Run

```bash
streamlit run src/app.py
```

## Project Structure

```
auto_sql/
├── src/
│   ├── app.py                               # Main Streamlit app
│   ├── config.py                            # Configuration
│   └── utils/
│       ├── bigquery_utils.py                # BigQuery client & execution
│       └── llm_utils.py                     # LLM SQL generation & summaries
├── data/
│   └── prompt/
│       ├── eth_mainnet_db_schema.yaml       # Database schema from Ethereum Bigquery docs
│       └── eth_mainnet_sql_fewshots.json    # Example queries
└── tests/                                   # Unit & integration tests
```

## Technologies

- **Streamlit** - Web UI
- **Google BigQuery** - Data warehouse
- **LangChain + Google Gemini** - LLM integration
- **Pandas** - Data processing



