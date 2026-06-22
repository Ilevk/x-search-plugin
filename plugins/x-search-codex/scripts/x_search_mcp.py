#!/usr/bin/env python3
"""Minimal stdio MCP server for xAI `x_search`.

The implementation intentionally has no third-party dependencies. It does not
install or import Hermes; it only preserves the xAI Responses API payload shape
used by Hermes' `x_search_tool`.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from typing import Any

import xai_oauth


DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4.20-reasoning"
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_RETRIES = 2
MAX_HANDLES = 10
SERVER_NAME = "x-search-codex"
SERVER_VERSION = "0.1.0"


class XSearchError(RuntimeError):
    """Raised when xAI `x_search` cannot complete."""


def _credential() -> tuple[str | None, str | None, str]:
    try:
        resolved = xai_oauth.resolve_credentials()
    except xai_oauth.XAIAuthError:
        return None, None, _base_url()
    return (
        str(resolved.get("bearer") or "").strip() or None,
        str(resolved.get("source") or "").strip() or None,
        str(resolved.get("base_url") or DEFAULT_BASE_URL).strip().rstrip("/"),
    )


def _base_url() -> str:
    return (os.environ.get("XAI_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")


def _model() -> str:
    return (os.environ.get("X_SEARCH_MODEL") or DEFAULT_MODEL).strip()


def _timeout_seconds() -> int:
    raw_value = os.environ.get("X_SEARCH_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return max(30, int(raw_value))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _retries() -> int:
    raw_value = os.environ.get("X_SEARCH_RETRIES", str(DEFAULT_RETRIES))
    try:
        return max(0, int(raw_value))
    except ValueError:
        return DEFAULT_RETRIES


def _normalize_handles(handles: list[str] | None, field_name: str) -> list[str]:
    normalized: list[str] = []
    for handle in handles or []:
        cleaned = str(handle or "").strip().lstrip("@")
        if cleaned:
            normalized.append(cleaned)
    if len(normalized) > MAX_HANDLES:
        raise ValueError(f"{field_name} supports at most {MAX_HANDLES} handles")
    return normalized


def _parse_iso_date(value: str, field_name: str) -> date:
    raw = value.strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} must be YYYY-MM-DD (got {raw!r})") from exc


def _validate_date_range(from_date: str, to_date: str) -> None:
    parsed_from = _parse_iso_date(from_date, "from_date") if from_date.strip() else None
    parsed_to = _parse_iso_date(to_date, "to_date") if to_date.strip() else None
    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise ValueError(
            f"from_date ({parsed_from.isoformat()}) must be on or before "
            f"to_date ({parsed_to.isoformat()})"
        )
    if parsed_from:
        today_utc = datetime.now(timezone.utc).date()
        if parsed_from > today_utc:
            raise ValueError(
                f"from_date ({parsed_from.isoformat()}) is in the future; "
                f"today UTC is {today_utc.isoformat()}"
            )


def _extract_response_text(payload: dict[str, Any]) -> str:
    output_text = str(payload.get("output_text") or "").strip()
    if output_text:
        return output_text

    parts: list[str] = []
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"}:
                text = str(content.get("text") or "").strip()
                if text:
                    parts.append(text)
    return "\n\n".join(parts).strip()


def _extract_inline_citations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            for annotation in content.get("annotations", []) or []:
                if not isinstance(annotation, dict):
                    continue
                if annotation.get("type") != "url_citation":
                    continue
                citations.append(
                    {
                        "url": annotation.get("url", ""),
                        "title": annotation.get("title", ""),
                        "start_index": annotation.get("start_index"),
                        "end_index": annotation.get("end_index"),
                    }
                )
    return citations


def _http_error_message(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(body)
    except Exception:
        payload = None
        body = ""

    if isinstance(payload, dict):
        code = str(payload.get("code") or "").strip()
        error = str(payload.get("error") or payload.get("message") or payload).strip()
        return f"{code}: {error}" if code and code not in error else error
    if body.strip():
        return body.strip()[:500]
    return str(exc)


def _post_json(url: str, bearer: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
            "User-Agent": f"x-search-codex/{SERVER_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=_timeout_seconds()) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise XSearchError(_http_error_message(exc)) from exc
    except urllib.error.URLError as exc:
        raise XSearchError(str(exc.reason)) from exc

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise XSearchError(f"xAI response was not valid JSON: {response_body[:500]!r}") from exc
    if not isinstance(parsed, dict):
        raise XSearchError("xAI response JSON was not an object")
    return parsed


def call_x_search(
    *,
    query: str,
    allowed_x_handles: list[str] | None = None,
    excluded_x_handles: list[str] | None = None,
    from_date: str = "",
    to_date: str = "",
    enable_image_understanding: bool = False,
    enable_video_understanding: bool = False,
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("query is required")

    bearer, credential_source, base_url = _credential()
    if not bearer:
        raise XSearchError(
            "No xAI credential found. Run `uv run --quiet --locked python scripts/x_search_auth.py login` "
            "for xAI OAuth, or set XAI_API_KEY."
        )

    allowed = _normalize_handles(allowed_x_handles, "allowed_x_handles")
    excluded = _normalize_handles(excluded_x_handles, "excluded_x_handles")
    if allowed and excluded:
        raise ValueError("allowed_x_handles and excluded_x_handles cannot be used together")
    _validate_date_range(from_date, to_date)

    tool_def: dict[str, Any] = {"type": "x_search"}
    if allowed:
        tool_def["allowed_x_handles"] = allowed
    if excluded:
        tool_def["excluded_x_handles"] = excluded
    if from_date.strip():
        tool_def["from_date"] = from_date.strip()
    if to_date.strip():
        tool_def["to_date"] = to_date.strip()
    if enable_image_understanding:
        tool_def["enable_image_understanding"] = True
    if enable_video_understanding:
        tool_def["enable_video_understanding"] = True

    payload = {
        "model": _model(),
        "input": [{"role": "user", "content": query}],
        "tools": [tool_def],
        "store": False,
    }

    endpoint = f"{base_url}/responses"
    last_error: Exception | None = None
    for attempt in range(_retries() + 1):
        try:
            data = _post_json(endpoint, bearer, payload)
            break
        except XSearchError as exc:
            last_error = exc
            if attempt >= _retries():
                raise
            time.sleep(min(5.0, 1.5 * (attempt + 1)))
    else:
        raise XSearchError(str(last_error) if last_error else "x_search request failed")

    answer = _extract_response_text(data)
    citations = list(data.get("citations") or [])
    inline_citations = _extract_inline_citations(data)

    active_filters: list[str] = []
    if allowed:
        active_filters.append("allowed_x_handles")
    if excluded:
        active_filters.append("excluded_x_handles")
    if from_date.strip():
        active_filters.append("from_date")
    if to_date.strip():
        active_filters.append("to_date")
    degraded = bool(active_filters) and not citations and not inline_citations
    degraded_reason = (
        f"no citations returned despite filters: {', '.join(active_filters)}"
        if degraded
        else None
    )

    return {
        "success": True,
        "provider": "xai",
        "credential_source": credential_source,
        "tool": "x_search",
        "model": payload["model"],
        "query": query,
        "answer": answer,
        "citations": citations,
        "inline_citations": inline_citations,
        "degraded": degraded,
        "degraded_reason": degraded_reason,
    }


def x_search_status() -> dict[str, Any]:
    auth_status = xai_oauth.status(refresh_if_expiring=False)
    return {
        "configured": bool(auth_status.get("configured")),
        "credential_source": auth_status.get("credential_source"),
        "auth": auth_status,
        "base_url": _base_url(),
        "model": _model(),
        "timeout_seconds": _timeout_seconds(),
        "retries": _retries(),
    }


def x_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return call_x_search(
        query=str(arguments.get("query") or ""),
        allowed_x_handles=arguments.get("allowed_x_handles"),
        excluded_x_handles=arguments.get("excluded_x_handles"),
        from_date=str(arguments.get("from_date") or ""),
        to_date=str(arguments.get("to_date") or ""),
        enable_image_understanding=bool(arguments.get("enable_image_understanding", False)),
        enable_video_understanding=bool(arguments.get("enable_video_understanding", False)),
    )


def search_tweets(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query") or "").strip()
    lang = str(arguments.get("lang") or "").strip()
    if lang:
        query = f"{query} lang:{lang}"
    structured_query = (
        "Use X search to find recent X posts matching this request. Return JSON with "
        "a `results` array of 5 to 10 items. Each item should include url, author_username, "
        "created_at when available, text, and engagement metrics when visible. "
        f"Request: {query}"
    )
    from_user = str(arguments.get("from_user") or "").strip().lstrip("@")
    return call_x_search(
        query=structured_query,
        allowed_x_handles=[from_user] if from_user else None,
        from_date=str(arguments.get("since") or ""),
        to_date=str(arguments.get("until") or ""),
    )


def fetch_tweet(arguments: dict[str, Any]) -> dict[str, Any]:
    url = str(arguments.get("url") or "").strip()
    if not url:
        raise ValueError("url is required")
    query = (
        "Use X search to inspect this exact X post URL. Return JSON with url, tweet_id, "
        "author username/display name, created_at, full text, media summary, referenced "
        f"posts, and visible metrics. URL: {url}"
    )
    return call_x_search(query=query, enable_image_understanding=True, enable_video_understanding=True)


def get_trends(arguments: dict[str, Any]) -> dict[str, Any]:
    region = str(arguments.get("region") or "Global").strip()
    limit = arguments.get("limit", 10)
    query = (
        f"Use X search to identify the current trending topics in {region}. Return JSON "
        f"with up to {limit} trends. Include rank, name, category, evidence_url, and a "
        "short reason for each trend. Do not invent evidence links."
    )
    return call_x_search(query=query)


TOOLS: dict[str, dict[str, Any]] = {
    "x_search_status": {
        "description": "Check x-search-codex configuration without making a network call.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": lambda _args: x_search_status(),
    },
    "x_search": {
        "description": "Free-form read-only X/Twitter research using xAI Responses API x_search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look up on X."},
                "allowed_x_handles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional X handles to include exclusively, max 10.",
                },
                "excluded_x_handles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional X handles to exclude, max 10.",
                },
                "from_date": {"type": "string", "description": "Optional YYYY-MM-DD start date."},
                "to_date": {"type": "string", "description": "Optional YYYY-MM-DD end date."},
                "enable_image_understanding": {"type": "boolean", "default": False},
                "enable_video_understanding": {"type": "boolean", "default": False},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "handler": x_search,
    },
    "search_tweets": {
        "description": "Search recent X posts by keyword with optional language, dates, and author filter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "lang": {"type": "string"},
                "since": {"type": "string", "description": "YYYY-MM-DD"},
                "until": {"type": "string", "description": "YYYY-MM-DD"},
                "from_user": {"type": "string", "description": "Optional author handle."},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "handler": search_tweets,
    },
    "fetch_tweet": {
        "description": "Fetch and summarize details for one X post URL.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
            "additionalProperties": False,
        },
        "handler": fetch_tweet,
    },
    "get_trends": {
        "description": "Get current X trends for a region using xAI x_search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "default": "Global"},
                "limit": {"type": "integer", "default": 10},
            },
            "additionalProperties": False,
        },
        "handler": get_trends,
    },
}


def _tool_descriptors() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": spec["description"],
            "inputSchema": spec["inputSchema"],
        }
        for name, spec in TOOLS.items()
    ]


def _text_content(payload: Any) -> list[dict[str, str]]:
    return [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]


def _success(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }
    if data is not None:
        payload["error"]["data"] = data
    return payload


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    message_id = request.get("id")

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _success(
            message_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
    if method == "ping":
        return _success(message_id, {})
    if method == "tools/list":
        return _success(message_id, {"tools": _tool_descriptors()})
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in TOOLS:
            return _error(message_id, -32602, f"unknown tool: {name}")
        try:
            result = TOOLS[name]["handler"](arguments)
            return _success(message_id, {"content": _text_content(result), "isError": False})
        except Exception as exc:
            data = {"error_type": type(exc).__name__}
            if os.environ.get("X_SEARCH_CODEX_DEBUG") == "1":
                data["traceback"] = traceback.format_exc()
            return _success(
                message_id,
                {"content": _text_content({"success": False, "error": str(exc), **data}), "isError": True},
            )
    if method in {"resources/list", "prompts/list"}:
        key = "resources" if method == "resources/list" else "prompts"
        return _success(message_id, {key: []})

    return _error(message_id, -32601, f"method not found: {method}")


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except json.JSONDecodeError as exc:
            response = _error(None, -32700, f"parse error: {exc}")
        except Exception as exc:
            response = _error(None, -32603, str(exc))
        if response is None:
            continue
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
