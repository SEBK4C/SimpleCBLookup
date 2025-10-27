#!/usr/bin/env python3
"""
Bulk query funding data for multiple companies from a CSV of URLs or a single URL.
Outputs a CSV with quarterly funding breakdown.
"""

import duckdb
import csv
import re
import os
import glob
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import sys


def sanitize_filename(filename: str) -> str:
    """Sanitize a string to be used as a filename."""
    # Remove protocol if present
    filename = re.sub(r'^https?://', '', filename)
    # Remove www
    filename = re.sub(r'^www\.', '', filename)
    # Remove trailing slash
    filename = filename.rstrip('/')
    # Remove path
    filename = filename.split('/')[0]
    # Replace invalid filename characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename


def find_database() -> Optional[str]:
    """Find the latest DuckDB database in the DATA folder."""
    # Look for databases matching the pattern cb_data.YYYY-MM-DD.duckdb
    db_pattern = os.path.join("../DATA", "cb_data.*.duckdb")
    db_files = glob.glob(db_pattern)
    
    if not db_files:
        return None
    
    # Return the most recent one (assuming sorted by date)
    return sorted(db_files)[-1]


def normalize_url(url: str) -> str:
    """Normalize URL for matching."""
    # Remove protocol
    url = re.sub(r'^https?://', '', url)
    # Remove www
    url = re.sub(r'^www\.', '', url)
    # Remove trailing slash
    url = url.rstrip('/')
    # Remove path
    url = url.split('/')[0]
    return url.lower()

def find_url_column(header_row: List[str]) -> int:
    """Find the URL column index by looking for common patterns."""
    # Primary keywords for URL columns
    url_keywords = ['url', 'website', 'domain', 'website_url', 'site', 'web']
    
    # Secondary keywords that might contain URLs
    secondary_keywords = ['company_url', 'firm', 'organization']
    
    found_indices = []
    for idx, col_name in enumerate(header_row):
        col_lower = col_name.lower().strip()
        
        # Skip empty headers
        if not col_lower:
            continue
            
        # Check primary keywords
        if any(keyword in col_lower for keyword in url_keywords):
            found_indices.append(idx)
        # Check secondary keywords (but with lower priority)
        elif any(keyword in col_lower for keyword in secondary_keywords):
            found_indices.append(idx)
    
    if len(found_indices) == 0:
        return None  # No URL column found
    elif len(found_indices) > 1:
        # Try to be smart - prefer columns with "url" or "website" in name
        priority_indices = [idx for idx in found_indices 
                           if any(kw in header_row[idx].lower() for kw in ['url', 'website'])]
        if len(priority_indices) == 1:
            return priority_indices[0]
        return -1  # Multiple URL columns found (error)
    else:
        return found_indices[0]  # Found exactly one URL column


def find_organization_by_url(db_path: str, url: str) -> Optional[Dict]:
    """Find organization in database by URL."""
    conn = duckdb.connect(db_path)
    
    # Normalize the search URL
    normalized_search = normalize_url(url)
    
    # Try to find exact match first
    query = """
        SELECT 
            "identifier.value" as name,
            website,
            website_url,
            "identifier.uuid" as uuid,
            description,
            short_description,
            "founded_on.value" as founded_on,
            "categories.value" as categories,
            "category_groups.value" as category_groups,
            "location_identifiers.value" as location,
            investor_stage,
            funding_stage,
            "funding_total.value_usd" as total_funding_usd,
            num_funding_rounds,
            num_investors
        FROM organizations
        WHERE LOWER(website) LIKE ?
           OR LOWER(website_url) LIKE ?
           OR LOWER(website) LIKE ?
           OR LOWER(website_url) LIKE ?
        LIMIT 1
    """
    
    # Create multiple LIKE patterns
    pattern1 = f"%{normalized_search}%"
    pattern2 = f"%{url.lower()}%"
    
    result = conn.execute(query, [pattern1, pattern1, pattern2, pattern2]).fetchone()
    conn.close()
    
    if result:
        return {
            'name': result[0],
            'website': result[1],
            'website_url': result[2],
            'uuid': result[3],
            'description': result[4],
            'short_description': result[5],
            'founded_on': result[6],
            'categories': result[7],
            'category_groups': result[8],
            'location': result[9],
            'investor_stage': result[10],
            'funding_stage': result[11],
            'total_funding_usd': result[12],
            'num_funding_rounds': result[13],
            'num_investors': result[14]
        }
    return None


