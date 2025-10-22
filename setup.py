#!/usr/bin/env python3
"""
Setup script for SimpleCBLookup.
Downloads Crunchbase data, imports into DuckDB, and tests with tesla.com
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n➜ {description}...")
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ Error: {description} failed!")
        sys.exit(1)
    
    print(f"✓ {description} completed successfully")

def main():
    print_header("SimpleCBLookup Setup")
    
    # Get API key
    print("Enter your Crunchbase API key:")
    print("(You can get one from https://data.crunchbase.com)")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("❌ Error: API key is required")
        sys.exit(1)
    
    # Set environment variable
    os.environ["CRUNCHBASE_USER_KEY"] = api_key
    
    # Step 1: Check available collections
    print_header("Step 1: Checking Available Collections")
    run_command(
        ["python", "-m", "cb_downloader", "list"],
        "Checking available collections"
    )
    
    # Step 2: Download collections
    print_header("Step 2: Downloading Collections")
    response = input("\nDownload all collections? This may take a while. (y/n): ").strip().lower()
    
    if response == 'y':
        print("\nDownloading all collections...")
        print("Note: This may take 30+ minutes depending on your connection speed.")
        run_command(
            ["python", "-m", "cb_downloader", "download", "--all"],
            "Downloading all collections"
        )
    else:
        print("\nDownloading essential collections only (organizations, funding_rounds)...")
        run_command(
            ["python", "-m", "cb_downloader", "download", "organizations"],
            "Downloading organizations"
        )
        run_command(
            ["python", "-m", "cb_downloader", "download", "funding_rounds"],
            "Downloading funding_rounds"
        )
    
    # Step 3: Import into DuckDB
    print_header("Step 3: Importing into DuckDB")
    
    # Find the data directory
    zip_dir = Path("data/zips")
    if not zip_dir.exists():
        print(f"❌ Error: Data directory {zip_dir} not found")
        sys.exit(1)
    
    run_command(
        ["python", "localduck/import_to_duckdb.py", str(zip_dir)],
        "Importing data into DuckDB"
    )
    
    # Step 4: Test query
    print_header("Step 4: Testing Query with Tesla")
    run_command(
        ["python", "localduck/query_funding_by_url.py", "tesla.com"],
        "Querying Tesla's funding data"
    )
    
    # Success message
    print_header("Setup Complete!")
    print("✓ Your Crunchbase data is now ready to use!")
    print("\nTo query other companies:")
    print("  python localduck/query_funding_by_url.py <company-url>")
    print("\nTo download more collections:")
    print("  python -m cb_downloader download <collection-name>")
    print("\nYour API key is saved in the environment for this session.")
    print("To use it in future sessions, run:")
    print(f"  export CRUNCHBASE_USER_KEY='{api_key}'")

if __name__ == "__main__":
    main()

