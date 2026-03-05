# Pre-Built AI Agent Samples

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-05

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

</details>

- `healthcare-multi-agent`: an advanced orchestrated multi-agent sample.
- The other industry samples: lightweight CLIs that (a) route to a role and (b) run a search tool via MCP, optionally using `openai_chat_completion` for routing and summaries when available.

<details>
<summary><strong>Patterns</strong></summary>

<details>
<summary><strong>Lightweight HTTP samples (most folders)</strong></summary>

```
User
    ↓
(optional) openai_chat_completion  → role routing
    ↓
search_semantic / search_documents → retrieve relevant items
    ↓
(optional) openai_chat_completion  → concise summary
```

</details>

<details>
<summary><strong>Advanced orchestration (healthcare-multi-agent)</strong></summary>

The healthcare sample demonstrates a richer orchestrator and multi-agent handoffs.

</details>

</details>

<details>
<summary><strong>Key Features</strong></summary>

- **MCP HTTP integration**: Calls `/health`, `/mcp/tools`, and `/mcp/execute`
- **Optional LLM routing**: Uses `openai_chat_completion` when the server exposes it
- **Search-first flow**: Uses `search_semantic` (preferred) or `search_documents`
- **Minimal dependencies**: `requests` + `python-dotenv`

</details>

<details>
<summary><strong>Quick Start</strong></summary>

```bash
cd agent-samples/retail-shopping-assistant
pip install -r requirements.txt
cp .env.example .env
python main.py --demo
```

</details>

<details>
<summary><strong>Sample Walkthroughs</strong></summary>

<details>
<summary><strong>1. Healthcare Multi-Agent</strong></summary>

**Scenario**: Medical records management with compliance checks

**Agents:**
1. **Triage Agent** (gpt-4o-mini) - Routes patient queries
2. **Clinical Data Agent** (gpt-4o-mini) - Queries patient records
3. **Diagnostic Agent** (gpt-4o) - Generates medical insights
4. **Compliance Agent** (gpt-4o-mini) - HIPAA verification
5. **Care Coordinator** (gpt-4o) - Aggregates results

**Example Interaction:**

```python
User: "Find all diabetic patients with recent lab results and generate a clinical summary"

→ Triage Agent (gpt-4o-mini):
  Classifies as: Clinical Research + AI Insights
  Plans sequence: [ClinicalData → Diagnostic → CareCoordinator]

→ Clinical Data Agent (gpt-4o-mini):
  MCP Tool: search_semantic("diabetic patients lab results")
  Result: 94 patients found

→ Diagnostic Agent (gpt-4o):
  MCP Tool: openai_chat_completion("Analyze 94 diabetic patients...")
  Result: Generated clinical summary with trends

→ Care Coordinator (gpt-4o):
  Aggregates: Patient list + AI insights
  Output: Comprehensive report
```

</details>

<details>
<summary><strong>2. Retail Shopping Assistant</strong></summary>

**Agents:**
1. **Cora** (Shopper Agent) - General queries
2. **Product Specialist** - Product details & comparisons
3. **Inventory Manager** - Stock checks
4. **Loyalty Manager** - Points & discounts
5. **Cart Manager** - Cart operations
6. **Recommendation Engine** - AI suggestions

**Model Router Logic:**

```python
    def select_model(self, agent_role: str, task_complexity: str) -> str:
        routing_rules = {
            ("triage", "simple"): "gpt-4o-mini",
        }
        return routing_rules.get((agent_role, task_complexity), "gpt-4o-mini")
```

</details>

<details>
<summary><strong>3. Financial Advisor</strong></summary>

**Agents:**
1. **Account Manager** - Account inquiries
2. **Fraud Detector** - Risk assessment
3. **Investment Advisor** - Financial planning
4. **Transaction Processor** - Payment operations

**Handoff Example:**

```python
# Complex query requiring multiple agents
query = "Show me high-risk transactions and suggest protective measures"

→ Handoff Plan:
  1. FraudDetector: Query transactions with fraud_score > 0.7
  2. InvestmentAdvisor: Analyze risk patterns, generate recommendations
  3. AccountManager: Present results with action items
```

</details>

</details>

<details>
<summary><strong>Implementation Deep Dive</strong></summary>

