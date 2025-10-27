# Installation Guide

## Prerequisites

- Python 3.8 or higher
- A Crunchbase API key (get one from https://data.crunchbase.com)
- Internet connection for initial setup

## Quick Installation

### One-Click Setup

Simply run the setup command:

```bash
./RUN.sh setup
```

This will:
1. Install UV (fast Python package manager) if needed
2. Create a virtual environment
3. Install all dependencies
4. Prompt for your API key
5. Download Crunchbase data (or use existing data)
6. Import data into DuckDB
7. Test with a sample query

### Manual Installation

If you prefer manual installation:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install httpx typer rich duckdb python-dateutil

# Or use UV (faster)
uv pip install httpx typer rich duckdb python-dateutil
```

## Dependency Management

### Using UV (Recommended)

UV is a fast Python package manager that's 10-100x faster than pip.

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Install dependencies
uv pip install httpx typer rich duckdb python-dateutil
```

### Using pip

```bash
pip install httpx typer rich duckdb python-dateutil
```

## Project Structure

After installation, your project will have:

```
SimpleCBLookup/
├── DIR/              # Temporary directories
├── DOCS/             # Documentation
├── SRC/              # Source code
├── SPEC/             # Specifications
├── INPUT/            # Input CSV files
├── OUTPUT/           # Output files
├── data/             # Downloaded data (created on first run)
│   ├── zips/         # ZIP files
│   ├── extracted_csvs/  # Extracted CSVs
│   └── cb_data.*.duckdb  # DuckDB databases
├── RUN.sh            # Main CLI entry point
└── README.md         # Quick start guide
```

## API Key Setup

Set your Crunchbase API key as an environment variable:

```bash
export CRUNCHBASE_USER_KEY="your-api-key-here"
```

Or pass it via command-line arguments when prompted.

## Verification

After installation, verify everything works:

```bash
# Check available collections
./RUN.sh list

# Query a test company
./RUN.sh query tesla.com
```

## Troubleshooting

### Permission Denied Error

If you get a permission error when running `./RUN.sh`:

```bash
chmod +x RUN.sh
```

### Virtual Environment Issues

If the virtual environment isn't activating:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Missing Dependencies

If imports fail, reinstall dependencies:

```bash
source .venv/bin/activate
pip install --upgrade httpx typer rich duckdb python-dateutil
```

## Next Steps

After installation, see:
- [Usage Guide](USAGE.md) - How to use the tool
- [Configuration](CONFIGURATION.md) - Configuration options
- [Examples](EXAMPLES.md) - Example use cases

