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
from fastapi import FastAPI, HTTPException, Request
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

# =============================================================================
# MCP PROTOCOL MODELS
# =============================================================================

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

# =============================================================================
# AZURE SERVICES INTEGRATION
# =============================================================================

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

# =============================================================================
# MCP SERVER IMPLEMENTATION
# =============================================================================

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

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

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

# =============================================================================
# API ENDPOINTS
# =============================================================================

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

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )