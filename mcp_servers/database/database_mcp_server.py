import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
import aiosqlite
import os

# Initialize MCP server
database_mcp = FastMCP("CEO Agent Database Server")

# Database path from environment
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./ceo_agent_system.db").replace("sqlite:///", "")

async def init_database():
    """Initialize database with required tables"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Agent memory table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content JSON NOT NULL,
                importance_score INTEGER DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX(agent_id),
                INDEX(memory_type),
                INDEX(timestamp)
            )
        """)
        
        # Agent decisions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                decision_context TEXT NOT NULL,
                options_analyzed JSON,
                decision_made TEXT NOT NULL,
                reasoning TEXT,
                outcome TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX(agent_id),
                INDEX(timestamp)
            )
        """)
        
        # Agent knowledge base
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                knowledge_type TEXT NOT NULL,
                content JSON NOT NULL,
                source TEXT,
                confidence_score REAL DEFAULT 0.5,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX(agent_id),
                INDEX(knowledge_type),
                INDEX(source)
            )
        """)
        
        # Agent interactions log
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                input_data JSON,
                output_data JSON,
                processing_time_ms INTEGER,
                success BOOLEAN DEFAULT TRUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX(agent_id),
                INDEX(interaction_type),
                INDEX(timestamp)
            )
        """)
        
        await db.commit()

@database_mcp.tool()
async def store_agent_memory(
    agent_id: str,
    memory_type: str,
    content: str,
    importance_score: int = 1
) -> str:
    """
    Store agent memory in database
    
    Args:
        agent_id: ID of the agent
        memory_type: Type of memory (working, session, long_term)
        content: Memory content as JSON string
        importance_score: Importance from 1-5
    """
    try:
        content_dict = json.loads(content) if isinstance(content, str) else content
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO agent_memory 
                   (agent_id, memory_type, content, importance_score) 
                   VALUES (?, ?, ?, ?)""",
                (agent_id, memory_type, json.dumps(content_dict), importance_score)
            )
            await db.commit()
            
        return json.dumps({
            "success": True,
            "message": f"Memory stored for agent {agent_id}",
            "memory_type": memory_type
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to store memory: {str(e)}"
        })

@database_mcp.tool()
async def retrieve_agent_memories(
    agent_id: str,
    memory_type: str = "",
    limit: int = 50,
    min_importance: int = 1
) -> str:
    """
    Retrieve agent memories from database
    
    Args:
        agent_id: ID of the agent
        memory_type: Optional filter by memory type
        limit: Maximum number of memories to retrieve
        min_importance: Minimum importance score
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            query = """
                SELECT id, memory_type, content, importance_score, timestamp
                FROM agent_memory 
                WHERE agent_id = ? AND importance_score >= ?
            """
            params = [agent_id, min_importance]
            
            if memory_type:
                query += " AND memory_type = ?"
                params.append(memory_type)
            
            query += " ORDER BY importance_score DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            
            async with db.execute(query, params) as cursor:
                memories = []
                async for row in cursor:
                    memories.append({
                        "id": row[0],
                        "memory_type": row[1],
                        "content": json.loads(row[2]),
                        "importance_score": row[3],
                        "timestamp": row[4]
                    })
        
        return json.dumps({
            "success": True,
            "memories": memories,
            "count": len(memories)
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to retrieve memories: {str(e)}"
        })

@database_mcp.tool()
async def store_agent_decision(
    agent_id: str,
    decision_context: str,
    options_analyzed: str,
    decision_made: str,
    reasoning: str = "",
    outcome: str = ""
) -> str:
    """
    Store agent decision in database
    
    Args:
        agent_id: ID of the agent
        decision_context: Context requiring decision
        options_analyzed: JSON string of options that were analyzed
        decision_made: The final decision
        reasoning: Reasoning behind the decision
        outcome: Outcome of the decision (if known)
    """
    try:
        options_dict = json.loads(options_analyzed) if isinstance(options_analyzed, str) else options_analyzed
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO agent_decisions 
                   (agent_id, decision_context, options_analyzed, decision_made, reasoning, outcome) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (agent_id, decision_context, json.dumps(options_dict), decision_made, reasoning, outcome)
            )
            await db.commit()
            
        return json.dumps({
            "success": True,
            "message": f"Decision stored for agent {agent_id}"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to store decision: {str(e)}"
        })

@database_mcp.tool()
async def store_agent_knowledge(
    agent_id: str,
    knowledge_type: str,
    content: str,
    source: str = "unknown",
    confidence_score: float = 0.5
) -> str:
    """
    Store agent knowledge in database
    
    Args:
        agent_id: ID of the agent
        knowledge_type: Type of knowledge (business, technical, operational)
        content: Knowledge content as JSON string
        source: Source of the knowledge
        confidence_score: Confidence in knowledge accuracy (0.0-1.0)
    """
    try:
        content_dict = json.loads(content) if isinstance(content, str) else content
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO agent_knowledge 
                   (agent_id, knowledge_type, content, source, confidence_score) 
                   VALUES (?, ?, ?, ?, ?)""",
                (agent_id, knowledge_type, json.dumps(content_dict), source, confidence_score)
            )
            await db.commit()
            
        return json.dumps({
            "success": True,
            "message": f"Knowledge stored for agent {agent_id}",
            "knowledge_type": knowledge_type
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to store knowledge: {str(e)}"
        })

