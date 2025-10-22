# SimpleCBLookup

A simple tool for downloading Crunchbase static exports and loading them into DuckDB for local querying.

## Features

- Download Crunchbase static export collections using your API key
- Import downloaded data into DuckDB for fast local querying
- Query funding data by company URL
- Check which collections are available with your API key
- Track updates with Last-Modified timestamps

## Installation

### Prerequisites

- Python 3.8+
- A Crunchbase API key

### Install Dependencies

```bash
pip install httpx typer rich duckdb
```

## Getting Started

### 1. Set Your API Key

Set your Crunchbase API key as an environment variable:

```bash
export CRUNCHBASE_USER_KEY="your-api-key-here"
```

Alternatively, you can pass it via command-line arguments.

### 2. Check Available Collections

List all available collections and their metadata:

```bash
python -m cb_downloader list
```

This will show you:
- Available collections
- HTTP status codes
- Last modified dates
- File sizes

### 3. Download Collections

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

### Download Options

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

### 4. Import into DuckDB

After downloading, import the ZIP files into DuckDB:

```bash
python localduck/import_to_duckdb.py
```

Or specify a custom directory:

```bash
python localduck/import_to_duckdb.py /path/to/downloaded/zips
```

This will:
- Extract CSV files from all ZIP archives
- Create tables in `localduck.duckdb`
- Import all data with automatic schema inference
- Show a summary of imported tables and row counts

### 5. Query the Data

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

conn = duckdb.connect("localduck.duckdb")

# List all tables
print(conn.execute("SHOW TABLES").fetchall())

# Query organizations
results = conn.execute("SELECT * FROM organizations LIMIT 10").fetchall()
print(results)

conn.close()
```

## Project Structure

```
SimpleCBLookup/
├── cb_downloader/          # Download tool
│   ├── cli.py              # Command-line interface
│   ├── collections.py      # Collection definitions
│   └── __init__.py
├── localduck/              # DuckDB import and query tools
│   ├── import_to_duckdb.py # Import script
│   └── query_funding_by_url.py  # Query example
├── data/                   # Downloaded data (created on first run)
│   ├── zips/              # Downloaded ZIP files
│   └── manifest.json      # Download tracking
└── README.md
```

## Requirements

- `httpx` - Async HTTP client
- `typer` - CLI framework
- `rich` - Terminal formatting
- `duckdb` - Local database

## License

MIT

## Support

For issues or questions about the Crunchbase API, visit: https://data.crunchbase.com/docs

