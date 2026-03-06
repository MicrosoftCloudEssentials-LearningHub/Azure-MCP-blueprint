#!/usr/bin/env python3
"""Deploy all industry template schemas into a single Azure AI Foundry project.

This is a practical "does Foundry work end-to-end" validation:
- Creates (or reuses) a single Vector Store in your Foundry project
- Uploads every `industry-templates/*/schema.json` and `queries.json`
- Creates an agent with the File Search tool pointing at that Vector Store
- Runs a short test prompt to confirm the agent can retrieve content

Prereqs (per Microsoft docs):
- `FOUNDRY_PROJECT_ENDPOINT` set (your project endpoint)
- `FOUNDRY_MODEL_DEPLOYMENT_NAME` set (model deployment name)
- Identity has permissions (Azure AI Owner on Foundry resource + Storage Blob Data Contributor on project storage)

Install deps:
  pip install --pre azure-ai-projects azure-identity

Run:
  python scripts/foundry_deploy_all_industry_schemas.py

Optional:
  python scripts/foundry_deploy_all_industry_schemas.py --vector-store-name MCPBlueprintIndustrySchemas --agent-name MCPBlueprintSchemaAgent
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def _iter_industry_files(root: Path) -> Iterable[Path]:
    templates_dir = root / "industry-templates"
    for industry_dir in sorted(p for p in templates_dir.iterdir() if p.is_dir()):
        for filename in ("schema.json", "queries.json"):
            path = industry_dir / filename
            if path.exists():
                yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload all industry schemas into one Foundry Vector Store")
    parser.add_argument("--vector-store-name", default="MCPBlueprintIndustrySchemas")
    parser.add_argument("--agent-name", default="MCPBlueprintSchemaAgent")
    parser.add_argument("--no-agent", action="store_true", help="Only upload files; do not create/test an agent")
    args = parser.parse_args()

    try:
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition
        from azure.identity import DefaultAzureCredential
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Missing dependencies. Install with: pip install --pre azure-ai-projects azure-identity\n"
            f"Import error: {exc}"
        )

    repo_root = Path(__file__).resolve().parents[1]

    project_endpoint = _require_env("FOUNDRY_PROJECT_ENDPOINT")
    model_deployment = _require_env("FOUNDRY_MODEL_DEPLOYMENT_NAME")

    files = list(_iter_industry_files(repo_root))
    if not files:
        raise SystemExit("No industry template files found under industry-templates/*/(schema.json,queries.json)")

    with (
        DefaultAzureCredential(exclude_interactive_browser_credential=False) as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        print(f"Foundry project endpoint: {project_endpoint}")
        print(f"Model deployment: {model_deployment}")

        # Create a new vector store every run (simple + reliable). If you want strict reuse,
        # you can delete/recreate by name in the portal, or enhance this script to search by name.
        print(f"\nCreating vector store: {args.vector_store_name}")
        vector_store = openai_client.vector_stores.create(name=args.vector_store_name)
        print(f"Vector store created: {vector_store.id}")

        print("\nUploading industry template files...")
        uploaded = 0
        for path in files:
            rel = path.relative_to(repo_root)
            print(f"- Uploading {rel} ...")
            with path.open("rb") as fh:
                openai_client.vector_stores.files.upload_and_poll(vector_store_id=vector_store.id, file=fh)
            uploaded += 1

        print(f"\nUploaded {uploaded} files into vector store {vector_store.id}")

        if args.no_agent:
            print("\nDone (skipped agent creation/test).")
            return 0

        print(f"\nCreating agent: {args.agent_name}")
        agent = project_client.agents.create_version(
            agent_name=args.agent_name,
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions=(
                    "You are a helpful assistant for the MCP Blueprint repository. "
                    "Use file search to answer questions about the industry templates, including schema.json and queries.json."
                ),
                tools=[FileSearchTool(vector_store_ids=[vector_store.id])],
            ),
            description="Agent grounded on MCP Blueprint industry template schemas (file search).",
        )
        print(f"Agent created: id={agent.id} name={agent.name} version={agent.version}")

        print("\nRunning a quick validation prompt...")
        conversation = openai_client.conversations.create()
        response = openai_client.responses.create(
            conversation=conversation.id,
            input=(
                "List the available industries in the uploaded templates, and for each one, "
                "summarize the Cosmos DB database/container and the AI Search index name."
            ),
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        )
        print("\nResponse:")
        print(response.output_text)

        print("\nSuccess. Vector store + agent are now deployed in this Foundry project.")
        print("Tip: You can delete the agent/vector store later from the Foundry portal.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
