#!/usr/bin/env python3
"""
Azure MCP Server - Model Context Protocol Implementation
Supports multiple Azure AI services: OpenAI, Search, Cosmos DB
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


def _pydantic_dump(model: Any) -> Any:
    """Serialize a Pydantic model across v1/v2 without importing version helpers."""
    if model is None:
        return None
    dump = getattr(model, "model_dump", None)
    if callable(dump):
        return dump()
    dump = getattr(model, "dict", None)
    if callable(dump):
        return dump()
    return model


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _maybe_json_dumps(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def _jsonrpc_error(
    message_id: Any,
    code: int,
    message: str,
    data: Optional[Any] = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    payload: dict[str, Any] = {"jsonrpc": "2.0", "error": error}
    if message_id is not None:
        payload["id"] = message_id
    return payload


def _jsonrpc_result(message_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _origin_allowed(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    allowed = _parse_csv_env("MCP_ALLOWED_ORIGINS")
    if not allowed:
        return False
    if "*" in allowed:
        return True
    return origin in allowed


def _require_api_key_if_configured(request: Request) -> None:
    expected = os.getenv("MCP_API_KEY")
    if not expected:
        return
    header_name = os.getenv("MCP_API_KEY_HEADER", "x-api-key")
    received = request.headers.get(header_name)
    if received != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _parse_enabled_tools() -> set[str]:
    raw = os.getenv("ENABLE_MCP_TOOLS", "")
    if not raw:
        return set()
    return {t.strip().lower() for t in raw.split(",") if t.strip()}

# Azure SDK imports
try:
    from azure.identity import DefaultAzureCredential
    from azure.cosmos import CosmosClient
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    import openai
except ImportError as e:
    logging.warning(f"Azure SDK not fully available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# MCP PROTOCOL MODELS
# -----------------------------------------------------------------------------

class MCPTool(BaseModel):
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    outputSchema: Optional[Dict[str, Any]] = None

class MCPResource(BaseModel):
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mimeType: str = "application/json"

class MCPPrompt(BaseModel):
    """MCP Prompt template"""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = []
    template: str

class MCPToolCall(BaseModel):
    """MCP Tool execution request"""
    name: str
    arguments: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    """MCP Response"""
    content: Any
    isError: bool = False
    errorMessage: Optional[str] = None

# -----------------------------------------------------------------------------
# AZURE SERVICES INTEGRATION
# -----------------------------------------------------------------------------

class AzureServicesManager:
    """Manages Azure service connections and credentials"""
    
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.cosmos_client = None
        self.search_client = None
        self.openai_client = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize Azure service clients based on environment configuration"""
        # IMPORTANT: initialize each service independently. If Cosmos fails (e.g., RBAC propagation),
        # Search/OpenAI should still initialize so the server stays partially functional.
        self._ensure_cosmos()
        self._ensure_search()
        self._ensure_openai()

    def refresh_missing(self) -> None:
        """Retry initialization for any missing service clients.

        Useful in cloud deployments where role assignments or secrets may take time to propagate.
        """
        if self.cosmos_client is None:
            self._ensure_cosmos()
        if self.search_client is None:
            self._ensure_search()
        if self.openai_client is None:
            self._ensure_openai()

    def _ensure_cosmos(self) -> None:
        if self.cosmos_client is not None:
            return
        cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
        cosmos_key = os.getenv("COSMOS_KEY")
        if not cosmos_endpoint:
            return
        try:
            cosmos_credential = cosmos_key if cosmos_key else self.credential
            self.cosmos_client = CosmosClient(url=cosmos_endpoint, credential=cosmos_credential)
            logger.info("Cosmos DB client initialized")
        except Exception as e:
            logger.error(f"Cosmos DB init failed: {e}")

    def _ensure_search(self) -> None:
        if self.search_client is not None:
            return
        search_endpoint = os.getenv("SEARCH_ENDPOINT")
        search_admin_key = os.getenv("SEARCH_ADMIN_KEY") or os.getenv("SEARCH_KEY")
        search_index_name = os.getenv("SEARCH_INDEX_NAME", "mcp-index")
        if not search_endpoint:
            return
        try:
            search_credential = AzureKeyCredential(search_admin_key) if search_admin_key else self.credential
            self.search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=search_index_name,
                credential=search_credential,
            )
            logger.info("Azure AI Search client initialized")
        except Exception as e:
            logger.error(f"Azure AI Search init failed: {e}")

    def _ensure_openai(self) -> None:
        if self.openai_client is not None:
            return
        openai_endpoint = os.getenv("OPENAI_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
        openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("FOUNDRY_API_KEY")
        if not openai_endpoint:
            return
        try:
            if openai_api_key and openai_api_key.strip().lower() != "managed_identity":
                self.openai_client = openai.AzureOpenAI(
                    azure_endpoint=openai_endpoint,
                    api_key=openai_api_key,
                    api_version="2024-08-01-preview",
                )
            else:
                self.openai_client = openai.AzureOpenAI(
                    azure_endpoint=openai_endpoint,
                    azure_ad_token_provider=lambda: self.credential.get_token(
                        "https://cognitiveservices.azure.com/.default"
                    ).token,
                    api_version="2024-08-01-preview",
                )
            logger.info("Azure OpenAI client initialized")
        except Exception as e:
            logger.error(f"Azure OpenAI init failed: {e}")

# -----------------------------------------------------------------------------
# MCP SERVER IMPLEMENTATION
# -----------------------------------------------------------------------------

class MCPServer:
    """Azure MCP Server implementation"""
    
    def __init__(self):
        self.azure_services = AzureServicesManager()
        self.cosmos_database = os.getenv("COSMOS_DATABASE", "mcp-database")
        self.cosmos_container = os.getenv("COSMOS_CONTAINER", "mcp-container")
        self.enabled_tools = _parse_enabled_tools()
        self.tools = self._register_tools()
        self.resources = self._register_resources()
        self.prompts = self._register_prompts()
    
    def _register_tools(self) -> List[MCPTool]:
        """Register available MCP tools based on enabled Azure services"""
        tools = []

        cosmos_enabled = ("cosmos" in self.enabled_tools) or (self.azure_services.cosmos_client is not None)
        search_enabled = ("search" in self.enabled_tools) or (self.azure_services.search_client is not None)
        # Terraform calls this "foundry"; the server exposes it as OpenAI-compatible tools.
        openai_enabled = (
            ("foundry" in self.enabled_tools)
            or ("openai" in self.enabled_tools)
            or (self.azure_services.openai_client is not None)
        )
        
        # Health check tool (always available)
        tools.append(MCPTool(
            name="health_check",
            description="Check the health status of the MCP server and Azure services",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ))
        
        # Cosmos DB tools
        if cosmos_enabled:
            tools.extend([
                MCPTool(
                    name="cosmos_create_item",
                    description="Create a new item in Cosmos DB",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "data": {"type": "object", "description": "Item data to store"},
                            "partition_key": {"type": "string", "description": "Partition key value"}
                        },
                        "required": ["data", "partition_key"]
                    }
                ),
                MCPTool(
                    name="cosmos_query_items",
                    description="Query items from Cosmos DB",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "SQL query string"},
                            "parameters": {"type": "array", "description": "Query parameters"}
                        },
                        "required": ["query"]
                    }
                )
            ])
        
        # Azure AI Search tools
        if search_enabled:
            tools.extend([
                MCPTool(
                    name="search_documents",
                    description="Search documents using Azure AI Search",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "top": {"type": "integer", "description": "Number of results", "default": 10},
                            "filter": {"type": "string", "description": "OData filter expression"}
                        },
                        "required": ["query"]
                    }
                ),
                MCPTool(
                    name="search_semantic",
                    description="Perform semantic search with AI-powered ranking",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Semantic search query"},
                            "top": {"type": "integer", "description": "Number of results", "default": 5}
                        },
                        "required": ["query"]
                    }
                )
            ])
        
        # Azure OpenAI tools
        if openai_enabled:
            tools.extend([
                MCPTool(
                    name="openai_chat_completion",
                    description="Generate chat completion using Azure OpenAI",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "messages": {"type": "array", "description": "Chat messages"},
                            "model": {"type": "string", "description": "Model name", "default": "gpt-4o"},
                            "temperature": {"type": "number", "description": "Temperature", "default": 0.7},
                            "max_tokens": {"type": "integer", "description": "Max tokens", "default": 1000}
                        },
                        "required": ["messages"]
                    }
                ),
                MCPTool(
                    name="openai_embeddings",
                    description="Generate text embeddings using Azure OpenAI",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to embed"},
                            "model": {"type": "string", "description": "Embedding model", "default": "text-embedding-ada-002"}
                        },
                        "required": ["text"]
                    }
                )
            ])
        
        return tools
    
    def _register_resources(self) -> List[MCPResource]:
        """Register available MCP resources"""
        resources = [
            MCPResource(
                uri="azure://mcp/server/status",
                name="Server Status",
                description="Current status and configuration of the MCP server"
            ),
            MCPResource(
                uri="azure://mcp/tools/list",
                name="Available Tools",
                description="List of all available MCP tools"
            )
        ]
        
        if self.azure_services.cosmos_client:
            resources.append(MCPResource(
                uri="azure://cosmos/containers",
                name="Cosmos DB Containers",
                description="List of available Cosmos DB containers"
            ))
        
        if self.azure_services.search_client:
            resources.append(MCPResource(
                uri="azure://search/indexes",
                name="Search Indexes",
                description="List of available Azure AI Search indexes"
            ))
        
        return resources
    
    def _register_prompts(self) -> List[MCPPrompt]:
        """Register MCP prompt templates"""
        return [
            MCPPrompt(
                name="azure_troubleshooting",
                description="Azure service troubleshooting assistant",
                arguments=[
                    {"name": "service", "description": "Azure service name", "required": True},
                    {"name": "issue", "description": "Issue description", "required": True}
                ],
                template="You are an Azure expert. Help troubleshoot {service} with the following issue: {issue}"
            ),
            MCPPrompt(
                name="data_analysis",
                description="Data analysis using Azure services",
                arguments=[
                    {"name": "dataset", "description": "Dataset description", "required": True},
                    {"name": "objective", "description": "Analysis objective", "required": True}
                ],
                template="Analyze the {dataset} data to achieve: {objective}. Use available Azure AI services."
            )
        ]
    
    async def execute_tool(self, tool_call: MCPToolCall) -> MCPResponse:
        """Execute a tool call"""
        try:
            tool_name = tool_call.name
            args = tool_call.arguments
            
            # Health check
            if tool_name == "health_check":
                return await self._health_check()
            
            # Cosmos DB tools
            elif tool_name == "cosmos_create_item":
                return await self._cosmos_create_item(args)
            elif tool_name == "cosmos_query_items":
                return await self._cosmos_query_items(args)
            
            # Search tools
            elif tool_name == "search_documents":
                return await self._search_documents(args)
            elif tool_name == "search_semantic":
                return await self._search_semantic(args)
            
            # OpenAI tools
            elif tool_name == "openai_chat_completion":
                return await self._openai_chat_completion(args)
            elif tool_name == "openai_embeddings":
                return await self._openai_embeddings(args)
            
            else:
                return MCPResponse(
                    content=None,
                    isError=True,
                    errorMessage=f"Unknown tool: {tool_name}"
                )
        
        except Exception as e:
            logger.error(f"Error executing tool {tool_call.name}: {e}")
            return MCPResponse(
                content=None,
                isError=True,
                errorMessage=str(e)
            )
    
    async def _health_check(self) -> MCPResponse:
        """Health check implementation"""
        # Retry initialization opportunistically. This helps in cloud deployments
        # where managed identity permissions and secret resolution can take time.
        self.azure_services.refresh_missing()

        status = {
            "server": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "services": {
                "cosmos_db": self.azure_services.cosmos_client is not None,
                "ai_search": self.azure_services.search_client is not None,
                "openai": self.azure_services.openai_client is not None
            },
            "tools_count": len(self.tools),
            "resources_count": len(self.resources)
        }
        return MCPResponse(content=status)
    
    async def _cosmos_create_item(self, args: Dict[str, Any]) -> MCPResponse:
        """Create Cosmos DB item"""
        if not self.azure_services.cosmos_client:
            return MCPResponse(content=None, isError=True, errorMessage="Cosmos DB not available")
        
        try:
            database = self.azure_services.cosmos_client.get_database_client(self.cosmos_database)
            container = database.get_container_client(self.cosmos_container)
            
            item_data = args["data"]
            item_data["id"] = item_data.get("id", f"item-{asyncio.get_event_loop().time()}")
            
            result = container.create_item(item_data)
            return MCPResponse(content={"created_item": result})
        
        except Exception as e:
            return MCPResponse(content=None, isError=True, errorMessage=f"Cosmos DB error: {e}")
    
    async def _cosmos_query_items(self, args: Dict[str, Any]) -> MCPResponse:
        """Query Cosmos DB items"""
        if not self.azure_services.cosmos_client:
            return MCPResponse(content=None, isError=True, errorMessage="Cosmos DB not available")
        
        try:
            database = self.azure_services.cosmos_client.get_database_client(self.cosmos_database)
            container = database.get_container_client(self.cosmos_container)
            
            query = args["query"]
            parameters = args.get("parameters", [])
            
            items = list(container.query_items(query=query, parameters=parameters))
            return MCPResponse(content={"items": items, "count": len(items)})
        
        except Exception as e:
            return MCPResponse(content=None, isError=True, errorMessage=f"Cosmos DB query error: {e}")
    
    async def _search_documents(self, args: Dict[str, Any]) -> MCPResponse:
        """Search documents"""
        if not self.azure_services.search_client:
            return MCPResponse(content=None, isError=True, errorMessage="Azure AI Search not available")
        
        try:
            query = args["query"]
            top = args.get("top", 10)
            filter_expr = args.get("filter")
            
            results = self.azure_services.search_client.search(
                search_text=query,
                top=top,
                filter=filter_expr
            )
            
            documents = [doc for doc in results]
            return MCPResponse(content={"documents": documents, "count": len(documents)})
        
        except Exception as e:
            return MCPResponse(content=None, isError=True, errorMessage=f"Search error: {e}")
    
    async def _search_semantic(self, args: Dict[str, Any]) -> MCPResponse:
        """Semantic search"""
        if not self.azure_services.search_client:
            return MCPResponse(content=None, isError=True, errorMessage="Azure AI Search not available")
        
        try:
            query = args["query"]
            top = args.get("top", 5)
            
            results = self.azure_services.search_client.search(
                search_text=query,
                top=top,
                query_type="semantic",
                semantic_configuration_name="default"
            )
            
            documents = [doc for doc in results]
            return MCPResponse(content={"documents": documents, "count": len(documents)})
        
        except Exception as e:
            return MCPResponse(content=None, isError=True, errorMessage=f"Semantic search error: {e}")
    
    async def _openai_chat_completion(self, args: Dict[str, Any]) -> MCPResponse:
        """OpenAI chat completion"""
        if not self.azure_services.openai_client:
            return MCPResponse(content=None, isError=True, errorMessage="Azure OpenAI not available")
        
        try:
            response = self.azure_services.openai_client.chat.completions.create(
                model=args.get("model", "gpt-4o"),
                messages=args["messages"],
                temperature=args.get("temperature", 0.7),
                max_tokens=args.get("max_tokens", 1000)
            )
            
            return MCPResponse(content={
                "response": response.choices[0].message.content,
                "usage": _pydantic_dump(response.usage) if response.usage else None
            })
        
        except Exception as e:
            return MCPResponse(content=None, isError=True, errorMessage=f"OpenAI error: {e}")
    
    async def _openai_embeddings(self, args: Dict[str, Any]) -> MCPResponse:
        """OpenAI embeddings"""
        if not self.azure_services.openai_client:
            return MCPResponse(content=None, isError=True, errorMessage="Azure OpenAI not available")
        
        try:
            response = self.azure_services.openai_client.embeddings.create(
                model=args.get("model", "text-embedding-ada-002"),
                input=args["text"]
            )
            
            return MCPResponse(content={
                "embedding": response.data[0].embedding,
                "usage": _pydantic_dump(response.usage) if response.usage else None
            })
        
        except Exception as e:
            return MCPResponse(content=None, isError=True, errorMessage=f"Embeddings error: {e}")


