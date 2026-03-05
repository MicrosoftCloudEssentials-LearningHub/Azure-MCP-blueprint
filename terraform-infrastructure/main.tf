# Azure MCP Blueprint - Zero-Touch Deployment
# Supports Container Apps, Functions, and App Service deployments
# Based on terraform.tfvars configuration

# Current Azure client configuration
data "azurerm_client_config" "current" {}

# Random string for unique naming
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Local variables for resource naming and configuration
locals {
  # Resource naming
  resource_suffix = "${var.name_prefix}-${random_string.suffix.result}"
  principal_id    = var.user_principal_id != null ? var.user_principal_id : data.azurerm_client_config.current.object_id

  # Load the selected industry schema to keep infra + server configuration consistent.
  # Terraform can read local files, so we treat the template JSON as the source of truth.
  industry_schema            = jsondecode(file("${path.module}/../industry-templates/${var.selected_industry}/schema.json"))
  cosmos_database_name        = try(local.industry_schema.cosmos_db.database, "mcp-database")
  cosmos_container_name       = try(local.industry_schema.cosmos_db.container, "mcp-container")
  cosmos_partition_key_path   = try(local.industry_schema.cosmos_db.partition_key, "/id")
  search_index_name           = try(local.industry_schema.search_index.name, "mcp-index")

  # MCP configuration
  mcp_port = var.mcp_deployment_type == "function" ? 80 : 8000

  # Common tags
  common_tags = {
    Project     = "Azure-MCP-Blueprint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# =============================================================================
# CORE AZURE INFRASTRUCTURE
# =============================================================================

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "main" {
  count               = var.enable_monitoring ? 1 : 0
  name                = "law-${local.resource_suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  count               = var.enable_monitoring ? 1 : 0
  name                = "ai-${local.resource_suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main[0].id
  application_type    = "web"
  tags                = local.common_tags
}

# Key Vault for secure configuration
resource "azurerm_key_vault" "main" {
  name                = "kv-${local.resource_suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Enable purge protection for production
  purge_protection_enabled = var.environment == "prod"

  # Network access
  network_acls {
    default_action = var.key_vault_network_access
    bypass         = "AzureServices"
  }

  tags = local.common_tags
}

# Key Vault Access Policy for current user
resource "azurerm_key_vault_access_policy" "current_user" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  key_permissions = [
    "Get", "List", "Create", "Delete", "Update", "Purge"
  ]

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge"
  ]

  lifecycle {
    ignore_changes = [key_permissions, secret_permissions]
  }
}

# Key Vault Access Policy for Managed Identity (will be added after deployment)
resource "azurerm_key_vault_access_policy" "managed_identity" {
  count        = var.mcp_deployment_type != "local" ? 1 : 0
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id = (
    var.mcp_deployment_type == "container-app" && length(azurerm_container_app.mcp_server) > 0 ? azurerm_container_app.mcp_server[0].identity[0].principal_id :
    var.mcp_deployment_type == "function" && length(azurerm_linux_function_app.mcp_server) > 0 ? azurerm_linux_function_app.mcp_server[0].identity[0].principal_id :
    var.mcp_deployment_type == "app-service" && length(azurerm_linux_web_app.mcp_server) > 0 ? azurerm_linux_web_app.mcp_server[0].identity[0].principal_id :
    data.azurerm_client_config.current.object_id
  )

  secret_permissions = [
    "Get", "List"
  ]

  depends_on = [
    azurerm_container_app.mcp_server,
    azurerm_linux_function_app.mcp_server,
    azurerm_linux_web_app.mcp_server
  ]
}

# =============================================================================
# CONTAINER REGISTRY FOR AUTOMATED BUILDS
# =============================================================================

# Azure Container Registry
resource "azurerm_container_registry" "main" {
  count               = var.enable_container_registry ? 1 : 0
  name                = "acr${replace(local.resource_suffix, "-", "")}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.acr_sku
  admin_enabled       = true

  # Enable geo-replication for Premium SKU
  dynamic "georeplications" {
    for_each = var.enable_geo_replication && var.acr_sku == "Premium" ? [1] : []
    content {
      location                = "West US 2"
      zone_redundancy_enabled = true
      tags                    = local.common_tags
    }
  }

  public_network_access_enabled = true
  tags                          = local.common_tags
}

