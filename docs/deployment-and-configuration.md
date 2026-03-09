# MCP Blueprint (Azure) <br/> Deployment & Configuration Best Practices - Overview

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-06

----------
> This blueprint supports running the MCP server in multiple ways.

<details>
<summary><strong>Table of contents</strong></summary>

- [What this repo deploys](#what-this-repo-deploys)
- [Standard configuration contract (env vars)](#standard-configuration-contract-env-vars)
- [Secrets best practices](#secrets-best-practices)
- [Observability best practices](#observability-best-practices)
- [Deployment options](#deployment-options)
- [Data modeling & Cosmos DB best practices (when using Cosmos)](#data-modeling--cosmos-db-best-practices-when-using-cosmos)
- [Validation](#validation)
- [Common pitfalls (and how this blueprint avoids them)](#common-pitfalls-and-how-this-blueprint-avoids-them)

</details>

## What this repo deploys

- **MCP Server**: [src/mcp-server/main.py](../src/mcp-server/main.py) (FastAPI + HTTP transport)
- **Industry templates**: [industry-templates/](../industry-templates/) (Cosmos DB + Search index names/schemas)
- **Provisioning (recommended)**: [terraform-infrastructure/](../terraform-infrastructure/) (Azure resources + Key Vault + optional “zero-touch” Container Apps deploy)
- **Optional scripts**: [scripts/](../scripts/) (deploy/validate/sample data)

## Standard configuration contract (env vars)

<details>
<summary><strong>Required (any deployment)</strong></summary>

- `PORT`
  - Container Apps / App Service: typically `8000`
  - Functions: typically `80` (fronted by Functions runtime)

</details>

<details>
<summary><strong>Data + Search (when enabled)</strong></summary>

- `COSMOS_ENDPOINT`
- `COSMOS_KEY` *(optional)*
  - If set, the server uses **key-based** auth.
  - If not set, the server uses **Managed Identity / DefaultAzureCredential**.
- `COSMOS_DATABASE`
- `COSMOS_CONTAINER`

- `SEARCH_ENDPOINT`
- `SEARCH_ADMIN_KEY` *(optional)*
  - If set, the server uses **admin key** via `AzureKeyCredential`.
  - If not set, the server uses **Managed Identity / DefaultAzureCredential**.
- `SEARCH_INDEX_NAME`

</details>

<details>
<summary><strong>Microsoft Foundry (Azure AI Foundry) (when enabled)</strong></summary>

> This repo treats **Foundry** (Azure AI Foundry) as the **model endpoint**.
> The runtime uses an **OpenAI-compatible API surface**, so configuration uses `OPENAI_*` env vars, with `FOUNDRY_*` supported as aliases.
> Learn more: https://learn.microsoft.com/azure/foundry/what-is-foundry

- `OPENAI_ENDPOINT` *(preferred)* or `FOUNDRY_ENDPOINT` *(alias)*
- `OPENAI_API_KEY` *(optional)* or `FOUNDRY_API_KEY` *(alias)*
  - If set and not equal to `managed_identity`, the server uses **key-based** auth.
  - Otherwise, the server uses **Managed Identity / DefaultAzureCredential** (AAD token provider).

</details>

<details>
<summary><strong>Common</strong></summary>

- `AZURE_KEY_VAULT_URI` (recommended in Azure)
- `APPLICATIONINSIGHTS_CONNECTION_STRING` (recommended)
- `SELECTED_INDUSTRY` (used to keep infra + data consistent)

- `MCP_API_KEY` *(optional)*
  - If set, requests to `POST /mcp` must include this value in the header specified by `MCP_API_KEY_HEADER`.
- `MCP_API_KEY_HEADER` *(optional, default: `x-api-key`)*
- `MCP_ALLOWED_ORIGINS` *(optional)*
  - Comma-separated allowlist for the `Origin` header (DNS rebinding protection). If unset and an `Origin` header is present, the request is rejected.

</details>

## Secrets best practices

- Use **Azure Key Vault** for secrets (`COSMOS_KEY`, `SEARCH_ADMIN_KEY`, `OPENAI_API_KEY`).
- Prefer **Managed Identity** to access Key Vault (no secrets in repo).
- Keep “non-secret config” (e.g., `COSMOS_DATABASE`, `SEARCH_INDEX_NAME`) as plain app settings.

## Observability best practices

- Emit structured logs and avoid logging request bodies that may contain PII.
- In production, enable:
  - Application Insights (`APPLICATIONINSIGHTS_CONNECTION_STRING`)
  - Log Analytics (Container Apps environment)

## Deployment options

<details>
<summary><strong>Option A (recommended): Terraform + Azure Container Apps (zero-touch)</strong></summary>

> This is the only path in this repo that is currently **end-to-end automated** via Terraform.

1. Configure [terraform-infrastructure/terraform.tfvars](../terraform-infrastructure/terraform.tfvars)
   - `selected_industry`
   - `mcp_deployment_type = "container-app"`
2. Deploy:
   - `az login`
   - `cd terraform-infrastructure`
   - `terraform init`
   - `terraform apply -auto-approve`

>[!NOTE]
> - The container image is built in Azure using **ACR Tasks** (`az acr build`).
> - The Container App is configured with Key Vault-backed secrets.

</details>

<details>
<summary><strong>Option B: Terraform provisions infra, then deploy code separately (Functions)</strong></summary>

> Terraform can provision the Function App + Key Vault + dependent services, but code deployment is best done via CI/CD (or your preferred release process).

- Set `mcp_deployment_type = "function"` in `terraform.tfvars`.
- Deploy code using one of:
  - GitHub Actions / Azure DevOps (recommended)
  - Manual publish (requires Azure Functions Core Tools): `func azure functionapp publish <name> --python`

</details>

<details>
<summary><strong>Option C: Terraform provisions infra, then deploy code separately (App Service)</strong></summary>

- Set `mcp_deployment_type = "app-service"` in `terraform.tfvars`.
- Deploy code using CI/CD or your chosen packaging method.

</details>

## Data modeling & Cosmos DB best practices (when using Cosmos)

- Choose partition keys that match your access patterns (high-cardinality; avoid hotspots).
- Model to minimize cross-partition queries.
- Keep items under the 2 MB item limit.
- Capture Cosmos SDK diagnostics for latency spikes and unexpected status codes.
- Handle `429` with backoff/retry.

## Validation

- Health endpoint: `GET /health`
- MCP Streamable (recommended for Copilot Studio):
  - `POST /mcp` (JSON-RPC: `initialize`, `tools/list`, `tools/call`, ...)
- Legacy HTTP endpoints (kept for backward compatibility):
  - `GET /mcp/tools`
  - `GET /mcp/resources`
  - `GET /mcp/prompts`
  - `POST /mcp/execute`

> [!TIP]
> You can also run the built-in validator: [scripts/validate-mcp.py](../scripts/validate-mcp.py)

## Common pitfalls (and how this blueprint avoids them)

- **Hard-coded Cosmos/Search names** → Terraform + server now read these from the selected industry template and env vars.
- **Key vs Managed Identity mismatch** → server supports both, based on presence of key env vars.
- **"Supports Functions/App Service" but breaks at apply time** → Terraform automation is scoped to Container Apps; other options are provision-only unless you add a deployment pipeline.

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