def _tool_to_mcp(tool: MCPTool) -> dict[str, Any]:
    data = _pydantic_dump(tool)
    data.setdefault("title", tool.name.replace("_", " ").title())
    return data


def _resource_to_mcp(resource: MCPResource) -> dict[str, Any]:
    data = _pydantic_dump(resource)
    data.setdefault("title", resource.name)
    return data


def _prompt_to_mcp(prompt: MCPPrompt) -> dict[str, Any]:
    data = _pydantic_dump(prompt)
    data.setdefault("title", prompt.name.replace("_", " ").title())
    return data


def _mcp_tool_result(response: MCPResponse) -> dict[str, Any]:
    if response.isError:
        return {
            "content": [{"type": "text", "text": response.errorMessage or "Tool execution error"}],
            "isError": True,
        }

    content = response.content
    if content is None:
        return {"content": [{"type": "text", "text": "null"}], "isError": False}
    if isinstance(content, str):
        return {"content": [{"type": "text", "text": content}], "isError": False}
    return {
        "content": [{"type": "text", "text": _maybe_json_dumps(content)}],
        "structuredContent": content,
        "isError": False,
    }

# -----------------------------------------------------------------------------
# FASTAPI APPLICATION
# -----------------------------------------------------------------------------

# Initialize MCP server
mcp_server = MCPServer()

