import asyncio
import logging
from typing import Dict, List, Any, Optional
import json
import aiohttp
from datetime import datetime

class MCPToolManager:
    """Manager for MCP tool connections and execution"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connections = {}
        self.tools_cache = {}
        
        # MCP server configurations
        self.servers = {
            'database': {
                'url': config.get('mcp_database_url', 'http://localhost:8001'),
                'name': 'Database MCP Server',
                'tools': ['query_database', 'execute_sql', 'get_schema']
            },
            'logging': {
                'url': config.get('mcp_logging_url', 'http://localhost:8002'), 
                'name': 'Logging MCP Server',
                'tools': ['log_event', 'query_logs', 'get_log_stats']
            },
            'calendar': {
                'url': config.get('mcp_calendar_url', 'http://localhost:8003'),
                'name': 'Calendar MCP Server', 
                'tools': ['create_event', 'list_events', 'update_event', 'delete_event']
            },
            'weather': {
                'url': config.get('mcp_weather_url', 'http://localhost:8004'),
                'name': 'Weather MCP Server',
                'tools': ['get_weather', 'get_forecast', 'get_weather_alerts']
            },
            'netcoro': {
                'url': config.get('mcp_netcoro_url', 'http://localhost:8005'),
                'name': 'NetcoRo Business MCP Server',
                'tools': ['get_company_data', 'update_metrics', 'generate_report']
            }
        }
    
    async def initialize_connections(self):
        """Initialize connections to all MCP servers"""
        self.logger.info("Initializing MCP connections...")
        
        for server_id, server_config in self.servers.items():
            try:
                await self._connect_to_server(server_id, server_config)
                self.logger.info(f"Connected to {server_config['name']}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {server_id}: {str(e)}")
    
    async def _connect_to_server(self, server_id: str, server_config: Dict[str, Any]):
        """Connect to individual MCP server"""
        url = server_config['url']
        
        # Test connection
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{url}/health") as response:
                    if response.status == 200:
                        self.connections[server_id] = {
                            'url': url,
                            'status': 'connected',
                            'last_check': datetime.now(),
                            'tools': server_config['tools']
                        }
                    else:
                        raise Exception(f"Server returned status {response.status}")
            except Exception as e:
                self.connections[server_id] = {
                    'url': url,
                    'status': 'disconnected',
                    'error': str(e),
                    'last_check': datetime.now()
                }
                raise
    
    async def execute_tool(self, server_id: str, tool_name: str, 
                          parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool on specific MCP server"""
        try:
            if server_id not in self.connections:
                raise ValueError(f"No connection to server: {server_id}")
            
            connection = self.connections[server_id]
            if connection['status'] != 'connected':
                raise ValueError(f"Server {server_id} is not connected")
            
            # Prepare MCP request
            mcp_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                },
                "id": f"{server_id}_{tool_name}_{datetime.now().timestamp()}"
            }
            
            # Execute request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{connection['url']}/mcp",
                    json=mcp_request,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'error' in result:
                            raise Exception(f"MCP Error: {result['error']}")
                        
                        return {
                            'success': True,
                            'result': result.get('result', {}),
                            'server_id': server_id,
                            'tool_name': tool_name,
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {server_id}.{tool_name} - {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'server_id': server_id,
                'tool_name': tool_name,
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_available_tools(self) -> Dict[str, List[str]]:
        """Get list of available tools from all connected servers"""
        available_tools = {}
        
        for server_id, connection in self.connections.items():
            if connection['status'] == 'connected':
                available_tools[server_id] = connection.get('tools', [])
        
        return available_tools
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all MCP connections"""
        health_status = {
            'overall_status': 'healthy',
            'servers': {},
            'total_servers': len(self.servers),
            'connected_servers': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        for server_id, connection in self.connections.items():
            try:
                # Test connection
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{connection['url']}/health",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            connection['status'] = 'connected'
                            health_status['connected_servers'] += 1
                        else:
                            connection['status'] = 'error'
                
                health_status['servers'][server_id] = {
                    'status': connection['status'],
                    'url': connection['url'],
                    'last_check': datetime.now().isoformat()
                }
                
            except Exception as e:
                connection['status'] = 'disconnected'
                connection['error'] = str(e)
                health_status['servers'][server_id] = {
                    'status': 'disconnected',
                    'error': str(e),
                    'last_check': datetime.now().isoformat()
                }
        
        # Determine overall status
        connected_ratio = health_status['connected_servers'] / health_status['total_servers']
        if connected_ratio < 0.5:
            health_status['overall_status'] = 'critical'
        elif connected_ratio < 1.0:
            health_status['overall_status'] = 'degraded'
        
        return health_status


# Specific tool managers for each domain
class DatabaseManager:
    """Database operations through MCP"""
    
    def __init__(self, mcp_manager: MCPToolManager):
        self.mcp_manager = mcp_manager
        self.server_id = 'database'
    
    async def query_database(self, query: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute database query"""
        return await self.mcp_manager.execute_tool(
            self.server_id, 
            'query_database',
            {
                'query': query,
                'parameters': parameters or {}
            }
        )
    
    async def get_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema information"""
        return await self.mcp_manager.execute_tool(
            self.server_id,
            'get_schema', 
            {'table_name': table_name}
        )


class CalendarManager:
    """Calendar operations through MCP"""
    
    def __init__(self, mcp_manager: MCPToolManager):
        self.mcp_manager = mcp_manager
        self.server_id = 'calendar'
    
    async def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create calendar event"""
        return await self.mcp_manager.execute_tool(
            self.server_id,
            'create_event',
            event_data
        )
    
    async def list_events(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """List calendar events in date range"""
        return await self.mcp_manager.execute_tool(
            self.server_id,
            'list_events',
            {
                'start_date': start_date,
                'end_date': end_date
            }
        )


class WeatherManager:
    """Weather data through MCP"""
    
    def __init__(self, mcp_manager: MCPToolManager):
        self.mcp_manager = mcp_manager
        self.server_id = 'weather'
    
    async def get_weather(self, location: str) -> Dict[str, Any]:
        """Get current weather for location"""
        return await self.mcp_manager.execute_tool(
            self.server_id,
            'get_weather',
            {'location': location}
        )
    
    async def get_forecast(self, location: str, days: int = 5) -> Dict[str, Any]:
        """Get weather forecast"""
        return await self.mcp_manager.execute_tool(
            self.server_id,
            'get_forecast',
            {
                'location': location,
                'days': days
            }
        )


class NetcoRoToolManager:
    """NetcoRo-specific business tools"""
    
    def __init__(self, mcp_manager: MCPToolManager):
        self.mcp_manager = mcp_manager
        self.server_id = 'netcoro'
    
    async def get_company_metrics(self) -> Dict[str, Any]:
        """Get current company metrics"""
        return await self.mcp_manager.execute_tool(
            self.server_id,
            'get_company_data',
            {'type': 'metrics'}
        )
    
    async def generate_report(self, report_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business report"""
        return await self.mcp_manager.execute_tool(
            self.server_id,
            'generate_report',
            {
                'report_type': report_type,
                'parameters': parameters
            }
        )