# MCP (Model Context Protocol) <br/> Blueprint in Azure – Overview

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-05

----------

> MCP is about `structured behavior, access control, and responsibilities` from the AI's perspective, and we expose it (often via HTTP) using whatever hosting option fits best.

> [!TIP]
> You can think of MCP as:
>
> - **A universal API contract for AI agents.**  
> - **A permissions framework** (AI can only do what's declared).  
> - **A deployment‑agnostic service** (you choose where/how to host it).
> - **An industry-ready demo** with 100K sample records and pre-configured queries

> [!IMPORTANT]
> The deployment process typically takes 15-20 minutes
>
> 1. Adjust [terraform.tfvars](./terraform-infrastructure/terraform.tfvars) values 
> 2. Initialize terraform with `terraform init`. Click here to [understand more about the deployment process](./terraform-infrastructure/README.md)
> 3. Run `terraform apply`, you can also leverage `terraform apply -auto-approve`. 

> [!NOTE]
> Configuration Options: Customize, and choose your hosting service by editing [terraform.tfvars](./terraform-infrastructure/terraform.tfvars).

```hcl
# Choose your industry template
selected_industry = "healthcare"  # Options: healthcare, retail, finance, manufacturing, education, logistics, insurance, hospitality, energy, realestate

# Choose deployment type
mcp_deployment_type = "container-app"  # Options: container-app, function, app-service
```

## What MCP Really Is?

> **MCP (Model Context Protocol)** is a **structured contract** between an AI client (like Copilot Studio or Azure AI Foundry) and an external service (your MCP server).

It defines:

- **What tools exist** (functions the AI can call).  
- **What inputs they require** (schemas).  
- **What outputs they return** (structured JSON).  
- **What resources are available** (read‑only context like docs, schemas, or files).  
- **What prompts are predefined** (templates the AI can use).  

> [!TIP]
> Like a **set of rules and responsibilities** that tell the AI: `"Here’s what you’re allowed to do, here’s how you call it, and here’s what you’ll get back"`

<details>
<summary><b>Rights & Responsibilities </b> (Click to expand)</summary>

> From the AI’s perspective:

- **Rights:** It can only call the tools/resources the MCP server advertises.  
- **Responsibilities:** It must respect the input/output schema and handle errors gracefully.  
- **Boundaries:** The AI cannot `“invent”` new tools, it only uses what the MCP server exposes.  

> From developer perspective (as the server owner):

- You decide **what to expose** (e.g., `getCustomerOrders`, `createInvoice`).  
- You enforce **security and governance** (auth, rate limits, logging).  
- You control **where it’s hosted** (local dev, Azure App Service, Container Apps, Functions, etc.).  

</details>

<details>
<summary><b> Transport Layer </b> (Click to expand)</summary>

- MCP itself is **transport‑agnostic**, it can run over **stdio, WebSockets, or HTTP**.  
- In practice, for Copilot Studio and Azure AI Foundry, you’ll usually expose it as an **HTTP(S) endpoint** so it’s accessible in the cloud.  
- That's why you see multiple hosting options:
  - **Local dev** → run on your laptop, expose via a dev tunnel.  
  - **Azure App Service / Container Apps** → production‑ready, scalable.  
  - **Azure Functions** → serverless, event‑driven.  

</details>

## What gets deployed

Terraform provisions:

1. Provisions Azure resources (Key Vault, Cosmos DB, Azure AI Search, Azure OpenAI/"Foundry", monitoring)
2. Configures app settings and Key Vault-backed secrets for the selected hosting option
3. **If** `mcp_deployment_type = "container-app"` and automation is enabled, builds the MCP server image **in Azure using ACR Tasks** and deploys it to Azure Container Apps
4. Returns the MCP endpoint URL as a Terraform output

<details>
<summary><b> Verify Deployment </b> (Click to expand)</summary>

> After `terraform apply`, use the `mcp_endpoint` output:

```bash
cd terraform-infrastructure
terraform output mcp_endpoint
```

> Then test:

```bash
curl -s "$(terraform output -raw mcp_endpoint)/health"
curl -s "$(terraform output -raw mcp_endpoint)/mcp/tools"
```

> Code samples you can run against the endpoint:

- `samples/mcp-http-client/`
- `agent-samples/`

</details>

## Industry Templates (10 Available)

Each template includes:

- **100,000 realistic sample records**
- **10 pre-configured example queries**
- **Industry-specific MCP tools**
- **Tailored Cosmos DB schema**
- **Optimized AI Search index**

<details>
<summary><b>Healthcare</b> (Click to expand)</summary>

E.g. Medical records management, patient data search, clinical research

**Sample Queries**:

1. Find patients with diabetes
2. Query patients by blood type (O-negative for emergency)
3. Search patients with penicillin allergies
4. List patients by primary physician
5. Semantic search for cardiac conditions
6. Query patients with multiple chronic conditions
7. Find recently admitted patients (last 30 days)
8. AI-assisted medical summary generation
9. Search by insurance provider
10. Find pediatric patients (under 18)

**Sample Data**: Patient records including:

- **Demographics**: Patient ID, name, date of birth, gender, contact information, address
- **Medical Profile**: Blood type, allergies (medications, foods), chronic conditions (diabetes, hypertension, asthma)
- **Clinical Data**: Current medications with dosages, vaccination history, lab results (blood tests, imaging)
- **Care Management**: Primary physician, insurance provider, last visit date, upcoming appointments
- **Emergency Info**: Emergency contact details, advance directives, medical alerts
- **History**: Complete medical history narrative, previous hospitalizations, surgical procedures

</details>

<details>
<summary><b>Retail & E-Commerce</b> (Click to expand)</summary>

Product catalog management, transaction analytics, customer insights

**Sample Queries**:

1. Find high-value transactions (>$500)
2. Search electronics purchases
3. Query recent online orders (last 7 days)
4. Find customer purchase history
5. Semantic search for gift purchases
6. Query by store location (regional analysis)
7. Find failed/cancelled transactions
8. AI product recommendation engine
9. Query loyalty program members
10. Search promotional campaign usage

**Sample Data**: Transaction records including:

- **Transaction Details**: Transaction ID, timestamp, total amount, payment method, status (completed/cancelled/refunded)
- **Products**: Product SKU, name, category, quantity, unit price, discount applied, tax amount
- **Customer Info**: Customer ID, name, email, phone, membership tier (bronze/silver/gold/platinum)
- **Loyalty Program**: Points earned, points redeemed, current balance, tier benefits, rewards history
- **Store Data**: Store location, region, sales associate, checkout lane, purchase channel (online/in-store)
- **Promotions**: Campaign codes used, discount percentages, seasonal offers, bundle deals

</details>

<details>
<summary><b>Financial Services</b> (Click to expand)</summary>

Transaction monitoring, fraud detection, customer account management

**Sample Queries**:

1. Find high-risk transactions (fraud score >0.7)
2. Search large withdrawals (>$10,000 for AML)
3. Query international transactions
4. Find account activity history
5. Semantic search for travel expenses
6. Query by merchant category (spending patterns)
7. Find declined transactions
8. AI financial advice generation
9. Query recent deposits (cash flow analysis)
10. Search by merchant name

**Sample Data**: Financial transaction records including:

- **Transaction Core**: Transaction ID, timestamp, amount, currency, transaction type (debit/credit/withdrawal)
- **Account Info**: Account number, account type (checking/savings/credit), customer ID, balance after transaction
- **Merchant Data**: Merchant name, category (retail/restaurant/travel/gas), MCC code, merchant ID
- **Location**: Transaction location (city, state, country), GPS coordinates, distance from home address
- **Risk Analysis**: Fraud score (0-1), risk flags, anomaly detection alerts, velocity checks
- **Security**: Card last 4 digits, authorization code, CVV verification status, 3D Secure authentication
- **Metadata**: IP address, device fingerprint, transaction description, reference number

</details>

<details>
<summary><b>Manufacturing & IoT</b> (Click to expand)</summary>

Equipment monitoring, predictive maintenance, production optimization

**Sample Queries**:

1. High-risk equipment requiring maintenance (failure score >0.7)
2. Equipment currently in fault status
3. Semantic search for overheating alerts
4. Equipment by facility location
5. Equipment due for maintenance (next 7 days)
6. Low efficiency equipment (quality <80%)
7. CNC machines performance monitoring
8. High power consumption equipment (>500 kW)
9. AI equipment diagnostics and recommendations
10. Recent equipment installations (last 90 days)

**Sample Data**: Equipment monitoring records including:

- **Equipment Profile**: Equipment ID, name, type (CNC/robotic arm/conveyor), manufacturer, model, serial number
- **Location**: Facility name, zone/department, floor level, GPS coordinates, installation date
- **Real-time Telemetry**: Temperature (°C), vibration (mm/s), pressure (PSI), RPM, power consumption (kW)
- **Performance Metrics**: Operating hours, production output, efficiency percentage, defect rate, uptime/downtime
- **Predictive Maintenance**: Failure prediction score (0-1), next maintenance due date, mean time between failures (MTBF)
- **Maintenance History**: Last service date, maintenance type, technician notes, parts replaced, cost
- **Quality Data**: Quality control results, specification compliance, tolerance measurements
- **Alerts**: Active warnings, fault codes, threshold violations, recommended actions

</details>

<details>
<summary><b>Education & Learning</b> (Click to expand)</summary>

Student records, academic analytics, enrollment management

**Sample Queries**:

1. Honor students with high GPA (>=3.5)
2. Students by major (e.g., Computer Science)
3. At-risk students (low attendance or probation)
4. Graduating seniors eligible for commencement
5. Financial aid recipients (active status)
6. Semantic search for course topics (AI, machine learning)
7. Near graduation students (within 15 credits)
8. Students by academic advisor
9. AI academic recommendations and course planning
10. Recently enrolled students (last semester)

**Sample Data**: Student records including:

- **Personal Info**: Student ID, name, email, date of birth, contact phone, home address
- **Academic Profile**: Major/program, minor, academic level (freshman/sophomore/junior/senior/graduate), enrollment date
- **Performance**: Current GPA, cumulative GPA, credits completed, credits in progress, credits required for graduation
- **Course Data**: Current courses enrolled, course history with grades, semester-by-semester transcripts
- **Attendance**: Attendance rate percentage, total absences, tardiness records, participation scores
- **Financial**: Financial aid status (active/pending/none), scholarship amounts, tuition balance, payment plans
- **Support Services**: Academic advisor name, tutoring services used, career counseling sessions
- **Standing**: Academic standing (good standing/probation/suspended), honors/dean's list, graduation date

</details>

<details>
<summary><b>Logistics & Supply Chain</b> (Click to expand)</summary>

Shipment tracking, inventory management, delivery optimization

**Sample Queries**:

1. Delayed shipments (current status)
2. High-value shipments in transit (>$10,000)
3. Customs clearance pending (international shipping)
4. Semantic search for delay reasons (weather, storms)
5. Priority overnight shipments tracking
6. Temperature-controlled cargo (refrigerated)
7. Shipments by carrier (FedEx, UPS, DHL)
8. Hazardous materials shipments (regulatory compliance)
9. AI route optimization recommendations
10. Recently delivered shipments (last 24 hours)

**Sample Data**: Shipment tracking records including:

- **Shipment Identity**: Shipment ID, tracking number, order reference, customer account number
- **Origin/Destination**: Origin facility, city, country, destination facility, delivery address, GPS coordinates
- **Carrier Info**: Carrier name (FedEx/UPS/DHL), service level (standard/express/overnight), vehicle ID
- **Package Details**: Weight (kg), dimensions (LxWxH), volume, declared value, number of packages
- **Status Tracking**: Current status, current location, last scan timestamp, estimated delivery, actual delivery
- **Route Data**: Planned route waypoints, actual route taken, distance traveled, transit time, delays
- **Special Handling**: Temperature-controlled (yes/no), hazardous materials (yes/no), signature required, priority level
- **Customs**: Customs clearance status, duty amount, import/export documents, country of origin
- **Customer**: Customer name, contact phone, delivery instructions, proof of delivery signature

</details>

<details>
<summary><b>Insurance & Claims</b> (Click to expand)</summary>

Claims processing, fraud detection, policy management

**Sample Queries**:

1. High-risk fraud claims (fraud score >0.8)
2. Pending claims awaiting review/approval
3. High-value claims (>$50,000 for special handling)
4. Semantic search for accident types (vehicle collision)
5. Claims by adjuster (workload balancing)
6. Recently filed claims (last 7 days)
7. Denied claims (appeals management)
8. Property damage claims (homeowner policies)
9. AI claims assessment and recommendations
10. Recently settled claims (last 30 days)

**Sample Data**: Insurance claims records including:

- **Claim Identity**: Claim ID, policy number, claim type (auto/property/health/liability), claim number
- **Policyholder**: Name, address, contact phone/email, policy effective dates, premium amount
- **Incident Details**: Incident date, filed date, location (city, state), incident description/narrative
- **Financial**: Claim amount requested, approved amount, deductible, previous payments, outstanding balance
- **Assessment**: Adjuster name, investigation status, repair estimates, medical reports, police reports
- **Fraud Detection**: Fraud risk score (0-1), red flags identified, investigation notes, third-party verification
- **Status Tracking**: Current status (pending/approved/denied/settled), last updated date, settlement date
- **Documentation**: Uploaded photos, damage reports, witness statements, receipts, invoices
- **Resolution**: Resolution type, settlement method, payment date, closing notes, appeal status

</details>

<details>
<summary><b>Hospitality & Tourism</b> (Click to expand)</summary>

Hotel reservations, guest management, service optimization

**Sample Queries**:

1. Today's check-ins (arrival preparation)
2. VIP guests (Platinum loyalty tier)
3. Pending reservations (unconfirmed bookings)
4. Suite reservations (luxury room management)
5. Long-stay guests (>=7 nights)
6. Guests with special requests (accessibility needs)
7. Online booking channel reservations
8. Unpaid reservations (payment follow-up)
9. AI guest concierge (personalized recommendations)
10. High-value reservations (>$2000)

**Sample Data**: Hotel reservation records including:

- **Reservation Details**: Reservation ID, confirmation number, booking date, status (confirmed/pending/cancelled)
- **Guest Information**: Guest name, email, phone, address, nationality, frequent guest number
- **Loyalty Program**: Tier (bronze/silver/gold/platinum), points balance, member since date, tier benefits
- **Stay Details**: Check-in date, check-out date, number of nights, number of guests (adults/children)
- **Room Info**: Room type (standard/deluxe/suite), room number, bed type (king/queen/twin), floor preference
- **Pricing**: Nightly rate, total amount, taxes/fees, discounts applied, deposit paid, balance due
- **Booking Channel**: Booking source (direct/online/OTA/travel agent), rate code, promotional code
- **Special Requests**: Accessibility needs, dietary restrictions, early check-in/late checkout, airport transfer
- **Guest Preferences**: Smoking/non-smoking, high/low floor, quiet room, pillow type, minibar preferences
- **Services**: Spa appointments, restaurant reservations, room service orders, concierge requests

</details>

<details>
<summary><b>Energy & Utilities</b> (Click to expand)</summary>

Smart grid monitoring, energy consumption analytics, utility management

**Sample Queries**:

1. High consumption meters (>1000 kWh)
2. Smart meters with alerts (grid maintenance)
3. Solar generation customers (renewable energy)
4. Power quality issues (voltage/frequency anomalies)
5. Meters by service zone (regional load balancing)
6. Commercial meters (business customers)
7. Recent outage history (last 30 days)
8. High carbon offset accounts (green energy contributors)
9. AI energy optimization (demand-side management)
10. Peak demand periods (capacity planning)

**Sample Data**: Smart meter records including:

- **Meter Identity**: Meter ID, customer account number, meter type (residential/commercial/industrial), serial number
- **Location**: Service address, city, state, zip code, service zone/district, GPS coordinates
- **Consumption Data**: Current reading (kWh), previous reading, consumption period, average daily usage
- **Billing**: Current charges, rate schedule, billing period, payment status, outstanding balance
- **Power Quality**: Voltage (V), frequency (Hz), power factor, harmonics, sag/swell events
- **Demand Metrics**: Peak demand (kW), time of peak usage, load factor, demand charges
- **Renewable Energy**: Solar generation (kWh), net metering credits, feed-in tariff, carbon offset (kg CO2)
- **Outage Data**: Outage history, duration, cause (weather/equipment/scheduled), restoration time
- **Smart Grid**: Real-time load, demand response participation, time-of-use rates, automated controls
- **Alerts**: High usage warnings, power quality alerts, payment reminders, maintenance notifications

</details>

<details>
<summary><b>Real Estate & Property</b> (Click to expand)</summary>

Property listings, sales tracking, portfolio management

**Sample Queries**:

1. Luxury properties (>$1,000,000)
2. Active listings (currently available)
3. Family homes (3+ bedrooms)
4. Properties with pools (amenity search)
5. New construction (built in last 5 years)
6. Properties with offers (competitive bidding)
7. Stale listings (on market >90 days)
8. Condos and townhomes (multi-family properties)
9. AI property recommendations (buyer matching)
10. Price per square foot analysis (investment opportunities)

**Sample Data**: Property listing records including:

- **Property Identity**: Property ID, listing ID, MLS number, parcel ID, address, neighborhood
- **Property Details**: Type (single-family/condo/townhouse/multi-family), bedrooms, bathrooms, square feet, lot size
- **Structure Info**: Year built, stories, garage spaces, basement, attic, architectural style, construction type
- **Pricing**: List price, price per square foot, previous price, price history, assessed value, tax amount
- **Status**: Listing status (active/pending/sold/withdrawn), days on market, listing date, sold date
- **Features**: Pool, fireplace, hardwood floors, updated kitchen, smart home, security system, HOA
- **Utilities**: Heating type, cooling type, water source, sewer type, energy efficiency rating
- **Agent Info**: Listing agent name, contact, brokerage/agency, co-listing agent
- **Showing**: Open house dates, showing instructions, lockbox code, virtual tour URL, photo count
- **Market Data**: Comparable sales, neighborhood trends, school district ratings, walk score, crime statistics
- **Offers**: Number of offers received, offer amounts (if disclosed), contingencies, closing timeline

</details>

## Features

> - Multi-agent orchestration
> - Model router (gpt-4o vs gpt-4o-mini optimization)
> - Intent classification & handoffs
> - Agent specialization patterns
> - Cost optimization strategies

<details>
<summary><b>Option 1: Custom Applications (Developers)</b> (Click to expand)</summary>

Build AI-powered applications with direct MCP SDK integration.

**Perfect for**: Custom web apps, mobile apps, enterprise systems

**Guide**: [Custom App Integration](docs/integration-guides/custom-app-integration.md)

**Features**:

- Python/Node.js SDK examples
- REST API integration
- Flask/FastAPI templates
- Authentication patterns
- Error handling & retries

</details>

<details>
<summary><b>Option 2: Azure AI Foundry (Data Scientists)</b> (Click to expand)</summary>

Create sophisticated multi-agent systems with model routing.

**Perfect for**: Complex AI workflows, multi-agent orchestration, advanced reasoning

**Guide**: [Azure AI Foundry Integration](docs/integration-guides/azure-ai-foundry-integration.md)

**Features**:

- Multi-agent orchestration
- Model router (gpt-4o vs gpt-4o-mini optimization)
- Intent classification & handoffs
- Agent specialization patterns
- Cost optimization strategies

</details>

<details>
<summary><b>Option 3: Copilot Studio (Business Users)</b> (Click to expand)</summary>

Low-code/no-code AI chatbots with enterprise data access.

**Perfect for**: Teams deployment, customer service bots, internal tools

**Guide**: [Copilot Studio Integration](docs/integration-guides/copilot-studio-integration.md)

**Features**:

- Visual topic builder
- OpenAPI connector setup
- Microsoft Teams integration
- Generative answers
- No coding required

</details>

## Pre-Built AI Agent Samples

> Production-ready multi-agent implementations with model routing:

| Sample | Industry | Agents | Complexity |
|--------|----------|---------|------------|
| [Healthcare Multi-Agent](agent-samples/healthcare-multi-agent/) | Healthcare | 5 | Advanced |
| [Retail Shopping Assistant](agent-samples/retail-shopping-assistant/) | Retail | 6 | Advanced |
| [Financial Advisor](agent-samples/financial-advisor/) | Finance | 4 | Intermediate |
| [Manufacturing Monitor](agent-samples/manufacturing-monitor/) | Manufacturing | 3 | Intermediate |
| [Education Student Assistant](agent-samples/education-student-assistant/) | Education | 3 | Intermediate |
| [Logistics Tracker](agent-samples/logistics-tracker/) | Logistics | 3 | Intermediate |
| [Insurance Claims Agent](agent-samples/insurance-claims-agent/) | Insurance | 4 | Intermediate |
| [Hospitality Concierge](agent-samples/hospitality-concierge/) | Hospitality | 3 | Intermediate |
| [Energy Usage Advisor](agent-samples/energy-usage-advisor/) | Energy | 3 | Intermediate |
| [Real Estate Portfolio Manager](agent-samples/realestate-portfolio-manager/) | Real Estate | 3 | Intermediate |

## MCP Tools Available

> Based on your selected industry and enabled services:

| Tool Name                | Description                                 | Category              |
|--------------------------|---------------------------------------------|-----------------------|
| `health_check`           | Server status and diagnostics               | Always Available      |
| `cosmos_create_item`     | Create documents                            | Cosmos DB Tools       |
| `cosmos_query_items`     | SQL-like queries                            | Cosmos DB Tools       |
| `search_documents`       | Full-text search with filters               | Azure AI Search Tools |
| `search_semantic`        | AI-powered semantic search                  | Azure AI Search Tools |
| `openai_chat_completion` | GPT-4o interactions                        | Azure OpenAI Tools    |
| `openai_embeddings`      | Text embeddings                             | Azure OpenAI Tools    |

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
