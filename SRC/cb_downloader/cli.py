from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from .collections import COLLECTIONS, COLLECTION_DISPLAY_NAMES

app = typer.Typer(help="Crunchbase static export checker and downloader")
console = Console()

DEFAULT_DEST = Path("../DATA/zips")
UPDATES_MD = Path("../Updates.md")
MANIFEST_JSON = Path("../DATA/manifest.json")

HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
HEADERS = {"User-Agent": "cb-downloader/0.1", "Accept": "application/zip"}


def get_user_key(user_key: Optional[str]) -> str:
    key = user_key or os.getenv("CRUNCHBASE_USER_KEY")
    if not key:
        raise typer.BadParameter("Provide --user-key or set CRUNCHBASE_USER_KEY env var.")
    return key


def ensure_dirs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_manifest() -> Dict[str, dict]:
    if MANIFEST_JSON.exists():
        try:
            return json.loads(MANIFEST_JSON.read_text())
        except Exception:
            return {}
    return {}


def save_manifest(data: Dict[str, dict]) -> None:
    ensure_dirs(MANIFEST_JSON.parent)
    MANIFEST_JSON.write_text(json.dumps(data, indent=2, sort_keys=True))


async def head_collection(client: httpx.AsyncClient, collection: str, user_key: str) -> Tuple[str, httpx.Response]:
    url = COLLECTIONS[collection]
    # Use GET with a Range request to fetch minimal bytes and still get headers.
    headers = dict(HEADERS)
    headers["Range"] = "bytes=0-0"
    resp = await client.get(url, params={"user_key": user_key}, headers=headers, follow_redirects=True)
    return collection, resp


def parse_last_modified(resp: httpx.Response) -> Optional[str]:
    # Return ISO8601 string in UTC if available
    lm = resp.headers.get("Last-Modified")
    if not lm:
        return None
    try:
        from email.utils import parsedate_to_datetime

        d = parsedate_to_datetime(lm)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc).isoformat()
    except Exception:
        return lm


def extract_total_size(headers: httpx.Headers) -> Optional[int]:
    # Prefer Content-Range total size if present (e.g., "bytes 0-0/12345")
    cr = headers.get("Content-Range")
    if cr and "/" in cr:
        try:
            total = cr.split("/")[-1].strip()
            return int(total)
        except Exception:
            pass
    # Fallback to Content-Length
    try:
        cl = headers.get("Content-Length")
        return int(cl) if cl is not None else None
    except Exception:
        return None


