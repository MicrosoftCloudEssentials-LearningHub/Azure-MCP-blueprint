# Custom Application Integration with MCP Server

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-06

----------
> This guide shows developers how to integrate the Azure MCP Server into custom applications using the MCP SDK.

<details>
<summary><strong>Table of contents</strong></summary>

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start (Python)](#quick-start-python)
- [Advanced Integration Examples](#advanced-integration-examples)
- [Node.js/TypeScript Integration](#nodejstypescript-integration)
- [Authentication Options](#authentication-options)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Sample Applications](#sample-applications)
- [Next Steps](#next-steps)

</details>

## Overview

Perfect for building AI-powered applications with direct MCP tool access.

## Prerequisites

- MCP Server deployed and running (see main README)
- MCP endpoint URL from deployment output
- Python 3.11+ or Node.js 18+

## Quick Start (Python)

<details>
<summary><strong>1. Install MCP SDK</strong></summary>

```bash
pip install mcp anthropic
```

</details>

<details>
<summary><strong>2. Basic MCP Client</strong></summary>

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import httpx

class MCPClient:
    def __init__(self, mcp_endpoint: str, api_key: str = None):
        """
        Initialize MCP client
        
        Args:
            mcp_endpoint: Your MCP server URL (e.g., https://your-mcp.azurecontainerapps.io)
            api_key: Optional API key for authentication
        """
        self.endpoint = mcp_endpoint
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient()
    
    async def list_tools(self):
        """Get all available MCP tools"""
        response = await self.client.get(
            f"{self.endpoint}/mcp/tools",
            headers=self.headers
        )
        return response.json()
    
    async def call_tool(self, tool_name: str, arguments: dict):
        """
        Execute an MCP tool
        
        Args:
            tool_name: Name of the tool (e.g., 'cosmos_query_items')
            arguments: Tool-specific parameters
        
        Returns:
            Tool execution result
        """
        response = await self.client.post(
            f"{self.endpoint}/mcp/tools/{tool_name}",
            json={"arguments": arguments},
            headers=self.headers
        )
        return response.json()
    
    async def health_check(self):
        """Check MCP server health"""
        response = await self.client.get(
            f"{self.endpoint}/health",
            headers=self.headers
        )
        return response.json()

# Usage Example
async def main():
    # Initialize client
    mcp = MCPClient(
        mcp_endpoint="https://your-mcp.azurecontainerapps.io"
    )
    
    # Check server health
    health = await mcp.health_check()
    print(f"Server Status: {health}")
    
    # List available tools
    tools = await mcp.list_tools()
    print(f"Available Tools: {[t['name'] for t in tools['tools']]}")
    
    # Example: Query Cosmos DB
    result = await mcp.call_tool(
        tool_name="cosmos_query_items",
        arguments={
            "query": "SELECT * FROM c WHERE c.status = 'Active' OFFSET 0 LIMIT 10"
        }
    )
    print(f"Query Results: {result}")
    
    # Example: AI Search
    search_result = await mcp.call_tool(
        tool_name="search_documents",
        arguments={
            "search_text": "diabetes",
            "top": 10
        }
    )
    print(f"Search Results: {search_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

</details>

## Advanced Integration Examples

<details>
<summary><strong>Building a Custom AI Agent</strong></summary>

```python
import os
from anthropic import Anthropic
from mcp_client import MCPClient

class CustomAIAgent:
    """AI Agent with MCP tool access"""
    
    def __init__(self, mcp_endpoint: str, anthropic_api_key: str):
        self.mcp = MCPClient(mcp_endpoint)
        self.claude = Anthropic(api_key=anthropic_api_key)
    
    async def process_query(self, user_query: str):
        """
        Process user query with AI + MCP tools
        
        Args:
            user_query: Natural language user request
        
        Returns:
            AI response with tool results
        """
        # Get available tools
        tools = await self.mcp.list_tools()
        
        # Convert MCP tools to Claude format
        claude_tools = self._convert_to_claude_tools(tools)
        
        # Initial AI request
        response = self.claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            tools=claude_tools,
            messages=[
                {"role": "user", "content": user_query}
            ]
        )
        
        # Handle tool calls
        while response.stop_reason == "tool_use":
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            
            # Execute MCP tools
            tool_results = []
            for tool_call in tool_calls:
                result = await self.mcp.call_tool(
                    tool_name=tool_call.name,
                    arguments=tool_call.input
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": str(result)
                })
            
            # Continue conversation with tool results
            response = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                tools=claude_tools,
                messages=[
                    {"role": "user", "content": user_query},
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": tool_results}
                ]
            )
        
        return response.content[0].text
    
    def _convert_to_claude_tools(self, mcp_tools):
        """Convert MCP tool schema to Claude format"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"]
            }
            for tool in mcp_tools["tools"]
        ]

# Usage
async def run_agent():
    agent = CustomAIAgent(
        mcp_endpoint="https://your-mcp.azurecontainerapps.io",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    # Healthcare example
    response = await agent.process_query(
        "Find all diabetic patients with recent lab results and summarize their status"
    )
    print(response)

asyncio.run(run_agent())
```

</details>

<details>
<summary><strong>Flask/FastAPI Integration</strong></summary>

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

app = FastAPI(title="Custom App with MCP")

# Initialize MCP client
mcp_client = MCPClient(
    mcp_endpoint=os.getenv("MCP_ENDPOINT"),
    api_key=os.getenv("MCP_API_KEY")
)

class QueryRequest(BaseModel):
    tool: str
    parameters: dict

@app.post("/api/query")
async def execute_query(request: QueryRequest):
    """
    Execute MCP tool via REST API
    
    Example:
        POST /api/query
        {
            "tool": "cosmos_query_items",
            "parameters": {
                "query": "SELECT * FROM c WHERE c.price > 1000000"
            }
        }
    """
    try:
        result = await mcp_client.call_tool(
            tool_name=request.tool,
            parameters=request.parameters
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools")
async def get_tools():
    """List all available MCP tools"""
    tools = await mcp_client.list_tools()
    return tools

@app.get("/health")
async def health():
    """Application health check"""
    mcp_health = await mcp_client.health_check()
    return {
        "app": "healthy",
        "mcp_server": mcp_health
    }
```

</details>

## Node.js/TypeScript Integration

```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import axios from 'axios';

class MCPClient {
    private endpoint: string;
    private headers: Record<string, string>;

    constructor(mcpEndpoint: string, apiKey?: string) {
        this.endpoint = mcpEndpoint;
        this.headers = apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {};
    }

    async listTools() {
        const response = await axios.get(`${this.endpoint}/mcp/tools`, {
            headers: this.headers
        });
        return response.data;
    }

    async callTool(toolName: string, args: any) {
        const response = await axios.post(
            `${this.endpoint}/mcp/tools/${toolName}`,
            { arguments: args },
            { headers: this.headers }
        );
        return response.data;
    }

    async healthCheck() {
        const response = await axios.get(`${this.endpoint}/health`, {
            headers: this.headers
        });
        return response.data;
    }
}

// Usage
const mcp = new MCPClient('https://your-mcp.azurecontainerapps.io');

async function main() {
    // Check health
    const health = await mcp.healthCheck();
    console.log('Server Health:', health);

    // Query data
    const result = await mcp.callTool('search_documents', {
        search_text: 'diabetes',
        top: 10
    });
    console.log('Search Results:', result);
}

main();
```

## Authentication Options

<details>
<summary><strong>1. Azure Managed Identity (Recommended)</strong></summary>

```python
from azure.identity import DefaultAzureCredential

class SecureMCPClient(MCPClient):
    def __init__(self, mcp_endpoint: str):
        self.credential = DefaultAzureCredential()
        token = self.credential.get_token("https://management.azure.com/.default")
        super().__init__(mcp_endpoint, api_key=token.token)
```

</details>

<details>
<summary><strong>2. API Key Authentication</strong></summary>

```python
# Set in environment variable
export MCP_API_KEY="your-secret-key"

# Use in code
mcp = MCPClient(
    mcp_endpoint="https://your-mcp.azurecontainerapps.io",
    api_key=os.getenv("MCP_API_KEY")
)
```

</details>

<details>
<summary><strong>3. OAuth 2.0 Flow</strong></summary>

```python
from msal import ConfidentialClientApplication

class OAuthMCPClient(MCPClient):
    def __init__(self, mcp_endpoint: str, client_id: str, client_secret: str, tenant_id: str):
        app = ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret
        )
        result = app.acquire_token_for_client(scopes=["api://your-mcp/.default"])
        super().__init__(mcp_endpoint, api_key=result['access_token'])
```

</details>

## Error Handling

```python
from mcp_client import MCPClient
from httpx import HTTPStatusError, TimeoutException

async def robust_tool_call(mcp: MCPClient, tool_name: str, args: dict, retries=3):
    """Call MCP tool with retry logic"""
    for attempt in range(retries):
        try:
            result = await mcp.call_tool(tool_name, args)
            return result
        except HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limit - exponential backoff
                await asyncio.sleep(2 ** attempt)
            elif e.response.status_code >= 500:
                # Server error - retry
                await asyncio.sleep(1)
            else:
                # Client error - don't retry
                raise
        except TimeoutException:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(1)
    
    raise Exception(f"Failed after {retries} attempts")
```

## Best Practices

1. **Connection Pooling**: Reuse HTTP clients
2. **Caching**: Cache tool schemas and frequently accessed data
3. **Rate Limiting**: Implement client-side rate limiting
4. **Monitoring**: Log all MCP calls and errors
5. **Security**: Always use HTTPS and secure credential storage

## Sample Applications

See [`/agent-samples`](../../agent-samples) directory for complete examples:

- Healthcare Patient Assistant
- Retail Product Recommendation Engine
- Financial Transaction Monitor
- Manufacturing Equipment Diagnostics

## Next Steps

- [Azure AI Foundry Integration](./azure-ai-foundry-integration.md)
- [Copilot Studio Integration](./copilot-studio-integration.md)
- [Pre-built Agent Samples](../../agent-samples/README.md)

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
