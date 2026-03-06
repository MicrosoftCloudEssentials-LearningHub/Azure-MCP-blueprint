#!/usr/bin/env python3
"""
Azure MCP Server Validation Script
Post-deployment validation and testing
"""

import argparse
import logging
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

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
        self.protocol_version: Optional[str] = None

        # Streamable HTTP requires Accept including application/json and text/event-stream.
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        })

    def _mcp_post(self, payload: Dict[str, Any]) -> requests.Response:
        headers: Dict[str, str] = {}
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        return self.session.post(
            f"{self.endpoint}/mcp",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

    def _mcp_initialize(self) -> bool:
        init: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "mcp-validator", "version": "1.0.0"},
            },
        }
        resp = self._mcp_post(init)
        if resp.status_code != 200:
            logger.error(f"MCP initialize failed: {resp.status_code} {resp.text}")
            return False
        payload = resp.json()
        if "error" in payload:
            logger.error(f"MCP initialize error: {payload['error']}")
            return False
        self.protocol_version = payload.get("result", {}).get("protocolVersion")
        if not self.protocol_version:
            logger.error("MCP initialize missing protocolVersion")
            return False

        initialized: Dict[str, Any] = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self._mcp_post(initialized)
        return True
    
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
        
        results: List[Tuple[str, bool, Optional[str]]] = []
        
        for step_name, test_func in validation_steps:
            logger.info(f"Running {step_name} validation...")
            try:
                result = test_func()
                results.append((step_name, result, None))
                if result:
                    logger.info(f"[PASS] {step_name}")
                else:
                    logger.error(f"[FAIL] {step_name}")
            except Exception as e:
                logger.error(f"[ERROR] {step_name}: {e}")
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
        """Test MCP Streamable HTTP endpoint"""
        try:
            if not self._mcp_initialize():
                return False

            for method in ["tools/list", "resources/list", "prompts/list"]:
                req: Dict[str, Any] = {"jsonrpc": "2.0", "id": 2, "method": method, "params": {}}
                response = self._mcp_post(req)
                if response.status_code != 200:
                    logger.error(f"{method} failed: {response.status_code}")
                    return False
                payload = response.json()
                if "error" in payload:
                    logger.error(f"{method} error: {payload['error']}")
                    return False

            return True
        
        except Exception as e:
            logger.error(f"MCP protocol test failed: {e}")
            return False
    
    def _test_tool_availability(self) -> bool:
        """Test that enabled tools are available"""
        try:
            req: Dict[str, Any] = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
            response = self._mcp_post(req)
            if response.status_code != 200:
                return False

            payload = response.json()
            if "error" in payload:
                logger.error(f"tools/list error: {payload['error']}")
                return False

            available_tools = [tool["name"] for tool in payload.get("result", {}).get("tools", [])]
            
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
            tool_call: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "health_check", "arguments": {}},
            }
            response = self._mcp_post(tool_call)
            if response.status_code != 200:
                logger.error(f"Tool execution failed: {response.status_code}")
                return False

            payload = response.json()
            if "error" in payload:
                logger.error(f"Tool execution error: {payload['error']}")
                return False
            result = payload.get("result", {})
            if result.get("isError", False):
                logger.error("Tool execution returned isError")
                return False

            if "content" not in result:
                logger.error("Tool execution result missing content")
                return False
            
            logger.info("Tool execution test successful")
            return True
        
        except Exception as e:
            logger.error(f"Tool execution test failed: {e}")
            return False
    
    def _test_resource_access(self) -> bool:
        """Test resource access"""
        try:
            req: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "resources/read",
                "params": {"uri": "azure://mcp/server/status"},
            }
            response = self._mcp_post(req)
            if response.status_code != 200:
                logger.error(f"Resource read failed: {response.status_code}")
                return False

            payload = response.json()
            if "error" in payload:
                logger.error(f"Resource read error: {payload['error']}")
                return False
            contents = payload.get("result", {}).get("contents")
            if not isinstance(contents, list) or not contents:
                logger.error("Invalid resources/read response format")
                return False
            
            logger.info("Resource access test successful")
            return True
        
        except Exception as e:
            logger.error(f"Resource access test failed: {e}")
            return False
    
    def _test_error_handling(self) -> bool:
        """Test error handling"""
        try:
            invalid_tool_call: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "invalid_tool", "arguments": {}},
            }

            response = self._mcp_post(invalid_tool_call)
            if response.status_code != 200:
                logger.error(f"Error handling test failed: {response.status_code}")
                return False

            payload = response.json()
            if "error" not in payload:
                logger.error("Expected JSON-RPC error for invalid tool")
                return False
            
            logger.info("Error handling test successful")
            return True
        
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    def _print_validation_summary(self, results: List[Tuple[str, bool, Optional[str]]]):
        """Print validation summary"""
        logger.info("\n" + "="*50)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*50)
        
        passed = sum(1 for _, result, _ in results if result)
        total = len(results)
        
        for step_name, result, error in results:
            status = "PASSED" if result else "FAILED"
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