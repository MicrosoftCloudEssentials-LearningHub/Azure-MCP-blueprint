# =============================================================================
# AZURE MCP BLUEPRINT - USER CONFIGURATION
# =============================================================================
# Zero-touch enterprise deployment - just run:
#   terraform init
#   terraform apply -auto-approve
# Deployment takes 20-30 minutes and sets up everything automatically including:
# - MCP Server with Container Registry
# - 50GB enterprise sample data
# - Microsoft Foundry, Cosmos DB, Azure Search
# - Monitoring, security, and scaling

# =============================================================================
# CORE AZURE SETTINGS
# =============================================================================
resource_group_name = "RG-mcp-blueprintx10"
location            = "East US 2"
name_prefix         = "mcp"
environment         = "poc" # poc -> mvp -> dev -> staging -> prod

# Optional: Specify user principal ID (defaults to current Azure CLI user)
# user_principal_id = "00000000-0000-0000-0000-000000000000"

# =============================================================================
# INDUSTRY TEMPLATE SELECTION
# =============================================================================
# Choose your industry template
# Each comes with 100K sample records and 10 pre-configured queries
selected_industry = "healthcare"

# =============================================================================
# MCP DEPLOYMENT CONFIGURATION
# =============================================================================
# Choose your deployment type:
# - "container-app" (Recommended) - Azure Container Apps, serverless containers
# - "function"                   - Azure Functions, event-driven serverless
# - "app-service"                - Azure App Service, traditional web apps
# - "local"                      - Local development only
mcp_deployment_type = "container-app"

# MCP tools to enable (available: search, cosmos, foundry, monitoring)
enable_mcp_tools = ["search", "cosmos", "foundry", "monitoring"]

# =============================================================================
# FEATURE TOGGLES
# =============================================================================
enable_monitoring           = true # Application Insights, Log Analytics
enable_validation           = true # Post-deployment validation
enable_dev_tools            = true # Development and debugging tools
enable_automated_deployment = true # Automated MCP server deployment
enable_cli_integration      = false # Legacy flag (CLI removed); keep disabled

# =============================================================================
# ENTERPRISE FEATURES
# =============================================================================
# Container Registry with automated builds
enable_container_registry = true      # Azure Container Registry with ACR Tasks
enable_geo_replication    = true      # Multi-region registry
acr_sku                   = "Premium" # Premium tier for enterprise features

# Sample data for testing and demonstration
enable_sample_data  = false # Disable to avoid storage account key auth issues
sample_data_size_gb = 50    # 50GB sample dataset
sample_data_types   = ["documents", "customer-data", "product-catalog", "chat-history", "embeddings"]

# Monitoring and observability
enable_security_center = false # Security scanning and compliance

# =============================================================================
# AI SERVICES CONFIGURATION
# =============================================================================
# Microsoft Foundry location (must support Foundry service)
foundry_location = "East US"

# Azure Search service tier (enterprise scale)
# NOTE: Some regions can temporarily run out of capacity for certain SKUs.
# If you see `ResourcesForSkuUnavailable` (e.g., Standard in East US 2), either:
# - switch to `basic`, or
# - set `search_location` to a different region (e.g., "East US").
search_sku             = "standard" # Standard tier for enterprise
search_location        = null       # Optional override, e.g. "East US"
search_replica_count   = 2          # High availability
search_partition_count = 2          # Performance scaling

# Cosmos DB configuration (enterprise scale)
cosmos_consistency_level = "Session"
cosmos_throughput        = 4000 # RU/s for enterprise workloads

# Foundry AI configuration
foundry_deployment_models = [
  {
    name    = "gpt-4o"
    version = "2024-08-06"
    sku     = "Standard"
  },
  {
    name    = "text-embedding-ada-002"
    version = "2"
    sku     = "Standard"
  },
  {
    name    = "gpt-35-turbo"
    version = "0125"
    sku     = "Standard"
  }
]

# =============================================================================
# COMPUTE RESOURCES
# =============================================================================
# Container Apps configuration (enterprise scale)
container_cpu          = 1.0   # Higher CPU for enterprise workloads
container_memory       = "2Gi" # More memory for large datasets
container_min_replicas = 1     # Always-on
container_max_replicas = 20    # Scale for enterprise load

# App Service plan SKU (if using app-service deployment)
app_service_sku = "B1" # B1, S1, P1v2, etc.

# =============================================================================
# SECURITY & NETWORKING
# =============================================================================
enable_managed_identity  = true
enable_private_endpoints = false  # Disabled for local development
enable_vnet_integration  = false  # Keep false for simplicity
key_vault_network_access = "Allow" # Allow public access for deployment

# CORS configuration
allowed_origins = ["https://localhost:3000", "https://*.azurewebsites.net"]

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================
storage_replication_type = "GRS" # Geo-redundant storage for enterprise

# =============================================================================
# MONITORING & DIAGNOSTICS
# =============================================================================
log_retention_days         = 30
enable_diagnostic_settings = true

# Optional: Email for alerts (leave empty to disable)
alert_email = ""


# =============================================================================
# ADVANCED FEATURES (Optional)
# =============================================================================
enable_multi_region      = false # Multi-region deployment
enable_backup            = false # Backup for stateful services
enable_disaster_recovery = false # Disaster recovery
enable_auto_scaling      = true  # Auto-scaling capabilities

# =============================================================================
# DEPLOYMENT SETTINGS
# =============================================================================
deployment_timeout = 30 # Extended timeout for enterprise deployment
mcp_image_tag      = "latest"