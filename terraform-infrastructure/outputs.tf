# =============================================================================
# AZURE MCP BLUEPRINT - TERRAFORM OUTPUTS
# =============================================================================

# =============================================================================
# DEPLOYMENT INFORMATION
# =============================================================================

output "deployment_summary" {
  description = "Summary of the MCP deployment"
  value = {
    deployment_type = var.mcp_deployment_type
    resource_group  = azurerm_resource_group.main.name
    location        = azurerm_resource_group.main.location
    environment     = var.environment
    enabled_tools   = var.enable_mcp_tools
    deployment_time = formatdate("YYYY-MM-DD hh:mm:ss ZZZ", timestamp())
  }
}

output "resource_group" {
  description = "Resource group information"
  value = {
    name     = azurerm_resource_group.main.name
    location = azurerm_resource_group.main.location
    id       = azurerm_resource_group.main.id
  }
}

# =============================================================================
# MCP SERVER ENDPOINTS
# =============================================================================

output "mcp_endpoint" {
  description = "MCP server endpoint URL"
  value       = local.mcp_endpoint
}

output "mcp_server_details" {
  description = "MCP server deployment details"
  value = {
    deployment_type = var.mcp_deployment_type
    endpoint        = local.mcp_endpoint
    port            = local.mcp_port
    status          = "deployed"
  }
}

# Container Apps specific outputs
output "container_app_details" {
  description = "Container App details (if deployed)"
  value = var.mcp_deployment_type == "container-app" && length(azurerm_container_app.mcp_server) > 0 ? {
    name     = azurerm_container_app.mcp_server[0].name
    fqdn     = azurerm_container_app.mcp_server[0].latest_revision_fqdn
    url      = "https://${azurerm_container_app.mcp_server[0].latest_revision_fqdn}"
    revision = azurerm_container_app.mcp_server[0].latest_revision_name
  } : null
}

# Function App specific outputs
output "function_app_details" {
  description = "Function App details (if deployed)"
  value = var.mcp_deployment_type == "function" && length(azurerm_linux_function_app.mcp_server) > 0 ? {
    name         = azurerm_linux_function_app.mcp_server[0].name
    hostname     = azurerm_linux_function_app.mcp_server[0].default_hostname
    url          = "https://${azurerm_linux_function_app.mcp_server[0].default_hostname}"
    principal_id = azurerm_linux_function_app.mcp_server[0].identity[0].principal_id
  } : null
}

# App Service specific outputs
output "app_service_details" {
  description = "App Service details (if deployed)"
  value = var.mcp_deployment_type == "app-service" && length(azurerm_linux_web_app.mcp_server) > 0 ? {
    name         = azurerm_linux_web_app.mcp_server[0].name
    hostname     = azurerm_linux_web_app.mcp_server[0].default_hostname
    url          = "https://${azurerm_linux_web_app.mcp_server[0].default_hostname}"
    principal_id = azurerm_linux_web_app.mcp_server[0].identity[0].principal_id
  } : null
}

# =============================================================================
# AI SERVICES OUTPUTS
# =============================================================================

output "foundry_service" {
  description = "Microsoft Foundry service details"
  value = contains(var.enable_mcp_tools, "foundry") && length(azurerm_cognitive_account.foundry) > 0 ? {
    name          = azurerm_cognitive_account.foundry[0].name
    endpoint      = azurerm_cognitive_account.foundry[0].endpoint
    location      = azurerm_cognitive_account.foundry[0].location
    custom_domain = azurerm_cognitive_account.foundry[0].custom_subdomain_name
  } : null
  sensitive = false
}

output "search_service" {
  description = "Azure AI Search service details"
  value = contains(var.enable_mcp_tools, "search") && length(azurerm_search_service.main) > 0 ? {
    name     = azurerm_search_service.main[0].name
    endpoint = "https://${azurerm_search_service.main[0].name}.search.windows.net"
    sku      = azurerm_search_service.main[0].sku
    location = azurerm_search_service.main[0].location
  } : null
}

