# Usage Guide

## Quick Start

The `RUN.sh` script is your main entry point for all operations.

```bash
./RUN.sh help
```

## Commands

### Setup

Complete setup workflow including dependency installation, data download, and database import:

```bash
./RUN.sh setup
```

Options during setup:
- Use existing data
- Download fresh data
- Download missing collections only
- Fix corrupted files

### Download

Download Crunchbase collections:

```bash
# Download all collections
./RUN.sh download --all

# Download specific collection
./RUN.sh download organizations

# Download with options
./RUN.sh download --all --max-concurrency 8
```

### Import

Import downloaded data into DuckDB:

```bash
./RUN.sh import
```

This extracts CSVs from ZIP files and creates a DuckDB database.

### Query

Query funding data for a single company:

```bash
./RUN.sh query tesla.com
./RUN.sh query https://www.apple.com
./RUN.sh query openai.com
```

### Bulk Query

Query multiple companies from a CSV file:

```bash
# Auto-generate output filename
./RUN.sh bulk INPUT/companies.csv

# Specify custom output filename
./RUN.sh bulk INPUT/companies.csv OUTPUT/results.csv
```

CSV format: URLs in the first column.

### List Collections

List all available collections:

```bash
./RUN.sh list
```

### Check Status

Check which collections are downloaded:

```bash
./RUN.sh check
```

### Verify Files

Verify integrity of downloaded files:

```bash
# Quick verification
./RUN.sh verify

# Full verification with CRC check
./RUN.sh verify --quick=false

# Auto-fix corrupted files
./RUN.sh verify --fix
```

## Advanced Usage

### Environment Variables

Set your API key:

```bash
export CRUNCHBASE_USER_KEY="your-api-key"
```

### Direct Access to Tools

You can also access tools directly in the SRC directory:

```bash
cd SRC

# Download collections
python -m cb_downloader download --all

# Import to DuckDB
python localduck/import_to_duckdb.py

# Query single company
python localduck/query_funding_by_url.py tesla.com

# Bulk query
python bulk_funding_query.py INPUT/companies.csv
```

### Custom Database Queries

Connect to DuckDB directly:

```python
import duckdb
import glob

# Find latest database
db_files = glob.glob("data/cb_data.*.duckdb")
db_path = sorted(db_files)[-1]

conn = duckdb.connect(db_path)

# Run custom queries
results = conn.execute("SELECT * FROM organizations LIMIT 10").fetchall()
print(results)

conn.close()
```

## Input Files

Place your input CSV files in the `INPUT/` directory:

```
INPUT/
└── companies.csv
```

Example CSV format:

```csv
tesla.com
apple.com
openai.com
```

## Output Files

Results are written to the root directory or `OUTPUT/`:

```
OUTPUT/
└── companies_Funding_rounds_to_date_2025-01-23.csv
```

## Data Directory

Downloaded data is stored in `data/`:

```
data/
├── zips/                    # Downloaded ZIP files
├── extracted_csvs/          # Extracted CSV files
├── cb_data.2025-01-23.duckdb  # DuckDB database
└── manifest.json            # Download tracking
```

## Best Practices

1. **Regular Updates**: Run `./RUN.sh verify` periodically to check for updates
2. **Backup Data**: Back up the `data/` directory regularly
3. **Batch Processing**: Use bulk queries for multiple companies
4. **API Key Security**: Don't commit your API key to version control
5. **Disk Space**: Ensure sufficient disk space (several GB for full dataset)

## Next Steps

- [Examples](EXAMPLES.md) - See examples
- [Configuration](CONFIGURATION.md) - Configure settings
- [API Reference](API_REFERENCE.md) - Technical details