def get_funding_rounds_with_investors(db_path: str, organization_uuid: str) -> List[Dict]:
    """Get all funding rounds with investor details for an organization."""
    conn = duckdb.connect(db_path)
    
    # Get funding rounds
    query = """
        SELECT 
            fr."identifier.value" as round_name,
            fr.announced_on,
            fr."closed_on.value" as closed_on,
            fr."money_raised.value_usd" as amount_usd,
            fr."money_raised.currency" as currency,
            fr.investment_type,
            fr.investment_stage as stage,
            fr.num_investors,
            fr."post_money_valuation.value_usd" as post_money_valuation_usd,
            fr."pre_money_valuation.value_usd" as pre_money_valuation_usd,
            fr.short_description,
            fr."identifier.uuid" as round_uuid
        FROM funding_rounds fr
        WHERE fr."funded_organization_identifier.uuid" = ?
        ORDER BY fr.announced_on DESC, fr."closed_on.value" DESC
    """
    
    rounds = conn.execute(query, [organization_uuid]).fetchall()
    
    # Get investors for each round
    funding_rounds = []
    for row in rounds:
        round_uuid = row[11]
        
        # Get investors for this round
        investor_query = """
            SELECT 
                i."investor_identifier.value" as investor_name,
                i.is_lead_investor,
                i."money_invested.value_usd" as amount_invested
            FROM investments i
            WHERE i."funding_round_identifier.uuid" = ?
            ORDER BY i.is_lead_investor DESC, i."investor_identifier.value"
        """
        
        investors = conn.execute(investor_query, [round_uuid]).fetchall()
        
        funding_rounds.append({
            'round_name': row[0],
            'announced_on': row[1],
            'closed_on': row[2],
            'amount_usd': row[3],
            'currency': row[4],
            'investment_type': row[5],
            'stage': row[6],
            'num_investors': row[7],
            'post_money_valuation_usd': row[8],
            'pre_money_valuation_usd': row[9],
            'short_description': row[10],
            'investors': investors
        })
    
    conn.close()
    return funding_rounds


def get_quarter(date_value: date) -> str:
    """Get quarter string from date (e.g., 2025 Q1)."""
    if not date_value:
        return None
    
    quarter = (date_value.month - 1) // 3 + 1
    year = date_value.year
    return f"{year} Q{quarter}"


def parse_quarter(quarter_str: str) -> Tuple[int, int]:
    """Parse a quarter string (e.g., '2025 Q1') into (year, quarter) tuple."""
    # Try new format: "2025 Q1"
    match = re.match(r'(\d{4}) Q(\d+)', quarter_str)
    if match:
        year = int(match.group(1))
        quarter_num = int(match.group(2))
        return (year, quarter_num)
    
    # Fallback to old format: "Q4-25" (for backward compatibility)
    match = re.match(r'Q(\d+)-(\d+)', quarter_str)
    if match:
        quarter_num = int(match.group(1))
        year_short = int(match.group(2))
        
        # Convert 2-digit year to 4-digit year
        # Assume years 00-50 are 2000-2050, and 51-99 are 1951-1999
        if year_short <= 50:
            year = 2000 + year_short
        else:
            year = 1900 + year_short
        
        return (year, quarter_num)
    return (0, 0)


def sort_quarters_chronologically(quarters: List[str], reverse: bool = True) -> List[str]:
    """Sort quarters chronologically, newest first by default."""
    return sorted(quarters, key=parse_quarter, reverse=reverse)