output "cosmos_db" {
  description = "Cosmos DB account details"
  value = contains(var.enable_mcp_tools, "cosmos") && length(azurerm_cosmosdb_account.main) > 0 ? {
    name      = azurerm_cosmosdb_account.main[0].name
    endpoint  = azurerm_cosmosdb_account.main[0].endpoint
    location  = azurerm_cosmosdb_account.main[0].location
    database  = azurerm_cosmosdb_sql_database.main[0].name
    container = azurerm_cosmosdb_sql_container.main[0].name
  } : null
  sensitive = false
}

# =============================================================================
# MONITORING OUTPUTS
# =============================================================================

output "monitoring_services" {
  description = "Monitoring and observability services"
  value = var.enable_monitoring ? {
    log_analytics = length(azurerm_log_analytics_workspace.main) > 0 ? {
      name         = azurerm_log_analytics_workspace.main[0].name
      workspace_id = azurerm_log_analytics_workspace.main[0].workspace_id
      location     = azurerm_log_analytics_workspace.main[0].location
    } : null
    application_insights = length(azurerm_application_insights.main) > 0 ? {
      name                = azurerm_application_insights.main[0].name
      instrumentation_key = azurerm_application_insights.main[0].instrumentation_key
      connection_string   = azurerm_application_insights.main[0].connection_string
      app_id              = azurerm_application_insights.main[0].app_id
    } : null
  } : null
  sensitive = true
}

# =============================================================================
# SECURITY OUTPUTS
# =============================================================================

output "key_vault" {
  description = "Key Vault details"
  value = {
    name      = azurerm_key_vault.main.name
    vault_uri = azurerm_key_vault.main.vault_uri
    location  = azurerm_key_vault.main.location
    secrets_stored = {
      cosmos_enabled     = contains(var.enable_mcp_tools, "cosmos")
      foundry_enabled    = contains(var.enable_mcp_tools, "foundry")
      search_enabled     = contains(var.enable_mcp_tools, "search")
      monitoring_enabled = var.enable_monitoring
    }
  }
}

output "security_configuration" {
  description = "Security configuration details"
  value = {
    managed_identity_enabled = var.mcp_deployment_type != "local"
    key_vault_integration    = true
    rbac_assignments = {
      cosmos_data_contributor = contains(var.enable_mcp_tools, "cosmos")
      cognitive_services_user = contains(var.enable_mcp_tools, "foundry")
      search_contributor      = contains(var.enable_mcp_tools, "search")
      key_vault_secrets_user  = var.mcp_deployment_type != "local"
    }
    authentication_method = "managed_identity_with_key_vault"
  }
}

output "managed_identity" {
  description = "Managed identity details"
  value = (
    var.mcp_deployment_type == "container-app" && length(azurerm_container_app.mcp_server) > 0 ? {
      object_id = azurerm_container_app.mcp_server[0].identity[0].principal_id
      type      = "SystemAssigned"
    } :
    var.mcp_deployment_type == "function" && length(azurerm_linux_function_app.mcp_server) > 0 ? {
      object_id = azurerm_linux_function_app.mcp_server[0].identity[0].principal_id
      type      = "SystemAssigned"
    } :
    var.mcp_deployment_type == "app-service" && length(azurerm_linux_web_app.mcp_server) > 0 ? {
      object_id = azurerm_linux_web_app.mcp_server[0].identity[0].principal_id
      type      = "SystemAssigned"
    } : null
  )
}

# =============================================================================
# CONNECTION STRINGS AND CONFIGURATION
# =============================================================================

output "mcp_configuration" {
  description = "MCP server configuration for clients"
  value = {
    server_url = local.mcp_endpoint
    tools      = var.enable_mcp_tools
    transport  = "http"
    auth_type  = "managed_identity"
  }
}

