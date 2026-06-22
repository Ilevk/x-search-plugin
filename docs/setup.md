# Setup Guide

This project supports direct MCP registration and Codex plugin marketplace-style
installation. The runtime is uv-first: both the root checkout and installable
plugin payload include `pyproject.toml` and `uv.lock`, and MCP startup uses
`uv run --quiet --locked ...`.

## Prerequisites

- `uv`
- GitHub SSH access, or use the repository HTTPS URL
- Codex CLI or Claude Code with MCP support
- An xAI account with SuperGrok / X Premium+ OAuth entitlement, or `XAI_API_KEY`

## Clone

```bash
git clone git@github.com:Ilevk/x-search-plugin.git
cd x-search-plugin
```

## Codex Direct MCP Registration

```bash
codex mcp add x-search-plugin -- uv run --quiet --locked python "$PWD/scripts/x_search_mcp.py"
uv run --quiet --locked python scripts/x_search_auth.py login
uv run --quiet --locked python scripts/x_search_auth.py status
uv run --quiet --locked python scripts/smoke_mcp.py
```

If Codex already had the MCP server running, open a new Codex thread or restart
Codex so it starts the updated server process.

## Codex Plugin Marketplace Install

From a full repository checkout:

```bash
codex plugin marketplace add "$PWD"
codex plugin add x-search-plugin@x-search-plugin
```

For Git-based install:

```bash
codex plugin marketplace add Ilevk/x-search-plugin --ref main
codex plugin add x-search-plugin@x-search-plugin
```

Run marketplace commands from the full repository root, not from the installed
plugin cache or `plugins/x-search-plugin/` payload directory.

## Claude Code Setup

The repository includes `.mcp.json`, `CLAUDE.md`, and `.claude/settings.json`.
Start Claude Code from the repository root:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login
claude
```

Approve the `x-search-plugin` MCP server if prompted, then check:

```text
/mcp
```

Manual Claude Code registration, if project `.mcp.json` is not picked up:

```bash
claude mcp add --transport stdio --scope project x-search-plugin -- uv run --quiet --locked python "$PWD/scripts/x_search_mcp.py"
```

## API-Key Fallback

For API-key usage, skip OAuth and set `XAI_API_KEY` before starting the agent
client:

```bash
export XAI_API_KEY="..."
```

Already-running MCP processes do not inherit new environment variables. Open a
new Codex thread, restart Codex, or restart Claude Code after changing
credentials.

## Live Search Check

After credentials are configured, this command verifies the credential and xAI
entitlement path:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"x_search","arguments":{"query":"latest posts about xAI"}}}' \
  | uv run --quiet --locked python scripts/x_search_mcp.py
```
