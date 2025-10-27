#!/bin/bash

# SimpleCBLookup - Main Execution CLI
# This script serves as the primary entry point for all project functions

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directories
SRC_DIR="SRC"
DOCS_DIR="DOCS"
DATA_DIR="DATA"
INPUT_DIR="INPUT"
OUTPUT_DIR="OUTPUT"

# Print header
print_header() {
    echo ""
    echo "================================================================================"
    echo "  SimpleCBLookup - Crunchbase Data Query Tool"
    echo "================================================================================"
    echo ""
}

# Print usage
print_usage() {
    echo "Usage: ./RUN.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  setup              Run complete setup (install dependencies, download data, import to DuckDB)"
    echo "  download           Download Crunchbase collections"
    echo "  unzip              Unzip all files in DATA/zips/ to DATA/extracted_csvs/"
    echo "  import             Import downloaded data into DuckDB"
    echo "  query <url>        Query funding data for a company by URL"
    echo "  bulk <input.csv>   Bulk query multiple companies from CSV"
    echo "  list               List available collections"
    echo "  check              Check which collections are downloaded"
    echo "  verify             Verify integrity of downloaded files"
    echo "  duckdb             Launch DuckDB web UI"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./RUN.sh setup"
    echo "  ./RUN.sh unzip"
    echo "  ./RUN.sh query tesla.com"
    echo "  ./RUN.sh bulk INPUT/companies.csv"
    echo ""
}

# Check if SRC directory exists
check_src() {
    if [ ! -d "$SRC_DIR" ]; then
        echo -e "${RED}Error: SRC directory not found${NC}"
        echo "Please ensure the project structure is intact."
        exit 1
    fi
}

# Check if virtual environment exists
check_venv() {
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
        python3 -m venv .venv || {
            echo -e "${RED}Error: Could not create virtual environment${NC}"
            echo "Please ensure Python 3.8+ is installed"
            exit 1
        }
    fi
    
    echo "Activating virtual environment..."
    source .venv/bin/activate || {
        echo -e "${RED}Error: Could not activate virtual environment${NC}"
        exit 1
    }
    
    # Verify we're using venv python
    PYTHON_PATH=$(which python3)
    if [[ "$PYTHON_PATH" != *".venv"* ]]; then
        echo -e "${YELLOW}Warning: Not using venv Python, forcing...${NC}"
        PYTHON3="$PWD/.venv/bin/python3"
    else
        PYTHON3="python3"
    fi
}