output "environment_variables" {
  description = "Environment variables for MCP client configuration"
  value = {
    MCP_SERVER_URL      = local.mcp_endpoint
    MCP_TOOLS_ENABLED   = join(",", var.enable_mcp_tools)
    AZURE_TENANT_ID     = data.azurerm_client_config.current.tenant_id
    AZURE_KEY_VAULT_URI = azurerm_key_vault.main.vault_uri
    AUTHENTICATION_TYPE = "managed_identity_with_key_vault"
  }
  sensitive = false
}

# =============================================================================
# NEXT STEPS AND USAGE INFORMATION
# =============================================================================

output "next_steps" {
  description = "Next steps and usage instructions"
  value = {
    quick_start   = "Visit ${local.mcp_endpoint} to access your MCP server"
    documentation = "See README.md for detailed usage instructions"
    monitoring    = var.enable_monitoring ? "View logs and metrics in Azure Portal under Application Insights" : "Monitoring disabled"
    validation    = var.enable_validation ? "Deployment validation completed successfully" : "Validation skipped"
  }
}

output "useful_commands" {
  description = "Useful Azure CLI commands for managing the deployment"
  value = {
    view_logs    = "az containerapp logs show --name ${var.mcp_deployment_type == "container-app" && length(azurerm_container_app.mcp_server) > 0 ? azurerm_container_app.mcp_server[0].name : "N/A"} --resource-group ${azurerm_resource_group.main.name}"
    scale_app    = "az containerapp update --name ${var.mcp_deployment_type == "container-app" && length(azurerm_container_app.mcp_server) > 0 ? azurerm_container_app.mcp_server[0].name : "N/A"} --resource-group ${azurerm_resource_group.main.name} --min-replicas 1 --max-replicas 5"
    check_status = "az group show --name ${azurerm_resource_group.main.name} --query 'properties.provisioningState'"
  }
}

# =============================================================================
# COST INFORMATION
# =============================================================================

output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown (USD)"
  value = {
    disclaimer      = "Costs are estimates and may vary based on usage"
    deployment_type = var.mcp_deployment_type
    estimated_ranges = {
      container_app = "$5-50/month (based on usage)"
      function      = "$0-20/month (consumption plan)"
      app_service   = "$15-100/month (based on SKU)"
      local         = "$0 (local development only)"
    }
    cost_optimization = "Consider using 'function' deployment for development or low-traffic scenarios"
  }
}

# =============================================================================
# TROUBLESHOOTING INFORMATION
# =============================================================================

output "troubleshooting" {
  description = "Common troubleshooting information"
  value = {
    health_check  = "${local.mcp_endpoint}/health"
    logs_location = var.enable_monitoring ? "Azure Portal > Application Insights > Logs" : "Container/Function logs"
    common_issues = {
      connection_failed = "Check if managed identity has proper permissions"
      slow_response     = "Verify AI service quotas and scaling settings"
      deployment_failed = "Review Terraform state and Azure resource logs"
    }
    support_resources = {
      documentation = "https://github.com/MicrosoftCloudEssentials-LearningHub/Azure-MCP-blueprint"
      azure_support = "https://azure.microsoft.com/support/"
      community     = "https://github.com/MicrosoftCloudEssentials-LearningHub/Azure-MCP-blueprint/issues"
    }
  }
}

output "deployment_complete_message" {
  description = "Success message with Terraform-only guidance"
  value       = <<-EOT
    
    🎉 Azure MCP Blueprint Deployment Complete!
    
    📋 Deployment Details:
    • Industry: ${var.selected_industry}
    • Hosting: ${var.mcp_deployment_type} 
    • Endpoint: ${local.mcp_endpoint}
    • Resource Group: ${azurerm_resource_group.main.name}
    
     🚀 Quick Start:
    
     1. Check deployment health:
       curl ${local.mcp_endpoint}/health

     2. List available MCP tools:
       curl ${local.mcp_endpoint}/mcp/tools

     3. Run the included samples:
       - HTTP client: samples/mcp-http-client/
       - Agents: agent-samples/
    
    📚 Documentation: README.md, docs/
    📊 Monitoring: Azure Portal > Application Insights
    
  EOT
}