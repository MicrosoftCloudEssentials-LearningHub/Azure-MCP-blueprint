#!/usr/bin/env python3
"""
Azure MCP Server Validation Script
Post-deployment validation and testing
"""

import argparse
import json
import logging
import sys
import time
from typing import Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPValidator:
    """Validates MCP server deployment and functionality"""
    
    def __init__(self, endpoint: str, tools: List[str], deployment_type: str):
        self.endpoint = endpoint.rstrip('/')
        # Terraform and docs may refer to Azure OpenAI as "foundry".
        # The MCP server exposes this capability via the "openai" service/tools.
        self.tools = ["openai" if t == "foundry" else t for t in tools]
        self.deployment_type = deployment_type
        self.session = requests.Session()
        self.timeout = 30
    
    def validate(self) -> bool:
        """Run comprehensive validation"""
        logger.info(f"Starting validation for {self.endpoint}")
        
        validation_steps = [
            ("Basic Connectivity", self._test_basic_connectivity),
            ("Health Check", self._test_health_check),
            ("MCP Protocol", self._test_mcp_protocol),
            ("Tool Availability", self._test_tool_availability),
            ("Tool Execution", self._test_tool_execution),
            ("Resource Access", self._test_resource_access),
            ("Error Handling", self._test_error_handling)
        ]
        
        results = []
        
        for step_name, test_func in validation_steps:
            logger.info(f"Running {step_name} validation...")
            try:
                result = test_func()
                results.append((step_name, result, None))
                if result:
                    logger.info(f"✅ {step_name}: PASSED")
                else:
                    logger.error(f"❌ {step_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {step_name}: ERROR - {e}")
                results.append((step_name, False, str(e)))
        
        # Print summary
        self._print_validation_summary(results)
        
        # Return overall success
        return all(result[1] for result in results)
    
    def _test_basic_connectivity(self) -> bool:
        """Test basic HTTP connectivity"""
        try:
            response = self.session.get(f"{self.endpoint}/", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Basic connectivity failed: {e}")
            return False
    
    def _test_health_check(self) -> bool:
        """Test health check endpoint"""
        try:
            response = self.session.get(f"{self.endpoint}/health", timeout=self.timeout)
            if response.status_code != 200:
                return False
            
            health_data = response.json()
            
            # Validate health response structure
            required_fields = ["server", "services", "tools_count"]
            for field in required_fields:
                if field not in health_data:
                    logger.error(f"Missing field in health response: {field}")
                    return False
            
            # Check service availability based on enabled tools
            services = health_data.get("services", {})
            for tool in self.tools:
                if tool == "cosmos" and not services.get("cosmos_db", False):
                    logger.warning("Cosmos DB not available but tool is enabled")
                elif tool == "search" and not services.get("ai_search", False):
                    logger.warning("AI Search not available but tool is enabled")
                elif tool == "openai" and not services.get("openai", False):
                    logger.warning("OpenAI not available but tool is enabled")
            
            return True
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def _test_mcp_protocol(self) -> bool:
        """Test MCP protocol endpoints"""
        try:
            # Test tools endpoint
            response = self.session.get(f"{self.endpoint}/mcp/tools", timeout=self.timeout)
            if response.status_code != 200:
                logger.error(f"Tools endpoint failed: {response.status_code}")
                return False
            
            tools_data = response.json()
            if "tools" not in tools_data:
                logger.error("Invalid tools response format")
                return False
            
            # Test resources endpoint
            response = self.session.get(f"{self.endpoint}/mcp/resources", timeout=self.timeout)
            if response.status_code != 200:
                logger.error(f"Resources endpoint failed: {response.status_code}")
                return False
            
            # Test prompts endpoint
            response = self.session.get(f"{self.endpoint}/mcp/prompts", timeout=self.timeout)
            if response.status_code != 200:
                logger.error(f"Prompts endpoint failed: {response.status_code}")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"MCP protocol test failed: {e}")
            return False
    
    def _test_tool_availability(self) -> bool:
        """Test that enabled tools are available"""
        try:
            response = self.session.get(f"{self.endpoint}/mcp/tools", timeout=self.timeout)
            if response.status_code != 200:
                return False
            
            tools_data = response.json()
            available_tools = [tool["name"] for tool in tools_data["tools"]]
            
            # Check for required tools based on enabled services
            expected_tools = ["health_check"]  # Always available
            
            if "cosmos" in self.tools:
                expected_tools.extend(["cosmos_create_item", "cosmos_query_items"])
            if "search" in self.tools:
                expected_tools.extend(["search_documents", "search_semantic"])
            if "openai" in self.tools:
                expected_tools.extend(["openai_chat_completion", "openai_embeddings"])
            
            missing_tools = [tool for tool in expected_tools if tool not in available_tools]
            if missing_tools:
                logger.error(f"Missing expected tools: {missing_tools}")
                return False
            
            logger.info(f"Available tools: {available_tools}")
            return True
        
        except Exception as e:
            logger.error(f"Tool availability test failed: {e}")
            return False
    
    def _test_tool_execution(self) -> bool:
        """Test tool execution"""
        try:
            # Test health check tool
            tool_call = {
                "name": "health_check",
                "arguments": {}
            }
            
            response = self.session.post(
                f"{self.endpoint}/mcp/execute",
                json=tool_call,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            
            if response.status_code != 200:
                logger.error(f"Tool execution failed: {response.status_code}")
                return False
            
            result = response.json()
            if result.get("isError", False):
                logger.error(f"Tool execution returned error: {result.get('errorMessage')}")
                return False
            
            # Verify response has content
            if "content" not in result:
                logger.error("Tool execution response missing content")
                return False
            
            logger.info("Tool execution test successful")
            return True
        
        except Exception as e:
            logger.error(f"Tool execution test failed: {e}")
            return False
    
    def _test_resource_access(self) -> bool:
        """Test resource access"""
        try:
            # Test server status resource
            response = self.session.get(f"{self.endpoint}/mcp/resources/mcp/server/status", timeout=self.timeout)
            if response.status_code != 200:
                logger.error(f"Resource access failed: {response.status_code}")
                return False
            
            resource_data = response.json()
            if not isinstance(resource_data, dict):
                logger.error("Invalid resource response format")
                return False
            
            logger.info("Resource access test successful")
            return True
        
        except Exception as e:
            logger.error(f"Resource access test failed: {e}")
            return False
    
    def _test_error_handling(self) -> bool:
        """Test error handling"""
        try:
            # Test invalid tool execution
            invalid_tool_call = {
                "name": "invalid_tool",
                "arguments": {}
            }
            
            response = self.session.post(
                f"{self.endpoint}/mcp/execute",
                json=invalid_tool_call,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            
            if response.status_code != 200:
                logger.error(f"Error handling test failed: {response.status_code}")
                return False
            
            result = response.json()
            if not result.get("isError", False):
                logger.error("Expected error response for invalid tool")
                return False
            
            if not result.get("errorMessage"):
                logger.error("Error response missing error message")
                return False
            
            logger.info("Error handling test successful")
            return True
        
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    def _print_validation_summary(self, results: List[tuple]):
        """Print validation summary"""
        logger.info("\n" + "="*50)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*50)
        
        passed = sum(1 for _, result, _ in results if result)
        total = len(results)
        
        for step_name, result, error in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{step_name:<20} {status}")
            if error:
                logger.info(f"  Error: {error}")
        
        logger.info("-" * 50)
        logger.info(f"Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All validation tests passed!")
            logger.info(f"MCP Server is ready at: {self.endpoint}")
        else:
            logger.error(f"⚠️  {total - passed} validation tests failed")
        
        logger.info("="*50)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate Azure MCP Server deployment")
    parser.add_argument("--endpoint", required=True, help="MCP server endpoint URL")
    parser.add_argument("--tools", required=True, help="Comma-separated list of enabled tools")
    parser.add_argument("--deployment-type", required=True, help="Deployment type")
    
    args = parser.parse_args()
    
    tools = [tool.strip() for tool in args.tools.split(",")]
    
    validator = MCPValidator(
        endpoint=args.endpoint,
        tools=tools,
        deployment_type=args.deployment_type
    )
    
    # Wait a moment for services to be ready
    logger.info("Waiting for services to initialize...")
    time.sleep(10)
    
    success = validator.validate()
    
    if success:
        logger.info("Validation completed successfully!")
        sys.exit(0)
    else:
        logger.error("Validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()