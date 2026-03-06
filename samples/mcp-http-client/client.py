#!/usr/bin/env python3
"""Minimal HTTP client for the MCP server in this repo.

Uses the MCP Streamable HTTP transport (JSON-RPC over HTTP POST to `/mcp`).

Examples:
    python client.py --endpoint https://<your-mcp>
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


def _mcp_post(session: requests.Session, endpoint: str, payload: dict[str, Any]) -> requests.Response:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    return session.post(f"{endpoint}/mcp", json=payload, headers=headers)


def _mcp_initialize(session: requests.Session, endpoint: str) -> str:
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "mcp-http-client", "version": "1.0.0"},
        },
    }
    resp = _mcp_post(session, endpoint, init)
    resp.raise_for_status()
    payload = resp.json()
    if "error" in payload:
        raise SystemExit(f"MCP initialize failed: {payload['error']}")
    negotiated = payload.get("result", {}).get("protocolVersion", "2025-03-26")

    # Per spec, clients should send the negotiated protocol version on subsequent HTTP requests.
    session.headers.update({"MCP-Protocol-Version": negotiated})

    initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    _mcp_post(session, endpoint, initialized)
    return negotiated


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

        if args.list_tools or args.tool:
            negotiated = _mcp_initialize(session, endpoint)
            print(f"\nMCP initialized (protocol={negotiated})")

        if args.list_tools:
            req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            tools = _mcp_post(session, endpoint, req)
            print(f"\nPOST /mcp (tools/list) -> {tools.status_code}")
            tools.raise_for_status()
            print(json.dumps(tools.json(), indent=2))

        if args.tool:
            try:
                tool_args = json.loads(args.args)
            except json.JSONDecodeError as e:
                raise SystemExit(f"--args must be valid JSON: {e}")

            payload: dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": args.tool, "arguments": tool_args},
            }
            resp = _mcp_post(session, endpoint, payload)
            print(f"\nPOST /mcp (tools/call) -> {resp.status_code}")
            resp.raise_for_status()
            print(json.dumps(resp.json(), indent=2))

    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
