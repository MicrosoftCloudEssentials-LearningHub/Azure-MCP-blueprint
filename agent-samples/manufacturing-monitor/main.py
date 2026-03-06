"""Manufacturing Monitor

Multi-role *sample* agent that calls MCP tools over HTTP.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import requests
from dotenv import load_dotenv


INDUSTRY_NAME = "Manufacturing"

AGENTS: dict[str, dict[str, Any]] = {
    "Operations Monitor": {
        "description": "Real-time status and alarms",
        "keywords": ["fault", "alert", "status", "downtime"],
    },
    "Maintenance Planner": {
        "description": "Predictive maintenance and schedules",
        "keywords": ["maintenance", "service", "mtbf", "failure"],
    },
    "Quality Analyst": {
        "description": "Efficiency and quality signals",
        "keywords": ["quality", "efficiency", "defect", "tolerance"],
    },
}

DEMO_QUERIES: list[str] = [
    "High-risk equipment requiring maintenance (failure score > 0.7)",
    "Semantic search for overheating alerts",
    "Low efficiency equipment with quality below 80%",
    "Equipment due for maintenance in the next 7 days",
    "High power consumption equipment above 500 kW",
]


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


def _tool_names(tools: list[dict[str, Any]]) -> set[str]:
    return {t.get("name", "") for t in tools if t.get("name")}


def _choose_model_for_task(query: str) -> str:
    q = query.lower()
    if len(q) > 120 or any(k in q for k in ["analyze", "diagnostics", "recommend"]):
        return "gpt-4o"
    return "gpt-4o-mini"


def _route_with_openai(
    session: requests.Session,
    endpoint: str,
    query: str,
    agent_names: list[str],
) -> str | None:
    system = (
        "You are an intent router for a Manufacturing monitor. "
        "Pick the single best specialist role from the provided list. "
        "Return JSON only: {\"agent\": \"<role>\"}."
    )
    user = f"Query: {query}\n\nRoles: {', '.join(agent_names)}"

    resp = _execute_tool(
        session,
        endpoint,
        "openai_chat_completion",
        {
            "model": _choose_model_for_task(query),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
            "max_tokens": 120,
        },
    )

    if resp.get("isError"):
        return None
    content = (resp.get("content") or {}).get("response")
    if not isinstance(content, str):
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    agent = parsed.get("agent")
    if agent in agent_names:
        return agent
    return None


def _route_with_keywords(query: str) -> str:
    q = query.lower()
    for name, meta in AGENTS.items():
        for kw in meta.get("keywords", []):
            if kw in q:
                return name
    return next(iter(AGENTS.keys()))


def _search(session: requests.Session, endpoint: str, tools: set[str], query: str) -> dict[str, Any] | None:
    if "search_semantic" in tools:
        return _execute_tool(session, endpoint, "search_semantic", {"query": query, "top": 5})
    if "search_documents" in tools:
        return _execute_tool(session, endpoint, "search_documents", {"query": query, "top": 10})
    return None


def _summarize_with_openai(
    session: requests.Session,
    endpoint: str,
    query: str,
    agent_name: str,
    raw_result: dict[str, Any],
) -> str | None:
    system = (
        "You are a manufacturing operations assistant. Summarize MCP search results concisely. "
        "Highlight equipment IDs, fault/alert themes, and suggested next queries."
    )
    user = json.dumps(
        {
            "industry": INDUSTRY_NAME,
            "agent": agent_name,
            "query": query,
            "result": raw_result.get("content"),
        },
        ensure_ascii=False,
    )
    resp = _execute_tool(
        session,
        endpoint,
        "openai_chat_completion",
        {
            "model": _choose_model_for_task(query),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 350,
        },
    )
    if resp.get("isError"):
        return None
    content = (resp.get("content") or {}).get("response")
    return content if isinstance(content, str) else None


def _print_tools(tools: list[dict[str, Any]]) -> None:
    print("\nAvailable tools:")
    for tool in tools:
        print(f"- {tool.get('name')}: {tool.get('description')}")


def _run_query(session: requests.Session, endpoint: str, tools: set[str], query: str, raw: bool) -> None:
    agent_names = list(AGENTS.keys())
    chosen = None
    if "openai_chat_completion" in tools:
        chosen = _route_with_openai(session, endpoint, query, agent_names)
    if not chosen:
        chosen = _route_with_keywords(query)

    print(f"\n[{INDUSTRY_NAME}] Routed to: {chosen}")

    result = _search(session, endpoint, tools, query)
    if result is None:
        print("No search tool available. Enable Azure AI Search to run this sample end-to-end.")
        return

    if raw:
        print(json.dumps(result, indent=2))
        return

    if "openai_chat_completion" in tools:
        summary = _summarize_with_openai(session, endpoint, query, chosen, result)
        if summary:
            print("\nSummary:")
            print(summary)
            return

    print("\nResult:")
    print(json.dumps(result, indent=2))


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description=f"{INDUSTRY_NAME} Monitor (MCP HTTP)")
    parser.add_argument("--endpoint", default=os.getenv("MCP_ENDPOINT", ""))
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)

    args = parser.parse_args()
    endpoint = _normalize_endpoint(args.endpoint)

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.request = lambda method, url, **kwargs: requests.Session.request(  # type: ignore[method-assign]
        session, method, url, timeout=args.timeout, **kwargs
    )

    health = session.get(f"{endpoint}/health")
    health.raise_for_status()
    print("/health:")
    print(json.dumps(health.json(), indent=2))

    tools_list = _list_tools(session, endpoint)
    tools = _tool_names(tools_list)
    _print_tools(tools_list)

    if args.demo:
        for q in DEMO_QUERIES:
            print("\n" + "=" * 80)
            print(f"Demo query: {q}")
            _run_query(session, endpoint, tools, q, raw=args.raw)
        return

    if args.interactive:
        print("\nInteractive mode. Type 'exit' to quit.")
        while True:
            q = input("Query: ").strip()
            if q.lower() in {"exit", "quit"}:
                break
            if not q:
                continue
            _run_query(session, endpoint, tools, q, raw=args.raw)
        return

    print("\nTip: run with --demo or --interactive")


if __name__ == "__main__":
    main()
