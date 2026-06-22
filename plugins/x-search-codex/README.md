# X Search Codex

Codex plugin for read-only X/Twitter research through xAI's Responses API
`x_search` tool, without installing Hermes. It supports xAI OAuth login for
SuperGrok / X Premium+ accounts and falls back to `XAI_API_KEY` when no usable
stored OAuth credential is present.

This is not a browser scraper. The plugin calls `https://api.x.ai/v1/responses`
with xAI's server-side `x_search` tool and returns Grok's answer plus citations
when xAI provides them.

## Quickstart

Prerequisites:

- uv
- Codex CLI with MCP support
- An xAI account with SuperGrok / X Premium+ OAuth entitlement, or `XAI_API_KEY`
- GitHub SSH access for the command below, or use the repository HTTPS URL

Clone the repository:

```bash
git clone git@github.com:Ilevk/x-search-codex.git
cd x-search-codex
```

Register the MCP server with Codex:

```bash
codex mcp add x-search-codex -- uv run --quiet --locked python "$PWD/scripts/x_search_mcp.py"
```

Authenticate with xAI OAuth:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login
```

Verify protocol wiring:

```bash
uv run --quiet --locked python scripts/x_search_auth.py status
uv run --quiet --locked python scripts/smoke_mcp.py
```

`smoke_mcp.py` intentionally isolates credentials and checks MCP protocol shape
plus missing-credential handling. The live search below is the credential and
xAI entitlement check.

Run a live search:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"x_search","arguments":{"query":"latest posts about xAI"}}}' \
  | uv run --quiet --locked python scripts/x_search_mcp.py
```

If Codex already had the MCP server running, open a new Codex thread or restart
Codex so it starts the updated server process.

## Installation Options

Option 1: direct MCP registration during local development:

```bash
codex mcp add x-search-codex -- uv run --quiet --locked python "$PWD/scripts/x_search_mcp.py"
```

Option 2: marketplace-style plugin install from this repository:

```bash
codex plugin marketplace add "$PWD"
codex plugin add x-search-codex@x-search-codex
```

For Git-based install, use the repository as a marketplace source:

```bash
codex plugin marketplace add Ilevk/x-search-codex --ref main
codex plugin add x-search-codex@x-search-codex
```

The installable plugin payload lives under `plugins/x-search-codex/`. Keep it in
sync with the root development files when changing scripts, MCP config, skills,
or plugin metadata.

The plugin is uv-first: `pyproject.toml` and `uv.lock` are included in both the
root development checkout and the installable plugin payload. MCP startup uses
`uv run --quiet --locked ...` so the runtime contract is explicit and lockfile-backed.

## What It Provides

- `x_search`: flexible X research with citations when xAI returns them.
- `search_tweets`: structured search for recent posts by query/date/handle.
- `fetch_tweet`: inspect one X post URL.
- `get_trends`: ask xAI for regional X trends with evidence links.
- `x_search_status`: verify credential and endpoint configuration without
  making a network call.
- `scripts/x_search_auth.py`: local xAI OAuth login, status, refresh, and logout.

## Authentication

Preferred path, no API key:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login
```

The login opens `accounts.x.ai` / `auth.x.ai`, stores tokens at
`~/.x-search-codex/auth.json`, and refreshes the access token before use.
The OAuth bearer is used against the same `https://api.x.ai/v1/responses`
endpoint as API-key calls.

xAI still controls account entitlement. OAuth login can succeed while the API
later returns `403` for a subscription tier or allowlist issue.

Headless or remote shell:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login --no-browser
uv run --quiet --locked python scripts/x_search_auth.py login --manual-paste
```

Status, refresh, and logout:

```bash
uv run --quiet --locked python scripts/x_search_auth.py status
uv run --quiet --locked python scripts/x_search_auth.py refresh
uv run --quiet --locked python scripts/x_search_auth.py logout
```

Credential priority:

1. Stored xAI OAuth credentials in `~/.x-search-codex/auth.json`
2. `XAI_OAUTH_BEARER_TOKEN`
3. `XAI_BEARER_TOKEN`
4. `XAI_API_KEY`

Fallback env credentials are used only when no usable stored OAuth credential is
present. If a stored OAuth credential exists but xAI rejects it with `403`, the
plugin does not automatically retry with `XAI_API_KEY`.

API-key fallback for direct shell tests:

```bash
uv run --quiet --locked python scripts/x_search_auth.py logout
export XAI_API_KEY="..."
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"x_search","arguments":{"query":"latest posts about xAI"}}}' \
  | uv run --quiet --locked python scripts/x_search_mcp.py
