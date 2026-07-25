---
name: tracy-analysis
description: >-
  Export and summarize Tracy zone statistics from saved .tracy traces.
license: MIT
compatibility: "Tracy 0.10+; dcc-mcp-core 0.19+"
allowed-tools: "python"
metadata:
  dcc-mcp:
    dcc: tracy
    layer: domain
    version: "0.2.4"  # x-release-please-version
    search-hint: "Tracy profiler CSV zone statistics performance triage"
    tags: "tracy,profiling,performance,diagnostics"
    tools: tools.yaml
    depends: "dcc-diagnostics"
---

# Tracy Analysis

Use `export_csv` for offline zone statistics, then `summarize_csv` to rank zones
by standard deviation. This is triage data, not a substitute for GPU-specific
or frame-capture analysis.
