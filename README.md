# Auto SQL - Natural Language to BigQuery SQL

A Streamlit-based web application that converts natural language queries into BigQuery SQL queries for Ethereum blockchain data analysis. Powered by Google Gemini LLM, this tool enables users to query Ethereum mainnet data without writing SQL.

## 🚀 Features

- **Natural Language to SQL**: Convert plain English questions into optimized BigQuery SQL queries
- **Ethereum Blockchain Data**: Query the Ethereum mainnet public dataset on BigQuery
- **AI-Powered Query Generation**: Uses Google Gemini 2.5 Flash Lite for fast SQL generation
- **Query Execution**: Execute generated queries directly on BigQuery and view results
- **AI Summaries**: Get natural language summaries of query results
- **Query History**: Automatically save successful queries as few-shot examples for improved future performance
- **Export Results**: Download query results as CSV files
- **Query Cost Tracking**: View detailed BigQuery job statistics including bytes processed, execution time, and cache hits

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed on your system
- **Google Cloud Project** with BigQuery API enabled
- **BigQuery Service Account** with read-only access to `bigquery-public-data.goog_blockchain_ethereum_mainnet_us` dataset
- **Google AI API Key** for Gemini models (get it from [Google AI Studio](https://makersuite.google.com/app/apikey))

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd auto_sql
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Windows PowerShell
python -m venv auto_sql
auto_sql\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Set Up Environment Variables

Create a `.env` file in the project root directory with the following variables:

```env
# Google BigQuery Service Account Credentials (JSON string)
GOOGLE_BIGQUERY_CREDENTIALS={"type":"service_account","project_id":"your-project-id",...}

# Google AI API Key for Gemini models
GOOGLE_LLM_API_KEY=your-google-ai-api-key-here
```

**Important Notes:**
- `GOOGLE_BIGQUERY_CREDENTIALS` should be the **entire JSON content** as a single-line string (not a file path)
- The service account must have `BigQuery Data Viewer` role for the Ethereum public dataset
- Never commit your `.env` file to version control

### 2. BigQuery Service Account Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the BigQuery API
4. Create a service account:
   - Navigate to **IAM & Admin** → **Service Accounts**
   - Click **Create Service Account**
   - Grant `BigQuery Data Viewer` role
   - Create and download a JSON key
5. Copy the entire JSON content and paste it as the value for `GOOGLE_BIGQUERY_CREDENTIALS` in your `.env` file

## 🎯 Usage

### Starting the Application

```bash
# Make sure your virtual environment is activated
streamlit run src/app.py
```

The application will open in your default web browser at `http://localhost:8501`

### Using the Application

1. **Enter Your Query**: Type a natural language question in the text input field, or select from example queries
   - Example: "show me the number of transactions in the last 30 days"
   - Example: "show me the average gas price by day for october"

2. **Review Generated SQL**: The LLM will generate a BigQuery SQL query based on your question. Review it before executing.

3. **Execute Query**: Click the "Execute Query" button to run the SQL on BigQuery

4. **View Results**: 
   - See the query results in an interactive table
   - Read the AI-generated summary of the results
   - Check BigQuery job details (cost, execution time, cache status) in the console

5. **Export Data**: Click "Export to CSV" to download results as a CSV file

6. **Provide Feedback**: Use the thumbs up/down to rate the query. Successful queries are automatically saved for future reference.

## 📁 Project Structure

```
auto_sql/
├── src/
│   ├── app.py                      # Main Streamlit application
│   ├── app_simple.py              # Simplified version (if exists)
│   └── utils/
│       ├── __init__.py
│       ├── bigquery_utils.py      # BigQuery authentication and query execution
│       └── llm_utils.py           # LLM integration for SQL generation and summaries
├── data/
│   └── prompt/
│       ├── eth_mainnet_db_schema.yaml      # Ethereum database schema
│       └── eth_mainnet_sql_fewshots.json   # Few-shot examples for LLM
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── .env                           # Environment variables (create this, not in repo)
```

## 🔧 Technologies Used

- **Streamlit**: Web application framework for building the UI
- **Google Cloud BigQuery**: Data warehouse for querying Ethereum blockchain data
- **LangChain**: Framework for building LLM applications
- **Google Gemini**: LLM models for SQL generation and result summarization
- **Pandas**: Data manipulation and analysis
- **Python-dotenv**: Environment variable management

## 🔒 Security Considerations

This application follows security best practices:

- **Read-Only Access**: Uses read-only BigQuery credentials (no write permissions)
- **No SQL Injection**: Generated SQL is executed directly without user input interpolation
- **Query Validation**: BigQuery validates all queries before execution
- **Environment Variables**: Sensitive credentials stored in `.env` file (not in code)
- **No DDL/DML**: Only SELECT queries are generated and executed

## How It Works

1. **User Input**: User enters a natural language query about Ethereum blockchain data
2. **SQL Generation**: The LLM (Gemini 2.5 Flash Lite) generates a BigQuery SQL query using:
   - Database schema (`eth_mainnet_db_schema.yaml`)
   - Few-shot examples (`eth_mainnet_sql_fewshots.json`)
   - User's natural language query
3. **Query Execution**: Generated SQL is executed on BigQuery's Ethereum public dataset
4. **Result Processing**: Results are converted to a pandas DataFrame and displayed
5. **AI Summary**: A second LLM call (Gemini 2.5 Flash) generates a natural language summary
6. **Feedback Loop**: Successful queries are saved as few-shot examples to improve future performance

## Troubleshooting

### Connection Issues

- **"Could not connect to BigQuery"**: 
  - Verify `GOOGLE_BIGQUERY_CREDENTIALS` is set correctly in `.env`
  - Ensure the JSON is valid and properly escaped
  - Check that BigQuery API is enabled in your Google Cloud project

### Query Generation Errors

- **"Error generating query"**: 
  - Verify `GOOGLE_LLM_API_KEY` is set correctly
  - Check your Google AI API quota and billing status
  - Ensure you have internet connectivity

### Query Execution Errors

- **SQL Syntax Errors**: The generated SQL may need manual correction. Review the query before executing.
- **Permission Errors**: Ensure your service account has access to the Ethereum public dataset
- **Timeout Errors**: Large queries may timeout. Try refining your query to be more specific

## 📝 Notes

- The application uses caching for LLM instances to improve performance
- Query results are stored in Streamlit session state to persist across reruns
- Successful queries are automatically added to the few-shot examples file
- BigQuery has a minimum billing of 10MB per query (even if less data is processed)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Improvements
- query review - check if generated query is reliable and safe (no SQL injection = partially mitigated due to BigQuery IAM roles restricting db modifications)
- 

## 📄 License

[Specify your license here]



