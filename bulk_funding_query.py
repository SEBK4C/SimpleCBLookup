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
    """Find the latest DuckDB database in the data folder."""
    # Look for databases matching the pattern cb_data.YYYY-MM-DD.duckdb
    db_pattern = os.path.join("data", "cb_data.*.duckdb")
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


def bulk_process_urls(db_path: str, urls: List[str], output_file: str):
    """Process multiple URLs and output to CSV."""
    today = date.today()
    
    # Process all companies
    results = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Processing: {url}")
        result = process_company(db_path, url)
        if result:
            results.append(result)
            print(f"  ✓ Found: {result['company_info'].split('Name: ')[1].split(' |')[0] if 'Name: ' in result['company_info'] else 'Unknown'}")
        else:
            print(f"  ✗ Not found")
    
    if not results:
        print("\nNo companies found!")
        return
    
    # Determine all unique quarters across all companies
    all_quarters = set()
    for result in results:
        all_quarters.update(result['quarters'])
    
    # Sort quarters chronologically - newest first
    all_quarters = sort_quarters_chronologically(list(all_quarters), reverse=True)
    
    # Write to CSV
    print(f"\nWriting results to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header row
        header = ['URL', 'Company Information', 'Investment Rounds and Funding Information', 
                  'Total Funding to Date']
        header.extend(all_quarters)
        writer.writerow(header)
        
        # Data rows
        for result in results:
            row = [
                result['url'],
                result['company_info'],
                result['funding_info'],
                result['total_funding'] if result['total_funding'] else ''
            ]
            
            # Add quarterly funding data
            for quarter in all_quarters:
                if quarter in result['quarterly_funding']:
                    row.append(result['quarterly_funding'][quarter])
                else:
                    row.append('')
            
            writer.writerow(row)
    
    print(f"✓ Done! Output written to {output_file}")
    print(f"  Processed {len(results)} companies")
    print(f"  Date range: {all_quarters[-1]} to {all_quarters[0]}")


def main():
    # Find the database file
    db_path = find_database()
    
    if not db_path:
        print("❌ No DuckDB database found in data folder.")
        print("   Please run the import script first to create the database.")
        sys.exit(1)
    
    print(f"Using database: {db_path}")
    
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        print("Usage:")
        print("  localduck-bulk <url>                      # Process single URL")
        print("  localduck-bulk <input.csv>                 # Process CSV of URLs (auto-generate output)")
        print("  localduck-bulk <input.csv> <output.csv>   # Process CSV with custom output filename")
        print("\nCSV format: URLs in first column")
        print("\nExample:")
        print("  localduck-bulk tesla.com")
        print("  localduck-bulk urls.csv")
        print("  localduck-bulk urls.csv custom_output.csv")
        sys.exit(0)
    
    # Single argument mode - could be URL or CSV
    if len(sys.argv) == 2:
        input_arg = sys.argv[1]
        
        # Check if it's a CSV file
        if input_arg.endswith('.csv'):
            # CSV input mode with auto-generated output filename
            input_csv = input_arg
            
            # Read URLs from CSV
            urls = []
            with open(input_csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        urls.append(row[0].strip())
            
            if not urls:
                print("❌ No URLs found in input CSV")
                sys.exit(1)
            
            # Create output filename: input (without .csv) + Funding_rounds_to_date + today's date
            today = date.today()
            input_basename = os.path.splitext(os.path.basename(input_csv))[0]
            output_csv = f"{input_basename}_Funding_rounds_to_date_{today.strftime('%Y-%m-%d')}.csv"
            
            print(f"Found {len(urls)} URLs in {input_csv}")
            bulk_process_urls(db_path, urls, output_csv)
        
        else:
            # Single URL mode
            url = input_arg
            print(f"Processing single URL: {url}")
            
            result = process_company(db_path, url)
            if not result:
                print(f"❌ No organization found matching URL: {url}")
                sys.exit(1)
            
            # Create output filename: input + Funding_rounds_to_date + today's date
            today = date.today()
            sanitized_input = sanitize_filename(url)
            output_file = f"{sanitized_input}_Funding_rounds_to_date_{today.strftime('%Y-%m-%d')}.csv"
            
            # Process as if it's a CSV with one URL
            bulk_process_urls(db_path, [url], output_file)
    
    # CSV input mode with explicit output filename
    elif len(sys.argv) == 3:
        input_csv = sys.argv[1]
        output_csv = sys.argv[2]
        
        # Read URLs from CSV
        urls = []
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    urls.append(row[0].strip())
        
        if not urls:
            print("❌ No URLs found in input CSV")
            sys.exit(1)
        
        print(f"Found {len(urls)} URLs in {input_csv}")
        bulk_process_urls(db_path, urls, output_csv)
    
    else:
        print("❌ Invalid arguments")
        print("Usage:")
        print("  localduck-bulk <url>                      # Process single URL")
        print("  localduck-bulk <input.csv>                 # Process CSV of URLs (auto-generate output)")
        print("  localduck-bulk <input.csv> <output.csv>   # Process CSV with custom output filename")
        sys.exit(1)


if __name__ == "__main__":
    main()

