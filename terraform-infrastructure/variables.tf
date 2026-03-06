# -----------------------------------------------------------------------------
# AZURE MCP BLUEPRINT - TERRAFORM VARIABLES
# -----------------------------------------------------------------------------

# Core Azure Configuration
variable "resource_group_name" {
  type        = string
  description = "Name of the Azure resource group"
}

variable "location" {
  type        = string
  description = "Azure region for resource deployment"
  default     = "East US 2"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource naming"
  default     = "mcp"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod, poc)"
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod", "poc"], var.environment)
    error_message = "Environment must be dev, staging, prod, or poc."
  }
}

# -----------------------------------------------------------------------------
# INDUSTRY TEMPLATE CONFIGURATION
# -----------------------------------------------------------------------------

variable "selected_industry" {
  type        = string
  description = "Industry template to deploy (healthcare, retail, finance, manufacturing, education, logistics, insurance, hospitality, energy, realestate)"
  default     = "healthcare"

  validation {
    condition = contains([
      "healthcare",
      "retail",
      "finance",
      "manufacturing",
      "education",
      "logistics",
      "insurance",
      "hospitality",
      "energy",
      "realestate",
    ], var.selected_industry)
    error_message = "Industry must be one of: healthcare, retail, finance, manufacturing, education, logistics, insurance, hospitality, energy, realestate."
  }
}

# -----------------------------------------------------------------------------
# ENTERPRISE SAMPLE DATA CONFIGURATION
# -----------------------------------------------------------------------------

variable "enable_sample_data" {
  type        = bool
  description = "Whether to deploy enterprise sample data"
  default     = true
}

variable "sample_data_size_gb" {
  type        = number
  description = "Target sample data size in GB for enterprise demo scenarios. Note: current automation uploads a template-driven record count and does not guarantee an on-disk size (e.g., 50GB)."
  default     = 50

  validation {
    condition     = var.sample_data_size_gb >= 1 && var.sample_data_size_gb <= 1000
    error_message = "Sample data size must be between 1 and 1000 GB."
  }
}

variable "sample_data_types" {
  type        = list(string)
  description = "Types of sample data to generate"
  default     = ["documents", "customer-data", "product-catalog", "chat-history", "embeddings"]

  validation {
    condition = alltrue([
      for data_type in var.sample_data_types : contains([
        "documents",
        "customer-data",
        "product-catalog",
        "chat-history",
        "embeddings",
        "audit-logs"
      ], data_type)
    ])
    error_message = "Invalid sample data type. Available: documents, customer-data, product-catalog, chat-history, embeddings, audit-logs."
  }
}

variable "enterprise_scale_config" {
  type = object({
    enable_auto_scaling    = bool
    max_storage_gb         = number
    enable_geo_replication = bool
    backup_retention_days  = number
  })
  description = "Enterprise scale configuration"
  default = {
    enable_auto_scaling    = true
    max_storage_gb         = 1000
    enable_geo_replication = true
    backup_retention_days  = 30
  }
}

# -----------------------------------------------------------------------------
# AUTOMATION AND CI/CD CONFIGURATION
# -----------------------------------------------------------------------------

variable "enable_container_registry" {
  type        = bool
  description = "Whether to deploy Azure Container Registry for MCP server images"
  default     = true
}

variable "enable_automated_builds" {
  type        = bool
  description = "Whether to enable automated container builds"
  default     = true
}

variable "github_repo_url" {
  type        = string
  description = "GitHub repository URL for CI/CD automation"
  default     = "https://github.com/MicrosoftCloudEssentials-LearningHub/Azure-MCP-blueprint"
}

variable "enable_health_checks" {
  type        = bool
  description = "Whether to enable comprehensive health checks"
  default     = true
}

variable "notification_email" {
  type        = string
  description = "Email for deployment notifications and alerts"
  default     = ""
}

# -----------------------------------------------------------------------------
# MCP DEPLOYMENT CONFIGURATION
# -----------------------------------------------------------------------------

variable "mcp_deployment_type" {
  type        = string
  description = "MCP deployment type: local, container-app, function, app-service"
  default     = "container-app"

  validation {
    condition = contains([
      "local",
      "container-app",
      "function",
      "app-service"
    ], var.mcp_deployment_type)
    error_message = "Invalid deployment type. Must be: local, container-app, function, or app-service."
  }
}

variable "enable_mcp_tools" {
  type        = list(string)
  description = "List of MCP tools to enable"
  default     = ["search", "cosmos", "foundry", "monitoring"]

  validation {
    condition = alltrue([
      for tool in var.enable_mcp_tools : contains([
        "search",
        "cosmos",
        "foundry",
        "monitoring"
      ], tool)
    ])
    error_message = "Invalid tool specified. Available tools: search, cosmos, foundry, monitoring."
  }
}

variable "enable_monitoring" {
  type        = bool
  description = "Whether to deploy monitoring and observability components"
  default     = true
}

