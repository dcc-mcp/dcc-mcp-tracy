"""Safe wrappers for Tracy's capture and CSV export utilities."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Optional, Sequence


class TracyError(RuntimeError):
    """Raised when a Tracy operation cannot satisfy its contract."""


TRACY_RELEASES_URL = "https://api.github.com/repos/wolfpld/tracy/releases/latest"
_DOWNLOADED_CAPTURE_NAMES = ("tracy-capture.exe", "capture.exe")
_DOWNLOADED_CSVEXPORT_NAMES = ("tracy-csvexport.exe", "csvexport.exe")
_CACHE_TTL_SECONDS = 24 * 60 * 60


def _runtime_cache() -> Path:
    configured = os.environ.get("DCC_MCP_RUNTIME_CACHE")
    if configured:
        return Path(configured).expanduser().resolve() / "tracy"
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "dcc-mcp" / "tracy"


def _safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise TracyError(f"Tracy archive contains unsafe path: {member.filename}")
        bundle.extractall(destination)


def _find_downloaded_tool(root: Path, names: Sequence[str]) -> Optional[Path]:
    for name in names:
        command = next(root.rglob(name), None)
        if command is not None:
            return command.resolve()
    return None


def _find_newest_downloaded_tool(root: Path, names: Sequence[str]) -> Optional[Path]:
    candidates = [path for name in names for path in root.rglob(name)]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.parent.stat().st_mtime).resolve()


def _download_latest_capture() -> Path:
    if os.name != "nt":
        raise TracyError(
            "Tracy automatic download currently supports Windows releases; "
            "set DCC_MCP_TRACY_CAPTURE on Linux/macOS"
        )
    cache_root = _runtime_cache()
    cached = _find_newest_downloaded_tool(cache_root, _DOWNLOADED_CAPTURE_NAMES)
    if cached is not None and time.time() - cached.parent.stat().st_mtime < _CACHE_TTL_SECONDS:
        return cached
    request = urllib.request.Request(
        TRACY_RELEASES_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "dcc-mcp-tracy"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            release = json.load(response)
    except OSError as exc:
        if cached is not None:
            return cached
        raise TracyError(f"Could not query Tracy releases: {exc}") from exc
    assets = [item for item in release.get("assets", []) if item.get("name", "").endswith(".zip")]
    if len(assets) != 1:
        raise TracyError(f"Expected one Tracy Windows release archive, found {len(assets)}")
    asset = assets[0]
    version_dir = cache_root / release["tag_name"]
    command = _find_downloaded_tool(version_dir, _DOWNLOADED_CAPTURE_NAMES)
    if command is not None:
        version_dir.touch()
        return command
    version_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
        archive = Path(handle.name)
    try:
        download = urllib.request.urlopen(asset["browser_download_url"], timeout=120)
        with download as response, archive.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        expected = asset.get("digest", "")
        if expected.startswith("sha256:"):
            actual = hashlib.sha256(archive.read_bytes()).hexdigest()
            if actual != expected.removeprefix("sha256:"):
                raise TracyError("Downloaded Tracy archive SHA256 does not match GitHub metadata")
        _safe_extract(archive, version_dir)
    except (OSError, KeyError, ValueError) as exc:
        raise TracyError(f"Could not download Tracy: {exc}") from exc
    finally:
        archive.unlink(missing_ok=True)
    command = _find_downloaded_tool(version_dir, _DOWNLOADED_CAPTURE_NAMES)
    if command is None:
        raise TracyError("Downloaded Tracy archive did not contain a Tracy capture executable")
    return command


def _resolve(explicit: Optional[str], env_name: str, names: Sequence[str], label: str) -> Path:
    candidate = explicit or os.environ.get(env_name)
    if candidate:
        path = Path(candidate).expanduser().resolve()
        if path.is_file():
            return path
        raise TracyError(f"{label} does not exist: {path}")
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found).resolve()
    raise TracyError(f"{label} was not found; set {env_name} or add it to PATH")


def resolve_capture(explicit: Optional[str] = None) -> Path:
    try:
        return _resolve(
            explicit,
            "DCC_MCP_TRACY_CAPTURE",
            ("tracy-capture.exe", "tracy-capture", "capture"),
            "Tracy capture utility",
        )
    except TracyError:
        if os.environ.get("DCC_MCP_TRACY_AUTO_DOWNLOAD", "1").lower() in {"0", "false", "no"}:
            raise
        return _download_latest_capture()


def resolve_csvexport(explicit: Optional[str] = None) -> Path:
    try:
        return _resolve(
            explicit,
            "DCC_MCP_TRACY_CSVEXPORT",
            ("tracy-csvexport.exe", "tracy-csvexport", "csvexport"),
            "Tracy CSV exporter",
        )
    except TracyError:
        if os.environ.get("DCC_MCP_TRACY_AUTO_DOWNLOAD", "1").lower() in {"0", "false", "no"}:
            raise
        capture = _download_latest_capture()
        sibling = _find_downloaded_tool(capture.parent, _DOWNLOADED_CSVEXPORT_NAMES)
        if sibling is None:
            raise TracyError(
                "Downloaded Tracy archive did not contain a Tracy CSV exporter"
            ) from None
        return sibling


def _run(
    executable: Path,
    arguments: Sequence[str],
    timeout_secs: int,
    allowed_returncodes: Sequence[int] = (0,),
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            [str(executable), *arguments], capture_output=True, text=True, shell=False,
            timeout=timeout_secs, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TracyError(f"Tracy command timed out after {timeout_secs}s") from exc
    except OSError as exc:
        raise TracyError(f"Could not start Tracy command: {exc}") from exc
    if result.returncode not in allowed_returncodes:
        detail = (result.stderr or result.stdout or "unknown error").strip()[-2000:]
        raise TracyError(f"Tracy exited with code {result.returncode}: {detail}")
    return result


def get_version(*, capture_command: Optional[str] = None) -> dict[str, Any]:
    executable = resolve_capture(capture_command)
    result = _run(executable, ["-h"], 30, allowed_returncodes=(0, 1))
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if not output:
        raise TracyError("Tracy capture utility did not report help or version information")
    return {"command": str(executable), "version_output": output}


def capture_trace(
    output_file: str,
    *,
    address: str = "127.0.0.1",
    port: Optional[int] = None,
    seconds: Optional[int] = None,
    memlimit_percent: Optional[int] = None,
    force: bool = False,
    timeout_secs: int = 3600,
    capture_command: Optional[str] = None,
) -> dict[str, Any]:
    output = Path(output_file).expanduser().resolve()
    if output.suffix.lower() != ".tracy":
        raise TracyError("Output must use the .tracy extension")
    output.parent.mkdir(parents=True, exist_ok=True)
    args = ["-a", address, "-o", str(output)]
    if port is not None:
        if not 1 <= port <= 65535:
            raise TracyError("Port must be between 1 and 65535")
        args.extend(["-p", str(port)])
    if seconds is not None:
        if not 1 <= seconds <= 86400:
            raise TracyError("Seconds must be between 1 and 86400")
        args.extend(["-s", str(seconds)])
    if memlimit_percent is not None:
        if not 1 <= memlimit_percent <= 1000:
            raise TracyError("Memory limit must be between 1 and 1000 percent")
        args.extend(["-m", str(memlimit_percent)])
    if force:
        args.append("-f")
    result = _run(resolve_capture(capture_command), args, timeout_secs)
    if not output.is_file():
        raise TracyError("Tracy reported success but did not create the trace")
    return {
        "output_file": str(output),
        "size_bytes": output.stat().st_size,
        "stdout": result.stdout.strip(),
    }


def export_csv(
    trace_file: str,
    output_file: str,
    *,
    filter_name: Optional[str] = None,
    case_sensitive: bool = False,
    csv_command: Optional[str] = None,
) -> dict[str, Any]:
    trace = Path(trace_file).expanduser().resolve()
    output = Path(output_file).expanduser().resolve()
    if not trace.is_file() or trace.suffix.lower() != ".tracy":
        raise TracyError(f"Tracy trace does not exist or is not .tracy: {trace}")
    if output.suffix.lower() != ".csv":
        raise TracyError("Output must use the .csv extension")
    output.parent.mkdir(parents=True, exist_ok=True)
    args = [str(trace)]
    if filter_name:
        args.extend(["-f", filter_name])
    if case_sensitive:
        args.append("-c")
    result = _run(resolve_csvexport(csv_command), args, 300)
    output.write_text(result.stdout, encoding="utf-8", newline="")
    return {
        "trace_file": str(trace),
        "output_file": str(output),
        "size_bytes": output.stat().st_size,
    }


def summarize_csv(csv_file: str, limit: int = 20) -> dict[str, Any]:
    path = Path(csv_file).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".csv":
        raise TracyError(f"CSV file does not exist or is not .csv: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: float(row.get("std_ns", 0) or 0), reverse=True)
    return {"csv_file": str(path), "zone_count": len(rows), "top_zones": rows[:limit]}
