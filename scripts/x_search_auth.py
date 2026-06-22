#!/usr/bin/env python3
"""Manage x-search-codex xAI OAuth credentials."""

from __future__ import annotations

import argparse
import json
import sys

import xai_oauth


def _print_status(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage x-search-codex xAI OAuth credentials.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    login = subparsers.add_parser("login", help="Run browser OAuth login against accounts.x.ai.")
    login.add_argument("--no-browser", action="store_true", help="Print the authorization URL without opening a browser.")
    login.add_argument(
        "--manual-paste",
        action="store_true",
        help="Do not run a loopback callback server; paste the callback URL or code manually.",
    )
    login.add_argument("--timeout", type=float, default=180.0, help="Seconds to wait for OAuth callback.")

    subparsers.add_parser("status", help="Show credential status without printing secrets.")
    subparsers.add_parser("refresh", help="Force-refresh the stored OAuth access token.")
    subparsers.add_parser("logout", help="Remove stored xAI OAuth credentials.")

    args = parser.parse_args()
    try:
        if args.command == "login":
            result = xai_oauth.login(
                open_browser=not args.no_browser,
                manual_paste=args.manual_paste,
                timeout_seconds=args.timeout,
            )
            print("xAI OAuth login complete.")
            _print_status(result)
            return 0
        if args.command == "status":
            _print_status(xai_oauth.status(refresh_if_expiring=False))
            return 0
        if args.command == "refresh":
            _print_status(xai_oauth.refresh(force=True))
            return 0
        if args.command == "logout":
            xai_oauth.clear_oauth_state()
            print("xAI OAuth credentials removed.")
            return 0
    except xai_oauth.XAIAuthError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
