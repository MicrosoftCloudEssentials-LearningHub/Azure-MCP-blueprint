# Manufacturing Monitor

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-05

----------
> Manufacturing-focused sample agent that calls MCP tools over HTTP.

<details>
<summary><strong>Table of contents</strong></summary>

- [Setup](#setup)
- [Run](#run)

</details>

It works best when Azure AI Search is enabled (uses `search_semantic` / `search_documents`). If Azure OpenAI is enabled on the MCP server, it will also use `openai_chat_completion` for routing/summaries.

## Setup

```bash
cd agent-samples/manufacturing-monitor
pip install -r requirements.txt
cp .env.example .env
```

Set `MCP_ENDPOINT` in `.env`.

## Run

```bash
python main.py --demo
```

Interactive:

```bash
python main.py --interactive
```

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