def get_quarters_from_to(start_date: date, end_date: date) -> List[str]:
    """Generate list of quarters from start_date to end_date."""
    quarters = []
    current = start_date
    end = end_date
    
    while current <= end:
        quarter = get_quarter(current)
        if quarter and quarter not in quarters:
            quarters.append(quarter)
        # Move to next quarter
        current = current + relativedelta(months=3)
        # Set to first month of quarter
        current = current.replace(day=1)
    
    return quarters


def process_company(db_path: str, url: str) -> Optional[Dict]:
    """Process a single company and return all data."""
    # Find organization
    org = find_organization_by_url(db_path, url)
    
    if not org:
        return None
    
    # Get founding date
    founded_on = org['founded_on']
    if not founded_on:
        founded_on = date(1900, 1, 1)  # Default if no founding date
    
    # Get funding rounds with investors
    funding_rounds = get_funding_rounds_with_investors(db_path, org['uuid'])
    
    # Calculate total funding
    total_funding = sum(r['amount_usd'] for r in funding_rounds if r['amount_usd'])
    
    # Create company info string
    company_info_parts = []
    if org['name']:
        company_info_parts.append(f"Name: {org['name']}")
    if org['short_description']:
        company_info_parts.append(f"Description: {org['short_description']}")
    if org['description']:
        company_info_parts.append(f"Full Description: {org['description']}")
    if founded_on:
        company_info_parts.append(f"Founded: {founded_on}")
    if org['categories']:
        company_info_parts.append(f"Categories: {org['categories']}")
    if org['category_groups']:
        company_info_parts.append(f"Category Groups: {org['category_groups']}")
    if org['location']:
        company_info_parts.append(f"Location: {org['location']}")
    if org['funding_stage']:
        company_info_parts.append(f"Funding Stage: {org['funding_stage']}")
    if org['investor_stage']:
        company_info_parts.append(f"Investor Stage: {org['investor_stage']}")
    if org['num_funding_rounds']:
        company_info_parts.append(f"Number of Funding Rounds: {org['num_funding_rounds']}")
    if org['num_investors']:
        company_info_parts.append(f"Number of Investors: {org['num_investors']}")
    
    company_info = " | ".join(company_info_parts)
    
    # Create funding rounds info string
    funding_info_parts = []
    for round_data in funding_rounds:
        round_text = f"[{round_data['round_name']}]"
        
        if round_data['announced_on']:
            round_text += f" Announced: {round_data['announced_on']}"
        if round_data['closed_on']:
            round_text += f" Closed: {round_data['closed_on']}"
        if round_data['amount_usd']:
            round_text += f" Amount: ${round_data['amount_usd']:,.0f}"
        if round_data['investment_type']:
            round_text += f" Type: {round_data['investment_type']}"
        if round_data['stage']:
            round_text += f" Stage: {round_data['stage']}"
        if round_data['post_money_valuation_usd']:
            round_text += f" Post-Money Valuation: ${round_data['post_money_valuation_usd']:,.0f}"
        if round_data['pre_money_valuation_usd']:
            round_text += f" Pre-Money Valuation: ${round_data['pre_money_valuation_usd']:,.0f}"
        
        # Add investors
        if round_data['investors']:
            investors_list = []
            for inv in round_data['investors']:
                inv_name = inv[0] if inv[0] else "Unknown"
                is_lead = inv[1]
                inv_amount = inv[2]
                
                investor_str = inv_name
                if is_lead:
                    investor_str += " (Lead)"
                if inv_amount:
                    investor_str += f" (${inv_amount:,.0f})"
                investors_list.append(investor_str)
            
            round_text += f" Investors: {', '.join(investors_list)}"
        
        if round_data['short_description']:
            round_text += f" Details: {round_data['short_description']}"
        
        funding_info_parts.append(round_text)
    
    funding_info = " | ".join(funding_info_parts)
    
    # Generate quarterly funding breakdown
    today = date.today()
    quarters = get_quarters_from_to(founded_on, today)
    
    # Group funding by quarter
    quarterly_funding = {}
    for round_data in funding_rounds:
        if not round_data['amount_usd']:
            continue
        
        # Use closed_on date, fallback to announced_on
        round_date = round_data['closed_on'] or round_data['announced_on']
        if not round_date:
            continue
        
        quarter = get_quarter(round_date)
        if quarter:
            if quarter not in quarterly_funding:
                quarterly_funding[quarter] = 0
            quarterly_funding[quarter] += round_data['amount_usd']
    
    return {
        'url': url,
        'company_info': company_info,
        'funding_info': funding_info,
        'total_funding': total_funding,
        'founded_on': founded_on,
        'quarters': quarters,
        'quarterly_funding': quarterly_funding
    }


