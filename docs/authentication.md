# Authentication

The preferred path is xAI OAuth:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login
```

The login opens `accounts.x.ai` / `auth.x.ai`, stores tokens at
`~/.x-search-plugin/auth.json`, and refreshes the access token before use. The
OAuth bearer is used against the same `https://api.x.ai/v1/responses` endpoint
as API-key calls.

If you authenticated before the project was renamed from `x-search-codex`, the
runtime will continue to use the legacy `~/.x-search-codex/auth.json` store
when the new `~/.x-search-plugin/auth.json` store does not exist.

xAI still controls account entitlement. OAuth login can succeed while the API
later returns `403` for a subscription tier or allowlist issue.

## Headless Login

```bash
uv run --quiet --locked python scripts/x_search_auth.py login --no-browser
uv run --quiet --locked python scripts/x_search_auth.py login --manual-paste
```

In manual paste mode, paste the full callback URL or `?code=...&state=...`
fragment into the terminal prompt. Do not paste OAuth codes or tokens into chat.

## Status, Refresh, and Logout

```bash
uv run --quiet --locked python scripts/x_search_auth.py status
uv run --quiet --locked python scripts/x_search_auth.py refresh
uv run --quiet --locked python scripts/x_search_auth.py logout
```

## Credential Priority

1. Stored xAI OAuth credentials in `~/.x-search-plugin/auth.json`
2. `XAI_OAUTH_BEARER_TOKEN`
3. `XAI_BEARER_TOKEN`
4. `XAI_API_KEY`

Fallback env credentials are used only when no usable stored OAuth credential is
present. If a stored OAuth credential exists but xAI rejects it with `403`, the
plugin does not automatically retry with `XAI_API_KEY`.

## API-Key Shell Test

```bash
uv run --quiet --locked python scripts/x_search_auth.py logout
export XAI_API_KEY="..."
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"x_search","arguments":{"query":"latest posts about xAI"}}}' \
  | uv run --quiet --locked python scripts/x_search_mcp.py
```

The plugin does not read browser, X, or Hermes credential stores.
