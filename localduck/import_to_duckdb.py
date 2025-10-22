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

def get_zip_files(zip_dir: str) -> List[str]:
    """Get all zip files in the directory."""
    return sorted(glob.glob(os.path.join(zip_dir, "*.zip")))

def extract_csv_from_zip(zip_path: str, extract_dir: str) -> str:
    """Extract CSV from zip file and return the CSV path."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get the CSV file inside the zip
        csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
        if not csv_files:
            raise ValueError(f"No CSV file found in {zip_path}")
        
        csv_filename = csv_files[0]
        zip_ref.extract(csv_filename, extract_dir)
        return os.path.join(extract_dir, csv_filename)

def import_csv_to_duckdb(csv_path: str, table_name: str, db_path: str = "localduck.duckdb"):
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
    
    # Configuration - accept command-line argument for zip directory
    if len(sys.argv) > 1:
        zip_dir = sys.argv[1]
    else:
        zip_dir = "CB-zips-date-2025-08-22"
    
    extract_dir = "extracted_csvs"
    db_path = "localduck.duckdb"
    
    print(f"Using zip directory: {zip_dir}")
    
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
            # Extract CSV
            csv_path = extract_csv_from_zip(zip_path, extract_dir)
            
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

