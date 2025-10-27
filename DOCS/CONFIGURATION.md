# Configuration Guide

## Environment Variables

### CRUNCHBASE_USER_KEY

Your Crunchbase API key. Required for downloading data.

```bash
export CRUNCHBASE_USER_KEY="your-api-key-here"
```

Get your API key from: https://data.crunchbase.com

## Directory Configuration

Default directories can be modified in `RUN.sh`:

```bash
SRC_DIR="SRC"
DOCS_DIR="DOCS"
DATA_DIR="data"
INPUT_DIR="INPUT"
OUTPUT_DIR="OUTPUT"
```

## Data Directory Structure

The `data/` directory contains:

```
data/
├── zips/                    # Downloaded ZIP files
├── extracted_csvs/          # Extracted CSV files
├── cb_data.*.duckdb         # DuckDB databases
└── manifest.json            # Download tracking
```

## Database Configuration

### Database Location

Databases are created in `data/` with date stamps:

```
data/cb_data.2025-01-23.duckdb
```

### Database Settings

DuckDB settings can be configured in import scripts:

```python
conn = duckdb.connect(db_path)
conn.execute("SET memory_limit='4GB'")
conn.execute("SET threads=4")
```

## Download Configuration

### Concurrency

Control download concurrency:

```bash
./RUN.sh download --all --max-concurrency 8
```

### Timeout

Adjust HTTP timeout (default: 180 seconds):

```bash
python -m cb_downloader download --all --timeout 300
```

### Destination

Specify custom download directory:

```bash
python -m cb_downloader download --all --dest ./custom/data
```

## Import Configuration

### Extract Directory

Extracted CSVs are stored with timestamps:

```
data/extracted_csvs/organizations.2025-01-23.a1b2c3d4.csv
```

### Schema Inference

DuckDB automatically infers schemas from CSV files. To customize:

```python
conn.execute(f"""
    CREATE TABLE {table_name} AS 
    SELECT * FROM read_csv_auto('{csv_path}', 
        header=true,
        auto_detect=true,
        auto_type_casting=true
    )
""")
```

## Verification Configuration

### Quick vs Full Verification

```bash
# Quick check (default, faster)
./RUN.sh verify --quick

# Full verification with CRC check (slower)
./RUN.sh verify --quick=false
```

### Auto-Fix

Automatically re-download corrupted files:

```bash
./RUN.sh verify --fix
```

## Query Configuration

### Output Format

Bulk query outputs include:

- Company information
- Funding rounds
- Quarterly breakdown
- Investor details

### CSV Output

Output files are named with timestamps:

```
{input}_Funding_rounds_to_date_{YYYY-MM-DD}.csv
```

## API Configuration

### Base URL

Crunchbase API base URL (configured in `SRC/cb_downloader/collections.py`):

```python
BASE_URL = "https://api.crunchbase.com/v4/data/static_exports"
```

### Available Collections

See collections in `SRC/cb_downloader/collections.py`:

- organizations
- funding_rounds
- investments
- acquisitions
- people
- events
- ... and more

## Logging

### Enable Verbose Output

Add verbose flags to commands:

```bash
python -m cb_downloader download --all --verbose
```

### Write Updates Log

Generate `Updates.md` with collection metadata:

```bash
python -m cb_downloader list --write-log
```

## Performance Tuning

### Database Performance

```python
# Increase memory limit
conn.execute("SET memory_limit='8GB'")

# Use multiple threads
conn.execute("SET threads=8")

# Enable parallel query execution
conn.execute("SET enable_progress_bar=true")
```

### Download Performance

```bash
# Use high concurrency
./RUN.sh download --all --max-concurrency 16

# Use faster connection
python -m cb_downloader download --all --timeout 60
```

## Security

### API Key Storage

Never commit API keys to version control. Use:

1. Environment variables
2. `.env` file (not committed)
3. Config file (gitignored)

### .gitignore

Recommended additions:

```
data/
.env
*.duckdb
.vscode/
.idea/
__pycache__/
```

## Customization

### Custom Collections

Add custom collections in `SRC/cb_downloader/collections.py`:

```python
COLLECTIONS = {
    "custom_collection": f"{BASE_URL}/custom_collection.zip",
    # ... existing collections
}
```

### Custom Query Scripts

Create custom query scripts in `SRC/`:

```python
#!/usr/bin/env python3
import duckdb
import glob

# Your custom queries here
```

## Troubleshooting

### Reset Environment

```bash
# Remove virtual environment
rm -rf .venv

# Remove cached data
rm -rf data/

# Start fresh
./RUN.sh setup
```

### Update Dependencies

```bash
source .venv/bin/activate
pip install --upgrade httpx typer rich duckdb python-dateutil
```