```

For Codex App usage, set `XAI_API_KEY` before the MCP server starts, then open a
new thread or restart Codex. Already-running MCP processes do not inherit new
environment variables.

The plugin does not read browser, X, or Hermes credential stores.

## Codex App Usage

After registering the MCP server and authenticating, start a new Codex thread.
Ask for X-sourced research directly, for example:

```text
Search X for recent posts from @xai and summarize the latest 5 with links.
```

If `x_search_status` in an existing thread still shows the old shape or
`configured: false` after a successful login, that thread is likely connected to
an already-running MCP process. Open a new thread or restart Codex.

## Tool Examples

Search broadly:

```json
{
  "query": "What are people saying about xAI today?"
}
```

Search one account:

```json
{
  "query": "Find recent posts from @xai",
  "allowed_x_handles": ["xai"]
}
```

Search a date range:

```json
{
  "query": "OpenAI Codex reactions",
  "from_date": "2026-06-01",
  "to_date": "2026-06-22"
}
```

## Configuration

- `XAI_BASE_URL` defaults to `https://api.x.ai/v1`; use only trusted xAI
  endpoints or local test endpoints, because bearer credentials are sent there
- `X_SEARCH_MODEL` defaults to `grok-4.20-reasoning`
- `X_SEARCH_TIMEOUT_SECONDS` defaults to `180`
- `X_SEARCH_RETRIES` defaults to `2`
- `X_SEARCH_CODEX_HOME` overrides the auth store directory
- `X_SEARCH_XAI_OAUTH_CLIENT_ID` overrides the public xAI OAuth client id

## Troubleshooting

### `configured: false`

Run:

```bash
uv run --quiet --locked python scripts/x_search_auth.py status
```

If OAuth is not configured, run `uv run --quiet --locked python scripts/x_search_auth.py login`. If the
CLI status is configured but Codex still says false, restart the Codex MCP
server by opening a new thread or restarting Codex.

### OAuth login succeeds, but search returns `403`

This is an xAI entitlement/API access issue, not a local token refresh problem.
Your X Premium+ or SuperGrok account may not be allowed on this OAuth API
surface. To use `XAI_API_KEY` as a fallback, remove or isolate the stored OAuth
credential first, then restart the MCP process:

```bash
uv run --quiet --locked python scripts/x_search_auth.py logout
export XAI_API_KEY="..."
```

For Codex App, open a new thread or restart Codex after changing credentials.

### `401` or refresh failure

Run:

```bash
uv run --quiet --locked python scripts/x_search_auth.py refresh
```

If refresh fails, run `uv run --quiet --locked python scripts/x_search_auth.py login` again.

### Callback timeout

Use manual paste mode:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login --manual-paste
```

Approve in the browser, then paste the full callback URL or
`?code=...&state=...` fragment into the terminal prompt. A bare authorization
code is accepted only as a last-resort local-terminal fallback when xAI does not
return a callback URL; it cannot verify OAuth `state`.

### `degraded: true`

xAI returned an answer without citations despite narrowing filters such as
handles or dates. Treat the result as unsourced. Broaden the filters, retry, or
verify with another source.

## Security Notes

- Do not paste OAuth codes, access tokens, refresh tokens, or API keys into chat.
- OAuth state is stored at `~/.x-search-codex/auth.json` by default.
- Use `uv run --quiet --locked python scripts/x_search_auth.py logout` to remove stored OAuth state.
- Do not set `XAI_BASE_URL` to an untrusted endpoint while using real OAuth or
  API-key credentials.
- This plugin is read-only. It does not post, like, follow, DM, or mutate X
  account state.
- The repository does not vendor Hermes and does not read Hermes auth files.

## Development

Protocol smoke test without network:

```bash
uv run --quiet --locked python scripts/smoke_mcp.py
```

Syntax check:

```bash
env PYTHONPYCACHEPREFIX=/tmp/x-search-codex-pycache \
  uv run --quiet --locked python -m py_compile scripts/xai_oauth.py scripts/x_search_auth.py scripts/x_search_mcp.py scripts/smoke_mcp.py
```

The smoke test isolates credentials with a temporary `X_SEARCH_CODEX_HOME` and
verifies that the server reports a clear missing-credential error.

## License

MIT. See `LICENSE` and `NOTICE.md`.
