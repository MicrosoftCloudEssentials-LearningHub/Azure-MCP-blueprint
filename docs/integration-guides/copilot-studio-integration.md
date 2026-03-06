# Microsoft Copilot Studio Integration with MCP Server

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-06

----------
> Connect your MCP Server to Microsoft Copilot Studio to create low-code/no-code AI agents with enterprise data access.

## Overview

Perfect for business users and citizen developers.

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

### Option A (Recommended): MCP onboarding wizard

Copilot Studio supports connecting directly to an MCP server using the **Model Context Protocol** tool type.

1. In your Copilot, go to the **Tools** page
2. Select **Add a tool** → **New tool**
3. Select **Model Context Protocol**
4. Enter:
   - **Server URL**: `https://your-mcp.azurecontainerapps.io/mcp`
   - **Authentication**: None, API key, or OAuth 2.0

Notes:

- Copilot Studio currently supports the **Streamable** transport type for MCP.
- This repo’s MCP server exposes a standards-based Streamable endpoint at `POST /mcp` (JSON-RPC).

### Option B: Custom connector (MCP Streamable)

If you need to manage the connection via Power Apps, create a custom connector using a minimal OpenAPI schema that points to `POST /mcp` and includes the MCP protocol marker.

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

### Example: Healthcare Patient Lookup

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

### Healthcare Topics

#### Medication Lookup

- Trigger: "What medications is patient taking?"
- Action: `cosmos_query_items` → `SELECT c.medications FROM c WHERE c.patientId = '{patientId}'`

#### Allergy Check

- Trigger: "Check patient allergies"
- Action: `search_documents` with filter on allergies field

### Retail Topics

#### Product Search

- Trigger: "Find product"
- Action: `search_documents` → search product catalog

#### Inventory Check

- Trigger: "Check stock availability"
- Action: `cosmos_query_items` → query inventory

### Finance Topics

#### Transaction Search

- Trigger: "Show my transactions"
- Action: `cosmos_query_items` → filter by account

#### Fraud Alert

- Trigger: "Check for suspicious activity"
- Action: `cosmos_query_items` → filter by fraud score > 0.7

</details>

<details>
### Publish to Demo Website

Enable generative responses powered by MCP data:

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

### Publish to Demo Website

1. Go to **Publish** tab
2. Click **Publish**
3. Select **Demo website**
4. Share link: `https://your-copilot.powerapps.com/...`

### Publish to Microsoft Teams

1. Go to **Publish** tab
2. Click **Publish**
3. Select **Microsoft Teams**
4. Configure:
   - Icon
   - Short description
   - Full description
5. **Submit for approval** (if required)
6. **Install in Teams**

### Embed in Website

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

### Azure AD Authentication

1. In **Settings** → **Security**
2. Enable **Authentication**
3. Select **Azure Active Directory**
4. Configure:
   - Tenant ID
   - Client ID
   - Redirect URI

### Row-Level Security

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

<details>
<summary><strong>Healthcare Copilot</strong></summary>

**Topics:**

1. Patient Lookup
2. Medication History
3. Appointment Scheduling
4. Lab Results Inquiry
5. Allergy Checker

**Sample Conversation:**

```
User: Find patients with diabetes
Copilot: [Calls search_documents]
        I found 342 patients with diabetes. Here are the top matches:
        - John Smith (ID: P12345) - Last visit: 2024-01-15
        - Sarah Johnson (ID: P67890) - Last visit: 2024-01-20
        
User: Show me John Smith's medications
Copilot: [Calls cosmos_query_items]
        John Smith is currently taking:
        - Metformin 500mg - Twice daily
        - Lisinopril 10mg - Once daily
        - Aspirin 81mg - Once daily
```

</details>

<details>
<summary><strong>Retail Copilot</strong></summary>

**Topics:**

1. Product Search
2. Inventory Status
3. Order Tracking
4. Loyalty Points
5. Recommendations

</details>

<details>
<summary><strong>Finance Copilot</strong></summary>

**Topics:**

1. Account Balance
2. Transaction History
3. Fraud Alerts
4. Payment Processing
5. Financial Insights

</details>

## Best Practices

1. **Keep topics focused**: One topic = one task
2. **Use fallback**: Configure fallback topic for unhandled queries
3. **Test thoroughly**: Test all conversation paths
4. **Monitor performance**: Review analytics weekly
5. **Iterate**: Update based on user feedback

## Troubleshooting

<details>
<summary><strong>MCP Connector Issues</strong></summary>

**Problem**: Connector fails to connect

**Solution**:

- Verify MCP endpoint URL is public
- Check CORS settings on MCP server
- Test endpoint with Postman first

</details>

<details>
<summary><strong>Tool Call Failures</strong></summary>

**Problem**: Tool returns error

**Solution**:

- Validate argument schema
- Check MCP server logs
- Verify Azure service connectivity

</details>

## Sample Copilot Export

See [`/agent-samples/copilot-studio/`](../../agent-samples/copilot-studio/) for:

- Healthcare Assistant (.zip export)
- Retail Assistant (.zip export)
- Finance Assistant (.zip export)

## Next Steps

- [Custom App Integration](./custom-app-integration.md)
- [Azure AI Foundry Integration](./azure-ai-foundry-integration.md)
- [Pre-built Agent Samples](../../agent-samples/README.md)

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
