# SimpleCBLookup

A simple tool for downloading Crunchbase static exports and loading them into DuckDB for local querying.

**Quick Start:** Just run `./setup.sh` - it handles everything automatically!

> **Note:** If you already have data downloaded, the setup script will detect it and ask if you want to use existing data or download fresh updates.

## Features

- Download Crunchbase static export collections using your API key
- Import downloaded data into DuckDB for fast local querying
- Query funding data by company URL (single or bulk)
- Bulk query multiple companies with quarterly funding breakdown
- Check which collections are available with your API key
- Track updates with Last-Modified timestamps

## Installation

### Prerequisites

- Python 3.8+
- A Crunchbase API key
- UV (recommended, installed automatically by setup.sh) or pip

### Install Dependencies

**Using UV (recommended, faster):**
```bash
uv pip install httpx typer rich duckdb python-dateutil
```

**Using pip:**
```bash
pip install httpx typer rich duckdb python-dateutil
```

## Getting Started

### One-Click Setup (Easiest)

Run the automated setup script with UV ([uv](https://github.com/astral-sh/uv) is a fast Python package installer that's 10-100x faster than pip):

```bash
./setup.sh
```

Or copy-paste this true one-liner:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh && ./setup.sh
```

> **Note:** UV will be automatically installed if you don't have it. It's a modern Python tool that's much faster than pip and manages dependencies better.

This will:
1. Install UV (if not already installed)
2. Install all Python dependencies
3. Check for existing data (if found, you can use it or download fresh)
4. Prompt for your Crunchbase API key
5. Check available collections (or skip if using existing data)
6. Download data (you can choose all or essential collections)
7. Import into DuckDB (or skip if database already exists)
8. Test with Tesla.com

### Re-running Setup

If you run `./setup.sh` again and already have data:

- **Download step**: You'll be asked if you want to use existing zips or download fresh data
- **Import step**: You'll be asked if you want to re-import or use the existing database

This allows you to easily:
- Update your data with fresh downloads
- Recreate your database if needed
- Skip unnecessary steps when you just want to test queries

### Python Setup (Manual Install)

If you prefer to manage dependencies yourself:

```bash
pip install httpx typer rich duckdb
python setup.py
```

### Manual Setup

If you prefer to do it step by step:

#### 1. Set Your API Key

Set your Crunchbase API key as an environment variable:

```bash
export CRUNCHBASE_USER_KEY="your-api-key-here"
```

Alternatively, you can pass it via command-line arguments.

#### 2. Check Available Collections

List all available collections and their metadata:

```bash
python -m cb_downloader list
```

This will show you:
- Available collections
- HTTP status codes
- Last modified dates
- File sizes

#### 3. Download Collections

Download all available collections:

```bash
python -m cb_downloader download --all
```

Or download a specific collection:

```bash
python -m cb_downloader download organizations
```

Available collections include:
- `organizations` - Company information
- `funding_rounds` - Funding round details
- `acquisitions` - Acquisition data
- `people` - Person profiles
- `events` - Event information
- And many more...

#### Download Options

```bash
# Download to a custom directory
python -m cb_downloader download --all --dest ./my-data

# Force re-download even if unchanged
python -m cb_downloader download --all --force

# Set concurrency level for faster downloads
python -m cb_downloader download --all --max-concurrency 8

# Use a specific API key
python -m cb_downloader download --all --user-key "your-key"
```

#### 4. Import into DuckDB

After downloading, import the ZIP files into DuckDB:

```bash
python localduck/import_to_duckdb.py
```

This will:
- Read the manifest.json to determine the data date
- Extract CSV files from all ZIP archives in `data/zips/`
- Save extracted CSVs to `data/extracted_csvs/` with timestamped filenames
- Create tables in `data/cb_data.YYYY-MM-DD.duckdb` (e.g., `data/cb_data.2025-10-21.duckdb`)
- Import all data with automatic schema inference
- Show a summary of imported tables and row counts

#### 5. Query the Data

Query funding data for a company by URL:

```bash
python localduck/query_funding_by_url.py tesla.com
```

Or with full URL:

```bash
python localduck/query_funding_by_url.py https://www.tesla.com
```

This will display:
- Company information
- All funding rounds
- Amount raised, valuations, stages
- Summary statistics

#### Bulk Query Multiple Companies

Query funding data for multiple companies from a CSV file:

```bash
# Auto-generate output filename from input CSV name
python bulk_funding_query.py urls.csv

# Or specify custom output filename
python bulk_funding_query.py urls.csv output.csv
```

Or query a single company and save to CSV (output filename auto-generated):

```bash
python bulk_funding_query.py tesla.com
```

**Output filename format:**
- Single URL: `{url}_Funding_rounds_to_date_{YYYY-MM-DD}.csv`
- CSV input: `{input_filename}_Funding_rounds_to_date_{YYYY-MM-DD}.csv`

Example outputs:
- `tesla.com` → `tesla.com_Funding_rounds_to_date_2025-01-23.csv`
- `companies.csv` → `companies_Funding_rounds_to_date_2025-01-23.csv`

The bulk query script outputs a CSV with:
- Company information (name, description, categories, etc.)
- Investment rounds and funding details
- Total funding to date
- Quarterly funding breakdown (2025 Q1, 2025 Q2, etc.)

CSV format: Put URLs in the first column of your input CSV.

## Data Structure

Downloaded files are stored in `data/zips/` by default. Each ZIP contains CSV files that are imported into DuckDB tables.

The manifest file (`data/manifest.json`) tracks:
- Downloaded file paths
- Last-Modified timestamps
- Download dates
- File sizes

## Advanced Usage

### Check for Updates

Check if collections have been updated:

```bash
python -m cb_downloader updates
```

This updates `Updates.md` with the latest Last-Modified information for all collections.

### Query DuckDB Directly

Connect to the DuckDB database:

```python
import duckdb
import glob

# Find the latest database
db_files = glob.glob("data/cb_data.*.duckdb")
db_path = sorted(db_files)[-1] if db_files else None

if db_path:
    conn = duckdb.connect(db_path)
    
    # List all tables
    print(conn.execute("SHOW TABLES").fetchall())
    
    # Query organizations
    results = conn.execute("SELECT * FROM organizations LIMIT 10").fetchall()
    print(results)
    
    conn.close()
else:
    print("No database found. Run the import script first.")
```

## Project Structure

```
SimpleCBLookup/
├── cb_downloader/             # Download tool
│   ├── cli.py                 # Command-line interface
│   ├── collections.py         # Collection definitions
│   └── __init__.py
├── localduck/                 # DuckDB import and query tools
│   ├── import_to_duckdb.py    # Import script
│   └── query_funding_by_url.py # Query example
├── bulk_funding_query.py      # Bulk query script
├── data/                      # Downloaded data (created on first run, gitignored)
│   ├── zips/                  # Downloaded ZIP files
│   ├── extracted_csvs/        # Extracted CSV files with timestamps
│   ├── cb_data.YYYY-MM-DD.duckdb  # DuckDB database with date
│   └── manifest.json           # Download tracking
├── setup.py                   # Setup script
├── setup.sh                   # Automated setup script
├── pyproject.toml             # UV dependencies
└── README.md
```

## Requirements

- `httpx` - Async HTTP client
- `typer` - CLI framework
- `rich` - Terminal formatting
- `duckdb` - Local database
- `python-dateutil` - Date utilities for bulk queries

## License

MIT

## Support

For issues or questions about the Crunchbase API, visit: https://data.crunchbase.com/docs

