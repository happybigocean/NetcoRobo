import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import aiohttp
import sqlite3
from dataclasses import dataclass
from enum import Enum

from ..base_agent import BaseAgent


class QueryType(Enum):
    """Types of queries for local processing"""
    OPERATIONAL = "operational"
    DATA_ANALYSIS = "data_analysis" 
    TACTICAL = "tactical"
    COMPLIANCE = "compliance"
    ROUTINE = "routine"


@dataclass
class LocalQuery:
    """Structure for local knowledge base queries"""
    query: str
    query_type: QueryType
    context: Optional[Dict[str, Any]] = None
    priority: str = "normal"  # low, normal, high, urgent
    agent_id: Optional[str] = None
    timestamp: Optional[datetime] = None


class OllamaClient:
    """Async client for Ollama API communication"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def generate(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using Ollama model"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    self.logger.error(f"Ollama API error: {response.status} - {error_text}")
                    return {"error": f"API error: {response.status}"}
        
        except asyncio.TimeoutError:
            self.logger.error("Ollama request timeout")
            return {"error": "Request timeout"}
        except Exception as e:
            self.logger.error(f"Ollama request failed: {str(e)}")
            return {"error": str(e)}
    
    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return [model['name'] for model in data.get('models', [])]
                return []
        except Exception as e:
            self.logger.error(f"Failed to list models: {str(e)}")
            return []
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(
                f"{self.base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception:
            return False


class LocalKnowledgeBase:
    """
    Local Knowledge Base using Ollama for operational and tactical queries
    Optimized for data privacy, fast response times, and routine operations
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Ollama configuration
        self.ollama_url = config.get('ollama_url', 'http://localhost:11434')
        self.default_model = config.get('default_model', 'llama3.2:latest')
        self.operational_model = config.get('operational_model', 'llama3.2:latest')
        self.analysis_model = config.get('analysis_model', 'llama3.2:latest')
        
        # Cache configuration
        self.cache_enabled = config.get('cache_enabled', True)
        self.cache_ttl = config.get('cache_ttl', 3600)  # 1 hour
        self.max_cache_size = config.get('max_cache_size', 1000)
        
        # Initialize components
        self.client = OllamaClient(self.ollama_url)
        self.query_cache = {}
        self.model_cache = {}
        
        # Performance tracking
        self.query_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'avg_response_time': 0,
            'error_count': 0
        }
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize local SQLite database for query history and caching"""
        try:
            self.db_path = self.config.get('local_db_path', 'data/local_kb.db')
            conn = sqlite3.connect(self.db_path)
            
            # Create tables
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT UNIQUE,
                    query TEXT,
                    query_type TEXT,
                    model_used TEXT,
                    response TEXT,
                    response_time REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    agent_id TEXT,
                    success BOOLEAN
                );
                
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT PRIMARY KEY,
                    response TEXT,
                    model_used TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS model_performance (
                    model_name TEXT,
                    query_type TEXT,
                    avg_response_time REAL,
                    success_rate REAL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (model_name, query_type)
                );
                
                CREATE INDEX IF NOT EXISTS idx_query_hash ON query_history(query_hash);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON query_history(timestamp);
                CREATE INDEX IF NOT EXISTS idx_agent_id ON query_history(agent_id);
            """)
            
            conn.commit()
            conn.close()
            self.logger.info("Local database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
    
    async def query(self, query_obj: Union[str, LocalQuery]) -> Dict[str, Any]:
        """
        Process query using local Ollama models
        
        Args:
            query_obj: Either a string query or LocalQuery object
            
        Returns:
            Dict containing response and metadata
        """
        start_time = datetime.now()
        
        # Convert string to LocalQuery if needed
        if isinstance(query_obj, str):
            query_obj = LocalQuery(
                query=query_obj,
                query_type=QueryType.OPERATIONAL,
                timestamp=start_time
            )
        
        try:
            # Update stats
            self.query_stats['total_queries'] += 1
            
            # Check cache first
            if self.cache_enabled:
                cached_response = await self._check_cache(query_obj)
                if cached_response:
                    self.query_stats['cache_hits'] += 1
                    return self._format_response(
                        cached_response['response'],
                        model_used=cached_response['model_used'],
                        response_time=(datetime.now() - start_time).total_seconds(),
                        from_cache=True,
                        query_obj=query_obj
                    )
            
            # Select appropriate model based on query type
            model = await self._select_model(query_obj)
            
            # Prepare prompt with context
            formatted_prompt = await self._format_prompt(query_obj)
            
            # Generate response using Ollama
            async with self.client as ollama:
                response = await ollama.generate(
                    model=model,
                    prompt=formatted_prompt,
                    temperature=self._get_temperature(query_obj.query_type),
                    max_tokens=self._get_max_tokens(query_obj.query_type)
                )
            
            if 'error' in response:
                raise Exception(f"Ollama generation failed: {response['error']}")
            
            response_text = response.get('response', '')
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Cache successful response
            if self.cache_enabled and response_text:
                await self._cache_response(query_obj, response_text, model)
            
            # Log query for analysis
            await self._log_query(query_obj, response_text, model, response_time, True)
            
            # Update performance stats
            self._update_stats(response_time)
            
            return self._format_response(
                response_text,
                model_used=model,
                response_time=response_time,
                from_cache=False,
                query_obj=query_obj
            )
            
        except Exception as e:
            self.logger.error(f"Local KB query failed: {str(e)}")
            self.query_stats['error_count'] += 1
            
            # Log failed query
            response_time = (datetime.now() - start_time).total_seconds()
            await self._log_query(query_obj, str(e), "error", response_time, False)
            
            return {
                'success': False,
                'response': f"Local knowledge base error: {str(e)}",
                'error': str(e),
                'model_used': 'none',
                'response_time': response_time,
                'query_type': query_obj.query_type.value,
                'from_cache': False
            }
    
    async def _select_model(self, query_obj: LocalQuery) -> str:
        """Select appropriate model based on query type and performance"""
        
        # Model selection strategy
        model_mapping = {
            QueryType.OPERATIONAL: self.operational_model,
            QueryType.DATA_ANALYSIS: self.analysis_model,
            QueryType.TACTICAL: self.operational_model,
            QueryType.COMPLIANCE: self.operational_model,
            QueryType.ROUTINE: self.operational_model
        }
        
        selected_model = model_mapping.get(query_obj.query_type, self.default_model)
        
        # Check if model is available
        async with self.client as ollama:
            available_models = await ollama.list_models()
            if selected_model not in available_models:
                self.logger.warning(f"Model {selected_model} not available, using default")
                return self.default_model if self.default_model in available_models else available_models[0] if available_models else 'llama3.2:latest'
        
        return selected_model
    
    async def _format_prompt(self, query_obj: LocalQuery) -> str:
        """Format prompt with context and instructions"""
        
        # Base system prompt for local operations
        system_prompt = """You are a local AI assistant for NetcoRo company operations. 
You specialize in operational tasks, data analysis, and tactical decision-making.
Focus on:
- Practical, actionable responses
- Data-driven insights
- Operational efficiency
- Compliance requirements
- Quick decision support

Current context: You are processing an internal query that requires immediate, practical assistance."""
        
        # Add query-specific instructions
        query_instructions = {
            QueryType.OPERATIONAL: "Focus on operational procedures, workflows, and immediate actions needed.",
            QueryType.DATA_ANALYSIS: "Provide detailed data analysis with specific metrics, trends, and actionable insights.",
            QueryType.TACTICAL: "Give tactical recommendations with step-by-step implementation guidance.",
            QueryType.COMPLIANCE: "Ensure all recommendations meet regulatory and company compliance requirements.",
            QueryType.ROUTINE: "Provide quick, standardized responses for routine operational questions."
        }
        
        instruction = query_instructions.get(query_obj.query_type, "Provide helpful and accurate information.")
        
        # Include context if available
        context_section = ""
        if query_obj.context:
            context_section = f"\nContext: {json.dumps(query_obj.context, indent=2)}"
        
        # Add agent context if available
        agent_section = ""
        if query_obj.agent_id:
            agent_section = f"\nRequesting Agent: {query_obj.agent_id}"
        
        # Priority handling
        priority_section = ""
        if query_obj.priority in ['high', 'urgent']:
            priority_section = f"\nPRIORITY {query_obj.priority.upper()}: This requires immediate attention and practical solutions."
        
        # Combine all sections
        full_prompt = f"""{system_prompt}

{instruction}
{context_section}
{agent_section}
{priority_section}

Query: {query_obj.query}

Response:"""
        
        return full_prompt
    
    def _get_temperature(self, query_type: QueryType) -> float:
        """Get appropriate temperature setting for query type"""
        temperature_map = {
            QueryType.OPERATIONAL: 0.1,      # Very focused
            QueryType.DATA_ANALYSIS: 0.2,   # Analytical
            QueryType.TACTICAL: 0.3,        # Slightly creative
            QueryType.COMPLIANCE: 0.1,      # Strict adherence
            QueryType.ROUTINE: 0.1          # Consistent responses
        }
        return temperature_map.get(query_type, 0.2)
    
    def _get_max_tokens(self, query_type: QueryType) -> int:
        """Get appropriate token limit for query type"""
        token_map = {
            QueryType.OPERATIONAL: 1500,
            QueryType.DATA_ANALYSIS: 2000,
            QueryType.TACTICAL: 1800,
            QueryType.COMPLIANCE: 1200,
            QueryType.ROUTINE: 800
        }
        return token_map.get(query_type, 1500)
    
    async def _check_cache(self, query_obj: LocalQuery) -> Optional[Dict[str, Any]]:
        """Check if query response is cached"""
        try:
            query_hash = self._generate_query_hash(query_obj)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check cache with TTL
            cursor.execute("""
                SELECT response, model_used, created_at 
                FROM query_cache 
                WHERE query_hash = ? 
                AND datetime(created_at, '+{} seconds') > datetime('now')
            """.format(self.cache_ttl), (query_hash,))
            
            result = cursor.fetchone()
            
            if result:
                # Update access statistics
                cursor.execute("""
                    UPDATE query_cache 
                    SET access_count = access_count + 1, 
                        last_accessed = datetime('now')
                    WHERE query_hash = ?
                """, (query_hash,))
                conn.commit()
                
                conn.close()
                return {
                    'response': result[0],
                    'model_used': result[1],
                    'cached_at': result[2]
                }
            
            conn.close()
            return None
            
        except Exception as e:
            self.logger.error(f"Cache check failed: {str(e)}")
            return None
    
    async def _cache_response(self, query_obj: LocalQuery, response: str, model: str):
        """Cache successful response"""
        try:
            query_hash = self._generate_query_hash(query_obj)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or replace cache entry
            cursor.execute("""
                INSERT OR REPLACE INTO query_cache 
                (query_hash, response, model_used, created_at, access_count, last_accessed)
                VALUES (?, ?, ?, datetime('now'), 1, datetime('now'))
            """, (query_hash, response, model))
            
            conn.commit()
            conn.close()
            
            # Clean old cache entries if needed
            await self._cleanup_cache()
            
        except Exception as e:
            self.logger.error(f"Cache storage failed: {str(e)}")
    
    async def _log_query(self, query_obj: LocalQuery, response: str, model: str, 
                        response_time: float, success: bool):
        """Log query for analysis and improvement"""
        try:
            query_hash = self._generate_query_hash(query_obj)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO query_history 
                (query_hash, query, query_type, model_used, response, response_time, 
                 agent_id, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_hash,
                query_obj.query,
                query_obj.query_type.value,
                model,
                response,
                response_time,
                query_obj.agent_id,
                success
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Query logging failed: {str(e)}")
    
    def _generate_query_hash(self, query_obj: LocalQuery) -> str:
        """Generate hash for query caching"""
        import hashlib
        
        # Create hash from query content and type
        hash_content = f"{query_obj.query}:{query_obj.query_type.value}"
        if query_obj.context:
            hash_content += f":{json.dumps(query_obj.context, sort_keys=True)}"
        
        return hashlib.md5(hash_content.encode()).hexdigest()
    
    async def _cleanup_cache(self):
        """Remove old cache entries to maintain size limit"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count current cache entries
            cursor.execute("SELECT COUNT(*) FROM query_cache")
            current_count = cursor.fetchone()[0]
            
            if current_count > self.max_cache_size:
                # Remove oldest entries
                entries_to_remove = current_count - self.max_cache_size
                cursor.execute("""
                    DELETE FROM query_cache 
                    WHERE query_hash IN (
                        SELECT query_hash FROM query_cache 
                        ORDER BY last_accessed ASC 
                        LIMIT ?
                    )
                """, (entries_to_remove,))
                
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Cache cleanup failed: {str(e)}")
    
    def _update_stats(self, response_time: float):
        """Update performance statistics"""
        current_avg = self.query_stats['avg_response_time']
        total_queries = self.query_stats['total_queries']
        
        # Calculate new average response time
        if current_avg == 0:
            self.query_stats['avg_response_time'] = response_time
        else:
            self.query_stats['avg_response_time'] = (
                (current_avg * (total_queries - 1)) + response_time
            ) / total_queries
    
    def _format_response(self, response: str, model_used: str, response_time: float, 
                        from_cache: bool, query_obj: LocalQuery) -> Dict[str, Any]:
        """Format response with metadata"""
        return {
            'success': True,
            'response': response,
            'model_used': model_used,
            'response_time': response_time,
            'query_type': query_obj.query_type.value,
            'from_cache': from_cache,
            'agent_id': query_obj.agent_id,
            'priority': query_obj.priority,
            'timestamp': query_obj.timestamp or datetime.now()
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of local knowledge base"""
        async with self.client as ollama:
            ollama_healthy = await ollama.health_check()
            available_models = await ollama.list_models() if ollama_healthy else []
        
        return {
            'ollama_healthy': ollama_healthy,
            'available_models': available_models,
            'default_model': self.default_model,
            'cache_enabled': self.cache_enabled,
            'query_stats': self.query_stats,
            'database_path': self.db_path
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query performance by type
            cursor.execute("""
                SELECT query_type, 
                       COUNT(*) as total_queries,
                       AVG(response_time) as avg_response_time,
                       AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                       MAX(timestamp) as last_query
                FROM query_history 
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY query_type
            """)
            
            performance_by_type = {}
            for row in cursor.fetchall():
                performance_by_type[row[0]] = {
                    'total_queries': row[1],
                    'avg_response_time': round(row[2], 3),
                    'success_rate': round(row[3], 3),
                    'last_query': row[4]
                }
            
            # Cache statistics
            cursor.execute("""
                SELECT COUNT(*) as total_cached,
                       AVG(access_count) as avg_access_count
                FROM query_cache
            """)
            cache_stats = cursor.fetchone()
            
            conn.close()
            
            return {
                'overall_stats': self.query_stats,
                'performance_by_type': performance_by_type,
                'cache_stats': {
                    'total_cached': cache_stats[0] if cache_stats else 0,
                    'avg_access_count': round(cache_stats[1], 2) if cache_stats and cache_stats[1] else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {str(e)}")
            return {'error': str(e)}
    
    async def optimize_models(self) -> Dict[str, Any]:
        """Analyze performance and suggest model optimizations"""
        try:
            metrics = await self.get_performance_metrics()
            performance_by_type = metrics.get('performance_by_type', {})
            
            recommendations = []
            
            for query_type, stats in performance_by_type.items():
                if stats['avg_response_time'] > 5.0:  # Slow responses
                    recommendations.append({
                        'query_type': query_type,
                        'issue': 'slow_response',
                        'current_time': stats['avg_response_time'],
                        'suggestion': 'Consider using a smaller, faster model for this query type'
                    })
                
                if stats['success_rate'] < 0.9:  # Low success rate
                    recommendations.append({
                        'query_type': query_type,
                        'issue': 'low_success_rate',
                        'current_rate': stats['success_rate'],
                        'suggestion': 'Consider using a more capable model or adjusting prompt templates'
                    })
            
            return {
                'recommendations': recommendations,
                'overall_performance': metrics['overall_stats'],
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Model optimization analysis failed: {str(e)}")
            return {'error': str(e)}


# Example usage and testing functions
async def test_local_kb():
    """Test function for local knowledge base"""
    config = {
        'ollama_url': 'http://localhost:11434',
        'default_model': 'llama3.2:latest',
        'operational_model': 'llama3.2:latest',
        'analysis_model': 'llama3.2:latest',
        'cache_enabled': True,
        'cache_ttl': 3600,
        'local_db_path': 'data/test_local_kb.db'
    }
    
    kb = LocalKnowledgeBase(config)
    
    # Test queries
    test_queries = [
        LocalQuery(
            query="What are the standard operating procedures for onboarding new employees?",
            query_type=QueryType.OPERATIONAL,
            agent_id="HR_Agent",
            priority="normal"
        ),
        LocalQuery(
            query="Analyze the sales data from last quarter and identify key trends",
            query_type=QueryType.DATA_ANALYSIS,
            agent_id="CFO_Agent",
            priority="high",
            context={"department": "sales", "period": "Q3_2024"}
        ),
        LocalQuery(
            query="What's the process for requesting office supplies?",
            query_type=QueryType.ROUTINE,
            agent_id="Operations_Agent"
        )
    ]
    
    print("Testing Local Knowledge Base with Ollama...")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: {query.query_type.value.upper()} Query")
        print(f"Query: {query.query}")
        
        response = await kb.query(query)
        
        if response['success']:
            print(f"✅ Success (Model: {response['model_used']}, Time: {response['response_time']:.2f}s)")
            print(f"Response: {response['response'][:200]}...")
            if response['from_cache']:
                print("📋 Response served from cache")
        else:
            print(f"❌ Failed: {response['error']}")
    
    # Get health status
    print("\n" + "="*50)
    print("HEALTH STATUS")
    health = await kb.get_health_status()
    print(f"Ollama Health: {'✅' if health['ollama_healthy'] else '❌'}")
    print(f"Available Models: {health['available_models']}")
    print(f"Query Stats: {health['query_stats']}")
    
    # Get performance metrics
    print("\n" + "="*50) 
    print("PERFORMANCE METRICS")
    metrics = await kb.get_performance_metrics()
    if 'error' not in metrics:
        print(f"Overall Stats: {metrics['overall_stats']}")
        print(f"Performance by Type: {metrics['performance_by_type']}")
    
    print("\nLocal KB testing completed!")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_local_kb())