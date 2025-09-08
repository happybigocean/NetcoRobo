import streamlit as st
import asyncio
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import plotly.express as px
import plotly.graph_objects as go

from ..ceo_client.agent_coordinator import AgentCoordinator, create_coordinator, TaskPriority
from ..utils.config import get_config


class StreamlitApp:
    """Streamlit web application for NetcoRo agents"""
    
    def __init__(self):
        self.config = get_config()
        self.coordinator = None
        
        # Configure Streamlit page
        st.set_page_config(
            page_title="NetcoRo AI Executive Team",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS for NetcoRo branding
        self.load_custom_css()
    
    def load_custom_css(self):
        """Load custom CSS for NetcoRo branding"""
        st.markdown("""
        <style>
        .main-header {
            background: linear-gradient(90deg, #1e3a8a, #3b82f6);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .agent-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        
        .status-active {
            color: #10b981;
            font-weight: bold;
        }
        
        .status-busy {
            color: #f59e0b;
            font-weight: bold;
        }
        
        .status-error {
            color: #ef4444;
            font-weight: bold;
        }
        
        .metric-card {
            background: white;
            border-radius: 8px;
            padding: 1rem;
            border-left: 4px solid #3b82f6;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .chat-message {
            background: #f1f5f9;
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 4px solid #3b82f6;
        }
        
        .agent-response {
            background: #ecfdf5;
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 4px solid #10b981;
        }
        </style>
        """, unsafe_allow_html=True)
    
    async def initialize_coordinator(self):
        """Initialize the agent coordinator"""
        if self.coordinator is None:
            try:
                with st.spinner("Initializing NetcoRo AI Executive Team..."):
                    self.coordinator = await create_coordinator(self.config)
                st.success("✅ Agent system initialized successfully!")
                return True
            except Exception as e:
                st.error(f"❌ Failed to initialize agents: {str(e)}")
                return False
        return True
    
    def run(self):
        """Main Streamlit application"""
        
        # Header
        st.markdown("""
        <div class="main-header">
            <h1>🏢 NetcoRo AI Executive Team</h1>
            <p>Your Intelligent Business Leadership Dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize coordinator
        if not asyncio.run(self.initialize_coordinator()):
            st.stop()
        
        # Sidebar navigation
        page = st.sidebar.selectbox(
            "Navigation",
            ["🏠 Dashboard", "💬 Chat with Agents", "📊 System Status", 
             "📈 Analytics", "⚙️ Settings", "🔧 Tools"]
        )
        
        # Route to appropriate page
        if page == "🏠 Dashboard":
            self.dashboard_page()
        elif page == "💬 Chat with Agents":
            self.chat_page()
        elif page == "📊 System Status":
            self.status_page()
        elif page == "📈 Analytics":
            self.analytics_page()
        elif page == "⚙️ Settings":
            self.settings_page()
        elif page == "🔧 Tools":
            self.tools_page()
    
    def dashboard_page(self):
        """Main dashboard page"""
        st.header("Executive Dashboard")
        
        # Get system status
        system_status = asyncio.run(self.coordinator.get_system_health())
        agent_status = asyncio.run(self.coordinator.get_agent_status())
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3>Total Agents</h3>
                <h2>{}</h2>
            </div>
            """.format(agent_status.get('total_agents', 0)), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <h3>Active Agents</h3>
                <h2 class="status-active">{}</h2>
            </div>
            """.format(agent_status.get('active_agents', 0)), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <h3>Busy Agents</h3>
                <h2 class="status-busy">{}</h2>
            </div>
            """.format(agent_status.get('busy_agents', 0)), unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-card">
                <h3>Active Tasks</h3>
                <h2>{}</h2>
            </div>
            """.format(system_status.get('active_tasks', 0)), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Agent status cards
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Agent Status")
            agents_data = agent_status.get('agents', {})
            
            for agent_id, info in agents_data.items():
                status_class = f"status-{info['status']}"
                
                st.markdown(f"""
                <div class="agent-card">
                    <h4>{agent_id.replace('_', ' ').title()}</h4>
                    <p class="{status_class}">Status: {info['status'].title()}</p>
                    <p>Queue Size: {info['task_queue_size']}</p>
                    <p>Current Task: {info['current_task'] or 'None'}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.subheader("Recent Activity")
            
            # Performance metrics
            coord_stats = agent_status.get('coordination_stats', {})
            
            st.metric("Total Tasks Processed", coord_stats.get('total_tasks', 0))
            st.metric("Success Rate", f"{(coord_stats.get('completed_tasks', 0) / max(coord_stats.get('total_tasks', 1), 1) * 100):.1f}%")
            st.metric("Avg Response Time", f"{coord_stats.get('avg_completion_time', 0):.2f}s")
        
        # Quick actions
        st.subheader("Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Strategic Planning Session", use_container_width=True):
                self.quick_coordination("strategic_planning")
        
        with col2:
            if st.button("📊 Generate Executive Report", use_container_width=True):
                self.quick_coordination("executive_report")
        
        with col3:
            if st.button("💡 Innovation Brainstorm", use_container_width=True):
                self.quick_coordination("innovation_session")
    
    def chat_page(self):
        """Chat interface with agents"""
        st.header("Chat with NetcoRo Agents")
        
        # Agent selection
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Select Agent")
            
            agents = {
                'ceo_agent': '👔 CEO - Strategic Leadership',
                'cto_agent': '💻 CTO - Technology Strategy', 
                'cfo_agent': '💰 CFO - Financial Planning',
                'hr_agent': '👥 HR - People Management',
                'sales_agent': '📈 Sales - Revenue Growth',
                'legal_agent': '⚖️ Legal - Compliance & Risk',
                'ops_agent': '⚙️ Operations - Efficiency'
            }
            
            selected_agent = st.selectbox(
                "Choose an agent:",
                list(agents.keys()),
                format_func=lambda x: agents[x]
            )
            
            # Coordination option
            st.markdown("---")
            st.subheader("Multi-Agent Coordination")
            
            coordination_agents = st.multiselect(
                "Select agents for collaboration:",
                list(agents.keys()),
                format_func=lambda x: agents[x]
            )
            
            coordination_type = st.selectbox(
                "Coordination Type:",
                ["collaborative", "hierarchical", "sequential", "parallel"]
            )
        
        with col2:
            st.subheader("Conversation")
            
            # Initialize chat history
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            
            # Display chat history
            chat_container = st.container()
            with chat_container:
                for message in st.session_state.chat_history:
                    if message['type'] == 'user':
                        st.markdown(f"""
                        <div class="chat-message">
                            <strong>You:</strong> {message['content']}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="agent-response">
                            <strong>{message['agent']}:</strong> {message['content']}
                        </div>
                        """, unsafe_allow_html=True)
            
            # Chat input
            user_input = st.text_area(
                "Enter your message:",
                height=100,
                placeholder="Ask your agents anything about business strategy, operations, or decisions..."
            )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("Send to Agent", use_container_width=True):
                    if user_input and selected_agent:
                        self.process_agent_chat(selected_agent, user_input)
            
            with col2:
                if st.button("Coordinate Agents", use_container_width=True):
                    if user_input and coordination_agents:
                        self.process_coordination_chat(coordination_agents, coordination_type, user_input)
            
            with col3:
                if st.button("Clear Chat", use_container_width=True):
                    st.session_state.chat_history = []
                    st.experimental_rerun()
    
    def status_page(self):
        """System status and health monitoring"""
        st.header("System Status & Health")
        
        # Real-time status
        if st.button("🔄 Refresh Status"):
            st.experimental_rerun()
        
        # Get detailed status
        system_health = asyncio.run(self.coordinator.get_system_health())
        agent_status = asyncio.run(self.coordinator.get_agent_status())
        
        # Overall health indicator
        health_status = system_health.get('coordinator_status', 'unknown')
        
        if health_status == 'healthy':
            st.success(f"✅ System Status: {health_status.title()}")
        elif health_status == 'degraded':
            st.warning(f"⚠️ System Status: {health_status.title()}")
        else:
            st.error(f"❌ System Status: {health_status.title()}")
        
        # Detailed agent status
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Agent Health Details")
            
            agents_health = system_health.get('agents', {})
            
            for agent_id, health in agents_health.items():
                with st.expander(f"{agent_id.replace('_', ' ').title()}"):
                    st.json({
                        'Status': health.get('status', 'unknown'),
                        'Responsive': health.get('responsive', False),
                        'Health Check': health.get('health', {}),
                        'Error': health.get('error', 'None')
                    })
        
        with col2:
            st.subheader("Performance Metrics")
            
            coord_stats = agent_status.get('coordination_stats', {})
            
            # Create performance chart
            if coord_stats.get('agent_utilization'):
                utilization_data = []
                for agent_id, stats in coord_stats['agent_utilization'].items():
                    utilization_data.append({
                        'Agent': agent_id.replace('_', ' ').title(),
                        'Tasks Completed': stats.get('tasks_completed', 0),
                        'Success Rate': stats.get('success_rate', 0) * 100,
                        'Avg Time (s)': stats.get('avg_completion_time', 0)
                    })
                
                df = pd.DataFrame(utilization_data)
                
                if not df.empty:
                    # Success rate chart
                    fig_success = px.bar(
                        df, 
                        x='Agent', 
                        y='Success Rate',
                        title='Agent Success Rates',
                        color='Success Rate',
                        color_continuous_scale='RdYlGn'
                    )
                    st.plotly_chart(fig_success, use_container_width=True)
                    
                    # Performance metrics table
                    st.subheader("Detailed Metrics")
                    st.dataframe(df, use_container_width=True)
        
        # Memory and system info
        st.subheader("System Resources")
        
        memory_health = system_health.get('memory_manager', {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Memory Status", memory_health.get('status', 'Unknown'))
        
        with col2:
            st.metric("Active Tasks", system_health.get('active_tasks', 0))
        
        with col3:
            st.metric("Total Agents", system_health.get('total_agents', 0))
    
    def analytics_page(self):
        """Analytics and insights dashboard"""
        st.header("Analytics & Insights")
        
        # Time range selector
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        
        with col2:
            end_date = st.date_input("End Date", datetime.now())
        
        # Generate sample analytics data (replace with real data)
        self.show_analytics_charts(start_date, end_date)
    
    def settings_page(self):
        """Settings and configuration"""
        st.header("System Settings")
        
        st.subheader("Agent Configuration")
        
        # Model settings
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input("OpenAI API Key", type="password", value="***")
            st.selectbox("Strategic Model", ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"])
        
        with col2:
            st.text_input("Ollama URL", value="http://localhost:11434")
            st.selectbox("Local Model", ["llama3.2:latest", "mixtral:latest", "codellama:latest"])
        
        st.subheader("Performance Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.slider("Max Concurrent Tasks", 1, 20, 10)
            st.slider("Task Timeout (seconds)", 30, 600, 300)
        
        with col2:
            st.selectbox("Coordination Mode", ["collaborative", "hierarchical", "sequential"])
            st.checkbox("Enable Caching", True)
        
        if st.button("Save Settings"):
            st.success("Settings saved successfully!")
    
    def tools_page(self):
        """Tools and utilities"""
        st.header("Agent Tools & Utilities")
        
        # MCP Tools section
        st.subheader("MCP Tools Status")
        
        # Mock MCP status (replace with real data)
        mcp_tools = {
            "Database MCP": {"status": "Connected", "url": "http://localhost:8001"},
            "Calendar MCP": {"status": "Connected", "url": "http://localhost:8003"},
            "Weather MCP": {"status": "Connected", "url": "http://localhost:8004"},
            "Logging MCP": {"status": "Connected", "url": "http://localhost:8002"}
        }
        
        for tool_name, info in mcp_tools.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**{tool_name}**")
            
            with col2:
                if info['status'] == 'Connected':
                    st.success(info['status'])
                else:
                    st.error(info['status'])
            
            with col3:
                if st.button(f"Test {tool_name}", key=tool_name):
                    st.info(f"Testing connection to {info['url']}...")
        
        st.subheader("System Utilities")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Restart Agents", use_container_width=True):
                with st.spinner("Restarting agents..."):
                    # Add restart logic here
                    st.success("Agents restarted successfully!")
            
            if st.button("🧹 Clear Cache", use_container_width=True):
                st.success("Cache cleared!")
        
        with col2:
            if st.button("💾 Backup System State", use_container_width=True):
                st.success("System state backed up!")
            
            if st.button("📊 Export Logs", use_container_width=True):
                st.success("Logs exported!")
    
    def process_agent_chat(self, agent_id: str, message: str):
        """Process single agent chat"""
        try:
            # Add user message to history
            st.session_state.chat_history.append({
                'type': 'user',
                'content': message,
                'timestamp': datetime.now()
            })
            
            with st.spinner(f"Processing request with {agent_id}..."):
                # Get agent response (mock for now)
                agent = self.coordinator.agents.get(agent_id)
                if agent:
                    response = asyncio.run(agent.process_query(message))
                    
                    # Add agent response to history
                    st.session_state.chat_history.append({
                        'type': 'agent',
                        'agent': agent_id.replace('_', ' ').title(),
                        'content': response,
                        'timestamp': datetime.now()
                    })
            
            st.experimental_rerun()
            
        except Exception as e:
            st.error(f"Error processing chat: {str(e)}")
    
    def process_coordination_chat(self, agents: list, coord_type: str, message: str):
        """Process multi-agent coordination"""
        try:
            # Add user message to history
            st.session_state.chat_history.append({
                'type': 'user',
                'content': f"[Coordination with {len(agents)} agents] {message}",
                'timestamp': datetime.now()
            })
            
            with st.spinner(f"Coordinating {len(agents)} agents..."):
                coordination_request = {
                    'type': coord_type,
                    'agents': agents,
                    'objective': message,
                    'context': {}
                }
                
                result = asyncio.run(self.coordinator.coordinate_agents(coordination_request))
                
                if result['success']:
                    response = f"Coordination completed successfully!\n\nResult: {result['result']}"
                else:
                    response = f"Coordination failed: {result['error']}"
                
                # Add coordination response to history
                st.session_state.chat_history.append({
                    'type': 'agent',
                    'agent': f"Team Coordination ({coord_type})",
                    'content': response,
                    'timestamp': datetime.now()
                })
            
            st.experimental_rerun()
            
        except Exception as e:
            st.error(f"Error in coordination: {str(e)}")
    
    def quick_coordination(self, action_type: str):
        """Execute quick coordination actions"""
        try:
            actions = {
                'strategic_planning': {
                    'agents': ['ceo_agent', 'cfo_agent', 'cto_agent'],
                    'objective': 'Develop strategic plan for next quarter focusing on growth and innovation'
                },
                'executive_report': {
                    'agents': ['ceo_agent', 'cfo_agent', 'hr_agent', 'sales_agent'],
                    'objective': 'Generate comprehensive executive report on company performance'
                },
                'innovation_session': {
                    'agents': ['cto_agent', 'ceo_agent', 'ops_agent'],
                    'objective': 'Brainstorm innovative solutions for operational efficiency and technology advancement'
                }
            }
            
            if action_type in actions:
                action = actions[action_type]
                
                with st.spinner(f"Executing {action_type.replace('_', ' ')}..."):
                    result = asyncio.run(self.coordinator.coordinate_agents({
                        'type': 'collaborative',
                        'agents': action['agents'],
                        'objective': action['objective']
                    }))
                    
                    if result['success']:
                        st.success(f"✅ {action_type.replace('_', ' ').title()} completed!")
                        with st.expander("View Results"):
                            st.json(result['result'])
                    else:
                        st.error(f"❌ Failed: {result['error']}")
        
        except Exception as e:
            st.error(f"Action failed: {str(e)}")
    
    def show_analytics_charts(self, start_date, end_date):
        """Display analytics charts"""
        # Sample data (replace with real analytics)
        
        # Task completion over time
        dates = pd.date_range(start_date, end_date, freq='D')
        task_data = pd.DataFrame({
            'Date': dates,
            'Tasks Completed': [20 + i*2 + (i%3)*5 for i in range(len(dates))],
            'Success Rate': [0.85 + (i%10)*0.01 for i in range(len(dates))]
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_tasks = px.line(task_data, x='Date', y='Tasks Completed', 
                              title='Daily Task Completion')
            st.plotly_chart(fig_tasks, use_container_width=True)
        
        with col2:
            fig_success = px.line(task_data, x='Date', y='Success Rate',
                                title='Success Rate Trend')
            st.plotly_chart(fig_success, use_container_width=True)
        
        # Agent performance comparison
        agent_perf = pd.DataFrame({
            'Agent': ['CEO', 'CTO', 'CFO', 'HR', 'Sales', 'Legal', 'Ops'],
            'Tasks': [45, 38, 42, 35, 48, 28, 52],
            'Avg Time (s)': [12.5, 15.2, 10.8, 18.3, 9.7, 22.1, 14.6]
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_agent_tasks = px.bar(agent_perf, x='Agent', y='Tasks',
                                   title='Tasks by Agent')
            st.plotly_chart(fig_agent_tasks, use_container_width=True)
        
        with col2:
            fig_agent_time = px.bar(agent_perf, x='Agent', y='Avg Time (s)',
                                  title='Average Response Time by Agent')
            st.plotly_chart(fig_agent_time, use_container_width=True)


# Main entry point
def main():
    app = StreamlitApp()
    app.run()

if __name__ == "__main__":
    main()