# User-assigned identity for Container Apps to pull from ACR and read Key Vault secrets.
# This avoids the system-assigned identity chicken-and-egg during initial provisioning.
resource "azurerm_user_assigned_identity" "container_app" {
  count               = var.mcp_deployment_type == "container-app" ? 1 : 0
  name                = "id-ca-${local.resource_suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_role_assignment" "container_app_acr_pull" {
  count                = var.mcp_deployment_type == "container-app" && var.enable_container_registry ? 1 : 0
  scope                = azurerm_container_registry.main[0].id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_app[0].principal_id
}

resource "azurerm_key_vault_access_policy" "container_app_identity" {
  count        = var.mcp_deployment_type == "container-app" ? 1 : 0
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.container_app[0].principal_id

  secret_permissions = [
    "Get",
    "List",
  ]

  depends_on = [azurerm_key_vault_access_policy.current_user]
}

# Build the container image in ACR before the Container App is created (so the initial
# revision can pull successfully without requiring a follow-up `az containerapp update`).
resource "null_resource" "build_mcp_image" {
  count = var.enable_automated_deployment && var.mcp_deployment_type == "container-app" && var.enable_container_registry ? 1 : 0

  provisioner "local-exec" {
    command     = <<-EOT
      # Azure CLI can emit warnings to stderr even on success.
      # In Windows PowerShell this can become a NativeCommandError; capture streams to files and
      # rely on $LASTEXITCODE for failure detection.
      $ErrorActionPreference = 'Stop'
      chcp 65001 > $null
      $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
      [Console]::InputEncoding  = $utf8NoBom
      [Console]::OutputEncoding = $utf8NoBom
      $OutputEncoding           = $utf8NoBom
      $env:PYTHONIOENCODING     = "utf-8"
      $env:PYTHONUTF8           = "1"
      $env:AZURE_CORE_NO_COLOR  = "1"
      $env:TERM                 = "xterm"
      $ProgressPreference       = 'SilentlyContinue'

      Write-Host "Building container image in Azure Container Registry..." -ForegroundColor Yellow
      $runId = [Guid]::NewGuid().ToString('N')
      $stdoutPath = Join-Path $env:TEMP "acr-build-$runId.stdout.txt"
      $stderrPath = Join-Path $env:TEMP "acr-build-$runId.stderr.txt"

      & az acr build `
        --only-show-errors `
        --registry "${azurerm_container_registry.main[0].name}" `
        --image "mcp-server:latest" `
        --file ../src/mcp-server/Dockerfile `
        --no-logs `
        ../src/mcp-server 1> $stdoutPath 2> $stderrPath

      $exitCode = $LASTEXITCODE
      if ($exitCode -ne 0) {
        Write-Host "Container build failed (exit code: $exitCode)" -ForegroundColor Red
        if (Test-Path $stdoutPath) { Get-Content $stdoutPath | Write-Host }
        if (Test-Path $stderrPath) { Get-Content $stderrPath | Write-Host }
        exit 1
      }
    EOT
    interpreter = ["PowerShell", "-Command"]
    working_dir = path.module
  }

  depends_on = [azurerm_container_registry.main]

  triggers = {
    always_run = timestamp()
  }
}

# Storage account for sample data (using managed identity)
resource "azurerm_storage_account" "sample_data" {
  count                    = var.enable_sample_data ? 1 : 0
  name                     = "st${replace(local.resource_suffix, "-", "")}data"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.storage_replication_type

  # Use Azure AD authentication instead of shared keys
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false

  tags = local.common_tags
}

# Container for sample documents
resource "azurerm_storage_container" "sample_documents" {
  count                 = var.enable_sample_data ? 1 : 0
  name                  = "sample-documents"
  storage_account_name  = azurerm_storage_account.sample_data[0].name
  container_access_type = "private"
}

# =============================================================================
# AI SERVICES INFRASTRUCTURE
# =============================================================================

# Microsoft Foundry (formerly Azure OpenAI)
resource "azurerm_cognitive_account" "foundry" {
  count                 = contains(var.enable_mcp_tools, "foundry") ? 1 : 0
  name                  = "foundry-${local.resource_suffix}"
  location              = var.foundry_location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "foundry-${local.resource_suffix}"
  local_auth_enabled    = true # Must be enabled for Terraform to manage keys

  # Network access configuration
  # Network access configuration
  public_network_access_enabled      = true
  outbound_network_access_restricted = false

  tags = local.common_tags
}

# Azure AI Search
resource "azurerm_search_service" "main" {
  count                         = contains(var.enable_mcp_tools, "search") ? 1 : 0
  name                          = "search-${local.resource_suffix}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = coalesce(var.search_location, azurerm_resource_group.main.location)
  sku                           = var.search_sku
  public_network_access_enabled = true

  tags = local.common_tags
}

# Cosmos DB Account
resource "azurerm_cosmosdb_account" "main" {
  count               = contains(var.enable_mcp_tools, "cosmos") ? 1 : 0
  name                = "cosmos-${local.resource_suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  # Authentication and access settings
  local_authentication_disabled = false # Keep keys enabled for initial setup
  public_network_access_enabled = true

  # Backup and reliability settings
  backup {
    type                = "Periodic"
    interval_in_minutes = 240
    retention_in_hours  = 8
    storage_redundancy  = "Local"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }

  tags = local.common_tags
}

# Time delay to ensure Cosmos DB account is fully online
resource "time_sleep" "cosmos_account_ready" {
  count           = contains(var.enable_mcp_tools, "cosmos") ? 1 : 0
  depends_on      = [azurerm_cosmosdb_account.main]
  create_duration = "180s" # Wait 3 minutes for account to be fully online
}

# Time delay to ensure Microsoft Foundry service is ready
resource "time_sleep" "foundry_service_ready" {
  count           = contains(var.enable_mcp_tools, "foundry") ? 1 : 0
  depends_on      = [azurerm_cognitive_account.foundry]
  create_duration = "60s" # Wait 1 minute for Foundry service to be ready
}

# =============================================================================
# KEY VAULT SECRETS
# =============================================================================

# Cosmos DB connection string
resource "azurerm_key_vault_secret" "cosmos_connection_string" {
  count        = contains(var.enable_mcp_tools, "cosmos") ? 1 : 0
  name         = "cosmos-connection-string"
  value        = azurerm_cosmosdb_account.main[0].primary_sql_connection_string
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [
    azurerm_key_vault_access_policy.current_user,
    time_sleep.cosmos_account_ready
  ]
}

# Cosmos DB endpoint
resource "azurerm_key_vault_secret" "cosmos_endpoint" {
  count        = contains(var.enable_mcp_tools, "cosmos") ? 1 : 0
  name         = "cosmos-endpoint"
  value        = azurerm_cosmosdb_account.main[0].endpoint
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [
    azurerm_key_vault_access_policy.current_user,
    time_sleep.cosmos_account_ready
  ]
}

# Cosmos DB primary key
resource "azurerm_key_vault_secret" "cosmos_primary_key" {
  count        = contains(var.enable_mcp_tools, "cosmos") ? 1 : 0
  name         = "cosmos-primary-key"
  value        = azurerm_cosmosdb_account.main[0].primary_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [
    azurerm_key_vault_access_policy.current_user,
    time_sleep.cosmos_account_ready
  ]
}

# Microsoft Foundry endpoint
resource "azurerm_key_vault_secret" "foundry_endpoint" {
  count        = contains(var.enable_mcp_tools, "foundry") ? 1 : 0
  name         = "foundry-endpoint"
  value        = azurerm_cognitive_account.foundry[0].endpoint
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [
    azurerm_key_vault_access_policy.current_user,
    time_sleep.foundry_service_ready
  ]
}

# Microsoft Foundry API key
resource "azurerm_key_vault_secret" "foundry_api_key" {
  count        = contains(var.enable_mcp_tools, "foundry") ? 1 : 0
  name         = "foundry-api-key"
  value        = "managed_identity" # Using Managed Identity as local auth is disabled
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [
    azurerm_key_vault_access_policy.current_user,
    time_sleep.foundry_service_ready
  ]
}

# Azure Search endpoint
resource "azurerm_key_vault_secret" "search_endpoint" {
  count        = contains(var.enable_mcp_tools, "search") ? 1 : 0
  name         = "search-endpoint"
  value        = "https://${azurerm_search_service.main[0].name}.search.windows.net"
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.current_user]
}

# Azure Search admin key
resource "azurerm_key_vault_secret" "search_admin_key" {
  count        = contains(var.enable_mcp_tools, "search") ? 1 : 0
  name         = "search-admin-key"
  value        = azurerm_search_service.main[0].primary_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.current_user]
}

# Application Insights connection string
resource "azurerm_key_vault_secret" "appinsights_connection_string" {
  count        = var.enable_monitoring ? 1 : 0
  name         = "appinsights-connection-string"
  value        = azurerm_application_insights.main[0].connection_string
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.current_user]
}

# Application Insights instrumentation key
resource "azurerm_key_vault_secret" "appinsights_instrumentation_key" {
  count        = var.enable_monitoring ? 1 : 0
  name         = "appinsights-instrumentation-key"
  value        = azurerm_application_insights.main[0].instrumentation_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.current_user]
}

# Cosmos DB SQL Database
resource "azurerm_cosmosdb_sql_database" "main" {
  count               = contains(var.enable_mcp_tools, "cosmos") ? 1 : 0
  name                = local.cosmos_database_name
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main[0].name
  throughput          = 400

  depends_on = [time_sleep.cosmos_account_ready]
}

# Cosmos DB SQL Container
resource "azurerm_cosmosdb_sql_container" "main" {
  count               = contains(var.enable_mcp_tools, "cosmos") ? 1 : 0
  name                = local.cosmos_container_name
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main[0].name
  database_name       = azurerm_cosmosdb_sql_database.main[0].name
  partition_key_paths = [local.cosmos_partition_key_path]
  throughput          = var.cosmos_throughput # Enterprise scale throughput

  # Indexing policy for large datasets
  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/excluded/*"
    }
  }

  depends_on = [azurerm_cosmosdb_sql_database.main]
}

# =============================================================================
# CONTAINER APPS DEPLOYMENT
# =============================================================================

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  count                      = var.mcp_deployment_type == "container-app" ? 1 : 0
  name                       = "cae-${local.resource_suffix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = var.enable_monitoring ? azurerm_log_analytics_workspace.main[0].id : null
  tags                       = local.common_tags
}

# Container App
resource "azurerm_container_app" "mcp_server" {
  count                        = var.mcp_deployment_type == "container-app" ? 1 : 0
  name                         = "ca-mcp-${local.resource_suffix}"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  dynamic "registry" {
    for_each = var.enable_container_registry ? [1] : []
    content {
      server   = azurerm_container_registry.main[0].login_server
      identity = azurerm_user_assigned_identity.container_app[0].id
    }
  }

  template {
    min_replicas = var.container_min_replicas
    max_replicas = var.container_max_replicas

    container {
      name   = "mcp-server"
      image  = var.enable_container_registry ? "${azurerm_container_registry.main[0].login_server}/mcp-server:latest" : "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      cpu    = var.container_cpu
      memory = var.container_memory

      env {
        name  = "PORT"
        value = tostring(local.mcp_port)
      }

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.container_app[0].client_id
      }

      env {
        name  = "ENABLE_MCP_TOOLS"
        value = join(",", var.enable_mcp_tools)
      }

      env {
        name  = "AZURE_KEY_VAULT_URI"
        value = azurerm_key_vault.main.vault_uri
      }

      env {
        name  = "SELECTED_INDUSTRY"
        value = var.selected_industry
      }

      env {
        name  = "COSMOS_DATABASE"
        value = local.cosmos_database_name
      }

      env {
        name  = "COSMOS_CONTAINER"
        value = local.cosmos_container_name
      }

      env {
        name  = "SEARCH_INDEX_NAME"
        value = local.search_index_name
      }

      # Application Insights connection string from Key Vault
      dynamic "env" {
        for_each = var.enable_monitoring ? [1] : []
        content {
          name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
          secret_name = "appinsights-connection-string"
        }
      }

      # Only add environment variables if services are enabled
      dynamic "env" {
        for_each = contains(var.enable_mcp_tools, "cosmos") ? [1] : []
        content {
          name        = "COSMOS_ENDPOINT"
          secret_name = "cosmos-endpoint"
        }
      }

      dynamic "env" {
        for_each = contains(var.enable_mcp_tools, "cosmos") ? [1] : []
        content {
          name        = "COSMOS_KEY"
          secret_name = "cosmos-primary-key"
        }
      }

      dynamic "env" {
        for_each = contains(var.enable_mcp_tools, "foundry") ? [1] : []
        content {
          name        = "FOUNDRY_ENDPOINT"
          secret_name = "foundry-endpoint"
        }
      }

      dynamic "env" {
        for_each = contains(var.enable_mcp_tools, "foundry") ? [1] : []
        content {
          name        = "FOUNDRY_API_KEY"
          secret_name = "foundry-api-key"
        }
      }

      dynamic "env" {
        for_each = contains(var.enable_mcp_tools, "search") ? [1] : []
        content {
          name        = "SEARCH_ENDPOINT"
          secret_name = "search-endpoint"
        }
      }

      dynamic "env" {
        for_each = contains(var.enable_mcp_tools, "search") ? [1] : []
        content {
          name        = "SEARCH_ADMIN_KEY"
          secret_name = "search-admin-key"
        }
      }

    }
  }

  # Enable managed identity
  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_app[0].id]
  }

  # Dynamic secrets configuration based on enabled tools - all from Key Vault
  dynamic "secret" {
    for_each = var.enable_monitoring ? [1] : []
    content {
      name                = "appinsights-connection-string"
      key_vault_secret_id = azurerm_key_vault_secret.appinsights_connection_string[0].id
      identity            = azurerm_user_assigned_identity.container_app[0].id
    }
  }

  dynamic "secret" {
    for_each = contains(var.enable_mcp_tools, "cosmos") ? [1] : []
    content {
      name                = "cosmos-endpoint"
      key_vault_secret_id = azurerm_key_vault_secret.cosmos_endpoint[0].id
      identity            = azurerm_user_assigned_identity.container_app[0].id
    }
  }

  dynamic "secret" {
    for_each = contains(var.enable_mcp_tools, "cosmos") ? [1] : []
    content {
      name                = "cosmos-primary-key"
      key_vault_secret_id = azurerm_key_vault_secret.cosmos_primary_key[0].id
      identity            = azurerm_user_assigned_identity.container_app[0].id
    }
  }

  dynamic "secret" {
    for_each = contains(var.enable_mcp_tools, "foundry") ? [1] : []
    content {
      name                = "foundry-endpoint"
      key_vault_secret_id = azurerm_key_vault_secret.foundry_endpoint[0].id
      identity            = azurerm_user_assigned_identity.container_app[0].id
    }
  }

  dynamic "secret" {
    for_each = contains(var.enable_mcp_tools, "foundry") ? [1] : []
    content {
      name                = "foundry-api-key"
      key_vault_secret_id = azurerm_key_vault_secret.foundry_api_key[0].id
      identity            = azurerm_user_assigned_identity.container_app[0].id
    }
  }

  dynamic "secret" {
    for_each = contains(var.enable_mcp_tools, "search") ? [1] : []
    content {
      name                = "search-endpoint"
      key_vault_secret_id = azurerm_key_vault_secret.search_endpoint[0].id
      identity            = azurerm_user_assigned_identity.container_app[0].id
    }
  }

  dynamic "secret" {
    for_each = contains(var.enable_mcp_tools, "search") ? [1] : []
    content {
      name                = "search-admin-key"
      key_vault_secret_id = azurerm_key_vault_secret.search_admin_key[0].id
      identity            = azurerm_user_assigned_identity.container_app[0].id
    }
  }

  ingress {
    external_enabled = true
    target_port      = local.mcp_port

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  depends_on = [
    time_sleep.cosmos_account_ready,
    time_sleep.foundry_service_ready,
    azurerm_key_vault_access_policy.container_app_identity,
    azurerm_role_assignment.container_app_acr_pull,
    null_resource.build_mcp_image
  ]

  tags = local.common_tags
}

# =============================================================================
# AZURE FUNCTIONS DEPLOYMENT
# =============================================================================

# Storage Account for Functions
resource "azurerm_storage_account" "functions" {
  count                    = var.mcp_deployment_type == "function" ? 1 : 0
  name                     = "stfunc${replace(local.resource_suffix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.common_tags
}

# App Service Plan for Functions
resource "azurerm_service_plan" "functions" {
  count               = var.mcp_deployment_type == "function" ? 1 : 0
  name                = "sp-func-${local.resource_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1" # Consumption plan
  tags                = local.common_tags
}

# Linux Function App
resource "azurerm_linux_function_app" "mcp_server" {
  count               = var.mcp_deployment_type == "function" ? 1 : 0
  name                = "func-mcp-${local.resource_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.functions[0].id

  storage_account_name       = azurerm_storage_account.functions[0].name
  storage_account_access_key = azurerm_storage_account.functions[0].primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = ["*"]
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "AzureWebJobsFeatureFlags" = "EnableWorkerIndexing"
    "AZURE_KEY_VAULT_URI"      = azurerm_key_vault.main.vault_uri
    "SELECTED_INDUSTRY"        = var.selected_industry
    "COSMOS_DATABASE"          = local.cosmos_database_name
    "COSMOS_CONTAINER"         = local.cosmos_container_name
    "SEARCH_INDEX_NAME"        = local.search_index_name
    # Key Vault references for sensitive values
    "COSMOS_ENDPOINT"                       = contains(var.enable_mcp_tools, "cosmos") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.cosmos_endpoint[0].id})" : ""
    "COSMOS_KEY"                            = contains(var.enable_mcp_tools, "cosmos") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.cosmos_primary_key[0].id})" : ""
    "FOUNDRY_ENDPOINT"                      = contains(var.enable_mcp_tools, "foundry") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.foundry_endpoint[0].id})" : ""
    "FOUNDRY_API_KEY"                       = contains(var.enable_mcp_tools, "foundry") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.foundry_api_key[0].id})" : ""
    "SEARCH_ENDPOINT"                       = contains(var.enable_mcp_tools, "search") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.search_endpoint[0].id})" : ""
    "SEARCH_ADMIN_KEY"                      = contains(var.enable_mcp_tools, "search") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.search_admin_key[0].id})" : ""
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.enable_monitoring ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.appinsights_connection_string[0].id})" : ""
  }

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

# =============================================================================
# APP SERVICE DEPLOYMENT
# =============================================================================

# App Service Plan
resource "azurerm_service_plan" "app_service" {
  count               = var.mcp_deployment_type == "app-service" ? 1 : 0
  name                = "sp-app-${local.resource_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "B1" # Basic plan
  tags                = local.common_tags
}

# Linux Web App
resource "azurerm_linux_web_app" "mcp_server" {
  count               = var.mcp_deployment_type == "app-service" ? 1 : 0
  name                = "app-mcp-${local.resource_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.app_service[0].id

  site_config {
    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = ["*"]
    }
  }

  app_settings = {
    "AZURE_KEY_VAULT_URI" = azurerm_key_vault.main.vault_uri
    "SELECTED_INDUSTRY"   = var.selected_industry
    "COSMOS_DATABASE"     = local.cosmos_database_name
    "COSMOS_CONTAINER"    = local.cosmos_container_name
    "SEARCH_INDEX_NAME"   = local.search_index_name
    # Key Vault references for sensitive values
    "COSMOS_ENDPOINT"                       = contains(var.enable_mcp_tools, "cosmos") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.cosmos_endpoint[0].id})" : ""
    "COSMOS_KEY"                            = contains(var.enable_mcp_tools, "cosmos") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.cosmos_primary_key[0].id})" : ""
    "FOUNDRY_ENDPOINT"                      = contains(var.enable_mcp_tools, "foundry") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.foundry_endpoint[0].id})" : ""
    "FOUNDRY_API_KEY"                       = contains(var.enable_mcp_tools, "foundry") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.foundry_api_key[0].id})" : ""
    "SEARCH_ENDPOINT"                       = contains(var.enable_mcp_tools, "search") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.search_endpoint[0].id})" : ""
    "SEARCH_ADMIN_KEY"                      = contains(var.enable_mcp_tools, "search") ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.search_admin_key[0].id})" : ""
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.enable_monitoring ? "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.appinsights_connection_string[0].id})" : ""
  }

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }

  tags = local.common_tags
}

# =============================================================================
# ROLE ASSIGNMENTS FOR MANAGED IDENTITY
# =============================================================================

# Get the managed identity object ID based on deployment type
locals {
  # Create a map for enabled tools that need role assignments
  cosmos_role_needed  = contains(var.enable_mcp_tools, "cosmos") ? { "cosmos" = "cosmos" } : {}
  foundry_role_needed = contains(var.enable_mcp_tools, "foundry") ? { "foundry" = "foundry" } : {}
  search_role_needed  = contains(var.enable_mcp_tools, "search") ? { "search" = "search" } : {}
}

# Cosmos DB role assignment
resource "azurerm_role_assignment" "cosmos_data_contributor" {
  for_each             = local.cosmos_role_needed
  scope                = azurerm_cosmosdb_account.main[0].id
  role_definition_name = "DocumentDB Account Contributor"
  principal_id = (
    var.mcp_deployment_type == "container-app" ? azurerm_container_app.mcp_server[0].identity[0].principal_id :
    var.mcp_deployment_type == "function" ? azurerm_linux_function_app.mcp_server[0].identity[0].principal_id :
    azurerm_linux_web_app.mcp_server[0].identity[0].principal_id
  )

  depends_on = [
    azurerm_container_app.mcp_server,
    azurerm_linux_function_app.mcp_server,
    azurerm_linux_web_app.mcp_server,
    time_sleep.cosmos_account_ready
  ]
}

# Microsoft Foundry role assignment
resource "azurerm_role_assignment" "foundry_user" {
  for_each             = local.foundry_role_needed
  scope                = azurerm_cognitive_account.foundry[0].id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id = (
    var.mcp_deployment_type == "container-app" ? azurerm_container_app.mcp_server[0].identity[0].principal_id :
    var.mcp_deployment_type == "function" ? azurerm_linux_function_app.mcp_server[0].identity[0].principal_id :
    azurerm_linux_web_app.mcp_server[0].identity[0].principal_id
  )

  depends_on = [
    azurerm_container_app.mcp_server,
    azurerm_linux_function_app.mcp_server,
    azurerm_linux_web_app.mcp_server,
    time_sleep.foundry_service_ready
  ]
}

# Key Vault Secrets User role assignment for managed identity
resource "azurerm_role_assignment" "key_vault_secrets_user" {
  count                = var.mcp_deployment_type != "local" ? 1 : 0
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id = (
    var.mcp_deployment_type == "container-app" ? azurerm_container_app.mcp_server[0].identity[0].principal_id :
    var.mcp_deployment_type == "function" ? azurerm_linux_function_app.mcp_server[0].identity[0].principal_id :
    azurerm_linux_web_app.mcp_server[0].identity[0].principal_id
  )

  depends_on = [
    azurerm_container_app.mcp_server,
    azurerm_linux_function_app.mcp_server,
    azurerm_linux_web_app.mcp_server
  ]
}

# Search role assignment
resource "azurerm_role_assignment" "search_contributor" {
  for_each             = local.search_role_needed
  scope                = azurerm_search_service.main[0].id
  role_definition_name = "Search Service Contributor"
  principal_id = (
    var.mcp_deployment_type == "container-app" ? azurerm_container_app.mcp_server[0].identity[0].principal_id :
    var.mcp_deployment_type == "function" ? azurerm_linux_function_app.mcp_server[0].identity[0].principal_id :
    azurerm_linux_web_app.mcp_server[0].identity[0].principal_id
  )

  depends_on = [
    azurerm_container_app.mcp_server,
    azurerm_linux_function_app.mcp_server,
    azurerm_linux_web_app.mcp_server
  ]
}

# =============================================================================
# MCP SERVER DEPLOYMENT AUTOMATION
# =============================================================================

# Build and deploy MCP server
# =============================================================================
# POST-DEPLOYMENT VALIDATION
# =============================================================================

# Validate MCP server deployment
resource "null_resource" "validate_deployment" {
  count = var.enable_validation && var.mcp_deployment_type == "container-app" ? 1 : 0

  provisioner "local-exec" {
    command     = <<-EOT
      Write-Host "Validating MCP server deployment..."
      Start-Sleep -Seconds 30  # Wait for services to start

      # Terraform runs this from the module folder (terraform-infrastructure).
      # Prefer a repo-root virtualenv to keep dependencies isolated; create it if missing.
      $repoRoot = (Resolve-Path (Join-Path (Get-Location) "..")).Path
      $venvDir = Join-Path $repoRoot "venv"
      $venvPython = Join-Path $venvDir "Scripts\python.exe"
      $validateScript = Join-Path $repoRoot "scripts\validate-mcp.py"

      if (-not (Test-Path -LiteralPath $validateScript)) {
        throw "Validation script not found: $validateScript"
      }

      if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host "Local venv not found; creating: $venvDir" -ForegroundColor Yellow

        $systemPython = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $systemPython) {
          $pyLauncher = (Get-Command py -ErrorAction SilentlyContinue).Source
          if ($pyLauncher) {
            $systemPython = $pyLauncher
          }
        }

        if (-not $systemPython) {
          throw "Python is required for deployment validation but was not found in PATH (python/py)."
        }

        if ($systemPython -like "*\\py.exe") {
          & $systemPython -3 -m venv $venvDir
        } else {
          & $systemPython -m venv $venvDir
        }
      }

      # Ensure the validator dependency is available (validate-mcp.py imports requests)
      & $venvPython -m pip install --quiet --upgrade pip
      & $venvPython -m pip install --quiet requests

      & $venvPython $validateScript `
        --deployment-type "${var.mcp_deployment_type}" `
        --endpoint "${local.mcp_endpoint}" `
        --tools "${join(",", var.enable_mcp_tools)}"
    EOT
    interpreter = ["PowerShell", "-Command"]
    working_dir = path.module
  }

  depends_on = [azurerm_container_app.mcp_server]
}

# MCP endpoint based on deployment type
locals {
  mcp_endpoint = (
    var.mcp_deployment_type == "container-app" && length(azurerm_container_app.mcp_server) > 0 ? "https://${azurerm_container_app.mcp_server[0].latest_revision_fqdn}" :
    var.mcp_deployment_type == "function" && length(azurerm_linux_function_app.mcp_server) > 0 ? "https://${azurerm_linux_function_app.mcp_server[0].default_hostname}/api" :
    var.mcp_deployment_type == "app-service" && length(azurerm_linux_web_app.mcp_server) > 0 ? "https://${azurerm_linux_web_app.mcp_server[0].default_hostname}" :
    "http://localhost:8000"
  )
}

# =============================================================================
# SAMPLE DATA DEPLOYMENT AUTOMATION
# =============================================================================

# Deploy sample data for enterprise demonstration
resource "null_resource" "deploy_sample_data" {
  count = var.enable_sample_data && var.mcp_deployment_type != "local" ? 1 : 0

  provisioner "local-exec" {
    command     = <<-EOT
      Write-Host "========================================" -ForegroundColor Cyan
      Write-Host "Generating sample records (template-driven count)" -ForegroundColor Cyan
      Write-Host "========================================" -ForegroundColor Cyan
      Write-Host ""
      
      # Install Python dependencies
      Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
      python -m pip install --quiet --upgrade pip
      python -m pip install --quiet azure-cosmos azure-storage-blob azure-search-documents azure-identity
      
      # Generate sample data
      Write-Host ""
      Write-Host "Generating sample data for industry: ${var.selected_industry}" -ForegroundColor Yellow
      cd ../scripts
      python generate_sample_data.py --industry ${var.selected_industry}
      
      # Upload to Azure
      Write-Host ""
      Write-Host "Uploading data to Azure..." -ForegroundColor Yellow
      
      $env:COSMOS_ENDPOINT = "${contains(var.enable_mcp_tools, "cosmos") ? azurerm_cosmosdb_account.main[0].endpoint : ""}"
      $env:COSMOS_KEY = "${contains(var.enable_mcp_tools, "cosmos") ? azurerm_cosmosdb_account.main[0].primary_key : ""}"
      $env:COSMOS_DATABASE = "${contains(var.enable_mcp_tools, "cosmos") ? azurerm_cosmosdb_sql_database.main[0].name : ""}"
      $env:COSMOS_CONTAINER = "${contains(var.enable_mcp_tools, "cosmos") ? azurerm_cosmosdb_sql_container.main[0].name : ""}"
      $env:SEARCH_ENDPOINT = "${contains(var.enable_mcp_tools, "search") ? "https://${azurerm_search_service.main[0].name}.search.windows.net" : ""}"
      $env:SEARCH_KEY = "${contains(var.enable_mcp_tools, "search") ? azurerm_search_service.main[0].primary_key : ""}"
      $env:INDUSTRY = "${var.selected_industry}"
      
      python upload_sample_data.py
      
      Write-Host ""
      Write-Host "Sample data deployment complete!" -ForegroundColor Green
    EOT
    interpreter = ["PowerShell", "-Command"]
    working_dir = path.module
  }

  depends_on = [
    azurerm_cosmosdb_sql_container.main,
    azurerm_search_service.main,
    time_sleep.cosmos_account_ready
  ]
}

# =============================================================================
# CLI INTEGRATION - AUTO-TRIGGER AFTER DEPLOYMENT
# =============================================================================

# CLI integration removed: Terraform apply should finish without launching interactive tooling.