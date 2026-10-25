---
trigger: always_on
description: Use Graphify locally for focused codebase and architecture exploration when available.
---

## Graphify

Graphify output under `graphify-out/` is generated local tooling data and is intentionally not committed.

- If `graphify-out/graph.json` exists locally, use `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` for focused architecture exploration.
- If the graph is absent and the Graphify CLI or MCP is available, generate/update it locally before relying on graph-based conclusions.
- If Graphify is unavailable, work directly from the tracked repository tree, entry points, tests, and configuration; do not assume a graph exists.
- Keep generated Graphify output out of commits. Commit source rules or workflows only, not the generated index/report/visualization.
