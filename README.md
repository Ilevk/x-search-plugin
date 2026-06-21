# X Search Codex

Codex plugin for read-only X/Twitter research through xAI's Responses API
`x_search` tool, without installing Hermes.

## What It Provides

- `x_search`: flexible X research with citations when xAI returns them.
- `search_tweets`: structured search for recent posts by query/date/handle.
- `fetch_tweet`: inspect one X post URL.
- `get_trends`: ask xAI for regional X trends with evidence links.
- `x_search_status`: verify local credential and endpoint configuration without
  making a network call.

## Credentials

Set one of these in the environment before Codex starts the MCP server:

- `XAI_OAUTH_BEARER_TOKEN`
- `XAI_BEARER_TOKEN`
- `XAI_API_KEY`

Optional configuration:

- `XAI_BASE_URL` defaults to `https://api.x.ai/v1`
- `X_SEARCH_MODEL` defaults to `grok-4.20-reasoning`
- `X_SEARCH_TIMEOUT_SECONDS` defaults to `180`
- `X_SEARCH_RETRIES` defaults to `2`

This plugin does not perform OAuth login or token refresh. It deliberately avoids
reading browser, X, or Hermes credential stores. Keep credentials in your local
environment or a secrets manager.

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
