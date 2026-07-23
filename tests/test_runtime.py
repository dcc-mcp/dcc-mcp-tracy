from pathlib import Path

import pytest

from dcc_mcp_tracy.runtime import TracyError, summarize_csv


def test_summarize_csv_orders_zones(tmp_path: Path) -> None:
    path = tmp_path / "zones.csv"
    path.write_text("name,std_ns\nslow,20\nfast,2\n", encoding="utf-8")
    result = summarize_csv(str(path))
    assert result["top_zones"][0]["name"] == "slow"


def test_capture_requires_tracy_suffix(tmp_path: Path) -> None:
    from dcc_mcp_tracy.runtime import capture_trace

    with pytest.raises(TracyError, match=".tracy"):
        capture_trace(str(tmp_path / "trace.bin"))
