#!/usr/bin/env python3
"""
Setup script for SimpleCBLookup.
Downloads Crunchbase data, imports into DuckDB, and tests with tesla.com
"""

import os
import sys
import subprocess
from pathlib import Path

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip

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
    
    # Get the python executable that's running this script (should be venv python)
    import sys
    venv_python = sys.executable
    
    # Check if DATA already exists (one level up from SRC)
    data_dir = Path("../DATA")
    zip_dir = Path("../DATA/zips")
    manifest_path = Path("../DATA/manifest.json")
    csv_dir = Path("../DATA/extracted_csvs")
    
    use_existing_data = False
    fix_corrupted = False
    download_missing = False
    api_key = None
    missing_collections = []
    
    zip_files = list(zip_dir.glob("*.zip")) if zip_dir.exists() else []
    if data_dir.exists() and zip_files:
        print("📦 Found existing data folder with downloaded files!")
        print(f"   Zips: {len(zip_files)} files")
        if csv_dir.exists():
            print(f"   Extracted CSVs: {len(list(csv_dir.glob('*.csv')))} files")
        
        # First, check which collections are missing
        print("\n🔍 Checking collection completeness...")
        print(f"Running: {venv_python} -m cb_downloader check")
        check_result = subprocess.run(
            [venv_python, "-m", "cb_downloader", "check"],
            capture_output=True,
            text=True
        )
        print(check_result.stdout)
        if check_result.stderr:
            print(check_result.stderr)
        
        if check_result.returncode == 0:
            print("✓ Collection check completed")
        
        # Extract missing collections from the output
        extracted_missing = []
        for line in check_result.stdout.split('\n'):
            if '✗ Missing' in line or '[red]✗ Missing[/red]' in line:
                # Extract collection name from the table row
                # Format: "| Collection Name | [red]✗ Missing[/red] | File |"
                parts = line.split('|')
                if len(parts) >= 2:
                    collection_name = parts[1].strip()
                    # Only add if it's not empty and not a header row
                    if collection_name and collection_name != 'Collection':
                        extracted_missing.append(collection_name)
        missing_collections = extracted_missing
        
        # First, verify existing files (without fix, since we don't have API key yet)
        print("\n🔍 Verifying existing files...")
        print(f"Running: {venv_python} -m cb_downloader verify --quick")
        result = subprocess.run(
            [venv_python, "-m", "cb_downloader", "verify", "--quick"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("✓ File verification completed")
        
        # Check if there are corrupted files
        has_corrupted = "corrupted file(s)" in result.stdout or "Found" in result.stdout and "corrupted" in result.stdout
        
        # Show summary of missing collections
        if missing_collections:
            print(f"\n⚠️  Missing {len(missing_collections)} collection(s) to complete the dataset:")
            for coll in missing_collections[:10]:  # Show first 10
                print(f"   - {coll}")
            if len(missing_collections) > 10:
                print(f"   ... and {len(missing_collections) - 10} more")
        else:
            print("\n✓ All collections are downloaded!")
        
        print("\nOptions:")
        print("  1. Use existing data (skip download, import directly)")
        print("  2. Download fresh data (re-download everything)")
        if missing_collections:
            print("  3. Download missing collections only (complete the dataset)")
        if has_corrupted:
            print("  4. Fix corrupted files only (re-download corrupted files)")
        
        if missing_collections and has_corrupted:
            max_option = "4"
        elif missing_collections or has_corrupted:
            max_option = "3"
        else:
            max_option = "2"
        
        choice = input(f"\nChoose an option (1-{max_option}): ").strip()
        
        if choice == '1':
            use_existing_data = True
            print("\n✓ Using existing data. Skipping download step.")
        elif choice == '2':
            print("\n✓ Will download fresh data.")
        elif choice == '3' and missing_collections:
            print("\n✓ Will download missing collections only.")
            download_missing = True
        elif choice == '3' and has_corrupted:
            print("\n✓ Will fix corrupted files only.")
            fix_corrupted = True
        elif choice == '4' and has_corrupted:
            print("\n✓ Will fix corrupted files only.")
            fix_corrupted = True
        else:
            print("❌ Invalid choice. Exiting.")
            sys.exit(1)
    
    if fix_corrupted:
        # Check if API key is already in environment (from .env)
        api_key = os.getenv("CRUNCHBASE_USER_KEY")
        
        if not api_key:
            # Get API key (needed for fixing corrupted files)
            print("\nEnter your Crunchbase API key:")
            print("(You can get one from https://data.crunchbase.com)")
            api_key = input("API Key: ").strip()
            
            if not api_key:
                print("❌ Error: API key is required")
                sys.exit(1)
            
            # Set environment variable
            os.environ["CRUNCHBASE_USER_KEY"] = api_key
        
        # Step 1 & 2: Fix corrupted files
        print_header("Step 1 & 2: Fixing Corrupted Files")
        run_command(
            [venv_python, "-m", "cb_downloader", "verify", "--fix"],
            "Fixing corrupted files"
        )
        use_existing_data = True  # After fixing, we're using existing data
    elif download_missing:
        # Check if API key is already in environment (from .env)
        api_key = os.getenv("CRUNCHBASE_USER_KEY")
        
        if not api_key:
            # Get API key (needed for downloading)
            print("\nEnter your Crunchbase API key:")
            print("(You can get one from https://data.crunchbase.com)")
            api_key = input("API Key: ").strip()
            
            if not api_key:
                print("❌ Error: API key is required")
                sys.exit(1)
            
            # Set environment variable
            os.environ["CRUNCHBASE_USER_KEY"] = api_key
        
        # Step 1 & 2: Download missing collections
        print_header("Step 1 & 2: Downloading Missing Collections")
        print(f"Downloading {len(missing_collections)} missing collection(s)...")
        print("Note: This may take a while depending on your connection speed.")
        
        # Download each missing collection
        for coll in missing_collections:
            run_command(
                [venv_python, "-m", "cb_downloader", "download", coll],
                f"Downloading {coll}"
            )
        
        use_existing_data = True  # After downloading missing, we're using existing data
    elif not use_existing_data:
        # Check if API key is already in environment (from .env)
        api_key = os.getenv("CRUNCHBASE_USER_KEY")
        
        if not api_key:
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
            [venv_python, "-m", "cb_downloader", "list"],
            "Checking available collections"
        )
        
        # Step 2: Download collections
        print_header("Step 2: Downloading Collections")
        response = input("\nDownload all collections? This may take a while. (y/n): ").strip().lower()
        
        if response == 'y':
            print("\nDownloading all collections...")
            print("Note: This may take 30+ minutes depending on your connection speed.")
            run_command(
                [venv_python, "-m", "cb_downloader", "download", "--all", "--max-concurrency", "8"],
                "Downloading all collections"
            )
        else:
            print("\nDownloading essential collections only (organizations, funding_rounds)...")
            run_command(
                [venv_python, "-m", "cb_downloader", "download", "organizations"],
                "Downloading organizations"
            )
            run_command(
                [venv_python, "-m", "cb_downloader", "download", "funding_rounds"],
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
    db_files = list(Path("../DATA").glob("cb_data.*.duckdb"))
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
        # Use venv python directly to ensure correct interpreter
        import sys
        venv_python = sys.executable  # Use the python that's running this script
        run_command(
            [venv_python, "localduck/import_to_duckdb.py"],
            "Importing data into DuckDB"
        )
    
    # Step 4: Test query
    print_header("Step 4: Testing Query with Tesla")
    run_command(
        [venv_python, "localduck/query_funding_by_url.py", "tesla.com"],
        "Querying Tesla's funding data"
    )
    
    # Success message
    print_header("Setup Complete!")
    print("✓ Your Crunchbase data is now ready to use!")
    print("\nTo query other companies:")
    print("  ./RUN.sh query <company-url>")
    print("\nTo download more collections:")
    print("  ./RUN.sh download <collection-name>")
    
    # Only show API key message if we actually got one
    if api_key:
        print("\nYour API key is saved in the environment for this session.")
        print("To use it in future sessions, run:")
        print(f"  export CRUNCHBASE_USER_KEY='{api_key}'")

if __name__ == "__main__":
    main()
