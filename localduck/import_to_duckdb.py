#!/usr/bin/env python3
"""
Import all CB zip CSV files into DuckDB.
"""

import os
import zipfile
import duckdb
from pathlib import Path
from typing import List
import glob
import json
import hashlib
from datetime import datetime

def load_manifest(manifest_path: str = "data/manifest.json") -> dict:
    """Load the manifest.json file to get data dates."""
    with open(manifest_path, 'r') as f:
        return json.load(f)

def get_data_date(manifest: dict) -> str:
    """Extract the date from the manifest's last_modified field."""
    # Get the first entry's last_modified to determine the date
    first_entry = next(iter(manifest.values()))
    last_modified = first_entry['last_modified']
    # Parse the ISO datetime and extract just the date part
    dt = datetime.fromisoformat(last_modified.replace('+00:00', ''))
    return dt.strftime('%Y-%m-%d')

def get_zip_files(zip_dir: str) -> List[str]:
    """Get all zip files in the directory."""
    return sorted(glob.glob(os.path.join(zip_dir, "*.zip")))

def extract_csv_from_zip(zip_path: str, extract_dir: str, date_str: str) -> str:
    """Extract CSV from zip file, rename with date, and return the CSV path."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get the CSV file inside the zip
        csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
        if not csv_files:
            raise ValueError(f"No CSV file found in {zip_path}")
        
        csv_filename = csv_files[0]
        
        # Extract CSV
        from io import BytesIO
        csv_data = zip_ref.read(csv_filename)
        
        # Generate hash for the content
        content_hash = hashlib.md5(csv_data).hexdigest()[:8]
        
        # Create new filename with date and hash
        table_name = os.path.splitext(os.path.basename(zip_path))[0]
        new_csv_filename = f"{table_name}.{date_str}.{content_hash}.csv"
        new_csv_path = os.path.join(extract_dir, new_csv_filename)
        
        # Write the extracted CSV with the new name
        with open(new_csv_path, 'wb') as f:
            f.write(csv_data)
        
        return new_csv_path

def import_csv_to_duckdb(csv_path: str, table_name: str, db_path: str):
    """Import a CSV file into DuckDB."""
    print(f"Importing {csv_path} into table '{table_name}'...")
    
    conn = duckdb.connect(db_path)
    
    # Use READ_CSV to create table from CSV
    # This handles schema inference automatically
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} AS 
        SELECT * FROM read_csv_auto('{csv_path}')
    """)
    
    # Get row count
    result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    print(f"  ✓ Imported {result[0]:,} rows into '{table_name}'")
    
    conn.close()

def main():
    import sys
    
    # Load manifest to get the data date
    manifest = load_manifest()
    date_str = get_data_date(manifest)
    
    print(f"Data date from manifest: {date_str}")
    
    # Configuration - use data folder structure
    zip_dir = "data/zips"
    extract_dir = "data/extracted_csvs"
    db_filename = f"cb_data.{date_str}.duckdb"
    db_path = os.path.join("data", db_filename)
    
    print(f"Using zip directory: {zip_dir}")
    print(f"Extracting CSVs to: {extract_dir}")
    print(f"Creating database: {db_path}\n")
    
    # Create extraction directory
    os.makedirs(extract_dir, exist_ok=True)
    
    # Get all zip files
    zip_files = get_zip_files(zip_dir)
    print(f"Found {len(zip_files)} zip files to process\n")
    
    # Process each zip file
    for zip_path in zip_files:
        zip_filename = os.path.basename(zip_path)
        table_name = os.path.splitext(zip_filename)[0]  # Remove .zip extension
        
        try:
            # Extract CSV with date and hash in filename
            csv_path = extract_csv_from_zip(zip_path, extract_dir, date_str)
            
            # Import to DuckDB
            import_csv_to_duckdb(csv_path, table_name, db_path)
            
        except Exception as e:
            print(f"  ✗ Error processing {zip_filename}: {e}")
    
    print(f"\n✓ Import complete! Database saved to: {db_path}")
    
    # Show summary
    conn = duckdb.connect(db_path)
    tables = conn.execute("SHOW TABLES").fetchall()
    print(f"\nTotal tables created: {len(tables)}")
    print("\nTables:")
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
        print(f"  - {table[0]}: {count:,} rows")
    conn.close()

if __name__ == "__main__":
    main()

