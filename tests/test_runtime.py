import hashlib
import io
import json
import os
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from dcc_mcp_tracy import runtime
from dcc_mcp_tracy.runtime import TracyError, resolve_capture, summarize_csv


def test_summarize_csv_orders_zones(tmp_path: Path) -> None:
    path = tmp_path / "zones.csv"
    path.write_text("name,std_ns\nslow,20\nfast,2\n", encoding="utf-8")
    result = summarize_csv(str(path))
    assert result["top_zones"][0]["name"] == "slow"


def test_capture_requires_tracy_suffix(tmp_path: Path) -> None:
    from dcc_mcp_tracy.runtime import capture_trace

    with pytest.raises(TracyError, match=".tracy"):
        capture_trace(str(tmp_path / "trace.bin"))


def test_auto_download_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DCC_MCP_TRACY_CAPTURE", "missing-capture")
    monkeypatch.setenv("DCC_MCP_TRACY_AUTO_DOWNLOAD", "0")
    with pytest.raises(TracyError, match="does not exist"):
        resolve_capture()


def test_auto_download_accepts_prefixed_runtime_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("tracy-capture.exe", b"capture")
        bundle.writestr("tracy-csvexport.exe", b"csvexport")
    archive_bytes = archive.getvalue()
    release_bytes = json.dumps(
        {
            "tag_name": "v0.13.1",
            "assets": [
                {
                    "name": "windows-0.13.1.zip",
                    "browser_download_url": "https://example.invalid/windows.zip",
                    "digest": "sha256:" + hashlib.sha256(archive_bytes).hexdigest(),
                }
            ],
        }
    ).encode()
    responses = iter(
        (io.BytesIO(release_bytes), io.BytesIO(archive_bytes), io.BytesIO(release_bytes))
    )
    monkeypatch.setattr(runtime, "os", SimpleNamespace(name="nt", environ=os.environ))
    monkeypatch.setattr(runtime, "_runtime_cache", lambda: tmp_path / "tracy")
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        runtime.urllib.request, "urlopen", lambda *_args, **_kwargs: next(responses)
    )

    capture = runtime._download_latest_capture()
    csvexport = runtime.resolve_csvexport()

    assert capture.name == "tracy-capture.exe"
    assert csvexport.name == "tracy-csvexport.exe"


def test_get_version_accepts_usage_exit_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime, "resolve_capture", lambda _explicit=None: Path("capture.exe"))
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *_args, **_kwargs: runtime.subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Usage: capture -o output.tracy"
        ),
    )

    result = runtime.get_version()

    assert result["version_output"].startswith("Usage: capture")
