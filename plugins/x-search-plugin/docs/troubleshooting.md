# Troubleshooting

## `configured: false`

Run:

```bash
uv run --quiet --locked python scripts/x_search_auth.py status
```

If OAuth is not configured, run:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login
```

If the CLI status is configured but Codex still says false, restart the Codex MCP
server by opening a new thread or restarting Codex.

## OAuth Login Succeeds, but Search Returns `403`

This is an xAI entitlement/API access issue, not a local token refresh problem.
Your X Premium, Premium+, or SuperGrok account may not be allowed on this OAuth
API surface.

To use `XAI_API_KEY` as a fallback, remove or isolate the stored OAuth credential
first, then restart the MCP process:

```bash
uv run --quiet --locked python scripts/x_search_auth.py logout
export XAI_API_KEY="..."
```

For Codex App, open a new thread or restart Codex after changing credentials.

## `401` or Refresh Failure

Run:

```bash
uv run --quiet --locked python scripts/x_search_auth.py refresh
```

If refresh fails, run:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login
```

## Callback Timeout

Use manual paste mode:

```bash
uv run --quiet --locked python scripts/x_search_auth.py login --manual-paste
```

Approve in the browser, then paste the full callback URL or
`?code=...&state=...` fragment into the terminal prompt. A bare authorization
code is accepted only as a last-resort local-terminal fallback when xAI does not
return a callback URL; it cannot verify OAuth `state`.

## `degraded: true`

xAI returned an answer without citations despite narrowing filters such as
handles or dates. Treat the result as unsourced. Broaden the filters, retry, or
verify with another source.
