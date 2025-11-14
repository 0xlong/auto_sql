# Tests for Auto SQL

## What's Here

```
tests/
├── unit/                              # Unit tests (test individual functions)
│   ├── test_config.py                 # Tests config loading
│   ├── test_llm_utils.py              # Tests SQL generation, AI answers
│   └── test_bigquery_utils.py         # Tests BigQuery authentication
│
├── integration/                       # Integration tests (test complete workflows)
│   └── test_end_to_end.py             # Tests end-to-end user flows
│
└── conftest.py                        # Shared test fixtures (reusable test data)
```

## Setup

Install dependencies (includes test packages):

```powershell
pip install -r requirements.txt
```

Test packages included:
- `pytest` - testing framework
- `pytest-mock` - for mocking/faking API calls
- `pytest-cov` - for code coverage reports

## Run Tests

```powershell
# Run all tests
pytest

# Run with verbose output (see each test name)
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html
start htmlcov\index.html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific file
pytest tests/unit/test_config.py -v
```

## What Each Test File Does

### Unit Tests (test individual functions in isolation)

**test_config.py** - Tests that configuration loads correctly
- Environment variables are read
- File paths are set up correctly
- Config values have correct types

**test_llm_utils.py** - Tests LLM utility functions
- `generate_sql_query()` - generates SQL from natural language
- `generate_ai_answer()` - creates summaries from query results
- `save_successful_query()` - saves queries to JSON file
- All LLM API calls are mocked (no real API calls)

**test_bigquery_utils.py** - Tests BigQuery utilities
- `authenticate_to_bigquery()` - authentication flow
- `bigquery_sqlrun_details()` - query logging
- All BigQuery API calls are mocked (no real API calls)

### Integration Tests (test complete workflows)

**test_end_to_end.py** - Tests complete user workflows
- Natural language query → SQL generation → execution → AI summary
- Tests that all modules work together correctly
- Tests error handling across the application

### Shared Fixtures (conftest.py)

Contains reusable test data that any test can use:
- `sample_dataframe` - fake query results
- `sample_few_shot_examples` - example queries for LLM
- `mock_bigquery_client` - fake BigQuery client
- ...
