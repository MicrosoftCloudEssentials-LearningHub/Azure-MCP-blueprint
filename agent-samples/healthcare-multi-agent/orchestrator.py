"""Healthcare multi-agent orchestrator (lightweight, MCP-first).

This sample intentionally relies on the MCP server in this repo for:
- data access (Cosmos DB + AI Search)
- optional reasoning/summarization (OpenAI-compatible tool exposed by the MCP server)

It does NOT require the client to directly authenticate to Cosmos/Search/OpenAI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import httpx


def _normalize_endpoint(endpoint: Optional[str]) -> str:
    if not endpoint or not endpoint.strip():
        raise ValueError("MCP_ENDPOINT is required (e.g. https://<app>.azurecontainerapps.io or https://<func>.azurewebsites.net/api)")
    return endpoint.strip().rstrip("/")


@dataclass(frozen=True)
class ToolInfo:
    name: str
    description: str = ""


class HealthcareOrchestrator:
    def __init__(
        self,
        *,
        mcp_endpoint: Optional[str],
        azure_openai_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        gpt4o_deployment: str = "gpt-4o",
        gpt4o_mini_deployment: str = "gpt-4o-mini",
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = _normalize_endpoint(mcp_endpoint)
        self.gpt4o_deployment = gpt4o_deployment
        self.gpt4o_mini_deployment = gpt4o_mini_deployment
        self.timeout_seconds = timeout_seconds

        # These are accepted for compatibility with the README, but this orchestrator
        # uses the MCP server's OpenAI tool when available.
        self.azure_openai_endpoint = azure_openai_endpoint
        self.api_key = api_key

        self._tools_cache: Optional[dict[str, ToolInfo]] = None

    async def _get_tools(self, client: httpx.AsyncClient) -> dict[str, ToolInfo]:
        if self._tools_cache is not None:
            return self._tools_cache

        resp = await client.get(f"{self.base_url}/mcp/tools")
        resp.raise_for_status()
        payload = resp.json()
        tools: dict[str, ToolInfo] = {}
        for t in payload.get("tools", []):
            name = t.get("name")
            if name:
                tools[name] = ToolInfo(name=name, description=t.get("description", ""))

        self._tools_cache = tools
        return tools

    async def _execute_tool(self, client: httpx.AsyncClient, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = {"name": name, "arguments": arguments}
        resp = await client.post(f"{self.base_url}/mcp/execute", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def _triage_with_llm(self, client: httpx.AsyncClient, query: str) -> Optional[dict[str, Any]]:
        """Ask the MCP OpenAI tool to propose a retrieval plan.

        Returns a dict like:
          {"route": "cosmos"|"search", "cosmos_query": "...", "search_query": "..."}
        """

        system = (
            "You are a triage assistant for a healthcare data agent. "
            "Choose ONE route: 'cosmos' for structured SQL queries over patient records, "
            "or 'search' for text/semantic search. "
            "Return ONLY strict JSON with keys: route, cosmos_query, search_query.\n\n"
            "Cosmos patient record fields include: patientId, firstName, lastName, dateOfBirth, gender, bloodType, "
            "allergies (array), chronicConditions (array), medications (array), lastVisitDate, primaryPhysician, "
            "insuranceProvider, contactPhone, medicalHistory (string), labResults (array), vaccinations (array).\n\n"
            "Cosmos SQL guidance: use SELECT TOP N ... FROM c WHERE ...; use ARRAY_CONTAINS for arrays. "
            "If unsure, prefer route='search' and put the user query into search_query."
        )

        tool_resp = await self._execute_tool(
            client,
            "openai_chat_completion",
            {
                "model": self.gpt4o_mini_deployment,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": query},
                ],
                "temperature": 0.2,
                "max_tokens": 400,
            },
        )

        content = (((tool_resp or {}).get("content") or {}).get("response"))
        if not isinstance(content, str):
            return None

        try:
            plan = json.loads(content)
        except json.JSONDecodeError:
            return None

        if not isinstance(plan, dict):
            return None

        route = plan.get("route")
        if route not in ("cosmos", "search"):
            return None

        return plan

    async def process(self, query: str) -> str:
        query = (query or "").strip()
        if not query:
            return "Please provide a query."

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            tools = await self._get_tools(client)

            have_cosmos = "cosmos_query_items" in tools
            have_search_semantic = "search_semantic" in tools
            have_search = "search_documents" in tools or have_search_semantic
            have_openai = "openai_chat_completion" in tools

            plan: Optional[dict[str, Any]] = None
            if have_openai:
                plan = await self._triage_with_llm(client, query)

            route = (plan or {}).get("route")
            if route is None:
                # Heuristic fallback
                route = "cosmos" if have_cosmos and any(k in query.lower() for k in ["patient", "allerg", "medicat", "hba1c", "diabet"]) else "search"
                if route == "search" and not have_search and have_cosmos:
                    route = "cosmos"

            retrieval_notes: list[str] = []
            evidence: dict[str, Any] | None = None

            if route == "cosmos" and have_cosmos:
                cosmos_query = (plan or {}).get("cosmos_query")
                if not isinstance(cosmos_query, str) or not cosmos_query.strip():
                    # Safe, schema-compatible default query
                    cosmos_query = "SELECT TOP 5 c.patientId, c.firstName, c.lastName, c.chronicConditions, c.allergies, c.medications, c.primaryPhysician FROM c"

                retrieval_notes.append(f"Route: cosmos_query_items")
                retrieval_notes.append(f"Query: {cosmos_query}")

                evidence = await self._execute_tool(client, "cosmos_query_items", {"query": cosmos_query})

            elif have_search_semantic:
                search_query = (plan or {}).get("search_query")
                if not isinstance(search_query, str) or not search_query.strip():
                    search_query = query
                retrieval_notes.append("Route: search_semantic")
                retrieval_notes.append(f"Query: {search_query}")
                evidence = await self._execute_tool(client, "search_semantic", {"query": search_query, "top": 5})

            elif "search_documents" in tools:
                retrieval_notes.append("Route: search_documents")
                retrieval_notes.append(f"Query: {query}")
                evidence = await self._execute_tool(client, "search_documents", {"query": query, "top": 5})

            else:
                return "No retrieval tools are enabled on the MCP server (need at least cosmos or search)."

            # If the MCP server has OpenAI enabled, ask it to produce a human-readable summary.
            if have_openai and evidence is not None:
                summary_prompt = (
                    "Summarize the retrieved results for the user. "
                    "Be concise and avoid including any unnecessary sensitive details. "
                    "If the query is clinical, include a short disclaimer that this is not medical advice."
                )
                tool_resp = await self._execute_tool(
                    client,
                    "openai_chat_completion",
                    {
                        "model": self.gpt4o_deployment,
                        "messages": [
                            {"role": "system", "content": summary_prompt},
                            {"role": "user", "content": f"User query: {query}\n\nRetrieval notes:\n- " + "\n- ".join(retrieval_notes)},
                            {"role": "user", "content": "Retrieved JSON:\n" + json.dumps(evidence, indent=2)[:12000]},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 700,
                    },
                )
                content = (((tool_resp or {}).get("content") or {}).get("response"))
                if isinstance(content, str) and content.strip():
                    return content.strip()

            # Fallback: return raw JSON (trimmed)
            raw = json.dumps(evidence, indent=2)
            if len(raw) > 12000:
                raw = raw[:12000] + "\n... (truncated)"
            return "\n".join(retrieval_notes) + "\n\n" + raw