# Create FastAPI app
app = FastAPI(
    title="Azure MCP Server",
    description="Model Context Protocol server with Azure AI services integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# API ENDPOINTS
# -----------------------------------------------------------------------------


@app.post("/mcp")
async def mcp_streamable_endpoint(request: Request):
    """MCP Streamable HTTP endpoint (JSON-RPC over HTTP).

    Copilot Studio expects a single MCP endpoint (e.g., `/mcp`) that accepts JSON-RPC
    messages via HTTP POST.
    """
    if not _origin_allowed(request):
        raise HTTPException(status_code=403, detail="Forbidden")
    _require_api_key_if_configured(request)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=_jsonrpc_error(None, -32600, "Invalid Request", data={"reason": "Invalid JSON"}),
        )

    messages: list[Any]
    is_batch = isinstance(body, list)
    if is_batch:
        messages = body
    elif isinstance(body, dict):
        messages = [body]
    else:
        return JSONResponse(
            status_code=400,
            content=_jsonrpc_error(None, -32600, "Invalid Request", data={"reason": "Expected object or array"}),
        )

    protocol_version = request.headers.get("mcp-protocol-version") or "2025-03-26"
    supported_versions = {"2025-03-26", "2025-06-18"}
    if protocol_version not in supported_versions:
        return JSONResponse(
            status_code=400,
            content=_jsonrpc_error(
                None,
                -32602,
                "Unsupported protocol version",
                data={"supported": sorted(supported_versions), "requested": protocol_version},
            ),
        )

    responses: list[dict[str, Any]] = []
    saw_request = False

    for msg in messages:
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            responses.append(_jsonrpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request"))
            saw_request = True
            continue

        method = msg.get("method")
        message_id = msg.get("id")

        # Client responses (result/error) and notifications are accepted with 202 and no body.
        if not method:
            continue

        # Notification: no id => no response
        if message_id is None:
            if method == "notifications/initialized":
                continue
            continue

        saw_request = True
        params = msg.get("params") or {}
        try:
            if method == "initialize":
                requested_version = params.get("protocolVersion")
                negotiated = requested_version if requested_version in supported_versions else max(supported_versions)

                result = {
                    "protocolVersion": negotiated,
                    "capabilities": {
                        "tools": {"listChanged": False} if mcp_server.tools else {},
                        "resources": {} if mcp_server.resources else {},
                        "prompts": {"listChanged": False} if mcp_server.prompts else {},
                    },
                    "serverInfo": {
                        "name": "azure-mcp-blueprint",
                        "title": "Azure MCP Blueprint Server",
                        "version": "1.0.0",
                    },
                    "instructions": "Use tools/list to discover tools, then tools/call to invoke them.",
                }
                responses.append(_jsonrpc_result(message_id, result))

            elif method == "tools/list":
                result = {
                    "tools": [_tool_to_mcp(tool) for tool in mcp_server.tools],
                    "nextCursor": None,
                }
                responses.append(_jsonrpc_result(message_id, result))

            elif method == "tools/call":
                tool_name = params.get("name")
                if not tool_name or not isinstance(tool_name, str):
                    responses.append(_jsonrpc_error(message_id, -32602, "Invalid params", data={"missing": "name"}))
                    continue
                registered = {t.name for t in mcp_server.tools}
                if tool_name not in registered:
                    responses.append(_jsonrpc_error(message_id, -32602, f"Unknown tool: {tool_name}"))
                    continue
                arguments = params.get("arguments")
                if arguments is None:
                    arguments = {}
                if not isinstance(arguments, dict):
                    responses.append(_jsonrpc_error(message_id, -32602, "Invalid params", data={"field": "arguments"}))
                    continue
                tool_response = await mcp_server.execute_tool(MCPToolCall(name=tool_name, arguments=arguments))
                responses.append(_jsonrpc_result(message_id, _mcp_tool_result(tool_response)))

            elif method == "resources/list":
                result = {
                    "resources": [_resource_to_mcp(resource) for resource in mcp_server.resources],
                    "nextCursor": None,
                }
                responses.append(_jsonrpc_result(message_id, result))

            elif method == "resources/read":
                uri = params.get("uri")
                if not uri or not isinstance(uri, str):
                    responses.append(_jsonrpc_error(message_id, -32602, "Invalid params", data={"missing": "uri"}))
                    continue
                contents: list[dict[str, Any]] = []

                if uri == "azure://mcp/server/status":
                    health_response = await mcp_server.execute_tool(MCPToolCall(name="health_check"))
                    contents.append(
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": _maybe_json_dumps(health_response.content),
                        }
                    )
                elif uri == "azure://mcp/tools/list":
                    contents.append(
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": _maybe_json_dumps({"tools": [_tool_to_mcp(tool) for tool in mcp_server.tools]}),
                        }
                    )
                else:
                    responses.append(
                        _jsonrpc_error(message_id, -32002, "Resource not found", data={"uri": uri})
                    )
                    continue

                responses.append(_jsonrpc_result(message_id, {"contents": contents}))

            elif method == "prompts/list":
                result = {
                    "prompts": [_prompt_to_mcp(prompt) for prompt in mcp_server.prompts],
                    "nextCursor": None,
                }
                responses.append(_jsonrpc_result(message_id, result))

            elif method == "prompts/get":
                prompt_name = params.get("name")
                if not prompt_name or not isinstance(prompt_name, str):
                    responses.append(_jsonrpc_error(message_id, -32602, "Invalid params", data={"missing": "name"}))
                    continue
                arguments = params.get("arguments") or {}
                if not isinstance(arguments, dict):
                    responses.append(_jsonrpc_error(message_id, -32602, "Invalid params", data={"field": "arguments"}))
                    continue

                prompt = next((p for p in mcp_server.prompts if p.name == prompt_name), None)
                if not prompt:
                    responses.append(_jsonrpc_error(message_id, -32602, "Invalid params", data={"name": prompt_name}))
                    continue

                try:
                    rendered = prompt.template.format(**arguments)
                except Exception as e:
                    responses.append(_jsonrpc_error(message_id, -32602, "Invalid params", data={"reason": str(e)}))
                    continue

                responses.append(
                    _jsonrpc_result(
                        message_id,
                        {
                            "description": prompt.description,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {"type": "text", "text": rendered},
                                }
                            ],
                        },
                    )
                )

            elif method == "ping":
                responses.append(_jsonrpc_result(message_id, {}))

            else:
                responses.append(_jsonrpc_error(message_id, -32601, f"Method not found: {method}"))

        except Exception as e:
            logger.exception("Unhandled MCP error")
            responses.append(_jsonrpc_error(message_id, -32603, "Internal error", data={"reason": str(e)}))

    if not saw_request:
        return Response(status_code=202)

    if not is_batch and len(responses) == 1:
        return JSONResponse(content=responses[0])
    return JSONResponse(content=responses)


