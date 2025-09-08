import asyncio
import streamlit as st
from agents.ceo_client.ceo_agent_client import get_ceo_agent
import json
from datetime import datetime

async def initialize_app():
    """Initialize the CEO Agent application"""
    if 'ceo_agent' not in st.session_state:
        with st.spinner("🚀 Initializing CEO Agent System..."):
            st.session_state.ceo_agent = await get_ceo_agent()
    return st.session_state.ceo_agent

def main():
    st.set_page_config(
        page_title="CEO Agent MCP Client System",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 CEO Agent System (MCP Client Architecture)")
    st.markdown("*Dual Knowledge Base AI Agent with OpenAI & Local Ollama + MCP Integration*")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🔧 System Configuration")
        
        st.subheader("Agent Architecture") 
        st.info("""
        **CEO Agent as MCP Client**
        - Business Agent (OpenAI GPT-4o → GPT-5)
        - Operations Agent (Local Llama 3.2:8b)
        - Connected to Multiple MCP Servers
        """)
        
        st.subheader("MCP Servers Connected")
        st.write("🗄️ Database Server")
        st.write("📝 Logging Server") 
        st.write("📅 Calendar Server")
        st.write("🌤️ Weather Server")
        
        # Request type selection
        request_type = st.selectbox(
            "Request Type",
            ["general", "strategic", "operational", "decision"],
            help="Select request type for optimal agent routing"
        )
        
        priority = st.selectbox(
            "Priority Level",
            ["normal", "high", "urgent", "low"],
            help="Set priority for request processing"
        )
        
        # Agent status check
        if st.button("📊 Check System Status"):
            with st.spinner("Checking system status..."):
                try:
                    agent = asyncio.run(initialize_app())
                    status = asyncio.run(agent.get_status())
                    st.json(status)
                except Exception as e:
                    st.error(f"Status check failed: {e}")
    
    # Main interface tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Ask CEO Agent", 
        "🧠 Strategic Decisions", 
        "📊 Performance Dashboard",
        "💾 Memory & Analytics"
    ])
    
    with tab1:
        st.header("Ask the CEO Agent")
        
        user_request = st.text_area(
            "Enter your request:",
            height=120,
            placeholder="Ask about business strategy, operational improvements, or get general guidance..."
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🚀 Process Request", type="primary", use_container_width=True):
                if user_request:
                    with st.spinner("Processing request through CEO Agent team..."):
                        try:
                            agent = asyncio.run(initialize_app())
                            result = asyncio.run(agent.process_request(
                                request=user_request,
                                request_type=request_type,
                                priority=priority
                            ))
                            
                            # Display main response
                            st.subheader("🎯 CEO Agent Response")
                            st.markdown(result.get("response", "No response"))
                            
                            # Display metadata
                            with st.expander("📋 Response Details"):
                                col_a, col_b = st.columns(2)
                                
                                with col_a:
                                    st.metric("Processing Time", f"{result.get('processing_time_ms', 0)} ms")
                                    st.write(f"**Request Type**: {result.get('request_type', 'unknown')}")
                                    st.write(f"**Priority**: {result.get('priority', 'normal')}")
                                
                                with col_b:
                                    st.write(f"**Agent ID**: {result.get('agent_id', 'unknown')}")
                                    st.write(f"**Context Used**: {result.get('context_used', False)}")
                                    st.write(f"**Timestamp**: {result.get('timestamp', 'unknown')}")
                        
                        except Exception as e:
                            st.error(f"Error processing request: {e}")
                else:
                    st.warning("Please enter a request")
        
        with col2:
            st.info("""
            **Request Types:**
            - **General**: Mixed strategic/operational
            - **Strategic**: Business planning, market analysis
            - **Operational**: Process optimization, efficiency
            - **Decision**: Structured decision support
            """)
    
    with tab2:
        st.header("🧠 Strategic Decision Support")
        
        decision_context = st.text_area(
            "Decision Context:",
            height=100,
            placeholder="Describe the situation requiring a strategic decision..."
        )
        
        options_input = st.text_area(
            "Decision Options (one per line):",
            height=80,
            placeholder="Option A: Expand to new market\nOption B: Invest in R&D\nOption C: Strategic partnership"
        )
        
        if st.button("🎯 Get Strategic Recommendation"):
            if decision_context and options_input:
                options_list = [opt.strip() for opt in options_input.split('\n') if opt.strip()]
                
                decision_request = f"""
                ## Strategic Decision Required
                
                **Context:** {decision_context}
                
                **Available Options:**
                {chr(10).join([f"{i+1}. {opt}" for i, opt in enumerate(options_list)])}
                
                Please provide comprehensive strategic analysis including:
                1. Detailed evaluation of each option
                2. Risk/benefit analysis
                3. Strategic alignment assessment
                4. Resource requirement analysis
                5. Implementation timeline
                6. Recommended decision with reasoning
                7. Success metrics and monitoring plan
                """
                
                with st.spinner("Analyzing strategic decision..."):
                    try:
                        agent = asyncio.run(initialize_app())
                        result = asyncio.run(agent.process_request(
                            request=decision_request,
                            request_type="decision",
                            priority="high"
                        ))
                        
                        st.subheader("🎯 Strategic Recommendation")
                        st.markdown(result.get("response", "No recommendation provided"))
                        
                        # Schedule follow-up if needed
                        if st.button("📅 Schedule Follow-up Review"):
                            st.success("Follow-up review scheduled (Calendar MCP integration)")
                        
                    except Exception as e:
                        st.error(f"Decision analysis failed: {e}")
            else:
                st.warning("Please provide both context and options")
    
    with tab3:
        st.header("📊 Performance Dashboard")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("System Metrics")
            if st.button("🔄 Refresh Metrics"):
                try:
                    agent = asyncio.run(initialize_app())
                    status = asyncio.run(agent.get_status())
                    
                    # Display key metrics
                    if "recent_analytics" in status:
                        analytics = status["recent_analytics"]
                        if isinstance(analytics, dict) and analytics.get("success"):
                            interactions = analytics.get("analytics", {}).get("interactions", [])
                            
                            if interactions:
                                for interaction in interactions:
                                    st.metric(
                                        f"{interaction['interaction_type']} Success Rate",
                                        f"{interaction['success_rate']:.1f}%",
                                        f"{interaction['total_count']} total"
                                    )
                
                except Exception as e:
                    st.error(f"Failed to load metrics: {e}")
        
        with col2:
            st.subheader("Agent Status")
            try:
                agent = asyncio.run(initialize_app())
                status = asyncio.run(agent.get_status())
                
                # Agent health indicators
                agents_status = status.get("agents", {})
                for agent_name, agent_info in agents_status.items():
                    st.write(f"**{agent_name}**: {agent_info.get('status', 'unknown')}")
                    st.write(f"   Model: {agent_info.get('model', 'unknown')}")
                
                # MCP servers status
                st.subheader("MCP Servers")
                mcp_status = status.get("mcp_servers", {})
                for server_name, server_info in mcp_status.items():
                    st.write(f"**{server_name}**: {server_info.get('status', 'unknown')}")
                    
            except Exception as e:
                st.error(f"Failed to load status: {e}")
    
    with tab4:
        st.header("💾 Memory & Analytics")
        
        if st.button("🧠 Load Recent Memories"):
            try:
                agent = asyncio.run(initialize_app())
                status = asyncio.run(agent.get_status())
                
                recent_memories = status.get("recent_memories", [])
                
                if recent_memories:
                    st.subheader("Recent Agent Memories")
                    for i, memory in enumerate(recent_memories[:10]):
                        with st.expander(f"Memory {i+1}: {memory.get('memory_type', 'unknown')} - Importance: {memory.get('importance_score', 0)}"):
                            st.write(f"**Timestamp**: {memory.get('timestamp', 'unknown')}")
                            st.json(memory.get('content', {}))
                else:
                    st.info("No recent memories found")
                    
            except Exception as e:
                st.error(f"Failed to load memories: {e}")
        
        # Analytics section
        st.subheader("📈 System Analytics")
        if st.button("📊 Generate Analytics Report"):
            with st.spinner("Generating analytics..."):
                try:
                    agent = asyncio.run(initialize_app())
                    
                    # Request analytics report
                    analytics_request = """
                    Generate a comprehensive analytics report including:
                    1. System performance summary
                    2. Agent utilization statistics
                    3. Knowledge base usage patterns
                    4. MCP server performance metrics
                    5. Memory and storage statistics
                    6. Recommendations for optimization
                    """
                    
                    result = asyncio.run(agent.process_request(
                        request=analytics_request,
                        request_type="operational",
                        priority="normal"
                    ))
                    
                    st.markdown(result.get("response", "No analytics available"))
                    
                except Exception as e:
                    st.error(f"Analytics generation failed: {e}")

if __name__ == "__main__":
    main()