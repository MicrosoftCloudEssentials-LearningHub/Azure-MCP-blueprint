# Industry Templates (MCP Blueprint) - Overview 

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-08

----------

> Industry templates are **the contract** that keeps Terraform, sample data, and the MCP server aligned.

<details>
<summary><strong>Table of contents</strong></summary>

- [What’s in a template](#whats-in-a-template)
- [How templates are used](#how-templates-are-used)
- [Available templates](#available-templates)
- [Synthetic data and PII-like fields](#synthetic-data-and-pii-like-fields)

</details>

> Each folder under `industry-templates/<industry>/` defines:
> - **Cosmos DB** database/container names + partition key
> - **Azure AI Search** index name + fields
> - **Example queries** (tool + parameters)
> - **Default sample record count** (typically 100,000)


## What’s in a template

> Each industry folder contains exactly two files:

- `schema.json`
  - **Identity**: `industry`, `display_name`, `description`, optional `icon`
  - **Cosmos DB**: `cosmos_db.database`, `cosmos_db.container`, `cosmos_db.partition_key`, and a lightweight `cosmos_db.schema` shape
  - **Azure AI Search**: `search_index.name` and `search_index.fields` (some templates also include `semantic_config`)
  - **Suggested MCP tools**: `mcp_tools` (what the agent is expected to call in this scenario)
  - **Sample size**: either `sample_data_size` or `sample_data_config.record_count`

- `queries.json`
  - `example_queries[]` list where each entry includes:
    - `tool` (e.g., `cosmos_query_items`, `search_documents`, `search_semantic`, `openai_chat_completion`)
    - `parameters` (the exact JSON arguments to pass)
    - `expected_use_case` (why the query exists)

## How templates are used

> Templates are consumed in three main places:

1. **Terraform provisioning**
   - Terraform reads the selected industry from `selected_industry` in [terraform-infrastructure/terraform.tfvars](../terraform-infrastructure/terraform.tfvars).
   - It loads the matching template from `industry-templates/<industry>/schema.json` to keep names and schema consistent.

2. **The MCP server (runtime configuration)**
   - Deployments set `SELECTED_INDUSTRY`, and the app uses it to find the correct `schema.json` / `queries.json`.

3. **Sample data generation and upload scripts (optional)**
   - Generate local JSON: `python scripts/generate_sample_data.py --industry <industry> [--count N]`
     - Note: `healthcare`, `retail`, and `finance` use custom generators; other industries are generated from `cosmos_db.schema`.
   - Upload to Cosmos DB + Azure AI Search (key-based script):
     - Set `SELECTED_INDUSTRY` (optional), `COSMOS_ENDPOINT`, `COSMOS_KEY`, `SEARCH_ENDPOINT`, and optionally `SEARCH_KEY`.
     - Run: `python scripts/upload_sample_data.py`

## Available templates

> All templates in this repo default to **100,000 records**.

| Industry (folder) | Cosmos DB (database / container) | Partition key | Azure AI Search index | Default records |
|---|---|---|---|---:|
| Education (education) | `education-mcp` / `student-records` | `/studentId` | `education-index` | 100,000 |
| Energy (energy) | `energy-mcp` / `meter-readings` | `/meterId` | `energy-index` | 100,000 |
| Finance (finance) | `finance-mcp` / `transactions` | `/accountId` | `finance-index` | 100,000 |
| Healthcare (healthcare) | `healthcare-mcp` / `patient-records` | `/patientId` | `healthcare-index` | 100,000 |
| Hospitality (hospitality) | `hospitality-mcp` / `reservations` | `/reservationId` | `hospitality-index` | 100,000 |
| Insurance (insurance) | `insurance-mcp` / `claims-records` | `/claimId` | `insurance-index` | 100,000 |
| Logistics (logistics) | `logistics-mcp` / `shipment-tracking` | `/shipmentId` | `logistics-index` | 100,000 |
| Manufacturing (manufacturing) | `manufacturing-mcp` / `equipment-telemetry` | `/equipmentId` | `manufacturing-index` | 100,000 |
| Real Estate (realestate) | `realestate-mcp` / `property-listings` | `/propertyId` | `realestate-index` | 100,000 |
| Retail (retail) | `retail-mcp` / `transactions` | `/customerId` | `retail-index` | 100,000 |

## Synthetic data and PII-like fields

> The sample data generated for these templates is **synthetic** (not sourced from real people).

> [!IMPORTANT]
> Even though it is synthetic, it includes **PII-like fields** (names, emails, phone numbers, addresses; and DOB in some industries).
> Treat it as sensitive for logging, sharing, and security/compliance testing.

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