variable "enable_validation" {
  type        = bool
  description = "Whether to run post-deployment validation"
  default     = true
}

variable "enable_dev_tools" {
  type        = bool
  description = "Whether to enable development and debugging tools"
  default     = false
}

# -----------------------------------------------------------------------------
# AI SERVICES CONFIGURATION
# -----------------------------------------------------------------------------

variable "foundry_location" {
  type        = string
  description = "Azure region for Microsoft Foundry service deployment"
  default     = "East US"

  validation {
    condition = contains([
      "East US",
      "East US 2",
      "South Central US",
      "West Europe",
      "France Central",
      "UK South",
      "Australia East",
      "Japan East",
      "Sweden Central"
    ], var.foundry_location)
    error_message = "Microsoft Foundry service is not available in the specified region."
  }
}

variable "foundry_models" {
  type = list(object({
    name    = string
    version = string
    sku     = string
  }))
  description = "Microsoft Foundry models to deploy"
  default = [
    {
      name    = "gpt-4o"
      version = "2024-08-06"
      sku     = "Standard"
    },
    {
      name    = "text-embedding-ada-002"
      version = "2"
      sku     = "Standard"
    }
  ]
}

variable "search_sku" {
  type        = string
  description = "Azure Search service SKU"
  default     = "basic"

  validation {
    condition     = contains(["free", "basic", "standard", "standard2", "standard3"], var.search_sku)
    error_message = "Invalid Search SKU. Must be: free, basic, standard, standard2, or standard3."
  }
}

variable "search_location" {
  type        = string
  description = "Optional region override for Azure AI Search (defaults to the resource group location). Useful when a SKU is unavailable in the primary region."
  default     = null
}

variable "cosmos_consistency_level" {
  type        = string
  description = "Cosmos DB consistency level"
  default     = "Session"

  validation {
    condition = contains([
      "BoundedStaleness",
      "Eventual",
      "Session",
      "Strong",
      "ConsistentPrefix"
    ], var.cosmos_consistency_level)
    error_message = "Invalid consistency level."
  }
}

# -----------------------------------------------------------------------------
# COMPUTE CONFIGURATION
# -----------------------------------------------------------------------------

variable "container_cpu" {
  type        = number
  description = "CPU allocation for container deployments"
  default     = 0.25
}

variable "container_memory" {
  type        = string
  description = "Memory allocation for container deployments"
  default     = "0.5Gi"
}

variable "min_replicas" {
  type        = number
  description = "Minimum number of replicas for auto-scaling"
  default     = 0
}

variable "max_replicas" {
  type        = number
  description = "Maximum number of replicas for auto-scaling"
  default     = 10
}

variable "app_service_sku" {
  type        = string
  description = "App Service plan SKU"
  default     = "B1"

  validation {
    condition = contains([
      "F1", "D1",            # Free and Shared
      "B1", "B2", "B3",      # Basic
      "S1", "S2", "S3",      # Standard
      "P1", "P2", "P3",      # Premium
      "P1v2", "P2v2", "P3v2" # Premium v2
    ], var.app_service_sku)
    error_message = "Invalid App Service SKU."
  }
}

# -----------------------------------------------------------------------------
# NETWORKING CONFIGURATION
# -----------------------------------------------------------------------------

variable "enable_private_endpoints" {
  type        = bool
  description = "Whether to enable private endpoints for secure connectivity"
  default     = false
}

variable "container_min_replicas" {
  type        = number
  description = "Minimum number of replicas for container scaling"
  default     = 0
}

variable "foundry_deployment_models" {
  type = list(object({
    name    = string
    version = string
    sku     = string
  }))
  description = "Microsoft Foundry models to deploy"
  default = [
    {
      name    = "gpt-4o"
      version = "2024-08-06"
      sku     = "Standard"
    },
    {
      name    = "text-embedding-ada-002"
      version = "2"
      sku     = "Standard"
    }
  ]
}

variable "allowed_origins" {
  type        = list(string)
  description = "CORS allowed origins"
  default     = ["*"]
}

variable "enable_vnet_integration" {
  type        = bool
  description = "Whether to enable VNet integration"
  default     = false
}

# -----------------------------------------------------------------------------
# SECURITY CONFIGURATION
# -----------------------------------------------------------------------------

variable "enable_key_vault_purge_protection" {
  type        = bool
  description = "Whether to enable Key Vault purge protection (recommended for production)"
  default     = false
}

variable "key_vault_network_access" {
  type        = string
  description = "Key Vault network access policy"
  default     = "Allow"

  validation {
    condition     = contains(["Allow", "Deny"], var.key_vault_network_access)
    error_message = "Key Vault network access must be Allow or Deny."
  }
}

variable "enable_managed_identity" {
  type        = bool
  description = "Whether to enable managed identity for Azure services"
  default     = true
}

# -----------------------------------------------------------------------------
# MONITORING & DIAGNOSTICS
# -----------------------------------------------------------------------------