# Install dependencies if needed
install_deps() {
    echo -e "${CYAN}Checking dependencies...${NC}"
    
    # Check if UV is available
    if command -v uv &> /dev/null; then
        echo "Using UV for package management..."
        uv pip install -r "$SRC_DIR/requirements.txt" 2>/dev/null || \
        uv pip install httpx typer rich duckdb python-dateutil
    else
        echo "Using pip for package management..."
        pip install -r "$SRC_DIR/requirements.txt" 2>/dev/null || \
        pip install httpx typer rich duckdb python-dateutil
    fi
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Setup command
cmd_setup() {
    print_header
    check_src
    check_venv
    install_deps
    setup_api_key
    
    echo -e "${GREEN}Running setup...${NC}"
    cd "$SRC_DIR"
    # Use venv python directly
    ../.venv/bin/python3 setup.py
    cd ..
    
    # Automatically unzip files after setup
    echo ""
    echo -e "${CYAN}Setup complete! Unzipping downloaded files...${NC}"
    cmd_unzip
}

# Download command
cmd_download() {
    print_header
    check_src
    check_venv
    setup_api_key
    
    echo -e "${GREEN}Starting download...${NC}"
    cd "$SRC_DIR"
    
    # Use venv python directly
    if [ "$1" == "--all" ]; then
        ../.venv/bin/python3 -m cb_downloader download --all "${@:2}"
    else
        ../.venv/bin/python3 -m cb_downloader download "$@"
    fi
    
    cd ..
}

# Unzip command
cmd_unzip() {
    print_header
    check_src
    
    echo -e "${GREEN}Unzipping all files in DATA/zips/...${NC}"
    
    ZIP_DIR="$DATA_DIR/zips"
    EXTRACT_DIR="$DATA_DIR/extracted_csvs"
    
    if [ ! -d "$ZIP_DIR" ]; then
        echo -e "${RED}Error: $ZIP_DIR not found${NC}"
        exit 1
    fi
    
    # Create extraction directory
    mkdir -p "$EXTRACT_DIR"
    
    # Count zip files
    zip_count=$(find "$ZIP_DIR" -name "*.zip" | wc -l | tr -d ' ')
    
    if [ "$zip_count" -eq 0 ]; then
        echo -e "${YELLOW}No zip files found in $ZIP_DIR${NC}"
        exit 0
    fi
    
    echo "Found $zip_count zip files"
    echo ""
    
    # Unzip each file
    processed=0
    skipped=0
    failed=0
    
    for zip_file in "$ZIP_DIR"/*.zip; do
        filename=$(basename "$zip_file")
        base_name="${filename%.zip}"
        
        # Check if CSV already exists
        existing_csv=$(find "$EXTRACT_DIR" -name "${base_name}.*.csv" 2>/dev/null | head -1)
        
        if [ -n "$existing_csv" ]; then
            echo -n "Skipping $filename (already extracted)... "
            skipped=$((skipped + 1))
            echo -e "${BLUE}⊘${NC}"
        else
            echo -n "Unzipping $filename... "
            
            if unzip -q -o "$zip_file" -d "$EXTRACT_DIR" 2>/dev/null; then
                processed=$((processed + 1))
                echo -e "${GREEN}✓${NC}"
            else
                failed=$((failed + 1))
                echo -e "${RED}✗${NC}"
            fi
        fi
    done
    
    echo ""
    echo -e "${GREEN}✓ Unzip complete!${NC}"
    echo "  Processed: $processed"
    if [ "$skipped" -gt 0 ]; then
        echo -e "  ${BLUE}Skipped (already extracted): $skipped${NC}"
    fi
    if [ "$failed" -gt 0 ]; then
        echo -e "  ${RED}Failed: $failed${NC}"
    fi
    echo ""
    echo "CSV files extracted to: $EXTRACT_DIR"
}

# DuckDB UI command
cmd_duckdb_ui() {
    print_header
    check_src
    check_venv
    
    echo -e "${GREEN}Launching DuckDB UI...${NC}"
    
    # Don't change directories - stay at project root where venv is
    
    # Find the latest database - check both DATA and data directories
    DB_FILES=""
    
    # Try uppercase DATA first
    if [ -d "$DATA_DIR" ]; then
        DB_PATTERN="$DATA_DIR/cb_data.*.duckdb"
        DB_FILES=$(ls -t $DB_PATTERN 2>/dev/null | head -1)
    fi
    
    # If not found, try lowercase data
    if [ -z "$DB_FILES" ] && [ -d "data" ]; then
        DB_PATTERN="data/cb_data.*.duckdb"
        DB_FILES=$(ls -t $DB_PATTERN 2>/dev/null | head -1)
    fi
    
    if [ -z "$DB_FILES" ]; then
        echo -e "${RED}Error: No DuckDB database found${NC}"
        echo "Please run 'import' first to create the database."
        exit 1
    fi
    
    echo "Using database: $DB_FILES"
    echo ""
    echo -e "${CYAN}Starting DuckDB UI...${NC}"
    echo ""
    echo -e "${BLUE}The DuckDB UI will open in your browser${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
    echo ""
    
    # Get absolute path to database
    DB_ABSOLUTE_PATH="$(cd "$(dirname "$DB_FILES")" && pwd)/$(basename "$DB_FILES")"
    
    # Use the venv Python (same pattern as other commands)
    PYTHON_CMD=".venv/bin/python3"
    
    # Try to use native duckdb command with -ui flag if available
    if command -v duckdb &> /dev/null; then
        echo -e "${CYAN}Using native DuckDB binary...${NC}"
        duckdb "$DB_ABSOLUTE_PATH" -ui 2>&1
    else
        # Fallback: Use Python to call start_ui()
        echo -e "${CYAN}Using Python fallback method...${NC}"
        $PYTHON_CMD -c "
import duckdb
import os
import sys
import traceback
import time

db_path = '$DB_ABSOLUTE_PATH'
print(f'Connecting to database: {db_path}')

try:
    con = duckdb.connect(db_path)
    print('✓ Database connected successfully')
except Exception as e:
    print(f'✗ Error connecting to database: {e}')
    traceback.print_exc()
    sys.exit(1)

# Install and start UI extension
print('\\nStarting DuckDB UI...')
print('Server logs will appear below:\\n')

try:
    # Call start_ui and capture output
    result = con.execute('CALL start_ui();').fetchall()
    print('UI command executed successfully')
    print(f'Result: {result}')
    
    # Try to get the URL/port info
    try:
        info = con.execute('SELECT * FROM pragma_ui_info();').fetchall()
        print(f'UI Info: {info}')
    except Exception as e:
        print(f'Could not get UI info: {e}')
    
    print('\\n' + '='*60)
    print('DuckDB UI Server Started')
    print('='*60)
    print('Keep this window open to keep the server running.')
    print('Press Ctrl+C to stop the server.')
    print('='*60 + '\\n')
    
    # Keep the connection alive
    import signal
    def signal_handler(sig, frame):
        print('\\nShutting down DuckDB UI server...')
        con.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep running
    while True:
        time.sleep(1)
        
except Exception as e:
    print(f'\\n✗ Error starting UI: {e}')
    print('\\nFull traceback:')
    traceback.print_exc()
    print('\\nPlease check:')
    print('1. DuckDB version >= 1.2.1')
    print('2. UI extension is available')
    print('3. No port conflicts')
    con.close()
    sys.exit(1)
" 2>&1
    fi
}

# Import command
cmd_import() {
    print_header
    check_src
    check_venv
    
    echo -e "${GREEN}Importing data to DuckDB...${NC}"
    cd "$SRC_DIR"
    # Use venv python directly
    ../.venv/bin/python3 localduck/import_to_duckdb.py
    cd ..
}

# Query command
cmd_query() {
    if [ -z "$1" ]; then
        echo -e "${RED}Error: URL required${NC}"
        echo "Usage: ./RUN.sh query <url>"
        exit 1
    fi
    
    check_src
    check_venv
    
    echo -e "${GREEN}Querying funding data for: $1${NC}"
    cd "$SRC_DIR"
    # Use venv python directly
    ../.venv/bin/python3 localduck/query_funding_by_url.py "$1"
    cd ..
}

# Bulk query command
cmd_bulk() {
    if [ -z "$1" ]; then
        echo -e "${RED}Error: Input CSV file required${NC}"
        echo "Usage: ./RUN.sh bulk <input.csv> [output.csv]"
        echo ""
        echo "Note: CSV must contain URLs in a SINGLE column only!"
        exit 1
    fi
    
    check_src
    check_venv
    
    # Create INPUT and OUTPUT directories if they don't exist
    mkdir -p "$INPUT_DIR" "$OUTPUT_DIR"
    
    # Check if file exists in INPUT directory or current directory
    if [ ! -f "$1" ] && [ ! -f "$INPUT_DIR/$1" ]; then
        echo -e "${RED}Error: File not found: $1${NC}"
        echo "Please ensure the file exists in INPUT/ or provide full path"
        exit 1
    fi
    
    # Use the file path directly or prepend INPUT_DIR
    if [ -f "$1" ]; then
        input_file="$1"
    else
        input_file="$INPUT_DIR/$1"
    fi
    
    echo -e "${GREEN}Bulk querying from: $input_file${NC}"
    echo -e "${YELLOW}Note: CSV must contain URLs in a SINGLE column only!${NC}"
    cd "$SRC_DIR"
    
    # Use venv python directly
    if [ -n "$2" ]; then
        ../.venv/bin/python3 bulk_funding_query.py "$input_file" "$2"
    else
        ../.venv/bin/python3 bulk_funding_query.py "$input_file"
    fi
    
    cd ..
}

# List command
cmd_list() {
    check_src
    check_venv
    setup_api_key
    
    echo -e "${GREEN}Listing available collections...${NC}"
    cd "$SRC_DIR"
    # Use venv python directly
    ../.venv/bin/python3 -m cb_downloader list "$@"
    cd ..
}

# Check command
cmd_check() {
    check_src
    check_venv
    
    echo -e "${GREEN}Checking downloaded collections...${NC}"
    cd "$SRC_DIR"
    # Use venv python directly
    ../.venv/bin/python3 -m cb_downloader check "$@"
    cd ..
}

# Verify command
cmd_verify() {
    check_src
    check_venv
    setup_api_key
    
    echo -e "${GREEN}Verifying file integrity...${NC}"
    cd "$SRC_DIR"
    # Use venv python directly
    ../.venv/bin/python3 -m cb_downloader verify "$@"
    cd ..
}


# Create requirements.txt if it doesn't exist
create_requirements() {
    if [ ! -f "$SRC_DIR/requirements.txt" ]; then
        cat > "$SRC_DIR/requirements.txt" << EOF
httpx>=0.24.0
typer>=0.9.0
rich>=13.0.0
duckdb>=0.9.0
python-dateutil>=2.8.0
python-dotenv>=1.0.0
EOF
    fi
}

# Check and setup API key
setup_api_key() {
    ENV_FILE=".env"
    
    # Check if .env file exists and has API key
    if [ -f "$ENV_FILE" ]; then
        if grep -q "CRUNCHBASE_USER_KEY=" "$ENV_FILE"; then
            # Load from .env
            export $(grep "CRUNCHBASE_USER_KEY=" "$ENV_FILE" | xargs)
            echo -e "${GREEN}✓ API key loaded from .env file${NC}"
            return 0
        fi
    fi
    
    # If no API key exists, prompt for it
    echo -e "${YELLOW}Crunchbase API key not found${NC}"
    echo "Get your API key from: https://data.crunchbase.com"
    echo ""
    read -p "Enter your Crunchbase API key: " api_key
    
    if [ -z "$api_key" ]; then
        echo -e "${RED}Error: API key is required${NC}"
        exit 1
    fi
    
    # Save to .env file
    echo "CRUNCHBASE_USER_KEY=$api_key" > "$ENV_FILE"
    export CRUNCHBASE_USER_KEY="$api_key"
    echo -e "${GREEN}✓ API key saved to .env file${NC}"
    echo ""
}

# Ask if user wants to return to menu
ask_return_to_menu() {
    echo ""
    read -p "Press Enter to return to menu... " dummy
    show_menu
}

# Show interactive menu
show_menu() {
    print_header
    echo -e "${CYAN}Main Menu - Select an option:${NC}"
    echo ""
    echo -e "${GREEN}Setup & Data Management:${NC}"
    echo "  1) Setup                 - Complete installation and data download"
    echo "  2) Download Collections  - Download Crunchbase collections"
    echo "  3) Unzip All Files       - Extract CSV files from zips"
    echo "  4) Import to DuckDB      - Import data into database"
    echo ""
    echo -e "${BLUE}Query & Analysis:${NC}"
    echo "  5) Query Company         - Query single company by URL"
    echo "  6) Bulk Query            - Process CSV with URLs (single row)"
    echo "  d) DuckDB UI             - Launch DuckDB web UI"
    echo ""
    echo -e "${YELLOW}Information & Verification:${NC}"
    echo "  7) List Collections      - List available collections"
    echo "  8) Check Downloaded     - Check download status"
    echo "  9) Verify Files         - Verify file integrity"
    echo ""
    echo -e "${CYAN}Other:${NC}"
    echo "  a) Help                 - Show help and documentation"
    echo "  0) Exit                 - Quit program"
    echo ""
    read -p "Enter your choice [0-9,a,d]: " choice
    echo ""
    
    case $choice in
        1)
            cmd_setup
            ask_return_to_menu
            ;;
        2)
            setup_api_key
            echo -e "${YELLOW}Enter collection name (or 'all' for all collections):${NC}"
            read -p "Collection: " collection
            if [ "$collection" = "all" ]; then
                cmd_download --all
            else
                cmd_download "$collection"
            fi
            ask_return_to_menu
            ;;
        3)
            cmd_unzip
            ask_return_to_menu
            ;;
        4)
            cmd_import
            ask_return_to_menu
            ;;
        5)
            read -p "Enter company URL: " url
            cmd_query "$url"
            ask_return_to_menu
            ;;
        6)
            read -p "Enter CSV file path: " csv_file
            cmd_bulk "$csv_file"
            ask_return_to_menu
            ;;
        7)
            setup_api_key
            cmd_list
            ask_return_to_menu
            ;;
        8)
            cmd_check
            ask_return_to_menu
            ;;
        9)
            setup_api_key
            cmd_verify
            ask_return_to_menu
            ;;
        d)
            cmd_duckdb_ui
            ask_return_to_menu
            ;;
        a)
            print_header
            print_usage
            echo ""
            echo -e "${CYAN}Documentation:${NC}"
            echo "  See DOCS/ directory for detailed documentation"
            echo "  - INSTALLATION.md"
            echo "  - USAGE.md"
            echo "  - EXAMPLES.md"
            echo "  - CONFIGURATION.md"
            echo "  - API_REFERENCE.md"
            ask_return_to_menu
            ;;
        0)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            echo ""
            sleep 1
            show_menu
            ;;
    esac
}

# Main script
main() {
    # Create requirements.txt if needed
    create_requirements
    
    # Create data directory structure
    mkdir -p "$DATA_DIR/zips" "$DATA_DIR/extracted_csvs" "$INPUT_DIR" "$OUTPUT_DIR"
    
    # If arguments provided, use command-line mode
    if [ $# -gt 0 ]; then
        # Check if first argument is a CSV file
        if [[ "$1" == *.csv ]] || [[ -f "$1" ]] && [[ "$1" == *.csv ]]; then
            # Auto-detect CSV file and run bulk query
            echo -e "${GREEN}Auto-detected CSV file: $1${NC}"
            echo -e "${YELLOW}Running bulk query...${NC}"
            cmd_bulk "$1" "$2"
        else
            # Regular command mode
            case "$1" in
                setup)
                    cmd_setup
                    ;;
                download)
                    cmd_download "${@:2}"
                    ;;
                unzip)
                    cmd_unzip
                    ;;
                import)
                    cmd_import
                    ;;
                query)
                    cmd_query "$2"
                    ;;
                bulk)
                    cmd_bulk "$2" "$3"
                    ;;
                list)
                    cmd_list "${@:2}"
                    ;;
                check)
                    cmd_check "${@:2}"
                    ;;
                verify)
                    cmd_verify "${@:2}"
                    ;;
                duckdb)
                    cmd_duckdb_ui
                    ;;
                help|--help|-h)
                    print_header
                    print_usage
                    ;;
                *)
                    echo -e "${RED}Unknown command: $1${NC}"
                    print_usage
                    exit 1
                    ;;
            esac
        fi
    else
        # No arguments - show interactive menu
        show_menu
    fi
}

# Run main function
main "$@"

