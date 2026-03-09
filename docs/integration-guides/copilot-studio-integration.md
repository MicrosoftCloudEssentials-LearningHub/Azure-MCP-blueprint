# Microsoft Copilot Studio Integration <br/> with MCP Server - Overview

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-06

----------
> Connect your MCP Server to Microsoft Copilot Studio to create low-code/no-code AI agents with enterprise data access. `Perfect for business users and citizen developers.`

<details>
<summary><strong>Table of contents</strong></summary>

- [What You'll Build](#what-youll-build)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Advanced Features](#advanced-features)
- [Industry Templates](#industry-templates)
- [Sample Copilot Export](#sample-copilot-export)

</details>

## What You'll Build

- **Custom Copilot** with MCP tool integration
- **Conversational AI** for domain-specific tasks
- **Enterprise Chatbot** with Azure service access
- **Teams/Web deployment** ready

## Prerequisites

- Microsoft Copilot Studio license
- MCP Server deployed with public endpoint
- Microsoft Teams (optional, for Teams deployment)

## Quick Start

<details>
<summary><strong>Step 1: Access Copilot Studio</strong></summary>

1. Navigate to [Copilot Studio](https://copilotstudio.microsoft.com/)
2. Sign in with your Microsoft account
3. Select your environment (or create new)

</details>

<details>
<summary><strong>Step 2: Create New Copilot</strong></summary>

1. Click **Create** → **New Copilot**
2. Choose **From Blank**
3. Enter details:
   - **Name**: Healthcare Assistant (or your industry)
   - **Description**: AI assistant with MCP-powered data access
   - **Language**: English
4. Click **Create**

</details>

<details>
<summary><strong>Step 3: Add MCP Server as Tool</strong></summary>

> Option A (Recommended): MCP onboarding wizard:Copilot Studio supports connecting directly to an MCP server using the **Model Context Protocol** tool type.

1. In your Copilot, go to the **Tools** page
2. Select **Add a tool** → **New tool**
3. Select **Model Context Protocol**
4. Enter:
   - **Server URL**: `https://your-mcp.azurecontainerapps.io/mcp`
   - **Authentication**: None, API key, or OAuth 2.0

> [!NOTE]
> - Copilot Studio currently supports the **Streamable** transport type for MCP.
> - This repo’s MCP server exposes a standards-based Streamable endpoint at `POST /mcp` (JSON-RPC).

> Option B: Custom connector (MCP Streamable): If you need to manage the connection via Power Apps, create a custom connector using a minimal OpenAPI schema that points to `POST /mcp` and includes the MCP protocol marker.

```yaml
swagger: '2.0'
info:
  title: Azure MCP Blueprint
  description: MCP Streamable endpoint for Copilot Studio
  version: 1.0.0
host: your-mcp.azurecontainerapps.io
basePath: /
schemes:
  - https
paths:
  /mcp:
    post:
      summary: MCP Streamable endpoint
      x-ms-agentic-protocol: mcp-streamable-1.0
      operationId: InvokeMCP
      responses:
        '200':
          description: JSON-RPC response
        '202':
          description: Accepted (notifications / responses)
```

</details>

<details>
<summary><strong>Step 4: Configure Topics with MCP Tools</strong></summary>

> Example: Healthcare Patient Lookup

1. Go to **Topics** tab
2. Click **+ New topic** → **From blank**
3. Name: "Patient Lookup"
4. Add trigger phrases:
   - "Find patient"
   - "Search for patient records"
   - "Show me patient information"

**Conversation Flow:**

```
Node 1: Trigger - Patient lookup request detected

Node 2: Question - Get patient details
  - "What is the patient name or ID you're looking for?"
  - Save response as: patientQuery

Node 3: Action - Call MCP Tool
  - Tool: `search_documents`
  - Arguments:
    {
      "query": "{patientQuery}",
      "top": 5
    }
  - Save response as: searchResults

Node 4: Message - Display results
  - "I found the following patient records:"
  - {searchResults.content.results[0].firstName} {searchResults.content.results[0].lastName}
  - Patient ID: {searchResults.content.results[0].patientId}
  - Last Visit: {searchResults.content.results[0].lastVisitDate}

Node 5: Question - Follow-up
  - "Would you like more details on any patient?"
  - Options: Yes / No
```

5. **Save topic**
6. **Test in Test Copilot pane**

</details>

<details>
<summary><strong>Step 5: Industry-Specific Topics</strong></summary>

> Example topic mappings (Industry → Trigger → MCP tool call)

| Industry | Topic | Trigger phrase examples | MCP tool | Example action (tool → parameters/query) |
|---|---|---|---|---|
| Healthcare | Medication Lookup | “What medications is patient taking?”, “Show meds for {patientId}” | `cosmos_query_items` | `cosmos_query_items` → `SELECT c.medications FROM c WHERE c.patientId = '{patientId}'` |
| Healthcare | Allergy Check | “Check patient allergies”, “Is {patientId} allergic to {allergy}?” | `search_documents` | `search_documents` → `{"query":"","top":10,"filter":"allergies/any(a: a eq '{allergy}')"}` |
| Retail | Product Search | “Find product”, “Search {product}”, “Products under $50” | `search_documents` | `search_documents` → `{"query":"{productQuery}","top":10,"filter":null}` |
| Retail | Inventory Check | “Check stock availability”, “Is SKU {sku} in stock?” | `cosmos_query_items` | `cosmos_query_items` → `SELECT * FROM c WHERE c.sku = '{sku}'` |
| Finance | Transaction Search | “Show my transactions”, “Transactions last 30 days” | `cosmos_query_items` | `cosmos_query_items` → `SELECT * FROM c WHERE c.accountId = '{accountId}' ORDER BY c.timestamp DESC` |
| Finance | Fraud Alert | “Check for suspicious activity”, “High fraud scores” | `cosmos_query_items` | `cosmos_query_items` → `SELECT * FROM c WHERE c.fraudScore > 0.7 ORDER BY c.fraudScore DESC` |

</details>

<details>
<summary><strong>Step 6: Generative Answers (Optional)</strong></summary>

> Publish to Demo Website: Enable generative responses powered by MCP data.

1. Go to **Settings** → **Generative AI**
2. Enable **Generative answers**
3. Configure:
   - **Data source**: MCP Server (via connector)
   - **Moderation**: Medium
   - **Content safety**: Enabled

4. Create **Generative Topic**:

```
System Instructions:
You are a {industry} AI assistant with access to real-time data via MCP tools.

Available Tools:
- search_documents: Full-text search
- cosmos_query_items: SQL-like queries
- search_semantic: AI-powered semantic search
- openai_chat_completion: Generate insights

When users ask questions:
1. Identify the appropriate MCP tool
2. Call the tool with correct parameters
3. Interpret results clearly
4. Provide helpful, accurate responses

Always maintain data privacy and security.
```

</details>

<details>
<summary><strong>Step 7: Test Your Copilot</strong></summary>

1. Click **Test your copilot** (top right)
2. Try example queries:
   - "Find all diabetic patients"
   - "Search for products under $50"
   - "Show high-value transactions"

3. Verify MCP tool calls in **Test** pane

</details>

<details>
<summary><strong>Step 8: Publish</strong></summary>

> Publish to Demo Website: 

1. Go to **Publish** tab
2. Click **Publish**
3. Select **Demo website**
4. Share link: `https://your-copilot.powerapps.com/...`

> Publish to Microsoft Teams:

1. Go to **Publish** tab
2. Click **Publish**
3. Select **Microsoft Teams**
4. Configure:
   - Icon
   - Short description
   - Full description
5. **Submit for approval** (if required)
6. **Install in Teams**

> Embed in Website: 

```html
<!DOCTYPE html>
<html>
<head>
    <title>Healthcare Assistant</title>
</head>
<body>
    <h1>Healthcare AI Assistant</h1>
    
    <!-- Copilot Studio Embed Code -->
    <div id="copilot-container"></div>
    <script src="https://cdn.botframework.com/botframework-webchat/latest/webchat.js"></script>
    <script>
        window.WebChat.renderWebChat({
            directLine: window.WebChat.createDirectLine({
                secret: 'YOUR_DIRECT_LINE_SECRET'
            }),
            userID: 'user-' + Date.now(),
            username: 'User',
            locale: 'en-US',
            styleOptions: {
                botAvatarImage: 'https://your-logo.png',
                botAvatarInitials: 'HA',
                userAvatarImage: '',
                userAvatarInitials: 'You',
                primaryFont: 'Segoe UI, sans-serif'
            }
        }, document.getElementById('copilot-container'));
    </script>
</body>
</html>
```

</details>

## Advanced Features

<details>
<summary><strong>Authentication & Security</strong></summary>

> Azure AD Authentication: 

1. In **Settings** → **Security**
2. Enable **Authentication**
3. Select **Azure Active Directory**
4. Configure:
   - Tenant ID
   - Client ID
   - Redirect URI

> Row-Level Security:

```yaml
# In MCP Server, implement user-scoped queries
def get_user_data(user_id: str, query: str):
    # Add user filter to all queries
    scoped_query = f"{query} AND c.ownerId = '{user_id}'"
    return cosmos_client.query(scoped_query)
```

</details>

<details>
<summary><strong>Analytics & Monitoring</strong></summary>

1. Go to **Analytics** tab
2. View metrics:
   - Total sessions
   - Resolution rate
   - Escalation rate
   - MCP tool usage

3. Export logs for analysis

</details>

<details>
<summary><strong>Multi-Language Support</strong></summary>

1. **Settings** → **Languages**
2. Add languages:
   - Spanish
   - French
   - German
3. MCP server returns localized results

</details>

## Industry Templates

> Each row maps a user intent to a specific MCP tool call, what to pass, and what to show.

| Industry | Topics (deep dive) | Trigger phrases (examples) | MCP tools used | Example calls (shapes) | What to display back | Notes (design + safety) |
|---|---|---|---|---|---|---|
| Healthcare | - Patient Lookup<br/>- Medication History<br/>- Appointment Scheduling<br/>- Lab Results Inquiry<br/>- Allergy Checker | - “Find patient”, “Find patients with diabetes”<br/>- “Show medications for {patientId}”<br/>- “Book with Dr. Smith next week”<br/>- “Show latest labs / HbA1c”<br/>- “Is {patientId} allergic to penicillin?” | - `search_documents`<br/>- `cosmos_query_items`<br/>- `search_semantic`<br/>- `openai_chat_completion` | - Search: `{"query":"diabetes","top":5,"filter":null}`<br/>- Cosmos: `{"query":"SELECT c.medications FROM c WHERE c.patientId = '{patientId}'"}`<br/>- Semantic: `{"query":"latest lab results HbA1c for {patientId}","top":5}`<br/>- Foundry: `{"messages":[...],"model":"gpt-4o"}` | - Patient match list (name, patientId, lastVisitDate)<br/>- Medication/allergy fields only (minimal data)<br/>- Lab snippets + dates<br/>- Clarifying questions for scheduling | - Prefer patientId over names for precision<br/>- Keep outputs descriptive (not prescriptive medical advice)<br/>- Avoid returning entire patient record unless required |
| Retail | - Product Search<br/>- Inventory Status<br/>- Order Tracking<br/>- Loyalty Points<br/>- Recommendations | - “Search headphones”, “Laptops under $1000”<br/>- “Is SKU {sku} in stock?”<br/>- “Track order {orderId}”<br/>- “My loyalty points”<br/>- “Recommend products like {productName}” | - `search_documents`<br/>- `cosmos_query_items`<br/>- `openai_chat_completion` | - Search: `{"query":"headphones","top":10,"filter":null}`<br/>- Cosmos: `{"query":"SELECT * FROM c WHERE c.transactionId = '{orderId}'"}`<br/>- Foundry: `{"messages":[...],"model":"gpt-4o"}` | - Product list (name/category/price if indexed)<br/>- Availability/stock fields (if present)<br/>- Order status + last update<br/>- Loyalty point balance<br/>- Short recommendation list | - Confirm identifier formats (orderId vs transactionId)<br/>- For recommendations: Search first (grounding) then summarize with Foundry<br/>- Minimize PII (use customerId, not email) |
| Finance | - Account Balance<br/>- Transaction History<br/>- Fraud Alerts<br/>- Payment Processing<br/>- Financial Insights | - “Balance for account {accountId}”<br/>- “Transactions last 30 days”<br/>- “Suspicious activity?”<br/>- “Pay my bill / send $50”<br/>- “Spending insights” | - `cosmos_query_items`<br/>- `openai_chat_completion` | - Cosmos: `{"query":"SELECT * FROM c WHERE c.accountId = '{accountId}' AND c.timestamp >= '{isoDate}' ORDER BY c.timestamp DESC"}`<br/>- Fraud: `{"query":"SELECT * FROM c WHERE c.fraudScore > 0.7 ORDER BY c.fraudScore DESC"}`<br/>- Foundry: `{"messages":[...],"model":"gpt-4o"}` | - Balance + currency (if stored)<br/>- Recent transactions (amount/merchant/time)<br/>- Flagged transactions + fraudScore<br/>- Confirmation step for payments<br/>- Category insights + next steps | - Present fraud as a signal, not a final determination<br/>- Only simulate payments unless you have a real backend<br/>- Best pattern for insights: Cosmos query → Foundry summary |

> [!IMPORTANT]
> Template data is synthetic but can contain **PII-like fields** (names/emails/phones/addresses; DOB in some industries). Avoid logging tool outputs and apply least-privilege access.

| Operations area | Symptom / goal | What to check | Fix |
|---|---|---|---|
| Topic design | Topic tries to do too much | One topic is handling multiple intents | Split into multiple topics; keep each topic to a single task. |
| Fallback | Users ask unhandled questions | No fallback topic / poor trigger phrases | Add a fallback topic; expand trigger phrases; route to a “help me choose” question. |
| Testing | Tools don’t fire in Test pane | Action node not reached; variables not set | Add explicit questions to capture inputs; verify the tool name and JSON shape; save tool response into a variable. |
| Monitoring | Need usage + quality visibility | No review cadence | Review Copilot Studio analytics weekly; correlate with MCP server logs (App Insights / platform logs). |
| MCP connector | Connector fails to connect | Endpoint not public; auth mismatch; CORS; wrong URL | Verify the MCP URL is reachable and points to `/mcp`; validate auth settings (none/API key/OAuth); configure allowed origins if enforced by the server. |
| Tool call failures | Tool returns an error | Bad arguments; missing dependent Azure service config | Validate against the tool’s input schema; check MCP server logs; verify Cosmos/Search/Foundry endpoints and credentials/managed identity permissions. |

## Sample Copilot Export

> See [`/agent-samples/copilot-studio/`](../../agent-samples/copilot-studio/) for:
> - Healthcare Assistant (.zip export)
> - Retail Assistant (.zip export)
> - Finance Assistant (.zip export)

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