variable "log_retention_days" {
  type        = number
  description = "Log Analytics workspace retention in days"
  default     = 30

  validation {
    condition     = var.log_retention_days >= 30 && var.log_retention_days <= 730
    error_message = "Log retention must be between 30 and 730 days."
  }
}

variable "enable_diagnostic_settings" {
  type        = bool
  description = "Whether to enable diagnostic settings for resources"
  default     = true
}

variable "alert_email" {
  type        = string
  description = "Email address for monitoring alerts"
  default     = ""
}

# -----------------------------------------------------------------------------
# DEPLOYMENT AUTOMATION
# -----------------------------------------------------------------------------

variable "enable_automated_deployment" {
  type        = bool
  description = "Whether to enable automated MCP server deployment"
  default     = true
}

variable "enable_cli_integration" {
  type        = bool
  description = "Whether to auto-trigger CLI operations after Terraform deployment"
  default     = false
}

variable "docker_registry" {
  type        = string
  description = "Docker registry for container images"
  default     = "mcr.microsoft.com"
}

variable "mcp_image_tag" {
  type        = string
  description = "Docker image tag for MCP server"
  default     = "latest"
}

variable "deployment_timeout" {
  type        = number
  description = "Deployment timeout in minutes"
  default     = 20
}

# -----------------------------------------------------------------------------
# FEATURE FLAGS
# -----------------------------------------------------------------------------

variable "enable_multi_region" {
  type        = bool
  description = "Whether to enable multi-region deployment"
  default     = false
}

variable "enable_backup" {
  type        = bool
  description = "Whether to enable backup for stateful services"
  default     = false
}

variable "enable_disaster_recovery" {
  type        = bool
  description = "Whether to enable disaster recovery"
  default     = false
}

variable "enable_auto_scaling" {
  type        = bool
  description = "Whether to enable auto-scaling"
  default     = true
}

# -----------------------------------------------------------------------------
# MISSING VARIABLES
# -----------------------------------------------------------------------------

variable "user_principal_id" {
  type        = string
  description = "User Principal ID for role assignments"
  default     = null
}

variable "acr_sku" {
  type        = string
  description = "SKU for Azure Container Registry"
  default     = "Standard"
}

variable "enable_geo_replication" {
  type        = bool
  description = "Whether to enable geo-replication for ACR"
  default     = false
}

variable "storage_replication_type" {
  type        = string
  description = "Replication type for Storage Account"
  default     = "LRS"
}

variable "cosmos_throughput" {
  type        = number
  description = "Throughput for Cosmos DB container"
  default     = 400
}

variable "search_replica_count" {
  type        = number
  description = "Replica count for Azure Search"
  default     = 1
}

variable "search_partition_count" {
  type        = number
  description = "Partition count for Azure Search"
  default     = 1
}

variable "container_max_replicas" {
  type        = number
  description = "Maximum number of replicas for container scaling"
  default     = 10
}

variable "enable_security_center" {
  type        = bool
  description = "Whether to enable Azure Security Center"
  default     = true
}

variable "enable_waf" {
  type        = bool
  description = "Whether to enable Web Application Firewall"
  default     = false
}

variable "enable_ddos_protection" {
  type        = bool
  description = "Whether to enable DDoS protection"
  default     = false
}

variable "enable_network_watcher" {
  type        = bool
  description = "Whether to enable Network Watcher"
  default     = false
}

variable "enable_bastion" {
  type        = bool
  description = "Whether to enable Azure Bastion"
  default     = false
}

variable "enable_vpn_gateway" {
  type        = bool
  description = "Whether to enable VPN Gateway"
  default     = false
}

variable "enable_express_route" {
  type        = bool
  description = "Whether to enable ExpressRoute"
  default     = false
}

variable "enable_firewall" {
  type        = bool
  description = "Whether to enable Azure Firewall"
  default     = false
}

variable "enable_front_door" {
  type        = bool
  description = "Whether to enable Azure Front Door"
  default     = false
}

variable "enable_traffic_manager" {
  type        = bool
  description = "Whether to enable Traffic Manager"
  default     = false
}

variable "enable_cdn" {
  type        = bool
  description = "Whether to enable CDN"
  default     = false
}

variable "enable_app_gateway" {
  type        = bool
  description = "Whether to enable Application Gateway"
  default     = false
}

variable "enable_load_balancer" {
  type        = bool
  description = "Whether to enable Load Balancer"
  default     = false
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Whether to enable NAT Gateway"
  default     = false
}

variable "enable_virtual_wan" {
  type        = bool
  description = "Whether to enable Virtual WAN"
  default     = false
}

variable "enable_private_link" {
  type        = bool
  description = "Whether to enable Private Link"
  default     = false
}

variable "enable_service_endpoints" {
  type        = bool
  description = "Whether to enable Service Endpoints"
  default     = false
}

variable "enable_nsg_flow_logs" {
  type        = bool
  description = "Whether to enable NSG Flow Logs"
  default     = false
}