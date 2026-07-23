"""Safe wrappers for Tracy's capture and CSV export utilities."""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional, Sequence


class TracyError(RuntimeError):
    """Raised when a Tracy operation cannot satisfy its contract."""


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
    return _resolve(
        explicit,
        "DCC_MCP_TRACY_CAPTURE",
        ("tracy-capture.exe", "tracy-capture", "capture"),
        "Tracy capture utility",
    )


def resolve_csvexport(explicit: Optional[str] = None) -> Path:
    return _resolve(
        explicit,
        "DCC_MCP_TRACY_CSVEXPORT",
        ("tracy-csvexport.exe", "tracy-csvexport", "csvexport"),
        "Tracy CSV exporter",
    )


def _run(
    executable: Path, arguments: Sequence[str], timeout_secs: int
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
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()[-2000:]
        raise TracyError(f"Tracy exited with code {result.returncode}: {detail}")
    return result


def get_version(*, capture_command: Optional[str] = None) -> dict[str, Any]:
    executable = resolve_capture(capture_command)
    result = _run(executable, ["-h"], 30)
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
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
