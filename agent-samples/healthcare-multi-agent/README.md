# Healthcare Multi-Agent System

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-05

----------
> Production-ready multi-agent AI system for healthcare data management with MCP integration.

## Architecture

```
User Query
    ↓
Triage Agent (gpt-4o-mini) - Intent classification
    ↓
┌─────────────────────────────────────┐
│  Agent Sequence (Handoff Pattern)  │
├─────────────────────────────────────┤
│ Clinical Data Agent                 │ → cosmos_query_items
│   (gpt-4o-mini)                    │ → search_documents
├─────────────────────────────────────┤
│ Diagnostic Agent                    │ → openai_chat_completion
│   (gpt-4o)                         │ → search_semantic
├─────────────────────────────────────┤
│ Compliance Agent                    │ → cosmos_query_items
│   (gpt-4o-mini)                    │   (HIPAA verification)
├─────────────────────────────────────┤
│ Care Coordinator                    │ → Result aggregation
│   (gpt-4o)                         │   (Final summary)
└─────────────────────────────────────┘
```

## Features

- Multi-agent orchestration with intelligent routing
- Model router (gpt-4o-mini vs gpt-4o optimization)
- HIPAA compliance checking
- Real-time patient data access via MCP
- AI-powered medical insights
- Production error handling and logging

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run
python main.py
```

## Configuration

`.env` file:

```env
# MCP Server
MCP_ENDPOINT=https://your-mcp.azurecontainerapps.io

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_API_KEY=your-key
GPT4O_DEPLOYMENT=gpt-4o
GPT4O_MINI_DEPLOYMENT=gpt-4o-mini

# Azure AI Foundry (optional)
AI_FOUNDRY_ENDPOINT=https://your-project.api.azureml.ms
SUBSCRIPTION_ID=your-subscription-id
RESOURCE_GROUP=your-rg
PROJECT_NAME=your-project
```

## Usage Examples

<details>
<summary><strong>Example 1: Patient Search</strong></summary>

```python
from orchestrator import HealthcareOrchestrator

orchestrator = HealthcareOrchestrator()

result = await orchestrator.process(
    "Find all diabetic patients with HbA1c > 7.0 and generate clinical summary"
)

print(result)
```

**Output:**

```
Routing Plan: 
  Primary Intent: clinical_research
  Agent Sequence: [ClinicalData, Diagnostic, CareCoordinator]

ClinicalData Agent (gpt-4o-mini):
  MCP Tool: cosmos_query_items
  Found: 94 patients

Diagnostic Agent (gpt-4o):
  MCP Tool: openai_chat_completion
  Generated insights on 94 patients

Care Coordinator (gpt-4o):
  Aggregated final report

Final Result:
  Clinical Summary - Diabetic Patients with Elevated HbA1c
  
  Total Patients: 94
  Average HbA1c: 8.2%
  
  Key Findings:
  - 46 patients require medication adjustment
  - 24 patients need dietary counseling
  - 16 patients recommended for endocrinology referral
  
  [Full patient list and recommendations attached]
