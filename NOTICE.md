# Notices

This project is MIT licensed.

It was informed by the following MIT-licensed projects:

- `arthurkatcher/x-search-via-hermes`
  - Copyright (c) 2026 Arthur Katcher
  - Used as a reference for Codex plugin and skill packaging.
- `kitepon-rgb/HermesAgent`
  - Copyright (c) 2026 kitepon-rgb
  - Used as a reference for MCP tool shape and X research workflows.
- `NousResearch/hermes-agent`
  - Used as a reference for the xAI Responses API `x_search` payload shape.

This implementation does not vendor Hermes Agent and does not read Hermes
credential files. It calls xAI directly with credentials supplied by the local
environment.
