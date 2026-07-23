# dcc-mcp-tracy

Tracy frame-profiler capture and offline zone analysis for DCC-MCP.

Tracy is a client/server profiler: the target must be built with Tracy instrumentation (C/C++, Rust, C#, Python, or another supported binding). This adapter controls the official `tracy-capture` and `tracy-csvexport` utilities; it does not inject Tracy into an uninstrumented process.

## Install

```bash
pip install dcc-mcp-tracy
```

Install Tracy separately and set `DCC_MCP_TRACY_CAPTURE` and `DCC_MCP_TRACY_CSVEXPORT`, or put the utilities on `PATH`. On Windows, if neither is available, the adapter downloads and caches the official latest Tracy release automatically. Set `DCC_MCP_TRACY_AUTO_DOWNLOAD=0` to require a local installation; use `DCC_MCP_RUNTIME_CACHE` to choose the cache root. Linux/macOS currently require explicit Tracy binaries because the official release does not ship those desktop bundles.

## Workflow

1. Build/run the instrumented game, engine, Unity native plugin, Unreal module, or gateway process.
2. Call `tracy_capture__capture_trace` with the client address and `.tracy` output path.
3. Call `tracy_analysis__export_csv`, then `tracy_analysis__summarize_csv` to identify high-variance zones.

The adapter invokes subprocesses with `shell=False`, validates trace/output extensions, and never accepts a shell command.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
```

Tracy is maintained independently at https://github.com/wolfpld/tracy.
