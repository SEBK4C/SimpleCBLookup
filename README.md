# SimpleCBLookup

A simple, powerful tool for downloading Crunchbase static export data and performing fast local queries using DuckDB.

## Installation

**Install from GitHub:**

```bash
# Clone the repository
git clone https://github.com/sebk4c/SimpleCBLookup.git

# Navigate to the project directory
cd SimpleCBLookup

# Make RUN.sh executable
chmod +x RUN.sh
```
## Quick Start

**Just run `./RUN.sh` - it shows an interactive menu!**

```bash
# Interactive menu (recommended)
./RUN.sh
```
### First-Time Setup

Follow the prompts to:
1. Install dependencies
2. Enter your API key
3. Download DATA
4. Automatically unzip files
5. Import to DuckDB
6. Test with a sample query

### Query a Company

```bash
./RUN.sh query tesla.com
./RUN.sh query apple.com
./RUN.sh query openai.com
```

### Bulk Query

Your CSV file should have a **URL column** (can be named: URL, Website, Domain, Website_URL, Site, or Web):

```csv
Company Name,Website,Industry
Tesla Inc,tesla.com,Automotive
Apple Inc,apple.com,Technology
OpenAI,openai.com,AI
```

**Example Headers Supported:**
```csv
Company,Website,Market          ✅ Works
Company_Name,URL,Industry       ✅ Works  
Firm,Website_URL,Sector         ✅ Works
Column_1,Column_2,Column_3      ⚠️ Needs a URL keyword
,Website,                       ✅ Auto-names empty columns
```

**Features:**
- ✅ Automatically finds the URL column
- ✅ Works with any CSV structure
- ✅ Processes all rows (one URL per row)
- ✅ Adds funding data to each row
- ✅ Handles empty/unheaded columns gracefully
- ✅ Interactive prompt to filter quarterly data by year (optional)

Run:
```bash
# Auto-detect CSV file
./RUN.sh INPUT/companies.csv
```

**Interactive Year Filter:**
After processing URLs, you'll be prompted to filter quarterly data:
```
============================================================
Quarterly Data Export Settings
============================================================
Found quarters from 2000 Q1 to 2025 Q4

Enter the oldest year to include in quarterly columns:
  - Press Enter for ALL quarters (default)
  - Or enter a year (e.g., 2010, 1990)

Oldest year (default=all): 
```

**Examples:**
- Press Enter → All quarters included (2010 Q1, 2011 Q1, ... 2025 Q4)
- Enter `2010` → Only quarters from 2010 onwards
- Enter `1990` → Only quarters from 1990 onwards

Output: Enhanced CSV written to `OUTPUT/` folder with:
- Original CSV structure preserved
- Additional columns appended: Company Information, Investment Rounds, Total Funding
- Quarterly funding breakdown columns (filtered by year if specified)

### Unzip Downloaded Files

After downloading collections, extract them before importing:

```bash
./RUN.sh unzip
```

This will unzip all files from `DATA/zips/` to `DATA/extracted_csvs/`.

### Check Status

```bash
# List all available collections
./RUN.sh list

# Check what's downloaded
./RUN.sh check

# Verify file integrity
./RUN.sh verify
```

## Documentation

For detailed information, see the **[DOCS](DOCS/)** directory:

- **[Menu System](DOCS/MENU_SYSTEM.md)** - Interactive menu guide ← **START HERE**
- **[Installation Guide](DOCS/INSTALLATION.md)** - Setup and dependencies
- **[Usage Guide](DOCS/USAGE.md)** - How to use the tool
- **[Examples](DOCS/EXAMPLES.md)** - Real-world examples
- **[Configuration](DOCS/CONFIGURATION.md)** - Settings and options
- **[API Reference](DOCS/API_REFERENCE.md)** - Technical details

## What is RUN.sh?

`RUN.sh` is the **centralized interactive menu system** for all SimpleCBLookup operations. It provides:

### Interactive Menu (Default)
Just run `./RUN.sh` to see a numbered menu:

**Setup & Data Management:**
- **1) Setup** - Complete installation and data download (includes automatic unzip)
- **2) Download Collections** - Download Crunchbase collections
- **3) Unzip All Files** - Extract CSV files from zips
- **4) Import to DuckDB** - Import data into database

**Query & Analysis:**
- **5) Query Company** - Query single company by URL
- **6) Bulk Query** - Process CSV with URLs (single row)
- **d) DuckDB UI** - Launch DuckDB web UI (browser-based)

**Information & Verification:**
- **7) List Collections** - List available collections
- **8) Check Downloaded** - Check download status
- **9) Verify Files** - Verify file integrity

**Other:**
- **a) Help** - Show help and documentation
- **0) Exit** - Quit program

### Command-Line Mode
Add arguments for automation:
- `./RUN.sh setup` - Run setup
- `./RUN.sh query tesla.com` - Query a company
- `./RUN.sh download --all` - Download all collections
- `./RUN.sh INPUT/companies.csv` - **Auto-detect CSV and run bulk query**

## Main Commands

| Command | Description |
|---------|-------------|
| `./RUN.sh setup` | Complete setup workflow (includes automatic unzip) |
| `./RUN.sh download` | Download Crunchbase collections |
| `./RUN.sh unzip` | Unzip all files in DATA/zips/ |
| `./RUN.sh import` | Import data to DuckDB |
| `./RUN.sh query <url>` | Query single company |
| `./RUN.sh bulk <csv>` | Bulk query from CSV (single row of URLs) |
| `./RUN.sh list` | List available collections |
| `./RUN.sh check` | Check download status |
| `./RUN.sh verify` | Verify file integrity |
| `./RUN.sh duckdb` | Launch DuckDB web UI |
| `./RUN.sh help` | Show help message |

## Project Structure

```
SimpleCBLookup/
├── RUN.sh                 # Main CLI entry point ← START HERE
├── DIR/                   # Temporary directories
├── DOCS/                  # Documentation
├── SRC/                   # Source code
├── SPEC/                  # Specifications
├── INPUT/                 # Input CSV files
├── OUTPUT/                # Output files
└── DATA/                  # Downloaded data (created on first run)
```

## Features

- ✅ **One-Click Setup** - Complete automation
- ✅ **Fast Local Queries** - No API limits
- ✅ **Bulk Processing** - Query hundreds of companies
- ✅ **Quarterly Breakdown** - Time-series analysis
- ✅ **File Verification** - Automatic integrity checks
- ✅ **Flexible Data Management** - Use existing or download fresh
- ✅ **Date-Stamped Databases** - Track data over time

## Requirements

- Python 3.8+
- Crunchbase API key ([get one here](https://data.crunchbase.com))
- Internet connection (for initial setup)

## Getting Help

```bash
# Show usage
./RUN.sh help

# Or
./RUN.sh
```

For detailed documentation:
- See files in [DOCS/](DOCS/)
- Check [API Reference](DOCS/API_REFERENCE.md)
- Review [Examples](DOCS/EXAMPLES.md)

## License

MIT

## Support

For issues with the Crunchbase API, visit: https://data.crunchbase.com/docs
