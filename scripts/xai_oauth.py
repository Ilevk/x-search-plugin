#!/usr/bin/env python3
"""xAI OAuth helpers for x-search-codex.

This module implements the same credential shape used by Hermes' xAI OAuth
provider: browser OAuth with PKCE against accounts.x.ai/auth.x.ai, persisted
locally, refreshed before expiry, then used as a bearer for api.x.ai.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.x.ai/v1"
OAUTH_ISSUER = "https://auth.x.ai"
OAUTH_DISCOVERY_URL = f"{OAUTH_ISSUER}/.well-known/openid-configuration"
OAUTH_CLIENT_ID = os.environ.get(
    "X_SEARCH_XAI_OAUTH_CLIENT_ID",
    "b1a00492-073a-47ea-816f-4c329264a828",
)
OAUTH_SCOPE = os.environ.get(
    "X_SEARCH_XAI_OAUTH_SCOPE",
    "openid profile email offline_access grok-cli:access api:access",
)
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 56121
REDIRECT_PATH = "/callback"
REFRESH_SKEW_SECONDS = 3600


class XAIAuthError(RuntimeError):
    """Raised when xAI OAuth credentials cannot be resolved."""


def auth_home() -> Path:
    """Return the local credential directory.

    `X_SEARCH_CODEX_HOME` exists so tests and power users can isolate auth
    state. The default intentionally does not reuse `~/.hermes/auth.json`.
    """
    configured = os.environ.get("X_SEARCH_CODEX_HOME", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".x-search-codex"


def auth_path() -> Path:
    return auth_home() / "auth.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise XAIAuthError(f"OAuth store is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise XAIAuthError(f"OAuth store must contain a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".auth.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


def _load_store() -> dict[str, Any]:
    return _read_json(auth_path())


def _save_store(store: dict[str, Any]) -> None:
    _write_json(auth_path(), store)


def _load_state() -> dict[str, Any]:
    store = _load_store()
    providers = store.get("providers")
    if not isinstance(providers, dict):
        return {}
    state = providers.get("xai-oauth")
    return state if isinstance(state, dict) else {}


def _save_state(state: dict[str, Any]) -> None:
    store = _load_store()
    providers = store.get("providers")
    if not isinstance(providers, dict):
        providers = {}
    providers["xai-oauth"] = state
    store["providers"] = providers
    _save_store(store)


def clear_oauth_state() -> None:
    store = _load_store()
    providers = store.get("providers")
    if isinstance(providers, dict):
        providers.pop("xai-oauth", None)
    store["providers"] = providers if isinstance(providers, dict) else {}
    _save_store(store)


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _pkce_verifier() -> str:
    return _base64url(secrets.token_bytes(64))


def _pkce_challenge(verifier: str) -> str:
    return _base64url(hashlib.sha256(verifier.encode("ascii")).digest())


def _json_request(
    url: str,
    *,
    method: str = "GET",
    data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    encoded: bytes | None = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if data is not None:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=encoded, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        message = f"xAI OAuth HTTP {exc.code}"
        if detail:
            message = f"{message}: {detail[:500]}"
        raise XAIAuthError(message) from exc
    except urllib.error.URLError as exc:
        raise XAIAuthError(f"xAI OAuth request failed: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise XAIAuthError(f"xAI OAuth response was not JSON: {raw[:200]!r}") from exc
    if not isinstance(payload, dict):
        raise XAIAuthError("xAI OAuth response JSON was not an object")
    return payload


def _validate_xai_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise XAIAuthError(f"Refusing non-HTTPS xAI OAuth endpoint: {url}")
    host = parsed.hostname or ""
    if host != "x.ai" and not host.endswith(".x.ai"):
        raise XAIAuthError(f"Refusing non-x.ai OAuth endpoint: {url}")


def discover(timeout: float = 20.0) -> dict[str, str]:
    payload = _json_request(OAUTH_DISCOVERY_URL, timeout=timeout)
    authorization_endpoint = str(payload.get("authorization_endpoint") or "").strip()
    token_endpoint = str(payload.get("token_endpoint") or "").strip()
    if not authorization_endpoint or not token_endpoint:
        raise XAIAuthError("xAI OIDC discovery response is missing required endpoints")
    _validate_xai_url(authorization_endpoint)
    _validate_xai_url(token_endpoint)
    return {
        "authorization_endpoint": authorization_endpoint,
        "token_endpoint": token_endpoint,
    }


def _authorization_url(
    *,
    authorization_endpoint: str,
    redirect_uri: str,
    code_challenge: str,
    state: str,
    nonce: str,
) -> str:
    params = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": OAUTH_SCOPE,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "nonce": nonce,
        "plan": "generic",
        "referrer": "x-search-codex",
    }
    return f"{authorization_endpoint}?{urllib.parse.urlencode(params)}"


def _make_callback_handler(expected_path: str) -> tuple[type[BaseHTTPRequestHandler], dict[str, Any]]:
    result: dict[str, Any] = {"code": None, "state": None, "error": None, "error_description": None}
    lock = threading.Lock()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != expected_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found.")
                return

            params = urllib.parse.parse_qs(parsed.query)
            incoming = {
                "code": params.get("code", [None])[0],
                "state": params.get("state", [None])[0],
                "error": params.get("error", [None])[0],
                "error_description": params.get("error_description", [None])[0],
            }
            with lock:
                if not (result["code"] or result["error"]):
                    result.update(incoming)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if incoming["error"]:
                body = "<html><body><h1>xAI authorization failed.</h1>You can close this tab.</body></html>"
            else:
                body = "<html><body><h1>xAI authorization received.</h1>You can close this tab.</body></html>"
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, _format: str, *args: Any) -> None:
            return

    return CallbackHandler, result


def _start_callback_server() -> tuple[ThreadingHTTPServer, threading.Thread, dict[str, Any], str]:
    handler, result = _make_callback_handler(REDIRECT_PATH)

    class ReuseServer(ThreadingHTTPServer):
        allow_reuse_address = True
        daemon_threads = True

    server: ThreadingHTTPServer | None = None
    last_error: OSError | None = None
    for port in (REDIRECT_PORT, 0):
        try:
            server = ReuseServer((REDIRECT_HOST, port), handler)
            break
        except OSError as exc:
            last_error = exc
    if server is None:
        raise XAIAuthError(f"Could not bind callback server: {last_error}")

    actual_port = int(server.server_address[1])
    redirect_uri = f"http://{REDIRECT_HOST}:{actual_port}{REDIRECT_PATH}"
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    return server, thread, result, redirect_uri


def _wait_for_callback(
    server: ThreadingHTTPServer,
    thread: threading.Thread,
    result: dict[str, Any],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(30.0, timeout_seconds)
    try:
        while time.monotonic() < deadline:
            if result["code"] or result["error"]:
                return result
            time.sleep(0.1)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)
    raise XAIAuthError("xAI authorization timed out waiting for the local callback")


def parse_callback_text(value: str) -> dict[str, Any]:
    """Parse a full callback URL, query fragment, or bare authorization code."""
    raw = value.strip()
    if not raw:
        raise XAIAuthError("callback value is empty")
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urllib.parse.urlparse(raw)
        params = urllib.parse.parse_qs(parsed.query)
        return {
            "code": params.get("code", [None])[0],
            "state": params.get("state", [None])[0],
            "error": params.get("error", [None])[0],
            "error_description": params.get("error_description", [None])[0],
        }
    if raw.startswith("?"):
        params = urllib.parse.parse_qs(raw[1:])
        return {
            "code": params.get("code", [None])[0],
            "state": params.get("state", [None])[0],
            "error": params.get("error", [None])[0],
            "error_description": params.get("error_description", [None])[0],
        }
    return {"code": raw, "state": None, "error": None, "error_description": None}


def _exchange_code(
    *,
    token_endpoint: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    code_challenge: str,
    timeout: float,
) -> dict[str, Any]:
    return _json_request(
        token_endpoint,
        method="POST",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": OAUTH_CLIENT_ID,
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        },
        timeout=timeout,
    )


def login(
    *,
    open_browser: bool = True,
    manual_paste: bool = False,
    timeout_seconds: float = 180.0,
) -> dict[str, Any]:
    """Run the xAI OAuth login flow and persist tokens."""
    discovery = discover()
    code_verifier = _pkce_verifier()
    code_challenge = _pkce_challenge(code_verifier)
    state = uuid.uuid4().hex
    nonce = uuid.uuid4().hex

    if manual_paste:
        redirect_uri = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}{REDIRECT_PATH}"
        callback_source = "manual-paste"
    else:
        server, thread, callback_result, redirect_uri = _start_callback_server()
        callback_source = "loopback"

    authorization_url = _authorization_url(
        authorization_endpoint=discovery["authorization_endpoint"],
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        state=state,
        nonce=nonce,
    )
    print("Open this URL to authorize x-search-codex with xAI:")
    print(authorization_url)
    print()
    if manual_paste:
        print("Paste the full callback URL, ?code=... fragment, or bare code after approving:")
        callback = parse_callback_text(sys.stdin.readline())
    else:
        print(f"Waiting for callback on {redirect_uri}")
        if open_browser:
            try:
                if webbrowser.open(authorization_url):
                    print("Browser opened for xAI authorization.")
            except Exception:
                pass
        callback = _wait_for_callback(
            server,
            thread,
            callback_result,
            timeout_seconds=timeout_seconds,
        )

    if callback.get("error"):
        detail = callback.get("error_description") or callback["error"]
        raise XAIAuthError(f"xAI authorization failed: {detail}")
    callback_state = callback.get("state")
    if callback_state is None and manual_paste:
        callback_state = state
    if callback_state != state:
        raise XAIAuthError("xAI authorization failed: state mismatch")
    code = str(callback.get("code") or "").strip()
    if not code:
        raise XAIAuthError("xAI authorization failed: missing authorization code")

    payload = _exchange_code(
        token_endpoint=discovery["token_endpoint"],
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
        code_challenge=code_challenge,
        timeout=20.0,
    )
    access_token = str(payload.get("access_token") or "").strip()
    refresh_token = str(payload.get("refresh_token") or "").strip()
    if not access_token:
        raise XAIAuthError("xAI token exchange did not return an access_token")
    if not refresh_token:
        raise XAIAuthError("xAI token exchange did not return a refresh_token")

    state_payload = {
        "tokens": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "id_token": str(payload.get("id_token") or "").strip(),
            "expires_in": payload.get("expires_in"),
            "token_type": str(payload.get("token_type") or "Bearer").strip() or "Bearer",
        },
        "discovery": discovery,
        "redirect_uri": redirect_uri,
        "base_url": _base_url_override(),
        "last_refresh": _now_iso(),
        "source": callback_source,
    }
    _save_state(state_payload)
    return status(refresh_if_expiring=False)


def _base_url_override() -> str:
    raw = (os.environ.get("XAI_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme != "https":
        raise XAIAuthError(f"Refusing non-HTTPS xAI base URL: {raw}")
    host = parsed.hostname or ""
    if host != "x.ai" and not host.endswith(".x.ai"):
        raise XAIAuthError(f"Refusing non-x.ai base URL for OAuth bearer: {raw}")
    return raw


def _env_base_url() -> str:
    return (os.environ.get("XAI_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")


def _jwt_expiry_epoch(token: str) -> int | None:
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        data = json.loads(decoded)
    except Exception:
        return None
    exp = data.get("exp") if isinstance(data, dict) else None
    return int(exp) if isinstance(exp, int) else None


def access_token_is_expiring(token: str, skew_seconds: int = REFRESH_SKEW_SECONDS) -> bool:
    exp = _jwt_expiry_epoch(token)
    if exp is None:
        return False
    return exp <= int(time.time()) + max(0, skew_seconds)


def refresh(*, force: bool = False) -> dict[str, Any]:
    state = _load_state()
    tokens = state.get("tokens") if isinstance(state, dict) else None
    if not isinstance(tokens, dict):
        raise XAIAuthError("No xAI OAuth credentials stored. Run `python3 scripts/x_search_auth.py login`.")
    access_token = str(tokens.get("access_token") or "").strip()
    refresh_token = str(tokens.get("refresh_token") or "").strip()
    if not refresh_token:
        raise XAIAuthError("Stored xAI OAuth credentials are missing refresh_token. Re-run login.")
    if access_token and not force and not access_token_is_expiring(access_token):
        return status(refresh_if_expiring=False)

    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    token_endpoint = str(discovery.get("token_endpoint") or "").strip()
    if not token_endpoint:
        token_endpoint = discover()["token_endpoint"]
    _validate_xai_url(token_endpoint)

    payload = _json_request(
        token_endpoint,
        method="POST",
        data={
            "grant_type": "refresh_token",
            "client_id": OAUTH_CLIENT_ID,
            "refresh_token": refresh_token,
        },
        timeout=20.0,
    )
    refreshed_access = str(payload.get("access_token") or "").strip()
    if not refreshed_access:
        raise XAIAuthError("xAI token refresh did not return an access_token")
    tokens["access_token"] = refreshed_access
    tokens["refresh_token"] = str(payload.get("refresh_token") or refresh_token).strip()
    if payload.get("id_token"):
        tokens["id_token"] = str(payload.get("id_token") or "").strip()
    if payload.get("expires_in") is not None:
        tokens["expires_in"] = payload.get("expires_in")
    tokens["token_type"] = str(payload.get("token_type") or tokens.get("token_type") or "Bearer").strip()
    state["tokens"] = tokens
    state["last_refresh"] = _now_iso()
    state["base_url"] = _base_url_override()
    _save_state(state)
    return status(refresh_if_expiring=False)


def resolve_oauth_credentials(*, refresh_if_expiring: bool = True) -> dict[str, str]:
    state = _load_state()
    tokens = state.get("tokens") if isinstance(state, dict) else None
    if not isinstance(tokens, dict):
        raise XAIAuthError("No xAI OAuth credentials stored")
    access_token = str(tokens.get("access_token") or "").strip()
    if not access_token:
        raise XAIAuthError("Stored xAI OAuth credentials are missing access_token")
    if refresh_if_expiring and access_token_is_expiring(access_token):
        refresh(force=True)
        state = _load_state()
        tokens = state.get("tokens") if isinstance(state, dict) else None
        access_token = str((tokens or {}).get("access_token") or "").strip()
    if not access_token:
        raise XAIAuthError("xAI OAuth refresh did not produce an access_token")
    base_url = str(state.get("base_url") or _base_url_override()).strip().rstrip("/")
    return {"bearer": access_token, "base_url": base_url, "source": "xai-oauth"}


def env_credentials() -> dict[str, str] | None:
    for name in ("XAI_OAUTH_BEARER_TOKEN", "XAI_BEARER_TOKEN", "XAI_API_KEY"):
        value = (os.environ.get(name) or "").strip()
        if value:
            return {"bearer": value, "base_url": _env_base_url(), "source": name}
    return None


def resolve_credentials() -> dict[str, str]:
    try:
        return resolve_oauth_credentials()
    except Exception:
        env = env_credentials()
        if env:
            return env
        raise XAIAuthError(
            "No xAI credential found. Run `python3 scripts/x_search_auth.py login` "
            "for xAI OAuth, or set XAI_API_KEY."
        )


def status(*, refresh_if_expiring: bool = False) -> dict[str, Any]:
    state = _load_state()
    tokens = state.get("tokens") if isinstance(state, dict) else None
    access_token = str((tokens or {}).get("access_token") or "").strip()
    refresh_token = str((tokens or {}).get("refresh_token") or "").strip()
    exp_epoch = _jwt_expiry_epoch(access_token) if access_token else None
    exp_iso = (
        datetime.fromtimestamp(exp_epoch, timezone.utc).isoformat().replace("+00:00", "Z")
        if exp_epoch
        else None
    )
    if refresh_if_expiring and access_token and refresh_token and access_token_is_expiring(access_token):
        return refresh(force=True)

    env = env_credentials()
    configured = bool(access_token and refresh_token) or bool(env)
    credential_source = "xai-oauth" if access_token and refresh_token else (env or {}).get("source")
    return {
        "configured": configured,
        "credential_source": credential_source,
        "oauth": {
            "configured": bool(access_token and refresh_token),
            "store_path": str(auth_path()),
            "expires_at": exp_iso,
            "refresh_token_present": bool(refresh_token),
            "last_refresh": state.get("last_refresh") if isinstance(state, dict) else None,
        },
        "env_fallback_configured": bool(env),
        "base_url": str(state.get("base_url") or _env_base_url()).rstrip("/"),
    }
