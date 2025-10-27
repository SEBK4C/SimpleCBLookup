# Virtual Environment Fix

## Problem

When running commands through RUN.sh, Python scripts were using the **system Python** instead of the **virtual environment Python**, causing `ModuleNotFoundError: No module named 'duckdb'`.

## Root Cause

1. After `source .venv/bin/activate`, the venv activation wasn't fully propagated to subprocess calls
2. `which python3` was returning system Python path instead of venv Python
3. Commands run from within `SRC/` directory lost the venv context

## Solution

Changed all Python calls to use the **absolute path** to venv Python:

### Before
```bash
cd "$SRC_DIR"
python3 setup.py
cd ..
```

### After
```bash
cd "$SRC_DIR"
../.venv/bin/python3 setup.py  # Full path to venv Python
cd ..
```

## Files Updated

All commands in RUN.sh now use the full venv path:

- `cmd_setup()` - Uses `../.venv/bin/python3 setup.py`
- `cmd_download()` - Uses `../.venv/bin/python3 -m cb_downloader`
- `cmd_import()` - Uses `../.venv/bin/python3 localduck/import_to_duckdb.py`
- `cmd_query()` - Uses `../.venv/bin/python3 localduck/query_funding_by_url.py`
- `cmd_bulk()` - Uses `../.venv/bin/python3 bulk_funding_query.py`
- `cmd_list()` - Uses `../.venv/bin/python3 -m cb_downloader list`
- `cmd_check()` - Uses `../.venv/bin/python3 -m cb_downloader check`
- `cmd_verify()` - Uses `../.venv/bin/python3 -m cb_downloader verify`

## Why This Works

1. **Absolute Path**: `../.venv/bin/python3` resolves to the venv Python from any directory
2. **No PATH Issues**: Doesn't rely on PATH modifications
3. **Consistent**: Always uses the same Python interpreter
4. **Reliable**: Works even when venv activation has issues

## Path Resolution

When in `SRC/` directory:
- `../.venv/bin/python3` resolves to `.venv/bin/python3` (root directory)
- This is the Python with all dependencies installed

## Testing

```bash
# Should now work correctly
./RUN.sh setup
# Or
./RUN.sh
# Select option 1 (Setup)
```

## Verification

To verify the fix worked:

```bash
# Check which Python is being used
cd SRC
../.venv/bin/python3 -c "import duckdb; print('DuckDB found!')"
```

Should output: `DuckDB found!`

## Related Issues

This fix also resolves:
- Missing dependencies in Python scripts
- Inconsistent Python interpreter selection
- Problems with venv activation in subprocesses