def bulk_process_csv(db_path: str, input_file: str, output_file: str):
    """Process CSV file row by row, finding URLs and adding funding data."""
    today = date.today()
    
    # Read the original CSV
    original_rows = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        original_rows = list(reader)
    
    if not original_rows:
        print("❌ CSV file is empty")
        return
    
    # Find URL column
    header_row = original_rows[0]
    
    # Clean header row - remove empty entries and normalize
    cleaned_header = [col.strip() if col else f'Column_{i+1}' for i, col in enumerate(header_row)]
    
    url_col_idx = find_url_column(cleaned_header)
    
    if url_col_idx is None:
        print("❌ Error: No URL column found!")
        print("   Please add a column with one of these names:")
        print("   URL, Website, Domain, Website_URL, Site, Web, Company_URL")
        print(f"   Current headers: {cleaned_header}")
        return
    
    if url_col_idx == -1:
        print("❌ Error: Multiple URL columns found!")
        print("   Please ensure there is only ONE column containing URLs.")
        print(f"   Header row: {cleaned_header}")
        return
    
    print(f"✓ Found URL column: '{cleaned_header[url_col_idx]}' (column {url_col_idx + 1})")
    
    # Process each data row
    enhanced_rows = []
    all_quarters = set()
    
    for row_idx, row in enumerate(original_rows[1:], start=1):
        # Get URL from the identified column
        if len(row) <= url_col_idx:
            print(f"  Row {row_idx}: Skipping (no URL in column)")
            enhanced_rows.append({
                'row': row,
                'result': None
            })
            continue
        
        url = row[url_col_idx].strip()
        if not url:
            print(f"  Row {row_idx}: Skipping (empty URL)")
            enhanced_rows.append({
                'row': row,
                'result': None
            })
            continue
        
        print(f"  Row {row_idx}: Processing {url}")
        result = process_company(db_path, url)
        
        if result:
            company_name = result['company_info'].split('Name: ')[1].split(' |')[0] if 'Name: ' in result['company_info'] else 'Unknown'
            print(f"    ✓ Found: {company_name}")
            
            # Collect quarters for later column generation
            all_quarters.update(result['quarters'])
            
            # Store enhanced row data
            enhanced_rows.append({
                'row': row,
                'result': result
            })
        else:
            print(f"    ✗ Not found")
            enhanced_rows.append({
                'row': row,
                'result': None
            })
    
    # Sort quarters chronologically - newest first
    all_quarters = sort_quarters_chronologically(list(all_quarters), reverse=True)
    
    # Ask user for oldest year to include
    print(f"\n{'='*60}")
    print("Quarterly Data Export Settings")
    print(f"{'='*60}")
    print(f"Found quarters from {all_quarters[-1]} to {all_quarters[0]}")
    print("\nEnter the oldest year to include in quarterly columns:")
    print("  - Press Enter for ALL quarters (default)")
    print("  - Or enter a year (e.g., 2010, 1990)")
    
    user_input = input("\nOldest year (default=all): ").strip()
    
    if user_input:
        try:
            oldest_year = int(user_input)
            # Filter quarters to only include those >= oldest_year
            filtered_quarters = [q for q in all_quarters if parse_quarter(q)[0] >= oldest_year]
            if filtered_quarters:
                all_quarters = filtered_quarters
                print(f"✓ Filtered to quarters from {all_quarters[-1]} onwards")
            else:
                print(f"⚠️  No quarters found for year {oldest_year} or later")
                print("   Using all quarters instead")
        except ValueError:
            print(f"⚠️  Invalid year input: '{user_input}'")
            print("   Using all quarters instead")
    else:
        print("✓ Using all quarters")
    
    # Write enhanced CSV
    print(f"\nWriting results to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Create enhanced header using cleaned headers
        enhanced_header = cleaned_header.copy()
        enhanced_header.extend(['Company Information', 'Investment Rounds and Funding Information', 
                               'Total Funding to Date'])
        enhanced_header.extend(all_quarters)
        writer.writerow(enhanced_header)
        
        # Write enhanced data rows
        for enhanced_row_data in enhanced_rows:
            row = enhanced_row_data['row'].copy()
            result = enhanced_row_data['result']
            
            # Ensure row has same number of columns as header
            while len(row) < len(cleaned_header):
                row.append('')
            
            if result:
                # Add funding data columns
                row.extend([
                    result['company_info'],
                    result['funding_info'],
                    result['total_funding'] if result['total_funding'] else ''
                ])
                
                # Add quarterly funding data
                for quarter in all_quarters:
                    if quarter in result['quarterly_funding']:
                        row.append(result['quarterly_funding'][quarter])
                    else:
                        row.append('')
            else:
                # No result - add empty columns
                row.extend(['', '', ''])  # Company info, Funding info, Total funding
                row.extend([''] * len(all_quarters))  # Empty quarterly columns
            
            writer.writerow(row)
    
    # Summary
    found_count = sum(1 for er in enhanced_rows if er['result'] is not None)
    print(f"\n✓ Done! Output written to {output_file}")
    print(f"  Total rows processed: {len(enhanced_rows)}")
    print(f"  Companies found: {found_count}")
    if all_quarters:
        print(f"  Date range: {all_quarters[-1]} to {all_quarters[0]}")


def main():
    # Find the database file
    db_path = find_database()
    
    if not db_path:
        print("❌ No DuckDB database found in DATA folder.")
        print("   Please run the import script first to create the database.")
        sys.exit(1)
    
    print(f"Using database: {db_path}")
    
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        print("Usage:")
        print("  bulk <input.csv>                           # Process CSV with single row of URLs")
        print("  bulk <input.csv> <output.csv>            # Process CSV with custom output filename")
        print("\nCSV format: URLs in single row (either header or data row)")
        print("Only ONE row with URLs allowed!")
        print("\nExample:")
        print("  bulk INPUT/companies.csv")
        print("  bulk INPUT/companies.csv OUTPUT/enhanced.csv")
        sys.exit(0)
    
    # Ensure INPUT and OUTPUT directories exist
    os.makedirs("../INPUT", exist_ok=True)
    os.makedirs("../OUTPUT", exist_ok=True)
    
    # CSV input mode
    if len(sys.argv) >= 2:
        input_csv = sys.argv[1]
        
        # Check if file exists in INPUT directory or current directory
        if not os.path.exists(input_csv) and os.path.exists(f"../INPUT/{input_csv}"):
            input_csv = f"../INPUT/{input_csv}"
        
        if not os.path.exists(input_csv):
            print(f"❌ Input file not found: {input_csv}")
            sys.exit(1)
        
        # Determine output file
        if len(sys.argv) == 3:
            output_csv = sys.argv[2]
            # If no path specified, put in OUTPUT directory
            if os.path.dirname(output_csv) == '':
                output_csv = f"../OUTPUT/{output_csv}"
        else:
            # Auto-generate output filename
            today = date.today()
            input_basename = os.path.splitext(os.path.basename(input_csv))[0]
            output_csv = f"../OUTPUT/{input_basename}_Funding_enhanced_{today.strftime('%Y-%m-%d')}.csv"
        
        # Process the CSV file
        bulk_process_csv(db_path, input_csv, output_csv)
    
    else:
        print("❌ Invalid arguments")
        print("Usage:")
        print("  bulk <input.csv>                           # Process CSV with single row of URLs")
        print("  bulk <input.csv> <output.csv>            # Process CSV with custom output filename")
        sys.exit(1)


if __name__ == "__main__":
    main()

