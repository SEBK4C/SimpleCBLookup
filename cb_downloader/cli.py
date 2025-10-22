from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
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

DEFAULT_DEST = Path("data/zips")
UPDATES_MD = Path("Updates.md")
MANIFEST_JSON = Path("data/manifest.json")

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


@app.command()
def download(
    collection: Optional[str] = typer.Argument(None, help="Collection key to download (e.g. organizations). If omitted, use --all."),
    download_all: bool = typer.Option(False, "--all", help="Download all accessible collections"),
    user_key: Optional[str] = typer.Option(None, "--user-key", help="Crunchbase user key; or set CRUNCHBASE_USER_KEY env var"),
    dest: Path = typer.Option(DEFAULT_DEST, "--dest", help="Destination directory for downloaded ZIPs"),
    force: bool = typer.Option(False, "--force", help="Download even if Last-Modified matches manifest"),
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

    async def download_one(client: httpx.AsyncClient, coll: str) -> Tuple[str, Optional[Path], Optional[str]]:
        url = COLLECTIONS[coll]
        params = {"user_key": key}

        # Conditional GET based on Last-Modified if we have it
        headers = dict(HEADERS)
        if not force and (lm := manifest.get(coll, {}).get("last_modified")):
            headers["If-Modified-Since"] = lm

        # Use streaming download to avoid loading the whole file in memory
        async with client.stream("GET", url, params=params, headers=headers, follow_redirects=True) as resp:
            if resp.status_code == 304:
                return coll, None, manifest.get(coll, {}).get("last_modified")
            if resp.status_code != 200:
                return coll, None, None

            name = url.split("/")[-1]
            out_path = dest / name
            with open(out_path, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        f.write(chunk)

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
                    return await download_one(client, coll)

            tasks = [guarded(t) for t in targets]
            results = await asyncio.gather(*tasks)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TimeElapsedColumn()) as progress:
        task = progress.add_task("Downloading...", total=None)
        asyncio.run(run())
        progress.update(task, description="Finished", completed=1)

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