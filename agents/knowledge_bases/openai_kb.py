import asyncio
import json
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from config.settings import settings
import chromadb
from chromadb.config import Settings as ChromaSettings

class OpenAIKnowledgeBase:
    """OpenAI-powered knowledge base with enhanced MCP integration"""
    
    def __init__(self, mcp_tools=None):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.mcp_tools = mcp_tools  # Reference to MCP tools for logging/storage
        
        # Initialize ChromaDB for RAG
        self.chroma_client = chromadb.Client(ChromaSettings(
            persist_directory=f"{settings.VECTOR_DB_PATH}/openai"
        ))
        self.collection = self.chroma_client.get_or_create_collection(
            name="openai_business_knowledge",
            metadata={"description": "OpenAI business knowledge base for CEO Agent"}
        )
        
        # Load company knowledge
        self.company_kb = settings.get_company_knowledge_base()
        
    async def query_knowledge(self, question: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Query OpenAI knowledge base with RAG and MCP logging"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Log query start
            if self.mcp_tools:
                await self.mcp_tools.log_agent_activity(
                    agent_id="OpenAI_KB",
                    activity_type="knowledge_query", 
                    message=f"Processing knowledge query: {question[:100]}...",
                    level="info",
                    metadata=json.dumps({"query_length": len(question)})
                )
            
            # Retrieve relevant context from vector DB
            relevant_docs = self.collection.query(
                query_texts=[question],
                n_results=5
            )
            
            # Build enhanced context
            context_text = ""
            if relevant_docs["documents"]:
                context_text = "\n\n".join(relevant_docs["documents"][0])
            
            system_prompt = f"""
            You are the CEO Agent's strategic business knowledge base powered by OpenAI.
            
            Company Context:
            - Identity: {self.company_kb['identity']}
            - Governance: {self.company_kb['governance_rules']}
            - Operations: {self.company_kb['operational_guidelines']}
            
            Relevant Knowledge Context:
            {context_text}
            
            Session Context:
            {json.dumps(context) if context else 'None'}
            
            Provide strategic, well-reasoned business insights that:
            1. Align with company mission and values
            2. Consider long-term strategic implications
            3. Include actionable recommendations
            4. Address potential risks and opportunities
            5. Support scalable decision-making
            
            Emphasize business strategy, market analysis, and leadership perspectives.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS
            )
            
            processing_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            result = {
                "answer": response.choices[0].message.content,
                "source": "OpenAI_Business_KB",
                "model": self.model,
                "relevant_context": relevant_docs["documents"][0] if relevant_docs["documents"] else [],
                "confidence": "high",
                "processing_time_ms": processing_time,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Log successful completion
            if self.mcp_tools:
                await self.mcp_tools.log_agent_performance(
                    agent_id="OpenAI_KB",
                    operation="knowledge_query",
                    duration_ms=processing_time,
                    success=True,
                    details=json.dumps({
                        "model": self.model,
                        "query_length": len(question),
                        "response_length": len(result["answer"])
                    })
                )
                
                # Store knowledge if valuable
                await self.mcp_tools.store_agent_knowledge(
                    agent_id="CEO_Alpha_Client",
                    knowledge_type="business_query",
                    content=json.dumps({
                        "question": question,
                        "answer": result["answer"],
                        "source": "OpenAI_KB"
                    }),
                    source="OpenAI_Business_KB",
                    confidence_score=0.9
                )
            
            return result
            
        except Exception as e:
            processing_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Log error
            if self.mcp_tools:
                await self.mcp_tools.log_agent_activity(
                    agent_id="OpenAI_KB",
                    activity_type="knowledge_query",
                    message=f"Error in knowledge query: {str(e)}",
                    level="error",
                    metadata=json.dumps({"error_type": type(e).__name__})
                )
            
            return {
                "answer": f"Error querying OpenAI knowledge base: {str(e)}",
                "source": "OpenAI_Business_KB",
                "error": True,
                "processing_time_ms": processing_time
            }
    
    async def store_knowledge(self, content: str, metadata: Dict[str, Any]):
        """Store knowledge with MCP logging"""
        try:
            # Store in ChromaDB
            doc_id = f"openai_doc_{len(self.collection.get()['ids'])}"
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            # Log to MCP
            if self.mcp_tools:
                await self.mcp_tools.store_agent_knowledge(
                    agent_id="CEO_Alpha_Client",
                    knowledge_type="stored_knowledge",
                    content=json.dumps({"content": content, "metadata": metadata}),
                    source="OpenAI_KB_Storage"
                )
            
            return True
        except Exception as e:
            if self.mcp_tools:
                await self.mcp_tools.log_agent_activity(
                    agent_id="OpenAI_KB",
                    activity_type="knowledge_storage",
                    message=f"Error storing knowledge: {str(e)}",
                    level="error"
                )
            return False
    
    async def reasoning_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform strategic reasoning with MCP integration"""
        start_time = asyncio.get_event_loop().time()
        
        system_prompt = f"""
        You are the strategic reasoning engine for the CEO Agent.
        
        Company Context: {json.dumps(self.company_kb, indent=2)}
        
        Provide comprehensive strategic analysis including:
        1. Situation Assessment
        2. Strategic Options Analysis  
        3. Risk/Opportunity Matrix
        4. Resource Requirements
        5. Implementation Roadmap
        6. Success Metrics
        7. Contingency Plans
        
        Base all reasoning on company values and long-term strategic objectives.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Strategic Task: {task}\n\nContext: {json.dumps(context, indent=2)}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            processing_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            result = {
                "reasoning": response.choices[0].message.content,
                "source": "OpenAI_Strategic_Reasoning",
                "confidence": "high",
                "processing_time_ms": processing_time
            }
            
            # Log reasoning task
            if self.mcp_tools:
                await self.mcp_tools.log_agent_performance(
                    agent_id="OpenAI_KB",
                    operation="strategic_reasoning",
                    duration_ms=processing_time,
                    success=True
                )
            
            return result
            
        except Exception as e:
            processing_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            if self.mcp_tools:
                await self.mcp_tools.log_agent_activity(
                    agent_id="OpenAI_KB",
                    activity_type="strategic_reasoning",
                    message=f"Error in reasoning task: {str(e)}",
                    level="error"
                )
            
            return {
                "reasoning": f"Error in strategic reasoning: {str(e)}",
                "error": True,
                "processing_time_ms": processing_time
            }