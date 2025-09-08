import os
from typing import Dict, List, Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

load_dotenv()

class MCPServerConfig(BaseSettings):
    """Configuration for individual MCP servers"""
    name: str
    type: str  # "command", "http", "stdio"
    command: Optional[List[str]] = None
    url: Optional[str] = None
    transport: Optional[str] = None
    port: Optional[int] = None
    env: Optional[Dict[str, str]] = None

class AgentSettings(BaseSettings):
    """Main settings for CEO Agent system"""
    
    # Agent Identity
    CEO_AGENT_ID: str = Field(default="CEO_Alpha_Client")
    COMPANY_NAME: str = Field(default="AI Community Corp")
    COMPANY_MISSION: str = Field(default="Build autonomous AI systems for global community empowerment")
    COMPANY_VALUES: str = Field(default="Innovation, Transparency, Scalability, Community-First")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o")  # Will upgrade to GPT-5
    OPENAI_TEMPERATURE: float = Field(default=0.2)
    OPENAI_MAX_TOKENS: int = Field(default=2000)
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama3.2:8b")
    OLLAMA_TEMPERATURE: float = Field(default=0.3)
    
    # Database Configuration
    DATABASE_URL: str = Field(default="sqlite:///./ceo_agent_system.db")
    VECTOR_DB_PATH: str = Field(default="./database/vector_db")
    
    # MCP Server Configurations
    MCP_SERVERS: Dict[str, MCPServerConfig] = Field(default_factory=lambda: {
        "database": MCPServerConfig(
            name="database_server",
            type="command",
            command=["python", "mcp_servers/database/database_mcp_server.py"],
            env={"DATABASE_URL": "sqlite:///./ceo_agent_system.db"}
        ),
        "logging": MCPServerConfig(
            name="logging_server", 
            type="command",
            command=["python", "mcp_servers/logging/logging_mcp_server.py"],
            env={"LOG_LEVEL": "INFO"}
        ),
        "calendar": MCPServerConfig(
            name="calendar_server",
            type="http",
            url="http://localhost:8081/mcp",
            transport="streamable-http"
        ),
        "weather": MCPServerConfig(
            name="weather_server",
            type="command", 
            command=["uvx", "--from", "git+https://github.com/adhikasp/mcp-weather.git", "mcp-weather"],
            env={"WEATHER_API_KEY": os.getenv("WEATHER_API_KEY", "")}
        )
    })
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="./logs/ceo_agent.log")
    STRUCTURED_LOGGING: bool = Field(default=True)
    
    # Memory Configuration
    MEMORY_RETENTION_DAYS: int = Field(default=30)
    SESSION_MEMORY_LIMIT: int = Field(default=100)
    LONG_TERM_MEMORY_LIMIT: int = Field(default=1000)
    
    # Agent Behavior Configuration
    REASONING_ENABLED: bool = Field(default=True)
    MULTI_AGENT_COORDINATION: bool = Field(default=True)
    AUTONOMOUS_LEARNING: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_company_knowledge_base(self) -> Dict:
        """Get structured company knowledge"""
        return {
            "identity": {
                "company_name": self.COMPANY_NAME,
                "mission": self.COMPANY_MISSION,
                "values": self.COMPANY_VALUES.split(", "),
                "agent_id": self.CEO_AGENT_ID
            },
            "governance_rules": [
                "All decisions must align with company mission and values",
                "Maintain transparency in AI operations and decision-making", 
                "Design for scalability to support future agent deployment",
                "Prioritize community benefit in all strategic decisions",
                "Ensure data privacy and security in all operations"
            ],
            "operational_guidelines": [
                "Use OpenAI knowledge base for strategic/business decisions",
                "Use Local Ollama knowledge base for operational/tactical tasks",
                "Leverage MCP tools for data storage, logging, and external integrations",
                "Maintain persistent memory of all interactions and decisions",
                "Coordinate between business and operations agents effectively"
            ],
            "agent_hierarchy": {
                "CEO": {
                    "role": "Strategic oversight and multi-agent coordination",
                    "agents": ["Business Agent", "Operations Agent"],
                    "tools": ["All MCP servers", "Knowledge bases", "Memory system"]
                },
                "Future_Agents": {
                    "CTO": "Technical architecture and implementation oversight",
                    "CFO": "Financial planning and resource allocation management", 
                    "HR": "Agent coordination and workflow optimization"
                }
            }
        }

# Global settings instance
settings = AgentSettings()