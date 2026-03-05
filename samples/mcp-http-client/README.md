# MCP HTTP Client (Sample)

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-05

----------
> Minimal Python client for calling the MCP server endpoints exposed by this blueprint.

## Setup

```bash
cd samples/mcp-http-client
pip install -r requirements.txt
```

## Usage

```bash
python client.py --endpoint https://<YOUR_MCP_ENDPOINT>
python client.py --endpoint https://<YOUR_MCP_ENDPOINT> --list-tools
python client.py --endpoint https://<YOUR_MCP_ENDPOINT> --tool health_check
```

Tool call with arguments:

```bash
python client.py \
  --endpoint https://<YOUR_MCP_ENDPOINT> \
  --tool cosmos_query_items \
  --args '{"query":"SELECT * FROM c OFFSET 0 LIMIT 1"}'
```

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
