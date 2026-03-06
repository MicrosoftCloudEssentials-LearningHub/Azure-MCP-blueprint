# Industry Sample Templates - Overview

Costa Rica

[![GitHub](https://img.shields.io/badge/--181717?logo=github&logoColor=ffffff)](https://github.com/)
[brown9804](https://github.com/brown9804)

Last updated: 2026-03-06

----------

> This directory contains pre-configured industry templates for the MCP Blueprint. Each template includes:

- **50,000 sample records** with realistic, industry-specific data
- **10 example queries** demonstrating common use cases  
- **Cosmos DB schema** with partition key strategy
- **Azure AI Search index** with optimized fields
- **MCP tool configurations** tailored to industry needs

## Available Templates

<details>
<summary><strong>Healthcare</strong></summary>

- **File**: `healthcare/`
- **Use Case**: Medical records management, patient care coordination, clinical research
- **Partition Key**: `/patientId`
- **Cosmos DB Container**: `patient-records`  
- **Search Index**: `healthcare-index`

**Data Schema**:
- Patient demographics (name, DOB (date of birth), gender, blood type)
- Medical history and chronic conditions
- Medications and allergies
- Insurance and emergency contacts
- Lab results and vaccinations

**Example Queries**:
- Find patients with specific conditions (diabetes, hypertension)
- Search by blood type for emergency scenarios
- Query patients by physician or insurance provider
- Semantic search for medical conditions
- AI-assisted medical summaries

</details>

<details>
<summary><strong>Retail & E-Commerce</strong></summary>

- **File**: `retail/`
- **Use Case**: Transaction analytics, customer insights, inventory management
- **Partition Key**: `/customerId`
- **Cosmos DB Container**: `transactions`  
- **Search Index**: `retail-index`

**Data Schema**:
- Transaction details (ID, date, amount, status)
- Customer information and loyalty points
- Product items with categories and SKUs
- Shipping address and store location
- Payment method and promotion codes

**Example Queries**:
- High-value transaction analysis (>$500)
- Product category performance tracking
- Customer purchase history retrieval
- Seasonal/promotional campaign effectiveness
- Loyalty program member identification

</details>

<details>
<summary><strong>Financial Services</strong></summary>

- **File**: `finance/`
- **Use Case**: Transaction monitoring, fraud detection, account management
- **Partition Key**: `/accountId`
- **Cosmos DB Container**: `transactions`  
- **Search Index**: `finance-index`

**Data Schema**:
- Transaction details (type, amount, timestamp)
- Account and customer information
- Merchant name and category
- Geographic location data
- Fraud score and risk indicators

**Example Queries**:
- Fraud detection (high fraud scores)
- AML compliance (large withdrawals >$10K)
- International transaction monitoring
- Spending pattern analysis by category
- AI-powered financial advice generation

</details>

<!-- START BADGE -->
<div align="center">
  <img src="https://img.shields.io/badge/Total%20views-1413-limegreen" alt="Total views">
  <p>Refresh Date: 2025-11-03</p>
</div>
<!-- END BADGE -->
