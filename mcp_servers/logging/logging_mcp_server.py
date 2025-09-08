import asyncio
import json
import logging
import structlog
from datetime import datetime
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
import os

# Initialize MCP server
logging_mcp = FastMCP("CEO Agent Logging Server")

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Setup loggers
ceo_logger = structlog.get_logger("ceo_agent")
business_logger = structlog.get_logger("business_agent")
operations_logger = structlog.get_logger("operations_agent")
system_logger = structlog.get_logger("system")

# Configure file handlers
log_level = os.getenv("LOG_LEVEL", "INFO")
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)

# Setup file handlers
file_handler = logging.FileHandler(f"{log_dir}/ceo_agent_system.log")
file_handler.setLevel(getattr(logging, log_level))
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Add handler to root logger
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)
root_logger.setLevel(getattr(logging, log_level))

@logging_mcp.tool()
async def log_agent_activity(
    agent_id: str,
    activity_type: str,
    message: str,
    level: str = "info",
    metadata: str = "{}"
) -> str:
    """
    Log agent activity with structured data
    
    Args:
        agent_id: ID of the agent performing activity
        activity_type: Type of activity (query, decision, reasoning, error)
        message: Log message
        level: Log level (debug, info, warning, error, critical)
        metadata: Additional metadata as JSON string
    """
    try:
        metadata_dict = json.loads(metadata) if metadata else {}
        
        # Select appropriate logger based on agent
        if "business" in agent_id.lower():
            logger = business_logger
        elif "operations" in agent_id.lower():
            logger = operations_logger
        else:
            logger = ceo_logger
        
        # Log with structured data
        log_data = {
            "agent_id": agent_id,
            "activity_type": activity_type,
            "timestamp": datetime.now().isoformat(),
            **metadata_dict
        }
        
        # Log at appropriate level
        if level.lower() == "debug":
            logger.debug(message, **log_data)
        elif level.lower() == "warning":
            logger.warning(message, **log_data)
        elif level.lower() == "error":
            logger.error(message, **log_data)
        elif level.lower() == "critical":
            logger.critical(message, **log_data)
        else:
            logger.info(message, **log_data)
        
        return json.dumps({
            "success": True,
            "message": f"Activity logged for {agent_id}",
            "log_level": level,
            "activity_type": activity_type
        })
        
    except Exception as e:
        system_logger.error(f"Failed to log activity: {str(e)}", 
                           agent_id=agent_id, activity_type=activity_type)
        return json.dumps({
            "success": False,
            "error": f"Failed to log activity: {str(e)}"
        })

@logging_mcp.tool()
async def log_agent_performance(
    agent_id: str,
    operation: str,
    duration_ms: int,
    success: bool,
    details: str = "{}"
) -> str:
    """
    Log agent performance metrics
    
    Args:
        agent_id: ID of the agent
        operation: Operation performed
        duration_ms: Duration in milliseconds
        success: Whether operation was successful
        details: Additional details as JSON string
    """
    try:
        details_dict = json.loads(details) if details else {}
        
        performance_data = {
            "agent_id": agent_id,
            "operation": operation,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            **details_dict
        }
        
        if success:
            ceo_logger.info(
                f"Operation completed: {operation}",
                **performance_data
            )
        else:
            ceo_logger.warning(
                f"Operation failed: {operation}",
                **performance_data
            )
        
        return json.dumps({
            "success": True,
            "message": f"Performance logged for {agent_id}",
            "operation": operation,
            "duration_ms": duration_ms
        })
        
    except Exception as e:
        system_logger.error(f"Failed to log performance: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Failed to log performance: {str(e)}"
        })

@logging_mcp.tool()
async def log_system_event(
    event_type: str,
    message: str,
    severity: str = "info",
    component: str = "system",
    metadata: str = "{}"
) -> str:
    """
    Log system-level events
    
    Args:
        event_type: Type of event (startup, shutdown, error, configuration)
        message: Event message
        severity: Event severity (info, warning, error, critical)
        component: System component (agent, mcp_server, database)
        metadata: Additional metadata as JSON string
    """
    try:
        metadata_dict = json.loads(metadata) if metadata else {}
        
        event_data = {
            "event_type": event_type,
            "component": component,
            "timestamp": datetime.now().isoformat(),
            **metadata_dict
        }
        
        if severity.lower() == "warning":
            system_logger.warning(message, **event_data)
        elif severity.lower() == "error":
            system_logger.error(message, **event_data)
        elif severity.lower() == "critical":
            system_logger.critical(message, **event_data)
        else:
            system_logger.info(message, **event_data)
        
        return json.dumps({
            "success": True,
            "message": f"System event logged: {event_type}",
            "severity": severity,
            "component": component
        })
        
    except Exception as e:
        print(f"Critical logging failure: {e}")  # Fallback to print
        return json.dumps({
            "success": False,
            "error": f"Failed to log system event: {str(e)}"
        })

@logging_mcp.tool()
async def get_recent_logs(
    agent_id: str = "",
    activity_type: str = "",
    level: str = "",
    limit: int = 100
) -> str:
    """
    Retrieve recent logs (Note: This is a simple implementation)
    In production, you'd want to integrate with a proper log management system
    
    Args:
        agent_id: Filter by agent ID
        activity_type: Filter by activity type
        level: Filter by log level
        limit: Maximum number of logs to return
    """
    try:
        # This is a simplified implementation
        # In production, integrate with proper log aggregation system
        
        logs_info = {
            "message": "Recent logs retrieval",
            "note": "This is a simplified implementation. Integrate with log aggregation system for production use.",
            "filters": {
                "agent_id": agent_id or "all",
                "activity_type": activity_type or "all", 
                "level": level or "all",
                "limit": limit
            },
            "log_files": [
                f"{log_dir}/ceo_agent_system.log"
            ]
        }
        
        return json.dumps({
            "success": True,
            "logs_info": logs_info
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to retrieve logs: {str(e)}"
        })

if __name__ == "__main__":
    print("📝 Starting Logging MCP Server...")
    system_logger.info("Logging MCP Server starting up")
    asyncio.run(logging_mcp.run())