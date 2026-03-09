# Pre-Built AI Agent Samples

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-06

----------
> Reference AI agent samples that use this repo's MCP Server over HTTP.

<details>
<summary><strong>List of References</strong></summary>

- [Blueprint Overview](../README.md)
- [Deployment & Configuration](../docs/deployment-and-configuration.md)
- Integration guides:
  - [Azure AI Foundry](../docs/integration-guides/azure-ai-foundry-integration.md)
  - [Microsoft Copilot Studio](../docs/integration-guides/copilot-studio-integration.md)
  - [Custom App](../docs/integration-guides/custom-app-integration.md)
- [MCP HTTP Client (Sample)](../samples/mcp-http-client/)

</details>

<details>
<summary><strong>Table of Content</strong></summary>

| Sample | Industry | Agents | Complexity |
|--------|----------|---------|------------|
| [Healthcare Multi-Agent](./healthcare-multi-agent/) | Healthcare | 5 | Advanced |
| [Simple Query Agent](./simple-query-agent/) | Any | 1 | Beginner |
| [Retail Shopping Assistant](./retail-shopping-assistant/) | Retail | 6 | Intermediate |
| [Financial Advisor](./financial-advisor/) | Finance | 4 | Intermediate |
| [Manufacturing Monitor](./manufacturing-monitor/) | Manufacturing | 3 | Intermediate |
| [Education Student Assistant](./education-student-assistant/) | Education | 3 | Intermediate |
| [Logistics Tracker](./logistics-tracker/) | Logistics | 3 | Intermediate |
| [Insurance Claims Agent](./insurance-claims-agent/) | Insurance | 4 | Intermediate |
| [Hospitality Concierge](./hospitality-concierge/) | Hospitality | 3 | Intermediate |
| [Energy Usage Advisor](./energy-usage-advisor/) | Energy | 3 | Intermediate |
| [Real Estate Portfolio Manager](./realestate-portfolio-manager/) | Real Estate | 3 | Intermediate |

- `healthcare-multi-agent`: an advanced orchestrated multi-agent sample.
- The other industry samples: lightweight CLIs that (a) route to a role and (b) run a search tool via MCP, optionally using `openai_chat_completion` for routing and summaries when available.

</details>

## Key Features

- **MCP HTTP integration**: Calls `/health`, `/mcp/tools`, and `/mcp/execute`
- **Optional LLM routing**: Uses `openai_chat_completion` when the server exposes it
- **Search-first flow**: Uses `search_semantic` (preferred) or `search_documents`
- **Minimal dependencies**: `requests` + `python-dotenv`

> Patterns: <br/>
>
> - Lightweight HTTP samples (most folders): 
>
  ```
  User
      ↓
  (optional) openai_chat_completion  → role routing
      ↓
  search_semantic / search_documents → retrieve relevant items
      ↓
  (optional) openai_chat_completion  → concise summary
  ```

> - Advanced orchestration (healthcare-multi-agent): For example, the healthcare sample demonstrates a richer orchestrator and multi-agent handoffs.

</details>

## Customization Guide

1. **Add New Industry**: Copy sample, modify agent definitions
2. **Adjust Model Routing**: Edit `model_router.py` complexity rules
3. **Add Agents**: Extend agent registry with new specialists
4. **Change MCP Tools**: Update agent tool permissions

## Next Steps

- Explore individual sample READMEs
- [Custom App Integration](../docs/integration-guides/custom-app-integration.md)
- [Azure AI Foundry Integration](../docs/integration-guides/azure-ai-foundry-integration.md)
- [Copilot Studio Integration](../docs/integration-guides/copilot-studio-integration.md)

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
