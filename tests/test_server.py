from __future__ import annotations

import re
from importlib import metadata
from pathlib import Path

import pytest

from dcc_mcp_tracy import server


def test_help_exits_without_starting_server(monkeypatch, capsys) -> None:
    started = []
    monkeypatch.setattr(server, "start_server", lambda: started.append(True))

    with pytest.raises(SystemExit) as exc:
        server.main(["--help"])

    assert exc.value.code == 0
    assert "Tracy MCP server" in capsys.readouterr().out
    assert started == []


def test_version_exits_without_starting_server(monkeypatch, capsys) -> None:
    started = []
    monkeypatch.setattr(server, "start_server", lambda: started.append(True))

    with pytest.raises(SystemExit) as exc:
        server.main(["--version"])

    assert exc.value.code == 0
    assert metadata.version("dcc-mcp-tracy") in capsys.readouterr().out
    assert started == []


def test_runtime_and_skill_versions_match_distribution() -> None:
    expected = metadata.version("dcc-mcp-tracy")
    skills = Path(__file__).parents[1] / "src" / "dcc_mcp_tracy" / "skills"

    assert server.__version__ == expected
    for skill in ("tracy-capture", "tracy-analysis"):
        text = (skills / skill / "SKILL.md").read_text(encoding="utf-8")
        assert re.search(rf'^    version: "{re.escape(expected)}"', text, re.MULTILINE)


@pytest.mark.parametrize(
    ("skill_name", "expected_tools"),
    [
        ("tracy-capture", {"get_version", "capture_trace"}),
        ("tracy-analysis", {"export_csv", "summarize_csv"}),
    ],
)
def test_bundled_skill_tools_load_with_current_core(skill_name, expected_tools) -> None:
    from dcc_mcp_core import parse_skill_md

    skills = Path(__file__).parents[1] / "src" / "dcc_mcp_tracy" / "skills"
    metadata = parse_skill_md(str(skills / skill_name))

    assert expected_tools == {tool.name for tool in metadata.tools}
