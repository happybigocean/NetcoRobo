import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.ceo_client.ceo_agent_client import CEOAgentClient

async def test_ceo_agent_client():
    """Comprehensive test of CEO Agent MCP Client"""
    
    print("🚀 Testing CEO Agent MCP Client System")
    print("=" * 50)
    
    # Initialize CEO Agent
    ceo = CEOAgentClient()
    
    print("1️⃣ Initializing CEO Agent...")
    success = await ceo.initialize()
    if not success:
        print("❌ Initialization failed!")
        return
    print("✅ CEO Agent initialized successfully")
    
    # Test 1: General query
    print("\n2️⃣ Testing General Query...")
    result = await ceo.process_request(
        "What is our company mission and how should we structure our AI development approach?",
        request_type="general",
        priority="normal"
    )
    print(f"✅ Response received (Length: {len(result['response'])} chars)")
    print(f"Processing time: {result['processing_time_ms']}ms")
    
    # Test 2: Strategic business query
    print("\n3️⃣ Testing Strategic Business Query...")
    result = await ceo.process_request(
        "What should be our strategic priorities for expanding into the AI agent marketplace in 2024?",
        request_type="strategic", 
        priority="high"
    )
    print(f"✅ Strategic response received")
    print(f"Agent coordination: {result.get('context_used', False)}")
    
    # Test 3: Operational query
    print("\n4️⃣ Testing Operational Query...")
    result = await ceo.process_request(
        "How can we optimize our local development workflow and reduce infrastructure costs?",
        request_type="operational",
        priority="normal"
    )
    print(f"✅ Operational response received")
    
    # Test 4: Decision support
    print("\n5️⃣ Testing Decision Support...")
    decision_request = """
    We need to choose our primary cloud infrastructure provider for the MCP server ecosystem.
    
    Options:
    1. AWS - Comprehensive services, higher cost, steep learning curve
    2. Google Cloud - AI/ML focused, good pricing, moderate complexity
    3. Digital Ocean - Simple, cost-effective, limited advanced services
    4. Azure - Enterprise integration, Microsoft ecosystem, complex pricing
    
    Consider factors: cost, scalability, ease of use, future growth, AI/ML capabilities.
    """
    
    result = await ceo.process_request(
        decision_request,
        request_type="decision",
        priority="high"
    )
    print(f"✅ Decision analysis completed")
    
    # Test 5: System status
    print("\n6️⃣ Testing System Status...")
    status = await ceo.get_status()
    print(f"✅ System status: {status['status']}")
    print(f"Connected MCP servers: {len(status.get('mcp_servers', {}))}")
    print(f"Active agents: {len(status.get('agents', {}))}")
    print(f"Knowledge bases: {len(status.get('knowledge_bases', {}))}")
    
    # Test 6: Performance under load
    print("\n7️⃣ Testing Performance (Multiple Requests)...")
    start_time = asyncio.get_event_loop().time()
    
    tasks = []
    for i in range(3):
        task = ceo.process_request(
            f"Quick status check #{i+1} - How are our AI agent operations performing?",
            request_type="operational",
            priority="low"
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    total_time = (asyncio.get_event_loop().time() - start_time) * 1000
    
    print(f"✅ Processed {len(results)} concurrent requests")
    print(f"Total time: {total_time:.0f}ms")
    print(f"Average per request: {total_time/len(results):.0f}ms")
    
    # Cleanup
    print("\n8️⃣ Cleaning up...")
    await ceo.cleanup()
    print("✅ Cleanup completed")
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed successfully!")
    print("\nNext steps:")
    print("- Run: streamlit run main.py")
    print("- Test MCP servers individually")
    print("- Set up cloud infrastructure")
    print("- Implement Agentic RAG")

if __name__ == "__main__":
    asyncio.run(test_ceo_agent_client())