"""Simple Query Agent (Beginner)

A tiny CLI agent that calls MCP tools over HTTP.

This is intentionally minimal: it does not require Azure OpenAI.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import requests
from dotenv import load_dotenv


def _normalize_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if not endpoint:
        raise SystemExit("MCP endpoint is required (set MCP_ENDPOINT or use --endpoint)")
    return endpoint.rstrip("/")


def _list_tools(session: requests.Session, endpoint: str) -> list[dict[str, Any]]:
    resp = session.get(f"{endpoint}/mcp/tools")
    resp.raise_for_status()
    return resp.json().get("tools", [])


def _execute_tool(session: requests.Session, endpoint: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    payload = {"name": name, "arguments": arguments}
    resp = session.post(f"{endpoint}/mcp/execute", json=payload)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Simple MCP Query Agent")
    parser.add_argument("--endpoint", default=os.getenv("MCP_ENDPOINT", ""))
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--tool", default="health_check")
    parser.add_argument("--args", default="{}")

    args = parser.parse_args()

    endpoint = _normalize_endpoint(args.endpoint)

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    # Basic connectivity
    health = session.get(f"{endpoint}/health")
    health.raise_for_status()
    print("/health:")
    print(json.dumps(health.json(), indent=2))

    tools = _list_tools(session, endpoint)
    print("\nAvailable tools:")
    for tool in tools:
        print(f"- {tool.get('name')}: {tool.get('description')}")

    if not args.interactive:
        tool_args = json.loads(args.args)
        result = _execute_tool(session, endpoint, args.tool, tool_args)
        print("\nResult:")
        print(json.dumps(result, indent=2))
        return

    print("\nInteractive mode. Type 'exit' to quit.")
    while True:
        name = input("Tool name: ").strip()
        if name.lower() in {"exit", "quit"}:
            break
        raw_args = input("Args JSON (or blank for {}): ").strip() or "{}"
        try:
            tool_args = json.loads(raw_args)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            continue
        result = _execute_tool(session, endpoint, name, tool_args)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
