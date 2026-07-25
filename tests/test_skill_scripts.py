import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("script", "runtime_name", "arguments"),
    [
        ("tracy-capture/scripts/capture_trace.py", "capture_trace", {"output_file": "out.tracy"}),
        (
            "tracy-analysis/scripts/export_csv.py",
            "export_csv",
            {"trace_file": "in.tracy", "output_file": "out.csv"},
        ),
    ],
)
def test_runtime_entries_do_not_forward_core_metadata(
    script: str, runtime_name: str, arguments: dict[str, str], monkeypatch
) -> None:
    path = Path(__file__).parents[1] / "src" / "dcc_mcp_tracy" / "skills" / script
    spec = importlib.util.spec_from_file_location(runtime_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    forwarded = {}
    monkeypatch.setattr(
        module, runtime_name, lambda *_args, **kwargs: forwarded.update(kwargs) or {}
    )

    result = module.main(**arguments, _meta={"job_id": "test"})

    assert result["success"] is True
    assert "_meta" not in forwarded
