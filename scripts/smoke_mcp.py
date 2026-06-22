#!/usr/bin/env python3
"""Offline smoke test for the x-search-codex MCP server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "scripts" / "x_search_mcp.py"


def main() -> int:
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke", "version": "0.1.0"},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "x_search_status", "arguments": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "x_search", "arguments": {"query": "latest posts about xAI"}},
        },
    ]
    payload = "".join(json.dumps(message) + "\n" for message in messages)
    env = os.environ.copy()
    for name in ("XAI_OAUTH_BEARER_TOKEN", "XAI_BEARER_TOKEN", "XAI_API_KEY"):
        env.pop(name, None)
    with tempfile.TemporaryDirectory(prefix="x-search-codex-smoke-") as auth_home:
        env["X_SEARCH_CODEX_HOME"] = auth_home
        result = subprocess.run(
            [sys.executable, str(SERVER)],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
            cwd=ROOT,
            env=env,
            timeout=10,
        )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    ids = {response.get("id") for response in responses}
    if ids != {1, 2, 3, 4}:
        raise RuntimeError(f"unexpected response ids: {ids}")
    tools = responses[1]["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    expected = {"x_search_status", "x_search", "search_tweets", "fetch_tweet", "get_trends"}
    missing = expected - tool_names
    if missing:
        raise RuntimeError(f"missing tools: {sorted(missing)}")
    if responses[3]["result"]["isError"] is not True:
        raise RuntimeError("x_search should fail without credentials")
    error_text = responses[3]["result"]["content"][0]["text"]
    if "x_search_auth.py login" not in error_text:
        raise RuntimeError(f"unexpected missing-credential error: {error_text}")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
