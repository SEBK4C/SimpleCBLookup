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
    
    # Check if data already exists
    data_dir = Path("data")
    zip_dir = Path("data/zips")
    manifest_path = Path("data/manifest.json")
    csv_dir = Path("data/extracted_csvs")
    
    use_existing_data = False
    
    if data_dir.exists() and zip_dir.exists() and manifest_path.exists():
        print("📦 Found existing data folder with downloaded files!")
        print(f"   Zips: {len(list(zip_dir.glob('*.zip')))} files")
        if csv_dir.exists():
            print(f"   Extracted CSVs: {len(list(csv_dir.glob('*.csv')))} files")
        
        print("\nOptions:")
        print("  1. Use existing data (skip download, import directly)")
        print("  2. Download fresh data (re-download everything)")
        
        choice = input("\nChoose an option (1 or 2): ").strip()
        
        if choice == '1':
            use_existing_data = True
            print("\n✓ Using existing data. Skipping download step.")
        elif choice == '2':
            print("\n✓ Will download fresh data.")
        else:
            print("❌ Invalid choice. Exiting.")
            sys.exit(1)
    
    if not use_existing_data:
        # Get API key (needed for downloading)
        print("\nEnter your Crunchbase API key:")
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
                ["python", "-m", "cb_downloader", "download", "--all", "--max-concurrency", "8"],
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
    else:
        print_header("Step 1 & 2: Using Existing Data")
        print("Skipping download step and using existing data from data/zips/")
    
    # Step 3: Import into DuckDB
    print_header("Step 3: Importing into DuckDB")
    
    # Check if data directory exists
    if not zip_dir.exists():
        print(f"❌ Error: Data directory {zip_dir} not found")
        print("   Make sure you downloaded collections in the previous step.")
        sys.exit(1)
    
    # Check if manifest exists
    if not manifest_path.exists():
        print(f"❌ Error: Manifest file {manifest_path} not found")
        print("   Make sure you downloaded collections in the previous step.")
        sys.exit(1)
    
    # Check if database already exists
    db_files = list(Path("data").glob("cb_data.*.duckdb"))
    has_extracted_csvs = csv_dir.exists() and len(list(csv_dir.glob("*.csv"))) > 0
    
    if db_files or has_extracted_csvs:
        print("\n📊 Found existing database or extracted CSVs!")
        if db_files:
            print(f"   Databases: {len(db_files)} files")
        if has_extracted_csvs:
            print(f"   Extracted CSVs: {len(list(csv_dir.glob('*.csv')))} files")
        
        print("\nOptions:")
        print("  1. Re-import (recreate database from scratch)")
        print("  2. Skip import (use existing database)")
        
        import_choice = input("\nChoose an option (1 or 2): ").strip()
        
        if import_choice == '2':
            print("\n✓ Skipping import. Using existing database.")
            skip_import = True
        else:
            print("\n✓ Will re-import data.")
            skip_import = False
    else:
        skip_import = False
    
    if not skip_import:
        # Import script now uses data/zips by default and reads manifest.json
        run_command(
            ["python", "localduck/import_to_duckdb.py"],
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
    
    # Only show API key message if we actually got one
    if not use_existing_data:
        print("\nYour API key is saved in the environment for this session.")
        print("To use it in future sessions, run:")
        print(f"  export CRUNCHBASE_USER_KEY='{api_key}'")

if __name__ == "__main__":
    main()