<details>
<summary><strong>Model Router Implementation</strong></summary>

```python
# agent-samples/common/model_router.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class ModelConfig:
    name: str
    cost_per_1k_tokens: float
    max_tokens: int
    latency_ms: int

class IntelligentModelRouter:
    """
    Selects optimal model based on:
    - Task complexity
    - Cost constraints
    - Latency requirements
    """
    
    MODELS = {
        "gpt-4o": ModelConfig("gpt-4o", 0.015, 16000, 2000),
        "gpt-4o-mini": ModelConfig("gpt-4o-mini", 0.0015, 16000, 500),
    }
    
    def route(
        self,
        task: str,
        agent_role: Literal["routing", "execution", "aggregation"],
        max_cost: float = None,
        max_latency_ms: int = None
    ) -> str:
        """
        Select model based on requirements
        
        Args:
            task: Description of task
            agent_role: Agent type
            max_cost: Maximum acceptable cost per call
            max_latency_ms: Maximum latency in milliseconds
        
        Returns:
            Model deployment name
        """
        # Priority 1: Routing always uses mini
        if agent_role == "routing":
            return "gpt-4o-mini"
        
        # Priority 2: Aggregation uses mini
        if agent_role == "aggregation":
            return "gpt-4o-mini"
        
        # Priority 3: Execution - analyze complexity
        complexity = self._analyze_complexity(task)
        
        if complexity == "simple":
            return "gpt-4o-mini"
        
        # Complex tasks need gpt-4o
        if complexity == "complex":
            # Check constraints
            if max_latency_ms and max_latency_ms < 1000:
                return "gpt-4o-mini"  # Fallback for latency
            if max_cost and max_cost < 0.01:
                return "gpt-4o-mini"  # Fallback for cost
            return "gpt-4o"
        
        return "gpt-4o-mini"  # Default
    
    def _analyze_complexity(self, task: str) -> str:
        """Determine task complexity"""
        complex_keywords = [
            "analyze", "compare", "generate", "summarize",
            "recommend", "diagnose", "predict", "optimize"
        ]
        
        simple_keywords = [
            "find", "search", "list", "show", "get", "query"
        ]
        
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in complex_keywords):
            return "complex"
        if any(kw in task_lower for kw in simple_keywords):
            return "simple"
        
        # Default to simple (cost-effective)
        return "simple"
```

</details>

<details>
<summary><strong>Intent Router Implementation</strong></summary>

```python
# agent-samples/common/intent_router.py
import json
from typing import List, Dict
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

class IntentRouter:
    """
    Routes user requests to appropriate agent sequence
    Uses lightweight gpt-4o-mini for fast, cheap classification
    """
    
    def __init__(self, azure_endpoint: str, api_key: str):
        self.client = ChatCompletionsClient(
            endpoint=azure_endpoint,
            credential=AzureKeyCredential(api_key)
        )
    
    def route(self, user_message: str, available_agents: List[str]) -> Dict:
        """
        Classify intent and plan agent sequence
        
        Returns:
        {
            "primary_intent": "...",
            "agent_sequence": ["agent1", "agent2"],
            "handoffs": [{"from": "agent1", "to": "agent2", "condition": "..."}]
        }
        """
        prompt = f"""Analyze this user request and create an execution plan.

Available Agents:
{json.dumps(available_agents, indent=2)}

User Request:
{user_message}

Provide:
1. Primary intent (single word: search, analyze, compare, create, etc.)
2. Agent sequence (ordered list of agents to execute)
3. Handoff points (when and why to transition between agents)

Respond in JSON format:
{{
    "primary_intent": "...",
    "agent_sequence": ["agent1", "agent2"],
    "handoffs": [
        {{"from": "agent1", "to": "agent2", "condition": "after data retrieval"}},
        ...
    ]
}}
"""
        
        response = self.client.complete(
            model="gpt-4o-mini",  # Fast routing
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1  # Deterministic routing
        )
        
        return json.loads(response.choices[0].message.content)
```

</details>

<details>
<summary><strong>Agent Orchestrator</strong></summary>

