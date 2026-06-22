# Repository Agent Guide

## Project Goal

This repository provides an MCP plugin for read-only X/Twitter research through
xAI's Responses API `x_search` tool. Codex and Claude Code are the first
supported client surfaces.

The primary authentication path is xAI OAuth for SuperGrok / X Premium+
accounts. `XAI_API_KEY` remains a fallback path. Do not redesign the project
around browser scraping or X API v2 unless Logan explicitly changes the goal.

## Boundaries

- Must remain read-only: no posting, liking, following, DM access, deletes, or
  account mutation.
- Do not read browser cookies, X app storage, or Hermes credential files.
- Do not print, log, commit, or ask the user to paste access tokens, refresh
  tokens, API keys, or credential file contents. OAuth authorization codes may
  be pasted only into the local
  `uv run --quiet --locked python scripts/x_search_auth.py login --manual-paste` terminal prompt,
  never into chat or docs. Prefer full callback URLs or `?code=...&state=...`
  fragments over bare authorization codes.
- Treat `XAI_BASE_URL` as a credential sink. Do not use real OAuth/API-key
  credentials with untrusted override endpoints.
- Non-x.ai `XAI_BASE_URL` with env fallback credentials requires
  `X_SEARCH_ALLOW_UNTRUSTED_BASE_URL=1` and is for local tests only.
- OAuth state belongs under `~/.x-search-plugin/auth.json` by default, or under
  `X_SEARCH_PLUGIN_HOME` when explicitly set.
- Legacy `~/.x-search-codex/auth.json` and `X_SEARCH_CODEX_HOME` are supported
  only for users who authenticated before the project rename.
- Keep the implementation dependency-light. The current runtime uses Python
  standard library only.

## Implementation Conventions

- Keep MCP protocol behavior in `scripts/x_search_mcp.py`.
- Keep OAuth login, refresh, status, and credential resolution in
  `scripts/xai_oauth.py`.
- Keep human-facing auth commands in `scripts/x_search_auth.py`.
- Preserve API-key fallback behavior when changing OAuth logic.
- Prefer explicit, structured JSON tool results. Missing credentials and
  upstream failures should return clear tool errors rather than stack traces.
- Validate external inputs at the tool boundary. Date ranges should be strict;
  handle filters should at minimum be normalized, bounded, and kept mutually
  exclusive where required.

## Verification

Before committing behavior changes, run:

```bash
env PYTHONPYCACHEPREFIX=/tmp/x-search-plugin-pycache \
  uv run --quiet --locked python -m py_compile scripts/xai_oauth.py scripts/x_search_auth.py scripts/x_search_mcp.py scripts/smoke_mcp.py plugins/x-search-plugin/scripts/xai_oauth.py plugins/x-search-plugin/scripts/x_search_auth.py plugins/x-search-plugin/scripts/x_search_mcp.py plugins/x-search-plugin/scripts/smoke_mcp.py
uv run --quiet --locked python scripts/smoke_mcp.py
```

For live validation, use OAuth or API-key credentials already configured in the
local environment. Do not expose the credential value in terminal output or
chat. A useful live check is:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"x_search","arguments":{"query":"latest posts about xAI"}}}' \
  | uv run --quiet --locked python scripts/x_search_mcp.py
```

## Documentation Expectations

When auth, setup, or failure behavior changes, update `README.md` and
`skills/x-search-plugin/SKILL.md` in the same change. Keep docs operational:
commands should be copy-pasteable and troubleshooting should name the expected
failure mode.

## Plugin Packaging Status

The repository supports both direct `codex mcp add` usage and marketplace-style
`codex plugin add` installation.

Marketplace installation uses:

```text
.agents/plugins/marketplace.json
plugins/x-search-plugin/.codex-plugin/plugin.json
plugins/x-search-plugin/.mcp.json
plugins/x-search-plugin/skills/...
plugins/x-search-plugin/scripts/...
```

The root files are the development source of truth. The `plugins/x-search-plugin`
payload must stay in sync when changing scripts, MCP config, skills, README,
NOTICE, LICENSE, or plugin metadata. After packaging changes, verify with a
local marketplace registration and `codex plugin add x-search-plugin@x-search-plugin`.

## Git Discipline

Stage files deliberately. Keep implementation and unrelated cleanup separate.
Do not commit generated credential stores, caches, or local machine artifacts.
