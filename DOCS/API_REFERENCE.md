# API Reference

## Command-Line Interface

### RUN.sh

Main entry point for all operations.

#### Commands

- `setup` - Complete setup workflow
- `download` - Download collections
- `import` - Import to DuckDB
- `query` - Query single company
- `bulk` - Bulk query from CSV
- `list` - List collections
- `check` - Check status
- `verify` - Verify files
- `help` - Show help

#### Examples

```bash
./RUN.sh setup
./RUN.sh query tesla.com
./RUN.sh bulk INPUT/companies.csv
```

## Python Modules

### cb_downloader

Crunchbase data downloader.

#### CLI Commands

```bash
python -m cb_downloader list [--write-log] [--user-key KEY]
python -m cb_downloader download [collection] [--all] [options]
python -m cb_downloader check [--dest DIR]
python -m cb_downloader verify [--fix] [--quick] [options]
python -m cb_downloader updates [--user-key KEY]
```

#### Options

- `--user-key` - API key (or use CRUNCHBASE_USER_KEY env var)
- `--dest` - Destination directory (default: data/zips)
- `--force` - Force re-download
- `--verify` - Verify existing files
- `--max-concurrency` - Concurrent downloads (default: 4)
- `--timeout` - HTTP timeout in seconds (default: 180)
- `--quick` - Quick verification mode (default: true)
- `--fix` - Auto-fix corrupted files

### localduck

DuckDB import and query tools.

#### import_to_duckdb.py

Import ZIP files into DuckDB.

```bash
python localduck/import_to_duckdb.py
```

**Process:**
1. Reads `data/manifest.json` for date
2. Extracts CSVs from `data/zips/*.zip`
3. Saves to `data/extracted_csvs/` with timestamps
4. Creates `data/cb_data.{date}.duckdb`
5. Imports all tables with schema inference

#### query_funding_by_url.py

Query funding data by company URL.

```bash
python localduck/query_funding_by_url.py <url>
```

**Returns:**
- Company information
- All funding rounds
- Amounts, valuations, stages
- Summary statistics

### bulk_funding_query.py

Bulk query multiple companies.

```bash
python bulk_funding_query.py <input.csv> [output.csv]
python bulk_funding_query.py <url>
```

**CSV Format:**
- URLs in first column
- One URL per row

**Output:**
- Company information
- Funding rounds
- Quarterly breakdown columns
- Total funding

## Database Schema

### organizations

Company information.

**Key Columns:**
- `identifier.value` - Company name
- `identifier.uuid` - Unique ID
- `website` - Website URL
- `website_url` - Alternative URL
- `description` - Full description
- `short_description` - Brief description
- `founded_on.value` - Founding date
- `categories.value` - Industry categories
- `category_groups.value` - Category groups
- `location_identifiers.value` - Location
- `funding_total.value_usd` - Total funding
- `num_funding_rounds` - Number of rounds
- `num_investors` - Number of investors

### funding_rounds

Funding round details.

**Key Columns:**
- `identifier.value` - Round name
- `identifier.uuid` - Unique ID
- `announced_on` - Announcement date
- `closed_on.value` - Closing date
- `money_raised.value_usd` - Amount raised
- `money_raised.currency` - Currency
- `investment_type` - Type of investment
- `investment_stage` - Funding stage
- `num_investors` - Number of investors
- `post_money_valuation.value_usd` - Post-money valuation
- `pre_money_valuation.value_usd` - Pre-money valuation
- `short_description` - Description
- `funded_organization_identifier.uuid` - Company UUID

### investments

Investor details for funding rounds.

**Key Columns:**
- `funding_round_identifier.uuid` - Round UUID
- `investor_identifier.value` - Investor name
- `is_lead_investor` - Lead investor flag
- `money_invested.value_usd` - Amount invested

### acquisitions

Acquisition information.

**Key Columns:**
- `identifier.value` - Acquisition name
- `acquired_organization_identifier.uuid` - Acquired company UUID
- `acquirer_organization_identifier.uuid` - Acquirer company UUID
- `announced_on` - Announcement date
- `price.value_usd` - Acquisition price

### Other Tables

- `people` - Person profiles
- `events` - Event information
- `jobs` - Job postings
- `products` - Product information
- And more...

## DuckDB Functions

### Connect to Database

```python
import duckdb
import glob

db_files = glob.glob("data/cb_data.*.duckdb")
db_path = sorted(db_files)[-1]
conn = duckdb.connect(db_path)
```

### List Tables

```python
tables = conn.execute("SHOW TABLES").fetchall()
```

### Query Data

```python
results = conn.execute("SELECT * FROM organizations LIMIT 10").fetchall()
```

### Close Connection

```python
conn.close()
```

## API Endpoints

### Crunchbase Static Exports

**Base URL:** `https://api.crunchbase.com/v4/data/static_exports`

**Endpoints:**
- `/{collection}.zip` - Download collection

**Parameters:**
- `user_key` - Your API key (required)

**Headers:**
- `User-Agent` - Client identifier
- `Accept` - application/zip
- `If-Modified-Since` - Check for updates

**Response:**
- ZIP file containing CSV data
- `Last-Modified` header with update timestamp
- `Content-Length` header with file size

## Error Handling

### Common Errors

**No API Key:**
```
Error: Provide --user-key or set CRUNCHBASE_USER_KEY env var.
```

**No Database:**
```
Error: No DuckDB database found in data folder.
```

**File Not Found:**
```
Error: File not found: INPUT/companies.csv
```

**Corrupted File:**
```
Error: Downloaded file appears corrupted
```

### Verification Errors

Files are checked for:
- Existence
- Non-zero size
- Valid ZIP format
- File size matches manifest

Auto-fix with `--fix` flag.

## Rate Limits

No rate limits for static exports, but:
- Download concurrently for speed
- Use reasonable concurrency (4-8)
- HTTP timeout is 180 seconds by default

## Best Practices

1. **Check Before Download:** Use `./RUN.sh check` first
2. **Verify Downloads:** Run `./RUN.sh verify` after downloads
3. **Backup Data:** Copy `data/` directory regularly
4. **Use Bulk Queries:** For multiple companies
5. **Index Frequently Used Columns:** In DuckDB
6. **Monitor Disk Space:** Several GB needed for full dataset

