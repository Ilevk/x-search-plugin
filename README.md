# X Search Codex

Codex plugin for read-only X/Twitter research through xAI's Responses API
`x_search` tool, without installing Hermes. It supports xAI OAuth login for
SuperGrok / X Premium+ accounts and falls back to `XAI_API_KEY` when needed.

## What It Provides

- `x_search`: flexible X research with citations when xAI returns them.
- `search_tweets`: structured search for recent posts by query/date/handle.
- `fetch_tweet`: inspect one X post URL.
- `get_trends`: ask xAI for regional X trends with evidence links.
- `x_search_status`: verify local credential and endpoint configuration without
  making a network call.
- `scripts/x_search_auth.py`: local xAI OAuth login, status, refresh, and logout.

## Credentials

Preferred path, no API key:

```bash
python3 scripts/x_search_auth.py login
```

This opens `accounts.x.ai` / `auth.x.ai`, stores tokens at
`~/.x-search-codex/auth.json`, and refreshes the access token before use. The
OAuth bearer is used against the same `https://api.x.ai/v1/responses` endpoint
as API-key calls. xAI still controls account entitlement; an OAuth login can
succeed while the API later returns `403` for a subscription or allowlist issue.

Headless or remote shell:

```bash
python3 scripts/x_search_auth.py login --no-browser
python3 scripts/x_search_auth.py login --manual-paste
```

Status and logout:

```bash
python3 scripts/x_search_auth.py status
python3 scripts/x_search_auth.py refresh
python3 scripts/x_search_auth.py logout
```

Fallback credentials, if OAuth is unavailable:

- `XAI_OAUTH_BEARER_TOKEN`
- `XAI_BEARER_TOKEN`
- `XAI_API_KEY`

Optional configuration:

- `XAI_BASE_URL` defaults to `https://api.x.ai/v1`
- `X_SEARCH_MODEL` defaults to `grok-4.20-reasoning`
- `X_SEARCH_TIMEOUT_SECONDS` defaults to `180`
- `X_SEARCH_RETRIES` defaults to `2`
- `X_SEARCH_CODEX_HOME` overrides the auth store directory
- `X_SEARCH_XAI_OAUTH_CLIENT_ID` overrides the public xAI OAuth client id

This plugin does not read browser, X, or Hermes credential stores. It stores
only its own xAI OAuth state under `~/.x-search-codex/` unless
`X_SEARCH_CODEX_HOME` is set. Never paste tokens into chat.

## Local Test

Protocol smoke test without network:

```bash
python3 scripts/smoke_mcp.py
```

Live call, only after setting a credential:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"x_search","arguments":{"query":"latest posts about xAI"}}}' \
  | python3 scripts/x_search_mcp.py
```

## License

MIT. See `LICENSE` and `NOTICE.md`.
