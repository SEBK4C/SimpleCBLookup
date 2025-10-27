# Examples

## Basic Setup and Query

```bash
# Step 1: Complete setup
./RUN.sh setup

# Step 2: Query a company
./RUN.sh query tesla.com
```

## Bulk Company Analysis

### Create Input CSV

Create `INPUT/tech_companies.csv`:

```csv
tesla.com
apple.com
openai.com
nvidia.com
microsoft.com
```

### Run Bulk Query

```bash
./RUN.sh bulk INPUT/tech_companies.csv
```

Output: `tech_companies_Funding_rounds_to_date_2025-01-23.csv`

## Check Data Status

```bash
# List all available collections
./RUN.sh list

# Check what's downloaded
./RUN.sh check

# Verify file integrity
./RUN.sh verify
```

## Download Specific Collections

```bash
# Download only organizations and funding data
./RUN.sh download organizations
./RUN.sh download funding_rounds
./RUN.sh download investments

# Import the downloaded data
./RUN.sh import
```

## Update Existing Data

```bash
# Download all collections (or updates)
./RUN.sh download --all

# Re-import to database
./RUN.sh import
```

## Query Different URL Formats

All these work identically:

```bash
./RUN.sh query tesla.com
./RUN.sh query www.tesla.com
./RUN.sh query https://tesla.com
./RUN.sh query https://www.tesla.com
```

## Custom Python Queries

```python
import duckdb
import glob

# Find latest database
db_files = glob.glob("data/cb_data.*.duckdb")
db_path = sorted(db_files)[-1]

conn = duckdb.connect(db_path)

# Get top funded companies
query = """
SELECT 
    "identifier.value" as name,
    "funding_total.value_usd" as total_funding,
    num_funding_rounds
FROM organizations
WHERE "funding_total.value_usd" IS NOT NULL
ORDER BY "funding_total.value_usd" DESC
LIMIT 10
"""

results = conn.execute(query).fetchall()
for row in results:
    print(f"{row[0]}: ${row[1]:,.0f} ({row[2]} rounds)")

conn.close()
```

## Finding Investors

```python
import duckdb
import glob

db_files = glob.glob("data/cb_data.*.duckdb")
db_path = sorted(db_files)[-1]

conn = duckdb.connect(db_path)

# Find all investments by a specific investor
query = """
SELECT 
    i."investor_identifier.value" as investor,
    fr."identifier.value" as round_name,
    o."identifier.value" as company,
    fr."money_raised.value_usd" as amount,
    fr.announced_on
FROM investments i
JOIN funding_rounds fr ON i."funding_round_identifier.uuid" = fr."identifier.uuid"
JOIN organizations o ON fr."funded_organization_identifier.uuid" = o."identifier.uuid"
WHERE i."investor_identifier.value" LIKE '%Y Combinator%'
ORDER BY fr.announced_on DESC
LIMIT 20
"""

results = conn.execute(query).fetchall()
for row in results:
    print(f"{row[0]} → {row[2]}: ${row[3]:,.0f} ({row[4]})")

conn.close()
```

## Quarterly Funding Trends

```python
import duckdb
import glob
from datetime import datetime

db_files = glob.glob("data/cb_data.*.duckdb")
db_path = sorted(db_files)[-1]

conn = duckdb.connect(db_path)

# Get quarterly funding totals
query = """
SELECT 
    strftime('%Y-Q', closed_on) as quarter,
    SUM("money_raised.value_usd") as total_funding
FROM funding_rounds
WHERE "money_raised.value_usd" IS NOT NULL
  AND closed_on IS NOT NULL
GROUP BY quarter
ORDER BY quarter DESC
LIMIT 20
"""

results = conn.execute(query).fetchall()
print("Quarterly Funding Trends:")
for row in results:
    print(f"{row[0]}: ${row[1]:,.0f}")

conn.close()
```

## Export Query Results

```python
import duckdb
import glob
import csv

db_files = glob.glob("data/cb_data.*.duckdb")
db_path = sorted(db_files)[-1]

conn = duckdb.connect(db_path)

# Get AI companies with funding
query = """
SELECT 
    "identifier.value" as name,
    website,
    "funding_total.value_usd" as total_funding,
    num_funding_rounds
FROM organizations
WHERE categories LIKE '%Artificial Intelligence%'
  AND "funding_total.value_usd" IS NOT NULL
ORDER BY "funding_total.value_usd" DESC
"""

results = conn.execute(query).fetchall()

# Write to CSV
with open('OUTPUT/ai_companies.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Name', 'Website', 'Total Funding', 'Rounds'])
    writer.writerows(results)

print(f"Exported {len(results)} companies to OUTPUT/ai_companies.csv")
conn.close()
```

## Compare Multiple Companies

```bash
# Create comparison list
cat > INPUT/comparison.csv << EOF
tesla.com
ford.com
rivian.com
EOF

# Query all
./RUN.sh bulk INPUT/comparison.csv OUTPUT/ev_companies.csv
```

## Verify and Fix Data

```bash
# Check for issues
./RUN.sh verify

# Auto-fix corrupted files
./RUN.sh verify --fix

# Check for missing collections
./RUN.sh check
```

## Advanced: Multi-Database Analysis

```python
import duckdb
import glob
from datetime import datetime

# Get all databases
db_files = sorted(glob.glob("data/cb_data.*.duckdb"))

# Compare data across different dates
results = []
for db_path in db_files[-3:]:  # Last 3 databases
    conn = duckdb.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0]
    date = db_path.split('.')[1]
    results.append((date, count))
    conn.close()

print("Organization Count Over Time:")
for date, count in results:
    print(f"{date}: {count:,} organizations")
```

