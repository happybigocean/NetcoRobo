import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class CEOMemoryManager:
    """Memory manager with MCP database integration"""
    
    def __init__(self, agent_id: str, mcp_tools):
        self.agent_id = agent_id
        self.mcp_tools = mcp_tools
    
    async def store_interaction(self, interaction_type: str, content: Dict[str, Any], importance: int = 1):
        """Store interaction in memory via MCP database"""
        try:
            await self.mcp_tools.store_agent_memory(
                agent_id=self.agent_id,
                memory_type="interaction",
                content=json.dumps({
                    "interaction_type": interaction_type,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }),
                importance_score=importance
            )
        except Exception as e:
            await self.mcp_tools.log_agent_activity(
                agent_id=self.agent_id,
                activity_type="memory_storage",
                message=f"Failed to store interaction: {str(e)}",
                level="error"
            )
    
    async def get_relevant_context(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Get relevant context for query"""
        try:
            # Get recent memories
            memories_result = await self.mcp_tools.retrieve_agent_memories(
                agent_id=self.agent_id,
                memory_type="interaction",
                limit=limit,
                min_importance=2
            )
            
            memories = json.loads(memories_result) if isinstance(memories_result, str) else memories_result
            
            if memories.get("success") and memories.get("memories"):
                return {
                    "recent_interactions": memories["memories"],
                    "context_count": len(memories["memories"])
                }
            
            return {}
            
        except Exception as e:
            await self.mcp_tools.log_agent_activity(
                agent_id=self.agent_id,
                activity_type="memory_retrieval",
                message=f"Failed to get context: {str(e)}",
                level="error"
            )
            return {}
    
    async def get_recent_memories(self, limit: int = 10) -> List[Dict]:
        """Get recent memories for status reporting"""
        try:
            memories_result = await self.mcp_tools.retrieve_agent_memories(
                agent_id=self.agent_id,
                limit=limit
            )
            
            memories = json.loads(memories_result) if isinstance(memories_result, str) else memories_result
            
            if memories.get("success"):
                return memories.get("memories", [])
            
            return []
            
        except Exception as e:
            return []