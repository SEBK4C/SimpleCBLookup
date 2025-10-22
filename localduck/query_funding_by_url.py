#!/usr/bin/env python3
"""
Query funding data and VC rounds for a company by URL.
"""

import duckdb
import re
from typing import Optional, List, Dict
from datetime import datetime


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
            "identifier.uuid" as uuid
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
            'uuid': result[3]
        }
    return None


def get_funding_rounds(db_path: str, organization_name: str, organization_uuid: str = None) -> List[Dict]:
    """Get all funding rounds for an organization."""
    conn = duckdb.connect(db_path)
    
    # Build query
    if organization_uuid:
        query = """
            SELECT 
                "identifier.value" as round_name,
                announced_on,
                "closed_on.value" as closed_on,
                "money_raised.value_usd" as amount_usd,
                "money_raised.currency" as currency,
                investment_type,
                investment_stage as stage,
                num_investors,
                "post_money_valuation.value_usd" as post_money_valuation_usd,
                "pre_money_valuation.value_usd" as pre_money_valuation_usd,
                short_description
            FROM funding_rounds
            WHERE "funded_organization_identifier.uuid" = ?
            ORDER BY announced_on DESC, "closed_on.value" DESC
        """
        results = conn.execute(query, [organization_uuid]).fetchall()
    else:
        query = """
            SELECT 
                "identifier.value" as round_name,
                announced_on,
                "closed_on.value" as closed_on,
                "money_raised.value_usd" as amount_usd,
                "money_raised.currency" as currency,
                investment_type,
                investment_stage as stage,
                num_investors,
                "post_money_valuation.value_usd" as post_money_valuation_usd,
                "pre_money_valuation.value_usd" as pre_money_valuation_usd,
                short_description
            FROM funding_rounds
            WHERE "funded_organization_identifier.value" = ?
            ORDER BY announced_on DESC, "closed_on.value" DESC
        """
        results = conn.execute(query, [organization_name]).fetchall()
    
    conn.close()
    
    # Convert to list of dicts
    funding_rounds = []
    for row in results:
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
            'short_description': row[10]
        })
    
    return funding_rounds


def format_currency(amount: float) -> str:
    """Format currency amount."""
    if amount is None:
        return "N/A"
    if amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.2f}B"
    elif amount >= 1_000_000:
        return f"${amount/1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.2f}K"
    else:
        return f"${amount:.2f}"


def query_funding_by_url(db_path: str, url: str):
    """Main function to query funding data by URL."""
    print(f"\nSearching for organization with URL: {url}")
    print("=" * 80)
    
    # Find organization
    org = find_organization_by_url(db_path, url)
    
    if not org:
        print(f"❌ No organization found matching URL: {url}")
        print("\n💡 Tip: Try searching without protocol (e.g., 'tesla.com' instead of 'https://tesla.com')")
        return
    
    print(f"\n✓ Found organization: {org['name']}")
    print(f"  Website: {org['website'] or org['website_url']}")
    print(f"  UUID: {org['uuid']}")
    
    # Get funding rounds
    print(f"\nFetching funding rounds...")
    funding_rounds = get_funding_rounds(db_path, org['name'], org['uuid'])
    
    if not funding_rounds:
        print("❌ No funding rounds found for this organization.")
        return
    
    print(f"\n✓ Found {len(funding_rounds)} funding rounds\n")
    print("=" * 80)
    
    # Display funding rounds
    for i, round_data in enumerate(funding_rounds, 1):
        print(f"\n[{i}] {round_data['round_name']}")
        print(f"    Announced: {round_data['announced_on']}")
        print(f"    Closed: {round_data['closed_on']}")
        
        if round_data['amount_usd']:
            print(f"    Amount: {format_currency(round_data['amount_usd'])}")
        
        if round_data['investment_type']:
            print(f"    Type: {round_data['investment_type']}")
        
        if round_data['stage']:
            print(f"    Stage: {round_data['stage']}")
        
        if round_data['num_investors']:
            print(f"    Investors: {round_data['num_investors']}")
        
        if round_data['post_money_valuation_usd']:
            print(f"    Post-Money Valuation: {format_currency(round_data['post_money_valuation_usd'])}")
        
        if round_data['pre_money_valuation_usd']:
            print(f"    Pre-Money Valuation: {format_currency(round_data['pre_money_valuation_usd'])}")
        
        if round_data['short_description']:
            print(f"    Description: {round_data['short_description']}")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("\nSUMMARY:")
    
    total_funding = sum(r['amount_usd'] for r in funding_rounds if r['amount_usd'])
    num_rounds_with_amount = sum(1 for r in funding_rounds if r['amount_usd'])
    
    print(f"  Total Funding Rounds: {len(funding_rounds)}")
    print(f"  Rounds with Amount Data: {num_rounds_with_amount}")
    if total_funding:
        print(f"  Total Funding Amount: {format_currency(total_funding)}")
    
    # Group by type
    by_type = {}
    for r in funding_rounds:
        if r['investment_type']:
            by_type[r['investment_type']] = by_type.get(r['investment_type'], 0) + 1
    
    if by_type:
        print(f"\n  Rounds by Type:")
        for inv_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {inv_type}: {count}")


def main():
    import sys
    
    db_path = "localduck.duckdb"
    
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        print("Usage: localduck-query <url>")
        print("\nQuery funding data and VC rounds for a company by URL.")
        print("\nExample:")
        print("  localduck-query tesla.com")
        print("  localduck-query https://www.tesla.com")
        print("  localduck-query apple.com")
        sys.exit(0)
    
    url = sys.argv[1]
    query_funding_by_url(db_path, url)


if __name__ == "__main__":
    main()