@database_mcp.tool()
async def log_agent_interaction(
    agent_id: str,
    interaction_type: str,
    input_data: str,
    output_data: str,
    processing_time_ms: int = 0,
    success: bool = True
) -> str:
    """
    Log agent interaction for monitoring and analysis
    
    Args:
        agent_id: ID of the agent
        interaction_type: Type of interaction (query, decision, reasoning)
        input_data: Input data as JSON string
        output_data: Output data as JSON string
        processing_time_ms: Processing time in milliseconds
        success: Whether interaction was successful
    """
    try:
        input_dict = json.loads(input_data) if isinstance(input_data, str) else input_data
        output_dict = json.loads(output_data) if isinstance(output_data, str) else output_data
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO agent_interactions 
                   (agent_id, interaction_type, input_data, output_data, processing_time_ms, success) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (agent_id, interaction_type, json.dumps(input_dict), 
                 json.dumps(output_dict), processing_time_ms, success)
            )
            await db.commit()
            
        return json.dumps({
            "success": True,
            "message": f"Interaction logged for agent {agent_id}"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to log interaction: {str(e)}"
        })

@database_mcp.tool()
async def get_agent_analytics(
    agent_id: str,
    days: int = 7
) -> str:
    """
    Get analytics for agent performance over specified period
    
    Args:
        agent_id: ID of the agent
        days: Number of days to analyze
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Get interaction statistics
            async with db.execute(
                """SELECT interaction_type, COUNT(*), AVG(processing_time_ms), 
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count
                   FROM agent_interactions 
                   WHERE agent_id = ? AND timestamp > ? 
                   GROUP BY interaction_type""",
                (agent_id, cutoff_date.isoformat())
            ) as cursor:
                interactions = []
                async for row in cursor:
                    interactions.append({
                        "interaction_type": row[0],
                        "total_count": row[1],
                        "avg_processing_time_ms": row[2],
                        "success_count": row[3],
                        "success_rate": (row[3] / row[1]) * 100 if row[1] > 0 else 0
                    })
            
            # Get memory statistics  
            async with db.execute(
                """SELECT memory_type, COUNT(*), AVG(importance_score)
                   FROM agent_memory 
                   WHERE agent_id = ? AND timestamp > ?
                   GROUP BY memory_type""",
                (agent_id, cutoff_date.isoformat())
            ) as cursor:
                memory_stats = []
                async for row in cursor:
                    memory_stats.append({
                        "memory_type": row[0],
                        "count": row[1], 
                        "avg_importance": row[2]
                    })
        
        analytics = {
            "agent_id": agent_id,
            "analysis_period_days": days,
            "interactions": interactions,
            "memory_statistics": memory_stats,
            "generated_at": datetime.now().isoformat()
        }
        
        return json.dumps({
            "success": True,
            "analytics": analytics
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to generate analytics: {str(e)}"
        })

# Initialize database on startup
async def startup():
    await init_database()
    print("✅ Database MCP Server initialized")

if __name__ == "__main__":
    print("🗄️ Starting Database MCP Server...")
    asyncio.run(startup())
    asyncio.run(database_mcp.run())