```python
# agent-samples/common/orchestrator.py
import asyncio
from typing import List, Dict
from .model_router import IntelligentModelRouter
from .intent_router import IntentRouter

class MultiAgentOrchestrator:
    """
    Orchestrates multi-agent workflows with MCP integration
    """
    
    def __init__(
        self,
        mcp_endpoint: str,
        azure_openai_endpoint: str,
        api_key: str,
        agents: Dict[str, 'Agent']
    ):
        self.mcp_endpoint = mcp_endpoint
        self.model_router = IntelligentModelRouter()
        self.intent_router = IntentRouter(azure_openai_endpoint, api_key)
        self.agents = agents
    
    async def process(self, user_message: str) -> str:
        """
        Main orchestration flow
        
        1. Route intent → determine agent sequence
        2. Execute agents in sequence with handoffs
        3. Aggregate results
        4. Return final response
        """
        # Step 1: Intent routing (gpt-4o-mini)
        routing_plan = self.intent_router.route(
            user_message,
            available_agents=list(self.agents.keys())
        )
        
        print(f"Routing Plan: {routing_plan}")
        
        # Step 2: Execute agent sequence
        results = []
        context = user_message
        
        for agent_name in routing_plan["agent_sequence"]:
            agent = self.agents[agent_name]
            
            # Model selection
            model = self.model_router.route(
                task=context,
                agent_role="execution"
            )
            
            print(f"Executing {agent_name} with {model}")
            
            # Run agent with MCP tools
            result = await agent.execute(
                message=context,
                model=model,
                mcp_endpoint=self.mcp_endpoint
            )
            
            results.append({
                "agent": agent_name,
                "model": model,
                "result": result
            })
            
            # Update context for next agent
            context = self._build_handoff_context(
                original_query=user_message,
                previous_results=results
            )
        
        # Step 3: Aggregate (gpt-4o-mini)
        final_response = await self._aggregate_results(results)
        
        return final_response
    
    def _build_handoff_context(self, original_query: str, previous_results: List[Dict]) -> str:
        """Build context for next agent in sequence"""
        context = f"Original Query: {original_query}\n\n"
        context += "Previous Agent Results:\n"
        for r in previous_results:
            context += f"- {r['agent']}: {r['result']}\n"
        return context
    
    async def _aggregate_results(self, results: List[Dict]) -> str:
        """Combine multi-agent results"""
        # Use gpt-4o-mini for cost-effective aggregation
        # Implementation details...
        pass
```

</details>

</details>

<details>
<summary><strong>Running the Samples</strong></summary>

<details>
<summary><strong>Healthcare Multi-Agent</strong></summary>

```bash
cd agent-samples/healthcare-multi-agent
python main.py

# Example queries:
# "Find all diabetic patients and generate a summary"
# "Search for patients with penicillin allergies"
# "List patients admitted in last 30 days"
```

</details>

<details>
<summary><strong>Retail Shopping Assistant</strong></summary>

```bash
cd agent-samples/retail-shopping-assistant
python main.py

# Example queries:
# "Find electronics under $500"
# "Recommend products for home office"
# "Check my loyalty points and cart"
```

</details>

</details>

<details>
<summary><strong>Customization Guide</strong></summary>

1. **Add New Industry**: Copy sample, modify agent definitions
2. **Adjust Model Routing**: Edit `model_router.py` complexity rules
3. **Add Agents**: Extend agent registry with new specialists
4. **Change MCP Tools**: Update agent tool permissions

</details>

<details>
<summary><strong>Cost Optimization</strong></summary>

| Component | Model | Reason |
|-----------|-------|--------|
| Intent Routing | gpt-4o-mini | Simple classification |
| Data Retrieval | gpt-4o-mini | Structured queries |
| AI Analysis | gpt-4o | Complex reasoning |
| Recommendations | gpt-4o | Quality matters |
| Aggregation | gpt-4o-mini | Formatting output |

**Estimated Cost per Query**: $0.002 - $0.02 (depending on complexity)

</details>

<details>
<summary><strong>Next Steps</strong></summary>

- Explore individual sample READMEs
- [Custom App Integration](../docs/integration-guides/custom-app-integration.md)
- [Azure AI Foundry Integration](../docs/integration-guides/azure-ai-foundry-integration.md)
- [Copilot Studio Integration](../docs/integration-guides/copilot-studio-integration.md)

</details>

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
