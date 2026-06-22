---
name: x-search-codex
description: Use when the user wants read-only X/Twitter research, recent posts, public reactions, trends, account-specific posts, or X-sourced evidence through the local x-search-codex MCP tools.
---

# X Search Codex

Use this skill for read-only X/Twitter research through the local
`x-search-codex` MCP server.

Do not use this skill for posting, liking, following, DMs, account changes, or
other X mutations. The plugin only supports read-only research.

## Preconditions

The MCP server needs one usable xAI credential. Prefer local xAI OAuth for
SuperGrok / X Premium+ accounts:

```bash
python3 scripts/x_search_auth.py login
```

The login stores token state under `~/.x-search-codex/auth.json` and the MCP
server refreshes the access token before X Search calls.

Fallback environment credentials:

- `XAI_OAUTH_BEARER_TOKEN`
- `XAI_BEARER_TOKEN`
- `XAI_API_KEY`

If the user asks to authenticate, do not ask them to paste secrets into chat.
Tell them to run `python3 scripts/x_search_auth.py login` locally, or put a
fallback credential in their local shell, secrets manager, or Codex environment.
Never read or print local credential files.

## Tool Choice

- Use `x_search_status` first when troubleshooting setup.
- Use `x_search` for flexible research questions, broad reactions, rumor checks,
  and source-backed summaries.
- Use `search_tweets` when the user wants a list of recent posts matching a
  query, optional language, date range, or specific author.
- Use `fetch_tweet` when the user provides one X post URL.
- Use `get_trends` when the user asks what is trending in a region.

## Reporting

When answering the user:

- Say that X was searched through xAI `x_search`.
- Include direct X links when returned.
- Include dates when available.
- Separate confirmed announcements from reactions, rumors, or commentary.
- If xAI returns no citations despite narrow filters, state that confidence is
  lower and recommend broadening filters or retrying.

## Failure Handling

- Missing credential: ask the user to run `python3 scripts/x_search_auth.py login`
  or configure one of the supported env vars.
- `401`: credential is invalid or expired; refresh or log in again.
- `403`: account entitlement or xAI OAuth/API access issue.
- Timeout: retry once with a narrower query or longer timeout.
- No citations with filters: treat the result as degraded, not fully sourced.
