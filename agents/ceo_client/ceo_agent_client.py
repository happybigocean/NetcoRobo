import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.models.ollama import Ollama
from agno.tools.mcp import MultiMCPTools
from agno.tools.reasoning import ReasoningTools

from config.settings import settings
from agents.knowledge_bases.openai_kb import OpenAIKnowledgeBase
from agents.knowledge_bases.local_kb import LocalKnowledgeBase
from agents.memory.memory_manager import CEOMemoryManager

class CEOAgentClient:
    """
    CEO Agent implemented as MCP Client connecting to multiple MCP servers
    """
    
    def __init__(self):
        self.agent_id = settings.CEO_AGENT_ID
        self.company_kb = settings.get_company_knowledge_base()
        
        # MCP connections
        self.mcp_tools = None
        self.knowledge_bases = {}
        self.agents = {}
        
        # Memory manager
        self.memory_manager = None
        
    async def initialize(self):
        """Initialize the CEO Agent system with MCP connections"""
        try:
            # Setup MCP connections
            await self._setup_mcp_connections()
            
            # Initialize knowledge bases with MCP tools
            await self._setup_knowledge_bases()
            
            # Initialize memory manager
            await self._setup_memory_manager()
            
            # Create specialized agents
            await self._create_agents()
            
            # Log system startup
            await self.mcp_tools.log_system_event(
                event_type="system_startup",
                message=f"CEO Agent Client {self.agent_id} initialized successfully",
                severity="info",
                component="ceo_agent",
                metadata=json.dumps({
                    "agent_id": self.agent_id,
                    "mcp_servers_connected": len(settings.MCP_SERVERS)
                })
            )
            
            print(f"✅ {self.agent_id} initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize {self.agent_id}: {e}")
            return False
    
    async def _setup_mcp_connections(self):
        """Setup connections to all configured MCP servers"""
        
        # Build MCP server configurations
        mcp_server_configs = []
        
        for server_name, config in settings.MCP_SERVERS.items():
            if config.type == "command":
                mcp_config = {
                    "command": config.command,
                    "name": config.name
                }
                if config.env:
                    mcp_config["env"] = config.env
                    
            elif config.type == "http":
                mcp_config = {
                    "url": config.url,
                    "transport": config.transport,
                    "name": config.name
                }
            
            mcp_server_configs.append(mcp_config)
        
        # Connect to all MCP servers
        self.mcp_tools = await MultiMCPTools(
            mcp_server_configs,
            env={
                **dict(os.environ),
                "DATABASE_URL": settings.DATABASE_URL,
                "LOG_LEVEL": settings.LOG_LEVEL
            }
        ).__aenter__()
        
        print(f"🔗 Connected to {len(mcp_server_configs)} MCP servers")
    
    async def _setup_knowledge_bases(self):
        """Initialize knowledge bases with MCP tool access"""
        self.knowledge_bases = {
            "openai": OpenAIKnowledgeBase(mcp_tools=self.mcp_tools),
            "local": LocalKnowledgeBase(mcp_tools=self.mcp_tools)
        }
        
        print("🧠 Knowledge bases initialized")
    
    async def _setup_memory_manager(self):
        """Initialize memory manager with MCP database access"""
        self.memory_manager = CEOMemoryManager(
            agent_id=self.agent_id,
            mcp_tools=self.mcp_tools
        )
        
        print("💾 Memory manager initialized")
    
    async def _create_agents(self):
        """Create specialized Agno agents with MCP tool access"""
        
        # Business Agent (Strategic - OpenAI powered)
        self.agents["business"] = Agent(
            model=OpenAIChat(
                id=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY
            ),
            tools=[
                self.mcp_tools,  # Access to all MCP servers
                ReasoningTools()
            ],
            name="CEO_Business_Agent",
            role="Strategic business operations and decision making",
            instructions=f"""
            You are the strategic business component of {self.agent_id}.
            
            ## Core Identity
            Company: {self.company_kb['identity']['company_name']}
            Mission: {self.company_kb['identity']['mission']}
            Values: {', '.join(self.company_kb['identity']['values'])}
            
            ## Your Responsibilities
            1. **Strategic Planning**: Long-term business strategy and market analysis
            2. **Decision Making**: High-impact business decisions with stakeholder consideration
            3. **Leadership**: Providing vision and direction for the organization
            4. **Stakeholder Management**: External relationships and partnerships
            5. **Resource Allocation**: Strategic budget and resource decisions
            
            ## Available MCP Tools
            - **Database Server**: Store/retrieve business data, decisions, and analytics
            - **Logging Server**: Log all strategic activities and performance metrics
            - **Calendar Server**: Schedule meetings, deadlines, and strategic milestones
            - **Weather Server**: Consider environmental factors for events and operations
            
            ## Operational Guidelines
            - Always use database MCP tools to store important decisions and reasoning
            - Log all significant activities for transparency and audit
            - Schedule follow-up meetings and deadlines using calendar tools
            - Maintain alignment with company mission and values in all decisions
            - Provide strategic context and long-term perspective
            - Consider scalability and future growth implications
            
            ## Decision Framework
            1. Assess strategic alignment with company mission
            2. Analyze stakeholder impact and benefits
            3. Consider resource requirements and ROI
            4. Evaluate risks and mitigation strategies
            5. Plan implementation timeline and milestones
            6. Store decision reasoning in database
            7. Schedule review and follow-up activities
            
            Always provide well-reasoned, strategic responses that advance the company's mission.
            """,
            show_tool_calls=True,
            markdown=True
        )
        
        # Operations Agent (Tactical - Local Ollama powered)  
        self.agents["operations"] = Agent(
            model=Ollama(
                id=settings.OLLAMA_MODEL,
                host=settings.OLLAMA_BASE_URL
            ),
            tools=[
                self.mcp_tools,  # Same MCP tools access
                ReasoningTools()
            ],
            name="CEO_Operations_Agent",
            role="Operational efficiency and tactical execution",
            instructions=f"""
            You are the operational component of {self.agent_id}.
            
            ## Core Focus
            Company: {self.company_kb['identity']['company_name']}
            Role: Operational excellence and efficient execution
            
            ## Your Responsibilities  
            1. **Process Optimization**: Streamline workflows and improve efficiency
            2. **Tactical Execution**: Implement strategic decisions operationally
            3. **Resource Management**: Optimize resource utilization and costs
            4. **Performance Monitoring**: Track KPIs and operational metrics
            5. **System Management**: Ensure smooth operation of all systems
            
            ## Available MCP Tools
            - **Database Server**: Store operational data and performance metrics
            - **Logging Server**: Monitor system performance and operational activities
            - **Calendar Server**: Schedule operational tasks and maintenance
            - **Weather Server**: Plan operations considering environmental factors
            
            ## Operational Guidelines
            - Focus on cost-effectiveness and efficiency in all recommendations
            - Use database tools to track operational metrics and improvements
            - Log all operational activities for performance analysis
            - Schedule regular maintenance and review activities
            - Provide practical, implementable solutions
            - Consider resource constraints and optimization opportunities
            
            ## Decision Framework
            1. Analyze current operational state
            2. Identify efficiency opportunities
            3. Assess resource requirements and constraints
            4. Design practical implementation approach
            5. Plan rollout and monitoring strategy
            6. Store operational data and lessons learned
            7. Schedule performance reviews
            
            Emphasize practical solutions, cost optimization, and efficient execution.
            """,
            show_tool_calls=True,
            markdown=True
        )
        
        # Create coordinated CEO team
        self.ceo_team = Team(
            members=[self.agents["business"], self.agents["operations"]],
            name=f"{self.agent_id}_Team",
            mode="coordinate",
            instructions=f"""
            You are the coordinated CEO Agent team for {self.company_kb['identity']['company_name']}.
            
            ## Team Coordination Model
            **Business Agent**: Handles strategic decisions, market analysis, stakeholder management
            **Operations Agent**: Manages tactical execution, process optimization, resource management
            
            ## Collaboration Guidelines
            1. **Strategic Decisions**: Business Agent leads with Operations Agent providing implementation perspective
            2. **Operational Decisions**: Operations Agent leads with Business Agent ensuring strategic alignment
            3. **Complex Issues**: Both agents collaborate with clear role boundaries
            4. **Resource Allocation**: Joint analysis with Business Agent on strategy, Operations Agent on efficiency
            5. **Performance Review**: Combined strategic and operational perspectives
            
            ## MCP Tool Usage Standards
            - **Always store important decisions** in database with full reasoning
            - **Log all significant activities** for audit and performance tracking
            - **Schedule follow-up actions** using calendar system
            - **Consider external factors** like weather for operational planning
            
            ## Response Framework
            1. **Situation Analysis**: Combined strategic and operational assessment
            2. **Option Generation**: Multiple perspectives from both agents
            3. **Impact Assessment**: Strategic implications + operational feasibility
            4. **Recommendation**: Unified recommendation with clear reasoning
            5. **Implementation Plan**: Detailed steps with timelines and responsibilities
            6. **Monitoring Strategy**: KPIs and review mechanisms
            7. **Documentation**: Store all key information using MCP tools
            
            ## Quality Standards
            - Maintain alignment with company mission: {self.company_kb['identity']['mission']}
            - Uphold company values: {', '.join(self.company_kb['identity']['values'])}
            - Follow governance rules: {self.company_kb['governance_rules']}
            - Enable scalable operations for future growth
            
            Provide comprehensive, actionable responses that leverage both strategic vision and operational excellence.
            """,
            show_tool_calls=True,
            markdown=True
        )
        
        print("🤖 CEO Agent team created with Business and Operations agents")
    
    async def process_request(self, request: str, request_type: str = "general", priority: str = "normal") -> Dict[str, Any]:
        """
        Process incoming requests using the CEO Agent team
        
        Args:
            request: The user request or question
            request_type: Type of request (strategic, operational, general, decision)
            priority: Priority level (low, normal, high, urgent)
        """
        start_time = datetime.now()
        
        try:
            # Log request initiation
            await self.mcp_tools.log_agent_activity(
                agent_id=self.agent_id,
                activity_type="request_processing",
                message=f"Processing {request_type} request: {request[:100]}...",
                level="info",
                metadata=json.dumps({
                    "request_type": request_type,
                    "priority": priority,
                    "request_length": len(request)
                })
            )
            
            # Store request in memory
            await self.memory_manager.store_interaction(
                interaction_type="request",
                content={"request": request, "request_type": request_type, "priority": priority},
                importance=self._calculate_importance(request_type, priority)
            )
            
            # Get relevant context from memory
            context = await self.memory_manager.get_relevant_context(request)
            
            # Enhance request with context and company information
            enhanced_request = f"""
            ## CEO Agent Request Processing
            
            **Company Context:**
            - Company: {self.company_kb['identity']['company_name']}
            - Mission: {self.company_kb['identity']['mission']}
            - Values: {', '.join(self.company_kb['identity']['values'])}
            
            **Request Details:**
            - Type: {request_type}
            - Priority: {priority}
            - Original Request: {request}
            
            **Relevant Context:**
            {json.dumps(context, indent=2) if context else 'No specific context'}
            
            ## Instructions
            1. **Analyze** the request considering company mission and strategic context
            2. **Coordinate** between Business Agent (strategic) and Operations Agent (tactical) as appropriate
            3. **Provide** comprehensive response with clear reasoning and actionable recommendations
            4. **Use MCP tools** to:
               - Store important decisions and reasoning in database
               - Log activities for audit and performance tracking
               - Schedule any required follow-up actions in calendar
               - Consider external factors as relevant
            5. **Ensure** response aligns with company values and governance principles
            
            Provide a comprehensive, actionable response that leverages both strategic insight and operational excellence.
            """
            
            # Process request through CEO team
            team_response = await self.ceo_team.arun(enhanced_request)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Prepare structured response
            result = {
                "response": team_response,
                "request_type": request_type,
                "priority": priority,
                "processing_time_ms": int(processing_time),
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "context_used": bool(context)
            }
            
            # Store response in memory
            await self.memory_manager.store_interaction(
                interaction_type="response", 
                content={
                    "request": request,
                    "response": team_response,
                    "processing_time_ms": int(processing_time)
                },
                importance=self._calculate_importance(request_type, priority)
            )
            
            # Log successful completion
            await self.mcp_tools.log_agent_performance(
                agent_id=self.agent_id,
                operation="request_processing",
                duration_ms=int(processing_time),
                success=True,
                details=json.dumps({
                    "request_type": request_type,
                    "priority": priority,
                    "response_length": len(team_response),
                    "context_used": bool(context)
                })
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log error
            await self.mcp_tools.log_agent_activity(
                agent_id=self.agent_id,
                activity_type="request_processing",
                message=f"Error processing request: {str(e)}",
                level="error",
                metadata=json.dumps({
                    "request_type": request_type,
                    "error_type": type(e).__name__,
                    "processing_time_ms": int(processing_time)
                })
            )
            
            return {
                "response": f"Error processing request: {str(e)}",
                "error": True,
                "request_type": request_type,
                "processing_time_ms": int(processing_time),
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_importance(self, request_type: str, priority: str) -> int:
        """Calculate importance score for memory storage"""
        base_scores = {
            "strategic": 4,
            "decision": 5,
            "operational": 3,
            "general": 2
        }
        
        priority_modifiers = {
            "urgent": 2,
            "high": 1,
            "normal": 0,
            "low": -1
        }
        
        base_score = base_scores.get(request_type, 2)
        modifier = priority_modifiers.get(priority, 0)
        
        return max(1, min(5, base_score + modifier))
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        try:
            # Get system analytics
            analytics = await self.mcp_tools.get_agent_analytics(
                agent_id=self.agent_id,
                days=7
            )
            
            # Get recent memory
            recent_memories = await self.memory_manager.get_recent_memories(limit=10)
            
            status = {
                "agent_id": self.agent_id,
                "status": "active",
                "company": self.company_kb['identity']['company_name'],
                "mission": self.company_kb['identity']['mission'],
                "agents": {
                    "business_agent": {
                        "model": settings.OPENAI_MODEL,
                        "role": "Strategic business operations",
                        "status": "active"
                    },
                    "operations_agent": {
                        "model": settings.OLLAMA_MODEL, 
                        "role": "Operational efficiency",
                        "status": "active"
                    }
                },
                "knowledge_bases": {
                    "openai": {"type": "Strategic/Business", "status": "connected"},
                    "local": {"type": "Operational/Tactical", "status": "connected"}
                },
                "mcp_servers": {
                    server_name: {"status": "connected"}
                    for server_name in settings.MCP_SERVERS.keys()
                },
                "recent_analytics": json.loads(analytics) if isinstance(analytics, str) else analytics,
                "recent_memories": recent_memories,
                "timestamp": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            return {
                "agent_id": self.agent_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup(self):
        """Clean up MCP connections and resources"""
        try:
            if self.mcp_tools:
                await self.mcp_tools.__aexit__(None, None, None)
            print(f"✅ {self.agent_id} cleaned up successfully")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

# Global CEO Agent instance
ceo_agent_client = None

async def get_ceo_agent() -> CEOAgentClient:
    """Get or create global CEO Agent instance"""
    global ceo_agent_client
    if ceo_agent_client is None:
        ceo_agent_client = CEOAgentClient()
        await ceo_agent_client.initialize()
    return ceo_agent_client