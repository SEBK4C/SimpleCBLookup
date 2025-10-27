# API Key Management with .env File

## Overview

The API key is now automatically saved to a `.env` file and loaded on every run, so you only need to enter it once!

## How It Works

### First Time Setup

When you run any command that needs the API key:

```bash
./RUN.sh
# Select option 1 (Setup) or 2 (Download)
```

You'll be prompted:
```
Crunchbase API key not found
Get your API key from: https://data.crunchbase.com

Enter your Crunchbase API key: [your-key-here]
✓ API key saved to .env file
```

### Subsequent Runs

On future runs, the API key is automatically loaded from `.env`:

```
✓ API key loaded from .env file
```

**No need to enter it again!**

## The .env File

The `.env` file is created in the project root:

```
SimpleCBLookup/
├── .env              ← API key stored here
├── RUN.sh
├── SRC/
└── ...
```

### File Contents

```bash
CRUNCHBASE_USER_KEY=your-api-key-here
```

## Security

### Git Ignored

The `.env` file is automatically ignored by git (added to `.gitignore`), so your API key won't be committed to version control.

### Manual Editing

You can manually edit `.env` if needed:

```bash
# Edit the file
nano .env

# Or
vim .env
```

Change the API key value if needed.

## Commands That Use .env

These commands automatically load the API key from `.env`:

- **Setup** (option 1)
- **Download Collections** (option 2)
- **List Collections** (option 6)
- **Verify Files** (option 8)

Commands that DON'T need API key:
- **Import to DuckDB** (option 3)
- **Query Company** (option 4)
- **Bulk Query** (option 5)
- **Check Status** (option 7)

## Update API Key

To update your API key:

1. Delete the `.env` file:
   ```bash
   rm .env
   ```

2. Run any command - you'll be prompted again:
   ```bash
   ./RUN.sh
   # Select option 1 or 2
   ```

Or manually edit `.env`:
```bash
echo "CRUNCHBASE_USER_KEY=new-key-here" > .env
```

## Behind the Scenes

### In RUN.sh

```bash
setup_api_key() {
    # Check if .env exists and has API key
    if [ -f ".env" ]; then
        # Load from .env
        export $(grep "CRUNCHBASE_USER_KEY=" .env | xargs)
        echo "✓ API key loaded from .env file"
    else
        # Prompt for API key
        read -p "Enter your Crunchbase API key: " api_key
        # Save to .env
        echo "CRUNCHBASE_USER_KEY=$api_key" > .env
        echo "✓ API key saved to .env file"
    fi
}
```

### In setup.py

```python
# Load .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Check environment first
api_key = os.getenv("CRUNCHBASE_USER_KEY")
if not api_key:
    # Prompt if not found
    api_key = input("API Key: ").strip()
```

## Dependency

The `python-dotenv` package is automatically added to `requirements.txt`:

```
python-dotenv>=1.0.0
```

It's installed automatically when you run setup.

## Troubleshooting

### API Key Not Loading

Check if `.env` file exists:
```bash
ls -la .env
```

Check if it has the correct format:
```bash
cat .env
# Should show: CRUNCHBASE_USER_KEY=your-key
```

### Reset API Key

```bash
rm .env
./RUN.sh
# Will prompt for new key
```

### Different API Key

Replace the content of `.env` with your new key:
```bash
echo "CRUNCHBASE_USER_KEY=new-key" > .env
```

## Benefits

1. **One-Time Entry**: Enter API key once, use forever
2. **Secure**: Never committed to git
3. **Easy Update**: Change anytime
4. **Automatic**: Loads automatically on every run
5. **No Manual Export**: No need to manually export environment variables

## Alternative: Manual Environment Variable

If you prefer not to use `.env`, you can still set the environment variable manually:

```bash
export CRUNCHBASE_USER_KEY="your-key-here"
./RUN.sh
```

But using `.env` is much easier! 🎉