```

</details>

<details>
<summary><strong>Example 2: Medication Safety Check</strong></summary>

```python
result = await orchestrator.process(
    "Check if patient P12345 has any drug interactions with new prescription for Warfarin"
)
```

</details>

<details>
<summary><strong>Example 3: Population Health Analysis</strong></summary>

```python
result = await orchestrator.process(
    "Analyze cardiovascular disease patients and identify high-risk individuals"
)
```

</details>

## Agent Definitions

<details>
<summary><strong>1. Triage Agent</strong></summary>

**Model**: gpt-4o-mini  
**Role**: Route requests to appropriate specialists  
**Tools**: None (classification only)

```python
TriageAgent(
    instructions="""You classify patient-related requests into categories:
    - patient_lookup: Finding specific patients
    - clinical_research: Population analysis
    - medication_safety: Drug interactions/allergies
    - diagnostic_insights: Medical reasoning
    
    Route to appropriate agent sequence."""
)
```

</details>

<details>
<summary><strong>2. Clinical Data Agent</strong></summary>

**Model**: gpt-4o-mini  
**Role**: Query patient records from Cosmos DB and AI Search  
**Tools**: `cosmos_query_items`, `search_documents`, `search_semantic`

```python
ClinicalDataAgent(
    instructions="""You retrieve patient data from medical records.
    
    Use:
    - cosmos_query_items for structured SQL queries
    - search_documents for full-text search
    - search_semantic for AI-powered searches
    
    Always filter for data privacy compliance.""",
    tools=["cosmos_query_items", "search_documents", "search_semantic"]
)
```

</details>

<details>
<summary><strong>3. Diagnostic Agent</strong></summary>

**Model**: gpt-4o (requires advanced reasoning)  
**Role**: Generate medical insights and recommendations  
**Tools**: `openai_chat_completion`

```python
DiagnosticAgent(
    instructions="""You are a medical AI assistant that analyzes patient data
    and generates clinical insights.
    
    Provide:
    - Clinical summaries
    - Risk assessments
    - Treatment recommendations
    - Differential diagnoses
    
    Always cite evidence and note limitations.""",
    tools=["openai_chat_completion"]
)
```

</details>

<details>
<summary><strong>4. Compliance Agent</strong></summary>

**Model**: gpt-4o-mini  
**Role**: Verify HIPAA compliance and data access permissions  
**Tools**: `cosmos_query_items`

```python
ComplianceAgent(
    instructions="""You ensure all data access complies with HIPAA regulations.
    
    Verify:
    - User has permission to access data
    - Minimum necessary standard
    - Audit trail logging
    - De-identification when required""",
    tools=["cosmos_query_items"]
)
```

</details>

<details>
<summary><strong>5. Care Coordinator</strong></summary>

**Model**: gpt-4o  
**Role**: Aggregate multi-agent results into actionable summary  
**Tools**: `openai_chat_completion`

```python
CareCoordinatorAgent(
    instructions="""You synthesize information from multiple agents into
    a comprehensive, actionable care plan.
    
    Provide:
    - Executive summary
    - Prioritized action items
    - Patient communication notes
    - Follow-up recommendations""",
    tools=["openai_chat_completion"]
)
```

</details>

## Model Router Logic

```python
def select_model(agent_role: str, task: str) -> str:
    """
    Optimize costs by using gpt-4o-mini when possible
    """
    # Routing/triage: always mini
    if agent_role == "triage":
        return "gpt-4o-mini"
    
    # Data retrieval: mini is sufficient
    if agent_role == "data_retrieval":
        return "gpt-4o-mini"
    
    # Medical reasoning: needs gpt-4o
    if agent_role == "diagnostic":
        return "gpt-4o"
    
    # Final synthesis: gpt-4o for quality
    if agent_role == "coordinator":
        return "gpt-4o"
    
    # Default: cost-effective
    return "gpt-4o-mini"
```

## Cost Analysis

**Typical Query Cost Breakdown:**

| Agent | Model | Tokens | Cost |
|-------|-------|--------|------|
| Triage | gpt-4o-mini | 500 | $0.0008 |
| Clinical Data | gpt-4o-mini | 2000 | $0.003 |
| Diagnostic | gpt-4o | 3000 | $0.045 |
| Compliance | gpt-4o-mini | 800 | $0.0012 |
| Coordinator | gpt-4o | 2500 | $0.0375 |
| **TOTAL** | - | - | **$0.087** |

## Error Handling

```python
try:
    result = await orchestrator.process(query)
except MCPToolError as e:
    logger.error(f"MCP tool failed: {e}")
    # Retry with exponential backoff
except AgentExecutionError as e:
    logger.error(f"Agent failed: {e}")
    # Fall back to simpler agent
except ComplianceViolation as e:
    logger.critical(f"HIPAA violation: {e}")
    # Alert security team
```

## Monitoring

```python
# Logs structured events
{
    "timestamp": "2024-02-02T10:30:00Z",
    "query": "Find diabetic patients",
    "routing_plan": {...},
    "agents_executed": ["ClinicalData", "Diagnostic", "Coordinator"],
    "total_cost": 0.087,
    "latency_ms": 3500,
    "success": true
}
```

## Deployment

<details>
<summary><strong>Local Development</strong></summary>

```bash
python main.py --interactive
```

</details>

<details>
<summary><strong>Azure Container Apps</strong></summary>

```bash
# Build and push
docker build -t healthcare-agent .
az acr build --registry your-acr --image healthcare-agent:latest .

# Deploy
az containerapp create \
    --name healthcare-agent \
    --resource-group your-rg \
    --image your-acr.azurecr.io/healthcare-agent:latest \
    --environment your-env
```

</details>

<details>
<summary><strong>Azure AI Foundry</strong></summary>

```python
# Deploy as Foundry agent
ai_client.agents.create_agent(
    model="gpt-4o",
    name="Healthcare Multi-Agent Orchestrator",
    instructions=orchestrator.get_system_prompt(),
    tools=orchestrator.get_tool_definitions()
)
```

</details>

## Next Steps

- [Retail Shopping Assistant](../retail-shopping-assistant/)
- [Financial Advisor](../financial-advisor/)
- [Integration Guides](../../docs/integration-guides/)

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
