# Security Notes

- Do not paste OAuth codes, access tokens, refresh tokens, or API keys into
  chat.
- OAuth state is stored at `~/.x-search-plugin/auth.json` by default.
- Existing `~/.x-search-codex/auth.json` credentials remain usable as a legacy
  fallback after the rename.
- Use `uv run --quiet --locked python scripts/x_search_auth.py logout` to remove
  stored OAuth state.
- Do not set `XAI_BASE_URL` to an untrusted endpoint while using real OAuth or
  API-key credentials.
- Env fallback credentials require `X_SEARCH_ALLOW_UNTRUSTED_BASE_URL=1` before
  non-x.ai endpoints are allowed.
- This plugin is read-only. It does not post, like, follow, DM, or mutate X
  account state.
- The repository does not vendor Hermes and does not read Hermes auth files.
