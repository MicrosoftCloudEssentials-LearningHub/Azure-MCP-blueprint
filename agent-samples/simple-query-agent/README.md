# Simple Query Agent

Beginner-friendly sample that calls MCP tools over HTTP.

## Setup

```bash
cd agent-samples/simple-query-agent
pip install -r requirements.txt
cp .env.example .env
```

Set `MCP_ENDPOINT` in `.env`.

## Run

```bash
python main.py
```

Interactive mode:

```bash
python main.py --interactive
```
