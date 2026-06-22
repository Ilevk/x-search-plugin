# X Search Plugin

MCP plugin for read-only X/Twitter research through xAI's Responses API
`x_search` tool. It is packaged for Codex and Claude Code, supports xAI OAuth
login for SuperGrok / X Premium+ accounts, and falls back to `XAI_API_KEY` when
no usable stored OAuth credential is present.

This is not a browser scraper. The plugin calls `https://api.x.ai/v1/responses`
with xAI's server-side `x_search` tool and returns Grok's answer plus citations
when xAI provides them.

## Copy-Paste Agent Prompt

Paste this into Codex or Claude Code to have the agent set up and verify the
plugin for you:

```text
Set up x-search-plugin from https://github.com/Ilevk/x-search-plugin for this machine.

Use uv. Prefer xAI OAuth, but if I already have XAI_API_KEY configured, use that as the fallback. Do not ask me to paste access tokens, refresh tokens, API keys, browser cookies, or credential file contents into chat.

Steps:
1. Clone or update the repository.
2. Register the x-search-plugin MCP server for the current agent client.
   - Codex: use codex mcp add or the Codex plugin marketplace flow.
   - Claude Code: use the repository .mcp.json, or claude mcp add --transport stdio --scope project if needed.
3. Run uv run --quiet --locked python scripts/x_search_auth.py status.
4. If no credential is configured, ask me to run uv run --quiet --locked python scripts/x_search_auth.py login locally.
5. Run uv run --quiet --locked python scripts/smoke_mcp.py.
6. Confirm the MCP tools are available, then try a read-only X search for recent posts from @Lo_gan__.

Keep this read-only. Do not post, like, follow, DM, or mutate any X account state.
```

## Quickstart for Codex

Prerequisites: `uv`, Codex CLI with MCP support, and either an xAI OAuth-capable
SuperGrok / X Premium+ account or `XAI_API_KEY`.

```bash
git clone git@github.com:Ilevk/x-search-plugin.git
cd x-search-plugin
codex mcp add x-search-plugin -- uv run --quiet --locked python "$PWD/scripts/x_search_mcp.py"
uv run --quiet --locked python scripts/x_search_auth.py login
uv run --quiet --locked python scripts/x_search_auth.py status
uv run --quiet --locked python scripts/smoke_mcp.py
```

For API-key usage instead, skip OAuth and set `XAI_API_KEY` before starting
Codex:

```bash
export XAI_API_KEY="..."
```

Open a new Codex thread or restart Codex after changing credentials or MCP
registration.

## Quickstart for Claude Code

Prerequisites: `uv`, Claude Code with MCP support, and either an xAI OAuth-capable
SuperGrok / X Premium+ account or `XAI_API_KEY`.

```bash
git clone git@github.com:Ilevk/x-search-plugin.git
cd x-search-plugin
uv run --quiet --locked python scripts/x_search_auth.py login
claude
```

Approve the `x-search-plugin` MCP server if prompted, then check `/mcp`.

Manual registration, if project `.mcp.json` is not picked up:

```bash
claude mcp add --transport stdio --scope project x-search-plugin -- uv run --quiet --locked python "$PWD/scripts/x_search_mcp.py"
```

## Documentation

- [Setup Guide](docs/setup.md) - Codex, Claude Code, and marketplace install
  paths.
- [Authentication](docs/authentication.md) - OAuth, refresh, logout, credential
  priority, and API-key fallback.
- [Tools and Examples](docs/tools.md) - MCP tools and common X research prompts.
- [Configuration](docs/configuration.md) - environment variables and runtime
  knobs.
- [Troubleshooting](docs/troubleshooting.md) - common setup, auth, and xAI
  response failures.
- [Security Notes](docs/security.md) - read-only boundary and credential
  handling.
- [Development](docs/development.md) - smoke tests, packaging sync, and local
  verification.

## License

MIT. See `LICENSE` and `NOTICE.md`.
