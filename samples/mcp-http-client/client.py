#!/usr/bin/env python3
"""Minimal HTTP client for the MCP server in this repo.

Works against any hosting option (Container Apps / Functions / App Service) because
it only relies on the public HTTP endpoints exposed by the MCP server.

Examples:
  python client.py --endpoint https://<your-mcp>/
  python client.py --endpoint https://<your-mcp> --list-tools
  python client.py --endpoint https://<your-mcp> --tool health_check
  python client.py --endpoint https://<your-mcp> --tool cosmos_query_items --args '{"query":"SELECT * FROM c OFFSET 0 LIMIT 1"}'
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests


def _normalize_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if not endpoint:
        raise SystemExit("--endpoint is required")
    return endpoint.rstrip("/")


def _get(session: requests.Session, endpoint: str, path: str) -> requests.Response:
    return session.get(f"{endpoint}{path}")


def _post(session: requests.Session, endpoint: str, path: str, payload: dict[str, Any]) -> requests.Response:
    return session.post(f"{endpoint}{path}", json=payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP HTTP client")
    parser.add_argument("--endpoint", required=True, help="Base URL, e.g. https://xyz.azurecontainerapps.io")
    parser.add_argument("--list-tools", action="store_true", help="List available MCP tools")
    parser.add_argument("--tool", help="Tool name to execute")
    parser.add_argument("--args", default="{}", help="Tool arguments as JSON string")
    parser.add_argument("--timeout", type=int, default=30)

    args = parser.parse_args()

    endpoint = _normalize_endpoint(args.endpoint)

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    try:
        health = _get(session, endpoint, "/health")
        print(f"GET /health -> {health.status_code}")
        if health.ok:
            print(json.dumps(health.json(), indent=2))

        if args.list_tools:
            tools = _get(session, endpoint, "/mcp/tools")
            print(f"\nGET /mcp/tools -> {tools.status_code}")
            tools.raise_for_status()
            print(json.dumps(tools.json(), indent=2))

        if args.tool:
            try:
                tool_args = json.loads(args.args)
            except json.JSONDecodeError as e:
                raise SystemExit(f"--args must be valid JSON: {e}")

            payload: dict[str, Any] = {"name": args.tool, "arguments": tool_args}
            resp = _post(session, endpoint, "/mcp/execute", payload)
            print(f"\nPOST /mcp/execute -> {resp.status_code}")
            resp.raise_for_status()
            print(json.dumps(resp.json(), indent=2))

    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
