# Development

## Protocol Smoke Test

```bash
uv run --quiet --locked python scripts/smoke_mcp.py
```

The smoke test isolates credentials with a temporary `X_SEARCH_PLUGIN_HOME` and
verifies that the server reports a clear missing-credential error.

## Syntax Check

```bash
env PYTHONPYCACHEPREFIX=/tmp/x-search-plugin-pycache \
  uv run --quiet --locked python -m py_compile scripts/xai_oauth.py scripts/x_search_auth.py scripts/x_search_mcp.py scripts/smoke_mcp.py plugins/x-search-plugin/scripts/xai_oauth.py plugins/x-search-plugin/scripts/x_search_auth.py plugins/x-search-plugin/scripts/x_search_mcp.py plugins/x-search-plugin/scripts/smoke_mcp.py
```

## Payload Smoke Test

```bash
cd plugins/x-search-plugin
uv run --quiet --locked python scripts/smoke_mcp.py
```

## Packaging Sync

The root files are the development source of truth. Keep
`plugins/x-search-plugin/` in sync when changing scripts, MCP config, skills,
README, docs, NOTICE, LICENSE, or plugin metadata.

Marketplace installation uses:

```text
.agents/plugins/marketplace.json
plugins/x-search-plugin/.codex-plugin/plugin.json
plugins/x-search-plugin/.mcp.json
plugins/x-search-plugin/skills/...
plugins/x-search-plugin/scripts/...
plugins/x-search-plugin/docs/...
```

After packaging changes, verify with a local marketplace registration and:

```bash
codex plugin add x-search-plugin@x-search-plugin
```
