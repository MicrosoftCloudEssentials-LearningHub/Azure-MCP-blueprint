# Azure AI Foundry Integration with MCP Server

## Overview

This guide demonstrates how to integrate your MCP Server with Azure AI Foundry to build sophisticated multi-agent AI applications. Includes model routing, agent orchestration, and agentic workflows.

## Architecture Pattern

```
User Request → Intent Router → Specialized Agents → MCP Tools → Azure Services
                    ↓
            [Primary Agent]
                    ↓
         Handoff Planning
                    ↓
    [Agent 1] → [Agent 2] → [Agent 3]
         ↓           ↓           ↓
    MCP Tools   MCP Tools   MCP Tools
```

## Prerequisites

- Azure AI Foundry project created
- MCP Server deployed (get endpoint URL)
- Azure OpenAI models deployed (gpt-4o, gpt-4o-mini)
- Azure CLI installed and authenticated

## Quick Start

### 1. Install Azure AI SDK

```bash
pip install azure-ai-projects azure-ai-agents azure-identity
```

### 2. Create Multi-Agent System

```python
import os
from azure.ai.projects import AIProjectClient
from azure.ai.agents import Agent, AgentRuntime
from azure.identity import DefaultAzureCredential

class MCPMultiAgentOrchestrator:
    """
    Multi-agent orchestrator with MCP server integration
    Based on Agent-to-Agent (A2A) protocol pattern
    """
    
    def __init__(
        self,
        project_endpoint: str,
        mcp_endpoint: str,
        subscription_id: str,
        resource_group: str,
        project_name: str
    ):
        self.credential = DefaultAzureCredential()
        
        # Initialize AI Foundry client
        self.ai_client = AIProjectClient(
            credential=self.credential,
            subscription_id=subscription_id,
            resource_group_name=resource_group,
            project_name=project_name
        )
        
        self.mcp_endpoint = mcp_endpoint
        self.agents = {}
        self.runtime = AgentRuntime(client=self.ai_client)
    
    def create_agent(
        self,
        name: str,
        role: str,
        instructions: str,
        mcp_tools: list[str],
        model: str = "gpt-4o"
    ) -> str:
        """
        Create specialized agent with MCP tool access
        
        Args:
            name: Agent identifier
            role: Agent's domain (e.g., "Healthcare Specialist", "Inventory Manager")
            instructions: System instructions for the agent
            mcp_tools: List of MCP tool names this agent can use
            model: Azure OpenAI model deployment name
        
        Returns:
            Agent ID (asst_*)
        """
        # Define tools with MCP endpoint
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"MCP tool: {tool_name}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mcp_endpoint": {
                                "type": "string",
                                "description": self.mcp_endpoint
                            },
                            "arguments": {
                                "type": "object",
                                "description": "Tool-specific parameters"
                            }
                        },
                        "required": ["arguments"]
                    }
                }
            }
            for tool_name in mcp_tools
        ]
        
        # Create agent in Azure AI Foundry
        agent = self.ai_client.agents.create_agent(
            model=model,
            name=name,
            instructions=f"""You are {role}.

{instructions}

You have access to MCP tools that connect to Azure services:
{', '.join(mcp_tools)}

When calling tools:
1. Analyze the user request
2. Select appropriate tool(s)
3. Format parameters correctly
4. Execute and interpret results
5. Provide clear, helpful responses

MCP Server Endpoint: {self.mcp_endpoint}
""",
            tools=tools
        )
        
        self.agents[name] = agent.id
        print(f"Created agent: {name} (ID: {agent.id})")
        return agent.id
    
    async def route_request(self, user_message: str) -> dict:
        """
        Route user request to appropriate agent(s)
        Implements intent classification and handoff planning
        
        Args:
            user_message: User's natural language request
        
        Returns:
            Orchestration plan with agent sequence
        """
        # Use routing model to classify intent
        routing_prompt = f"""Analyze this user request and determine:
1. Primary domain (healthcare, retail, finance, etc.)
2. Required agents (list in execution order)
3. Handoff points between agents

User Request: {user_message}

Available Agents:
{list(self.agents.keys())}

Respond in JSON format:
{{
    "primary_domain": "...",
    "agent_sequence": ["agent1", "agent2", ...],
    "handoffs": [
        {{"from": "agent1", "to": "agent2", "condition": "..."}},
        ...
    ]
}}
"""
        
        # Call routing model (lightweight GPT-4o-mini)
        response = self.ai_client.inference.get_chat_completions(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": routing_prompt}]
        )
        
        import json
        routing_plan = json.loads(response.choices[0].message.content)
        return routing_plan
    
    async def execute_agent_chain(
        self,
        user_message: str,
        agent_sequence: list[str]
    ) -> str:
        """
        Execute multi-agent workflow with handoffs
        
        Args:
            user_message: Original user request
            agent_sequence: Ordered list of agent names
        
        Returns:
            Final aggregated response
        """
        context = user_message
        results = []
        
        for i, agent_name in enumerate(agent_sequence):
            agent_id = self.agents.get(agent_name)
            if not agent_id:
                continue
            
            # Create thread for this agent
            thread = self.ai_client.agents.create_thread()
            
            # Add message
            self.ai_client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=context
            )
            
            # Run agent
            run = self.ai_client.agents.create_run(
                thread_id=thread.id,
                assistant_id=agent_id
            )
            
            # Wait for completion
            while run.status in ["queued", "in_progress", "requires_action"]:
                run = self.ai_client.agents.get_run(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                # Handle tool calls (MCP integration)
                if run.status == "requires_action":
                    tool_outputs = await self._handle_mcp_tool_calls(
                        run.required_action.submit_tool_outputs.tool_calls
                    )
                    
                    run = self.ai_client.agents.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                
                await asyncio.sleep(0.5)
            
            # Get agent response
            messages = self.ai_client.agents.list_messages(thread_id=thread.id)
            agent_response = messages.data[0].content[0].text.value
            
            results.append({
                "agent": agent_name,
                "response": agent_response
            })
            
            # Update context for next agent
            if i < len(agent_sequence) - 1:
                context = f"""Previous agent ({agent_name}) response:
{agent_response}

Original request: {user_message}
Continue the workflow."""
        
        return self._aggregate_results(results)
    
    async def _handle_mcp_tool_calls(self, tool_calls):
        """Execute MCP tools and return results"""
        import httpx
        
        outputs = []
        async with httpx.AsyncClient() as client:
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                # Call MCP server
                response = await client.post(
                    f"{self.mcp_endpoint}/mcp/tools/{tool_name}",
                    json={"arguments": args["arguments"]}
                )
                
                outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": response.text
                })
        
        return outputs
    
    def _aggregate_results(self, results: list[dict]) -> str:
        """Combine multi-agent results into coherent response"""
        aggregated = "Multi-Agent Response:\n\n"
        for result in results:
            aggregated += f"**{result['agent']}:**\n{result['response']}\n\n"
        return aggregated

# Usage Example
async def main():
    orchestrator = MCPMultiAgentOrchestrator(
        project_endpoint=os.getenv("AI_FOUNDRY_ENDPOINT"),
        mcp_endpoint=os.getenv("MCP_ENDPOINT"),
        subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
        resource_group=os.getenv("AZURE_RESOURCE_GROUP"),
        project_name=os.getenv("AI_FOUNDRY_PROJECT")
    )
    
    # Create specialized agents
    orchestrator.create_agent(
        name="HealthcareSpecialist",
        role="Medical Records Expert",
        instructions="""You handle patient data queries, medical history lookups,
        and clinical research tasks. Use MCP tools to access Cosmos DB and AI Search.""",
        mcp_tools=["cosmos_query_items", "search_documents", "search_semantic"]
    )
    
    orchestrator.create_agent(
        name="DiagnosticAssistant",
        role="AI Medical Diagnostic Helper",
        instructions="""You generate medical insights and summaries using AI.
        You work with data from other agents to provide diagnostic support.""",
        mcp_tools=["openai_chat_completion"]
    )
    
    orchestrator.create_agent(
        name="ComplianceMonitor",
        role="Healthcare Compliance Officer",
        instructions="""You ensure all queries comply with HIPAA and verify
        data access permissions.""",
        mcp_tools=["cosmos_query_items"]
    )
    
    # Execute multi-agent workflow
    user_request = """Find all diabetic patients with recent lab results,
    generate a clinical summary, and verify compliance with data access policies."""
    
    # Route request
    routing_plan = await orchestrator.route_request(user_request)
    print(f"Routing Plan: {routing_plan}")
    
    # Execute agent chain
    result = await orchestrator.execute_agent_chain(
        user_message=user_request,
        agent_sequence=routing_plan["agent_sequence"]
    )
    
    print(f"\nFinal Result:\n{result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Industry-Specific Multi-Agent Setups

### Healthcare Example

```python
# Create healthcare agent team
agents = {
    "Triage": orchestrator.create_agent(
        name="TriageAgent",
        role="Patient Request Router",
        instructions="Route patient queries to appropriate specialists",
        mcp_tools=["search_semantic"]
    ),
    
    "Clinician": orchestrator.create_agent(
        name="ClinicalAgent",
        role="Clinical Data Specialist",
        instructions="Query patient records, medications, allergies, lab results",
        mcp_tools=["cosmos_query_items", "search_documents"]
    ),
    
    "Researcher": orchestrator.create_agent(
        name="ResearchAgent",
        role="Medical Research Assistant",
        instructions="Analyze patient populations, identify patterns",
        mcp_tools=["search_semantic", "openai_chat_completion"]
    ),
    
    "Coordinator": orchestrator.create_agent(
        name="CareCoordinator",
        role="Patient Care Coordinator",
        instructions="Aggregate information and provide comprehensive patient summaries",
        mcp_tools=["openai_chat_completion"]
    )
}
```

### Retail Example

```python
# Create retail agent team
agents = {
    "ProductExpert": orchestrator.create_agent(
        name="ProductAgent",
        role="Product Catalog Specialist",
        instructions="Search inventory, check availability, provide product details",
        mcp_tools=["search_documents", "cosmos_query_items"]
    ),
    
    "RecommendationEngine": orchestrator.create_agent(
        name="RecommendationAgent",
        role="AI Product Recommender",
        instructions="Generate personalized product recommendations",
        mcp_tools=["search_semantic", "openai_chat_completion"]
    ),
    
    "LoyaltyManager": orchestrator.create_agent(
        name="LoyaltyAgent",
        role="Customer Loyalty Specialist",
        instructions="Check points, apply discounts, manage rewards",
        mcp_tools=["cosmos_query_items"]
    ),
    
    "CartManager": orchestrator.create_agent(
        name="CartAgent",
        role="Shopping Cart Manager",
        instructions="Add items, calculate totals, process checkout",
        mcp_tools=["cosmos_create_item", "cosmos_query_items"]
    )
}
```

## Model Router Pattern

```python
class ModelRouter:
    """
    Route requests to optimal models based on complexity and cost
    Inspired by Agentic-DevOps-AI-Shopping example
    """
    
    def __init__(self):
        self.models = {
            "simple": "gpt-4o-mini",      # Fast, cheap
            "complex": "gpt-4o",           # Powerful, expensive
            "embedding": "text-embedding-3-small"
        }
    
    def select_model(self, request: str, agent_type: str) -> str:
        """
        Choose model based on request complexity
        
        Args:
            request: User request text
            agent_type: Agent role (routing, execution, aggregation)
        
        Returns:
            Model deployment name
        """
        # Simple routing/triage tasks → gpt-4o-mini
        if agent_type == "routing":
            return self.models["simple"]
        
        # Complex reasoning/generation → gpt-4o
        if agent_type == "execution":
            if len(request) > 500 or "analyze" in request.lower():
                return self.models["complex"]
            return self.models["simple"]
        
        # Aggregation → gpt-4o-mini
        if agent_type == "aggregation":
            return self.models["simple"]
        
        return self.models["simple"]
