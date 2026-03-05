# MCP HTTP Client (Sample)

Minimal Python client for calling the MCP server endpoints exposed by this blueprint.

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