@app.get("/mcp")
async def mcp_streamable_get(_: Request):
    """Optional SSE stream endpoint.

    Copilot Studio's MCP support is Streamable; SSE is deprecated and not required here.
    """
    raise HTTPException(status_code=405, detail="Method Not Allowed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Azure MCP Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "tools": "/mcp/tools",
            "resources": "/mcp/resources",
            "prompts": "/mcp/prompts",
            "execute": "/mcp/execute",
            "mcp": "/mcp",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    response = await mcp_server.execute_tool(MCPToolCall(name="health_check"))
    return response.content

@app.get("/mcp/tools")
async def list_tools():
    """List available MCP tools"""
    return {"tools": [_pydantic_dump(tool) for tool in mcp_server.tools]}

@app.get("/mcp/resources")
async def list_resources():
    """List available MCP resources"""
    return {"resources": [_pydantic_dump(resource) for resource in mcp_server.resources]}

@app.get("/mcp/prompts")
async def list_prompts():
    """List available MCP prompts"""
    return {"prompts": [_pydantic_dump(prompt) for prompt in mcp_server.prompts]}

@app.post("/mcp/execute")
async def execute_tool(tool_call: MCPToolCall):
    """Execute an MCP tool"""
    response = await mcp_server.execute_tool(tool_call)
    return _pydantic_dump(response)

@app.get("/mcp/resources/{resource_uri:path}")
async def get_resource(resource_uri: str):
    """Get a specific MCP resource"""
    # Find the resource
    resource = next((r for r in mcp_server.resources if r.uri == f"azure://{resource_uri}"), None)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Return resource-specific data
    if resource_uri == "mcp/server/status":
        health_response = await mcp_server.execute_tool(MCPToolCall(name="health_check"))
        return health_response.content
    elif resource_uri == "mcp/tools/list":
        return {"tools": [_pydantic_dump(tool) for tool in mcp_server.tools]}
    else:
        return _pydantic_dump(resource)

# -----------------------------------------------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )