# Tools and Examples

## MCP Tools

- `x_search`: flexible X research with citations when xAI returns them.
- `search_tweets`: structured search for recent posts by query, date, or
  handle.
- `fetch_tweet`: inspect one X post URL.
- `get_trends`: ask xAI for regional X trends with evidence links.
- `x_search_status`: verify credential and endpoint configuration without
  making a network call.

## Local Auth Utility

- `scripts/x_search_auth.py`: local xAI OAuth login, status, refresh, and
  logout.

## Agent Prompts

```text
Search X for recent posts from @Lo_gan__ and summarize the latest 5 with links.
```

```text
Find current X reactions to OpenAI Codex and include source links.
```

```text
Check X trends related to xAI in the United States and separate sourced claims from unsourced summaries.
```

## Tool Payload Examples

Search broadly:

```json
{
  "query": "What are people saying about xAI today?"
}
```

Search one account:

```json
{
  "query": "Find recent posts from @Lo_gan__",
  "allowed_x_handles": ["Lo_gan__"]
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
