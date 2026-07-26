---
name: tracy-capture
description: >-
  Capture a trace from an already instrumented Tracy client with the official
  tracy-capture utility. This skill does not inject into uninstrumented apps.
license: MIT
compatibility: "Tracy 0.10+; dcc-mcp-core 0.19+"
allowed-tools: "python"
metadata:
  dcc-mcp:
    dcc: tracy
    layer: domain
    version: "0.2.5"  # x-release-please-version
    search-hint: "Tracy profiler capture trace game performance"
    tags: "tracy,profiling,performance,game-development"
    tools: tools.yaml
    depends: "dcc-diagnostics"
---

# Tracy Capture

The target process must be built with Tracy instrumentation and reachable at the
requested address. Call `get_version` first, then `capture_trace` with a `.tracy`
output path and an optional duration. The adapter never injects into arbitrary
processes or invokes a shell.