def human_size_from_int(num_bytes: Optional[int]) -> str:
    if num_bytes is None:
        return "?"
    n = float(num_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    return f"{int(n) if i == 0 else n:.2f} {units[i]}" if i > 0 else f"{int(n)} {units[i]}"


def verify_zip_integrity_quick(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Quick check if a ZIP file is valid (faster, skips CRC verification)."""
    if not file_path.exists():
        return False, "File does not exist"
    
    if file_path.stat().st_size == 0:
        return False, "File is empty"
    
    try:
        # Quick check: just verify the ZIP file can be opened and has entries
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Just check if we can read the file list (much faster than testzip)
            file_list = zip_ref.namelist()
            if not file_list:
                return False, "ZIP file has no entries"
            return True, None
    except zipfile.BadZipFile:
        return False, "Invalid ZIP file format"
    except Exception as e:
        return False, f"Error reading ZIP: {str(e)}"


def verify_zip_integrity(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Check if a ZIP file is valid and not corrupted (full CRC check - slow)."""
    if not file_path.exists():
        return False, "File does not exist"
    
    if file_path.stat().st_size == 0:
        return False, "File is empty"
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Test if ZIP file is valid by trying to read its contents
            zip_ref.testzip()
            return True, None
    except zipfile.BadZipFile:
        return False, "Invalid ZIP file format"
    except Exception as e:
        return False, f"Error reading ZIP: {str(e)}"


def check_file_size(file_path: Path, expected_size: Optional[int]) -> Tuple[bool, Optional[str]]:
    """Check if file size matches expected size."""
    if not file_path.exists():
        return False, "File does not exist"
    
    actual_size = file_path.stat().st_size
    
    if expected_size is None:
        return True, None  # Can't verify without expected size
    
    if actual_size != expected_size:
        return False, f"Size mismatch: expected {expected_size} bytes, got {actual_size} bytes"
    
    return True, None


def find_existing_files(dest: Path) -> Dict[str, Path]:
    """Find all existing ZIP files in the destination directory."""
    existing = {}
    if not dest.exists():
        return existing
    
    for zip_file in dest.glob("*.zip"):
        # Extract collection name from filename (e.g., "organizations.zip" -> "organizations")
        collection_name = zip_file.stem
        existing[collection_name] = zip_file
    
    return existing


@app.command("list")
def list_cmd(
    user_key: Optional[str] = typer.Option(None, "--user-key", help="Crunchbase user key; or set CRUNCHBASE_USER_KEY env var"),
    write_log: bool = typer.Option(False, "--write-log", help="Write/refresh Updates.md with latest Last-Modified info"),
    timeout: float = typer.Option(30.0, help="HTTP timeout seconds"),
):
    """Check which collections are accessible with your key and show metadata."""
    key = get_user_key(user_key)

    rows: List[Tuple[str, httpx.Response]] = []

    async def run() -> None:
        nonlocal rows
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
            coros = [head_collection(client, c, key) for c in COLLECTIONS.keys()]
            rows = await asyncio.gather(*coros)

    with console.status("Checking access..."):
        asyncio.run(run())

    table = Table(title="Crunchbase Static Exports", show_lines=False)
    table.add_column("Collection")
    table.add_column("Status")
    table.add_column("Last-Modified")
    table.add_column("Size")
    table.add_column("URL")

    updates: List[Tuple[str, str, str, str]] = []

    for collection, resp in sorted(rows, key=lambda r: r[0]):
        name = COLLECTION_DISPLAY_NAMES.get(collection, collection)
        status = str(resp.status_code)
        lm = parse_last_modified(resp) or ""
        total_size = extract_total_size(resp.headers)
        size = human_size_from_int(total_size)
        url = str(resp.request.url)
        table.add_row(name, status, lm, size, url)
        updates.append((name, status, lm or "N/A", size))

    console.print(table)

    if write_log:
        write_updates_md(updates)
        console.print(f"[green]Updated {UPDATES_MD}[/green]")


@app.command("check")
def check_cmd(
    dest: Path = typer.Option(DEFAULT_DEST, "--dest", help="Directory containing downloaded ZIPs"),
):
    """Check which collections are missing compared to what's available on the server."""
    existing_files = find_existing_files(dest)
    existing_collections = set(existing_files.keys())
    server_collections = set(COLLECTIONS.keys())
    
    missing_collections = server_collections - existing_collections
    
    table = Table(title="Collection Availability Check")
    table.add_column("Collection")
    table.add_column("Status")
    table.add_column("File")
    
    for coll in sorted(server_collections):
        if coll in existing_collections:
            status = "[green]✓ Downloaded[/green]"
            file_path = existing_files[coll]
        else:
            status = "[red]✗ Missing[/red]"
            file_path = ""
        
        table.add_row(
            COLLECTION_DISPLAY_NAMES.get(coll, coll),
            status,
            file_path.name if file_path else ""
        )
    
    console.print(table)
    
    if missing_collections:
        console.print(f"\n[yellow]Found {len(missing_collections)} missing collection(s)[/yellow]")
        console.print(f"Run: cb-downloader download --all")
    else:
        console.print("\n[green]All collections are downloaded![/green]")


@app.command("verify")
def verify_cmd(
    dest: Path = typer.Option(DEFAULT_DEST, "--dest", help="Directory containing downloaded ZIPs"),
    fix: bool = typer.Option(False, "--fix", help="Automatically re-download corrupted files"),
    user_key: Optional[str] = typer.Option(None, "--user-key", help="Crunchbase user key; or set CRUNCHBASE_USER_KEY env var"),
    timeout: float = typer.Option(180.0, help="HTTP timeout seconds"),
    quick: bool = typer.Option(True, "--quick/--full", help="Quick verification (skip CRC check) for speed"),
):
    """Verify integrity of downloaded ZIP files."""
    existing_files = find_existing_files(dest)
    manifest = load_manifest()
    
    if not existing_files:
        console.print("[yellow]No ZIP files found in destination directory[/yellow]")
        return
    
    total_files = len([f for f in existing_files.keys() if f in COLLECTIONS])
    console.print(f"[cyan]Verifying {total_files} file(s)...[/cyan]")
    
    table = Table(title="File Verification Results")
    table.add_column("Collection")
    table.add_column("File")
    table.add_column("Status")
    table.add_column("Issue")
    
    corrupted: List[str] = []
    
    for idx, (collection_name, file_path) in enumerate(sorted(existing_files.items()), 1):
        if collection_name not in COLLECTIONS:
            continue
        
        # Show progress
        coll_display = COLLECTION_DISPLAY_NAMES.get(collection_name, collection_name)
        console.print(f"[dim]Checking [{idx}/{total_files}]: {coll_display}[/dim]")
        
        # Check ZIP integrity with quick mode option
        if quick:
            # Quick check: just verify file exists, is not empty, and can be opened
            is_valid, zip_error = verify_zip_integrity_quick(file_path)
        else:
            # Full check: verify all CRC checksums (slow!)
            is_valid, zip_error = verify_zip_integrity(file_path)
        
        # Check file size
        expected_size = None
        if collection_name in manifest:
            try:
                expected_size = int(manifest[collection_name].get("content_length", 0) or 0)
            except (ValueError, TypeError):
                pass
        
        size_valid, size_error = check_file_size(file_path, expected_size)
        
        if is_valid and size_valid:
            status = "[green]✓ Valid[/green]"
            issue = ""
        else:
            status = "[red]✗ Corrupted[/red]"
            issue = zip_error or size_error or "Unknown issue"
            corrupted.append(collection_name)
        
        table.add_row(
            coll_display,
            file_path.name,
            status,
            issue
        )
    
    console.print(table)
    
    if corrupted:
        console.print(f"\n[red]Found {len(corrupted)} corrupted file(s)[/red]")
        if fix:
            console.print("[yellow]Re-downloading corrupted files...[/yellow]")
            # Trigger re-download of corrupted files
            key = get_user_key(user_key)
            ensure_dirs(dest)
            
            async def download_one(client: httpx.AsyncClient, coll: str) -> Tuple[str, Optional[Path], Optional[str]]:
                url = COLLECTIONS[coll]
                params = {"user_key": key}
                headers = dict(HEADERS)
                
                async with client.stream("GET", url, params=params, headers=headers, follow_redirects=True) as resp:
                    if resp.status_code != 200:
                        return coll, None, None
                    
                    name = url.split("/")[-1]
                    out_path = dest / name
                    with open(out_path, "wb") as f:
                        async for chunk in resp.aiter_bytes():
                            if chunk:
                                f.write(chunk)
                    
                    lm_val = parse_last_modified(resp)
                    manifest[coll] = {
                        "file": str(out_path),
                        "last_modified": lm_val,
                        "content_length": str(extract_total_size(resp.headers) or ""),
                        "downloaded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    }
                    return coll, out_path, lm_val
            
            async def run() -> None:
                async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=15.0)) as client:
                    tasks = [download_one(client, coll) for coll in corrupted]
                    results = await asyncio.gather(*tasks)
                    
                    for coll, path, lm in results:
                        if path:
                            console.print(f"[green]Re-downloaded: {COLLECTION_DISPLAY_NAMES.get(coll, coll)}[/green]")
                        else:
                            console.print(f"[red]Failed to re-download: {COLLECTION_DISPLAY_NAMES.get(coll, coll)}[/red]")
            
            asyncio.run(run())
            save_manifest(manifest)
        else:
            console.print("Run with --fix to automatically re-download corrupted files")
    else:
        console.print("\n[green]All files are valid![/green]")


@app.command()
def download(
    collection: Optional[str] = typer.Argument(None, help="Collection key to download (e.g. organizations). If omitted, use --all."),
    download_all: bool = typer.Option(False, "--all", help="Download all accessible collections"),
    user_key: Optional[str] = typer.Option(None, "--user-key", help="Crunchbase user key; or set CRUNCHBASE_USER_KEY env var"),
    dest: Path = typer.Option(DEFAULT_DEST, "--dest", help="Destination directory for downloaded ZIPs"),
    force: bool = typer.Option(False, "--force", help="Download even if Last-Modified matches manifest"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify existing files before skipping download"),
    timeout: float = typer.Option(180.0, help="HTTP timeout seconds"),
    max_concurrency: int = typer.Option(4, "--max-concurrency", min=1, help="Maximum number of concurrent downloads"),
):
    """Download one or all collections as ZIP files."""
    key = get_user_key(user_key)

    if not download_all and not collection:
        raise typer.BadParameter("Provide a collection key or use --all")

    targets: List[str]
    if download_all:
        targets = list(COLLECTIONS.keys())
    else:
        if collection not in COLLECTIONS:
            valid = ", ".join(sorted(COLLECTIONS.keys()))
            raise typer.BadParameter(f"Unknown collection '{collection}'. Valid: {valid}")
        targets = [collection]

    ensure_dirs(dest)

    manifest = load_manifest()
    
    # Check existing files for corruption
    existing_files = find_existing_files(dest)
    
    # Automatically check for missing collections if files exist
    if existing_files:
        console.print("[cyan]Checking for missing collections...[/cyan]")
        existing_collections = set(existing_files.keys())
        server_collections = set(COLLECTIONS.keys())
        missing_collections = server_collections - existing_collections
        
        if missing_collections:
            console.print(f"[yellow]Found {len(missing_collections)} missing collection(s): {', '.join(sorted(missing_collections))}[/yellow]")
            if not download_all:
                console.print("[yellow]Note: Use --all to download all missing collections[/yellow]")
        else:
            console.print("[green]All collections are already downloaded[/green]")
    
    if verify and existing_files:
        console.print("[cyan]Verifying existing files...[/cyan]")
        corrupted = []
        for coll in targets:
            if coll in existing_files:
                file_path = existing_files[coll]
                is_valid, zip_error = verify_zip_integrity_quick(file_path)
                if not is_valid:
                    corrupted.append(coll)
                    console.print(f"[yellow]Found corrupted file: {coll} - {zip_error}[/yellow]")
                    # Remove corrupted file
                    try:
                        file_path.unlink()
                        console.print(f"[yellow]Deleted corrupted file: {file_path}[/yellow]")
                    except Exception as e:
                        console.print(f"[red]Failed to delete corrupted file: {e}[/red]")

    async def download_one(client: httpx.AsyncClient, coll: str) -> Tuple[str, Optional[Path], Optional[str]]:
        url = COLLECTIONS[coll]
        params = {"user_key": key}

        # Check if file already exists and is valid
        existing_file = existing_files.get(coll)
        if existing_file and not force:
            is_valid, zip_error = verify_zip_integrity_quick(existing_file)
            if is_valid:
                # File exists and is valid, check if we should skip based on Last-Modified
                headers = dict(HEADERS)
                if lm := manifest.get(coll, {}).get("last_modified"):
                    headers["If-Modified-Since"] = lm
                    # Just check without downloading
                    resp = await client.head(url, params=params, headers=headers, follow_redirects=True)
                    if resp.status_code == 304:
                        return coll, existing_file, manifest.get(coll, {}).get("last_modified")
                    # If not 304, file has changed, proceed with download
            else:
                # File exists but is corrupted, will proceed with download
                console.print(f"[yellow]Detected corrupted file for {coll}, will re-download[/yellow]")

        # Conditional GET based on Last-Modified if we have it
        headers = dict(HEADERS)
        if not force and (lm := manifest.get(coll, {}).get("last_modified")):
            headers["If-Modified-Since"] = lm

        # Use streaming download to avoid loading the whole file in memory
        async with client.stream("GET", url, params=params, headers=headers, follow_redirects=True) as resp:
            if resp.status_code == 304:
                return coll, existing_file, manifest.get(coll, {}).get("last_modified")
            if resp.status_code != 200:
                return coll, None, None

            name = url.split("/")[-1]
            out_path = dest / name
            
            # Delete existing file if it exists (might be corrupted)
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception:
                    pass
            
            with open(out_path, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        f.write(chunk)

            # Verify the downloaded file
            is_valid, zip_error = verify_zip_integrity_quick(out_path)
            if not is_valid:
                console.print(f"[red]Downloaded file for {coll} appears corrupted: {zip_error}[/red]")
                # Keep the manifest updated anyway
                lm_val = parse_last_modified(resp) or manifest.get(coll, {}).get("last_modified")
                manifest[coll] = {
                    "file": str(out_path),
                    "last_modified": lm_val,
                    "content_length": str(extract_total_size(resp.headers) or ""),
                    "downloaded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
                return coll, None, lm_val

            lm_val = parse_last_modified(resp) or manifest.get(coll, {}).get("last_modified")
            manifest[coll] = {
                "file": str(out_path),
                "last_modified": lm_val,
                "content_length": str(extract_total_size(resp.headers) or ""),
                "downloaded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            return coll, out_path, lm_val

    results: List[Tuple[str, Optional[Path], Optional[str]]] = []

    async def run() -> None:
        nonlocal results
        sem = asyncio.Semaphore(max_concurrency)

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=15.0)) as client:
            async def guarded(coll: str):
                async with sem:
                    coll_name = COLLECTION_DISPLAY_NAMES.get(coll, coll)
                    console.print(f"[cyan]▶ {coll_name}[/cyan] - Starting download...")
                    result = await download_one(client, coll)
                    path, lm = result[1], result[2]
                    if path:
                        console.print(f"[green]✓ {coll_name}[/green] - Downloaded successfully")
                    elif lm:
                        console.print(f"[yellow]↑ {coll_name}[/yellow] - Already up-to-date")
                    else:
                        console.print(f"[red]✗ {coll_name}[/red] - Download failed")
                    return result

            tasks = [guarded(t) for t in targets]
            results = await asyncio.gather(*tasks)

    console.print(f"\n[bold cyan]Downloading {len(targets)} collection(s) with max concurrency of {max_concurrency}[/bold cyan]\n")
    asyncio.run(run())
    console.print("")  # Empty line after downloads

    save_manifest(manifest)

    table = Table(title="Download Results")
    table.add_column("Collection")
    table.add_column("Status")
    table.add_column("Last-Modified")
    table.add_column("File")

    for coll, path, lm in sorted(results, key=lambda r: r[0]):
        status = "Downloaded" if path else ("Up-to-date" if lm else "Skipped/Failed")
        table.add_row(COLLECTION_DISPLAY_NAMES.get(coll, coll), status, lm or "", str(path) if path else "")

    console.print(table)


@app.command()
def updates(
    user_key: Optional[str] = typer.Option(None, "--user-key", help="Crunchbase user key; or set CRUNCHBASE_USER_KEY env var"),
    timeout: float = typer.Option(30.0, help="HTTP timeout seconds"),
):
    """Refresh Updates.md with Last-Modified info across all collections."""
    key = get_user_key(user_key)

    rows: List[Tuple[str, httpx.Response]] = []

    async def run() -> None:
        nonlocal rows
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
            coros = [head_collection(client, c, key) for c in COLLECTIONS.keys()]
            rows = await asyncio.gather(*coros)

    asyncio.run(run())

    updates_data: List[Tuple[str, str, str, str]] = []
    for collection, resp in sorted(rows, key=lambda r: r[0]):
        name = COLLECTION_DISPLAY_NAMES.get(collection, collection)
        status = str(resp.status_code)
        lm = parse_last_modified(resp) or "N/A"
        size = human_size_from_int(extract_total_size(resp.headers))
        updates_data.append((name, status, lm, size))

    write_updates_md(updates_data)
    console.print(f"[green]Updated {UPDATES_MD}[/green]")


def write_updates_md(rows: List[Tuple[str, str, str, str]]) -> None:
    lines: List[str] = []
    lines.append("# Updates.md")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    lines.append("")
    lines.append(f"Last checked: {now}")
    lines.append("")
    lines.append("| Collection | Status | Last-Modified (UTC) | Size |")
    lines.append("| --- | --- | --- | --- |")
    for name, status, lm, size in rows:
        lines.append(f"| {name} | {status} | {lm} | {size} |")
    UPDATES_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    app() 