# Interactive Menu System

## Overview

RUN.sh now features an **interactive menu system** that makes it easy to use all features without remembering command-line arguments.

## Usage

### Interactive Mode (Default)

Simply run RUN.sh without any arguments to see the menu:

```bash
./RUN.sh
```

This will display:

```
================================================================================
  SimpleCBLookup - Crunchbase Data Query Tool
================================================================================

Main Menu - Select an option:

  1) Setup (Complete installation and data download)
  2) Download Collections
  3) Import to DuckDB
  4) Query Company by URL
  5) Bulk Query from CSV
  6) List Available Collections
  7) Check Downloaded Collections
  8) Verify File Integrity
  9) Help & Documentation
  0) Exit

Enter your choice [0-9]:
```

### Menu Options

#### 1) Setup
Complete installation workflow:
- Install dependencies
- Download Crunchbase data
- Import to DuckDB
- Test with sample query

Includes interactive sub-menus for:
- Using existing data
- Downloading fresh data
- Downloading missing collections
- Fixing corrupted files

#### 2) Download Collections
Prompt for collection name or "all":
```
Enter collection name (or 'all' for all collections):
Collection: 
```

Examples:
- `all` - Download all collections
- `organizations` - Download organizations only
- `funding_rounds` - Download funding rounds only

#### 3) Import to DuckDB
Import downloaded ZIP files into DuckDB database.

#### 4) Query Company by URL
Prompt for company URL:
```
Enter company URL: 
```

Examples:
- `tesla.com`
- `apple.com`
- `https://www.openai.com`

#### 5) Bulk Query from CSV
Prompt for CSV file path:
```
Enter CSV file path: 
```

File should contain URLs in the first column.

#### 6) List Available Collections
Show all available Crunchbase collections.

#### 7) Check Downloaded Collections
Check which collections are downloaded vs. available.

#### 8) Verify File Integrity
Verify downloaded files are not corrupted.

#### 9) Help & Documentation
Show help information and links to documentation.

#### 0) Exit
Exit the program.

## Command-Line Mode

You can still use RUN.sh with command-line arguments for automation:

```bash
# Setup
./RUN.sh setup

# Download specific collection
./RUN.sh download organizations

# Download all collections
./RUN.sh download --all

# Query a company
./RUN.sh query tesla.com

# Bulk query
./RUN.sh bulk INPUT/companies.csv

# Other commands
./RUN.sh list
./RUN.sh check
./RUN.sh verify
./RUN.sh help
```

## Return to Menu

After completing any operation, you'll be prompted to return to the menu:

```
Press Enter to return to menu...
```

This allows you to:
- Run multiple operations without restarting
- Try different features easily
- See results before deciding what to do next

## Advantages

### User-Friendly
- No need to remember command syntax
- Clear numbered options
- Prompts guide you through each step

### Flexible
- Works in interactive mode or command-line mode
- Easy to switch between operations
- Supports both manual and automated workflows

### Discoverable
- See all available options at once
- Help information readily available
- Documentation links provided

## Examples

### First-Time Setup
```bash
./RUN.sh
# Select: 1 (Setup)
# Follow prompts
```

### Download Missing Collections
```bash
./RUN.sh
# Select: 2 (Download Collections)
# Enter: all
```

### Query Multiple Companies
```bash
./RUN.sh
# Select: 5 (Bulk Query from CSV)
# Enter: INPUT/companies.csv
```

### Check Status
```bash
./RUN.sh
# Select: 7 (Check Downloaded Collections)
```

## Tips

1. **Start with Setup**: If this is your first time, select option 1 (Setup)
2. **Check Status**: Use option 7 to see what's downloaded before downloading more
3. **Verify Files**: Use option 8 if you suspect file corruption
4. **Use Bulk Query**: Option 5 is fastest for querying multiple companies
5. **Help Available**: Option 9 shows quick help and documentation links

## Keyboard Shortcuts

While menu-based, you can still use command-line arguments for scripts and automation:

```bash
# In scripts
./RUN.sh setup
./RUN.sh query tesla.com
./RUN.sh bulk INPUT/companies.csv
```

## Troubleshooting

**Menu doesn't appear?**
- Make sure you're running `./RUN.sh` without arguments
- Check file permissions: `chmod +x RUN.sh`

**Can't enter selection?**
- Ensure terminal supports interactive input
- Try command-line mode instead

**Want to skip menu?**
- Use command-line arguments: `./RUN.sh setup`
- Or `./RUN.sh help` for direct help

