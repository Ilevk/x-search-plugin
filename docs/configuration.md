# Configuration

The default configuration should work for normal OAuth or API-key usage. Use
environment variables only when you need explicit runtime overrides.

| Variable | Default | Purpose |
| --- | --- | --- |
| `XAI_BASE_URL` | `https://api.x.ai/v1` | xAI API base URL. Use only trusted xAI endpoints or local test endpoints. |
| `X_SEARCH_MODEL` | `grok-4.20-reasoning` | Model sent to the xAI Responses API. |
| `X_SEARCH_TIMEOUT_SECONDS` | `180` | Network timeout for xAI calls. |
| `X_SEARCH_RETRIES` | `2` | Retry count for retryable upstream failures. |
| `X_SEARCH_PLUGIN_HOME` | `~/.x-search-plugin` | Auth store directory override. |
| `X_SEARCH_CODEX_HOME` | unset | Legacy auth-store override after the project rename. |
| `X_SEARCH_XAI_OAUTH_CLIENT_ID` | bundled public client id | xAI OAuth client id override. |
| `X_SEARCH_PLUGIN_DEBUG` | unset | Include tracebacks in MCP tool errors when set to `1`. |
| `X_SEARCH_CODEX_DEBUG` | unset | Legacy debug alias after the project rename. |
| `X_SEARCH_ALLOW_UNTRUSTED_BASE_URL` | unset | Allows env fallback credentials with a non-x.ai `XAI_BASE_URL`; local tests only. |

Treat `XAI_BASE_URL` as a credential sink because bearer credentials are sent to
that endpoint. Do not use real OAuth or API-key credentials with untrusted
override endpoints.