```

## Deployment to Azure

### 1. Create Azure AI Foundry Project

```bash
# Using Azure CLI
az ml workspace create \
    --name my-ai-project \
    --resource-group my-rg \
    --location eastus

# Enable Agents API
az ml workspace update \
    --name my-ai-project \
    --resource-group my-rg \
    --enable-agents true
```

### 2. Deploy Models

```bash
# Deploy GPT-4o
az ml online-deployment create \
    --file gpt4o-deployment.yml \
    --workspace-name my-ai-project \
    --resource-group my-rg

# Deploy GPT-4o-mini
az ml online-deployment create \
    --file gpt4o-mini-deployment.yml \
    --workspace-name my-ai-project \
    --resource-group my-rg
```

### 3. Configure MCP Connection

```python
# Store MCP endpoint in Azure Key Vault
from azure.keyvault.secrets import SecretClient

kv_client = SecretClient(
    vault_url="https://my-keyvault.vault.azure.net",
    credential=DefaultAzureCredential()
)

kv_client.set_secret("MCP-Endpoint", "https://your-mcp.azurecontainerapps.io")
```

## Best Practices

1. **Agent Specialization**: Create focused agents for specific domains
2. **Model Selection**: Use gpt-4o-mini for routing, gpt-4o for complex tasks
3. **Handoff Logic**: Define clear handoff conditions between agents
4. **Error Handling**: Implement retry logic for MCP tool calls
5. **Monitoring**: Log all agent interactions and tool calls
6. **Security**: Use Managed Identity for MCP authentication

## Complete Example

See [`/agent-samples/healthcare-multi-agent/`](../../agent-samples/healthcare-multi-agent/) for full implementation.

## Next Steps

- [Copilot Studio Integration](./copilot-studio-integration.md)
- [Pre-built Agent Samples](../../agent-samples/README.md)
- [Custom App Integration](./custom-app-integration.md)
