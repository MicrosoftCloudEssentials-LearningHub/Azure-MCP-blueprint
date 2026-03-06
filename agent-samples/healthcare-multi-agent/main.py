"""
Healthcare Multi-Agent Orchestrator
Main entry point for the multi-agent system
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from orchestrator import HealthcareOrchestrator

# Load environment variables
load_dotenv()

async def main():
    """Main execution function"""
    
    # Initialize orchestrator
    orchestrator = HealthcareOrchestrator(
        mcp_endpoint=os.getenv("MCP_ENDPOINT"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        gpt4o_deployment=os.getenv("GPT4O_DEPLOYMENT", "gpt-4o"),
        gpt4o_mini_deployment=os.getenv("GPT4O_MINI_DEPLOYMENT", "gpt-4o-mini")
    )
    
    print("=" * 80)
    print("Healthcare Multi-Agent System")
    print("Powered by Azure MCP Server")
    print("=" * 80)
    print()
    
    # Interactive mode
    if "--interactive" in sys.argv:
        await run_interactive(orchestrator)
    else:
        # Demo queries
        await run_demo(orchestrator)


async def run_interactive(orchestrator):
    """Interactive command-line interface"""
    print("Enter your healthcare queries (type 'exit' to quit):")
    print()
    
    while True:
        query = input("Query: ").strip()
        
        if query.lower() in ['exit', 'quit']:
            break
        
        if not query:
            continue
        
        print()
        print("-" * 80)
        
        try:
            result = await orchestrator.process(query)
            print(result)
        except Exception as e:
            print(f"[ERROR] {str(e)}")
        
        print("-" * 80)
        print()


async def run_demo(orchestrator):
    """Run demo queries"""
    
    demo_queries = [
        "Find all diabetic patients with HbA1c > 7.0",
        "Search for patients allergic to penicillin",
        "Analyze cardiovascular disease patients for high-risk indicators",
        "List patients admitted in the last 30 days",
        "Check medication interactions for patient P12345 with new Warfarin prescription"
    ]
    
    print("Running Demo Queries...")
    print()
    
    for i, query in enumerate(demo_queries, 1):
        print(f"Query {i}: {query}")
        print()
        
        try:
            result = await orchestrator.process(query)
            print(result)
        except Exception as e:
            print(f"[ERROR] {str(e)}")
        
        print()
        print("=" * 80)
        print()
        
        # Small delay between queries
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
