import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

from agno import Team, Agent
from ..agents.ceo_agent import CEOAgent
from ..agents.cto_agent import CTOAgent
from ..agents.cfo_agent import CFOAgent
from ..agents.hr_agent import HRAgent
from ..agents.sales_agent import SalesAgent
from ..agents.legal_agent import LegalAgent
from ..agents.operations_agent import OperationsAgent
from ..memory.persistent_memory import PersistentMemoryManager
from ..utils.config import get_config


class AgentStatus(Enum):
    """Agent status enumeration"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class CoordinationMode(Enum):
    """Agent coordination modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel" 
    HIERARCHICAL = "hierarchical"
    COLLABORATIVE = "collaborative"


@dataclass
class AgentTask:
    """Task structure for agent coordination"""
    task_id: str
    agent_id: str
    task_type: str
    description: str
    priority: TaskPriority
    assigned_at: datetime
    due_date: Optional[datetime] = None
    dependencies: List[str] = None
    context: Dict[str, Any] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.context is None:
            self.context = {}


@dataclass
class AgentInfo:
    """Agent information structure"""
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: List[str]
    status: AgentStatus
    current_task: Optional[str] = None
    task_queue_size: int = 0
    last_activity: Optional[datetime] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}


class AgentCoordinator:
    """
    Central coordinator for NetcoRo AI Multi-Agent System
    Manages agent lifecycle, task distribution, and inter-agent communication
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.agents: Dict[str, Agent] = {}
        self.agent_info: Dict[str, AgentInfo] = {}
        self.active_tasks: Dict[str, AgentTask] = {}
        self.task_history: List[AgentTask] = []
        self.team: Optional[Team] = None
        
        # Memory and persistence
        self.memory_manager = PersistentMemoryManager(config)
        
        # Coordination settings
        self.max_concurrent_tasks = config.get('max_concurrent_tasks', 10)
        self.task_timeout = config.get('task_timeout', 300)  # 5 minutes
        self.coordination_mode = CoordinationMode.COLLABORATIVE
        
        # Performance tracking
        self.coordination_stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'avg_completion_time': 0,
            'agent_utilization': {}
        }
        
        # Event handlers
        self.event_handlers = {}
        
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all NetcoRo agents"""
        try:
            agent_configs = {
                'ceo_agent': {
                    'class': CEOAgent,
                    'name': 'CEO Agent',
                    'description': 'Strategic leadership and executive decisions',
                    'capabilities': ['strategic_planning', 'executive_decisions', 'investor_relations']
                },
                'cto_agent': {
                    'class': CTOAgent,
                    'name': 'CTO Agent', 
                    'description': 'Technology strategy and architecture decisions',
                    'capabilities': ['tech_strategy', 'architecture_review', 'innovation_planning']
                },
                'cfo_agent': {
                    'class': CFOAgent,
                    'name': 'CFO Agent',
                    'description': 'Financial planning and budget management',
                    'capabilities': ['financial_analysis', 'budget_planning', 'risk_assessment']
                },
                'hr_agent': {
                    'class': HRAgent,
                    'name': 'HR Agent',
                    'description': 'Human resources and talent management',
                    'capabilities': ['talent_management', 'onboarding', 'performance_review']
                },
                'sales_agent': {
                    'class': SalesAgent,
                    'name': 'Sales Agent',
                    'description': 'Sales strategy and customer acquisition',
                    'capabilities': ['sales_strategy', 'lead_generation', 'customer_analysis']
                },
                'legal_agent': {
                    'class': LegalAgent,
                    'name': 'Legal Agent',
                    'description': 'Legal compliance and contract management',
                    'capabilities': ['contract_review', 'compliance_check', 'risk_mitigation']
                },
                'ops_agent': {
                    'class': OperationsAgent,
                    'name': 'Operations Agent',
                    'description': 'Operational efficiency and process optimization',
                    'capabilities': ['process_optimization', 'resource_management', 'workflow_automation']
                }
            }
            
            # Initialize each agent
            for agent_id, agent_config in agent_configs.items():
                try:
                    agent_class = agent_config['class']
                    agent = agent_class(
                        agent_id=agent_id,
                        config=self.config,
                        memory_manager=self.memory_manager
                    )
                    
                    self.agents[agent_id] = agent
                    self.agent_info[agent_id] = AgentInfo(
                        agent_id=agent_id,
                        agent_type=agent_class.__name__,
                        name=agent_config['name'],
                        description=agent_config['description'],
                        capabilities=agent_config['capabilities'],
                        status=AgentStatus.INACTIVE,
                        last_activity=datetime.now()
                    )
                    
                    self.logger.info(f"Initialized agent: {agent_id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to initialize agent {agent_id}: {str(e)}")
            
            # Initialize Agno Team for coordination
            if self.agents:
                self.team = Team(
                    agents=list(self.agents.values()),
                    mode="coordinate"  # Enable coordination mode
                )
                self.logger.info(f"Team initialized with {len(self.agents)} agents")
            
        except Exception as e:
            self.logger.error(f"Agent initialization failed: {str(e)}")
    
    async def start_coordinator(self):
        """Start the agent coordinator"""
        try:
            self.logger.info("Starting NetcoRo Agent Coordinator...")
            
            # Activate all agents
            for agent_id, agent in self.agents.items():
                await self._activate_agent(agent_id)
            
            # Start background tasks
            asyncio.create_task(self._task_monitor())
            asyncio.create_task(self._performance_monitor())
            asyncio.create_task(self._health_monitor())
            
            self.logger.info("Agent Coordinator started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start coordinator: {str(e)}")
            raise
    
    async def stop_coordinator(self):
        """Stop the agent coordinator"""
        try:
            self.logger.info("Stopping Agent Coordinator...")
            
            # Complete pending tasks
            await self._complete_pending_tasks()
            
            # Deactivate all agents
            for agent_id in self.agents:
                await self._deactivate_agent(agent_id)
            
            # Save state
            await self._save_coordinator_state()
            
            self.logger.info("Agent Coordinator stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping coordinator: {str(e)}")
    
    async def assign_task(self, task: AgentTask) -> str:
        """Assign task to appropriate agent"""
        try:
            # Validate task
            if not await self._validate_task(task):
                raise ValueError(f"Invalid task: {task.task_id}")
            
            # Check agent availability
            agent_id = task.agent_id
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")
            
            if self.agent_info[agent_id].status not in [AgentStatus.ACTIVE, AgentStatus.INACTIVE]:
                raise ValueError(f"Agent {agent_id} is not available (status: {self.agent_info[agent_id].status})")
            
            # Add to active tasks
            self.active_tasks[task.task_id] = task
            
            # Update agent status
            self.agent_info[agent_id].status = AgentStatus.BUSY
            self.agent_info[agent_id].current_task = task.task_id
            self.agent_info[agent_id].task_queue_size += 1
            
            # Execute task
            asyncio.create_task(self._execute_task(task))
            
            self.logger.info(f"Task {task.task_id} assigned to agent {agent_id}")
            return task.task_id
            
        except Exception as e:
            self.logger.error(f"Task assignment failed: {str(e)}")
            raise
    
    async def coordinate_agents(self, coordination_request: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate multiple agents for complex tasks"""
        try:
            request_id = str(uuid.uuid4())
            request_type = coordination_request.get('type', 'collaborative')
            participating_agents = coordination_request.get('agents', [])
            objective = coordination_request.get('objective', '')
            
            self.logger.info(f"Starting coordination request {request_id} with {len(participating_agents)} agents")
            
            # Validate participating agents
            valid_agents = []
            for agent_id in participating_agents:
                if agent_id in self.agents and self.agent_info[agent_id].status == AgentStatus.ACTIVE:
                    valid_agents.append(agent_id)
            
            if not valid_agents:
                raise ValueError("No valid agents available for coordination")
            
            # Execute coordination based on type
            if request_type == 'collaborative':
                result = await self._collaborative_coordination(valid_agents, objective, coordination_request)
            elif request_type == 'hierarchical':
                result = await self._hierarchical_coordination(valid_agents, objective, coordination_request)
            elif request_type == 'sequential':
                result = await self._sequential_coordination(valid_agents, objective, coordination_request)
            else:
                result = await self._parallel_coordination(valid_agents, objective, coordination_request)
            
            return {
                'success': True,
                'request_id': request_id,
                'result': result,
                'participating_agents': valid_agents,
                'coordination_type': request_type
            }
            
        except Exception as e:
            self.logger.error(f"Agent coordination failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'request_id': request_id if 'request_id' in locals() else None
            }
    
    async def _collaborative_coordination(self, agents: List[str], objective: str, 
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute collaborative coordination using Agno Team"""
        try:
            # Prepare team query
            team_query = f"""
            Objective: {objective}
            
            Context: {json.dumps(context.get('context', {}), indent=2)}
            
            Please collaborate to address this objective. Each agent should contribute 
            their expertise and work together to develop a comprehensive solution.
            """
            
            # Filter team to include only participating agents
            participating_team_agents = [
                agent for agent_id, agent in self.agents.items() 
                if agent_id in agents
            ]
            
            if not participating_team_agents:
                raise ValueError("No valid participating agents")
            
            # Create temporary team for this coordination
            coordination_team = Team(
                agents=participating_team_agents,
                mode="coordinate"
            )
            
            # Execute team query
            team_response = await coordination_team.run(team_query)
            
            return {
                'type': 'collaborative',
                'response': team_response,
                'participants': agents,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Collaborative coordination failed: {str(e)}")
            raise
    
    async def _hierarchical_coordination(self, agents: List[str], objective: str,
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hierarchical coordination (CEO leads)"""
        try:
            results = {}
            
            # CEO leads the coordination
            if 'ceo_agent' in agents:
                ceo_query = f"""
                As CEO, coordinate the following agents to achieve this objective:
                
                Objective: {objective}
                Available Agents: {', '.join(agents)}
                Context: {json.dumps(context.get('context', {}), indent=2)}
                
                Please provide strategic direction and coordinate the team.
                """
                
                ceo_response = await self.agents['ceo_agent'].process_query(ceo_query)
                results['ceo_direction'] = ceo_response
                
                # Get input from other agents based on CEO direction
                for agent_id in agents:
                    if agent_id != 'ceo_agent':
                        agent_query = f"""
                        CEO Direction: {ceo_response}
                        Your Role: Provide {agent_id} perspective on: {objective}
                        Context: {json.dumps(context.get('context', {}), indent=2)}
                        """
                        
                        agent_response = await self.agents[agent_id].process_query(agent_query)
                        results[agent_id] = agent_response
            
            return {
                'type': 'hierarchical',
                'results': results,
                'participants': agents,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Hierarchical coordination failed: {str(e)}")
            raise
    
    async def _sequential_coordination(self, agents: List[str], objective: str,
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute sequential coordination (agents work in order)"""
        try:
            results = {}
            accumulated_context = context.get('context', {})
            
            for i, agent_id in enumerate(agents):
                agent_query = f"""
                Sequential Task {i+1}/{len(agents)}
                
                Objective: {objective}
                Previous Results: {json.dumps(results, indent=2)}
                Current Context: {json.dumps(accumulated_context, indent=2)}
                
                Build upon previous work and contribute your expertise.
                """
                
                agent_response = await self.agents[agent_id].process_query(agent_query)
                results[f"step_{i+1}_{agent_id}"] = agent_response
                
                # Update context for next agent
                accumulated_context[f"previous_{agent_id}"] = agent_response
            
            return {
                'type': 'sequential',
                'results': results,
                'participants': agents,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Sequential coordination failed: {str(e)}")
            raise
    
    async def _parallel_coordination(self, agents: List[str], objective: str,
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parallel coordination (agents work simultaneously)"""
        try:
            # Prepare queries for each agent
            agent_tasks = []
            
            for agent_id in agents:
                agent_query = f"""
                Parallel Task Assignment
                
                Objective: {objective}
                Your Role: Provide {agent_id} perspective and expertise
                Context: {json.dumps(context.get('context', {}), indent=2)}
                
                Work independently and provide your best contribution.
                """
                
                task = self.agents[agent_id].process_query(agent_query)
                agent_tasks.append((agent_id, task))
            
            # Execute all tasks in parallel
            results = {}
            completed_tasks = await asyncio.gather(
                *[task for _, task in agent_tasks],
                return_exceptions=True
            )
            
            # Collect results
            for (agent_id, _), result in zip(agent_tasks, completed_tasks):
                if isinstance(result, Exception):
                    results[agent_id] = f"Error: {str(result)}"
                else:
                    results[agent_id] = result
            
            return {
                'type': 'parallel',
                'results': results,
                'participants': agents,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Parallel coordination failed: {str(e)}")
            raise
    
    async def get_agent_status(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of specific agent or all agents"""
        try:
            if agent_id:
                if agent_id not in self.agent_info:
                    raise ValueError(f"Agent {agent_id} not found")
                
                agent_info = self.agent_info[agent_id]
                return {
                    'agent_id': agent_id,
                    'status': agent_info.status.value,
                    'current_task': agent_info.current_task,
                    'task_queue_size': agent_info.task_queue_size,
                    'last_activity': agent_info.last_activity.isoformat() if agent_info.last_activity else None,
                    'performance_metrics': agent_info.performance_metrics
                }
            else:
                # Return status of all agents
                all_status = {}
                for aid, info in self.agent_info.items():
                    all_status[aid] = {
                        'status': info.status.value,
                        'current_task': info.current_task,
                        'task_queue_size': info.task_queue_size,
                        'last_activity': info.last_activity.isoformat() if info.last_activity else None
                    }
                
                return {
                    'agents': all_status,
                    'total_agents': len(self.agent_info),
                    'active_agents': len([info for info in self.agent_info.values() 
                                        if info.status == AgentStatus.ACTIVE]),
                    'busy_agents': len([info for info in self.agent_info.values() 
                                      if info.status == AgentStatus.BUSY]),
                    'coordination_stats': self.coordination_stats
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get agent status: {str(e)}")
            return {'error': str(e)}
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            health_status = {
                'coordinator_status': 'healthy',
                'agents': {},
                'active_tasks': len(self.active_tasks),
                'total_agents': len(self.agents),
                'memory_manager': await self.memory_manager.get_health_status(),
                'performance_stats': self.coordination_stats,
                'timestamp': datetime.now().isoformat()
            }
            
            # Check each agent's health
            for agent_id, agent in self.agents.items():
                try:
                    agent_health = await agent.get_health_status()
                    health_status['agents'][agent_id] = {
                        'status': self.agent_info[agent_id].status.value,
                        'health': agent_health,
                        'responsive': True
                    }
                except Exception as e:
                    health_status['agents'][agent_id] = {
                        'status': 'error',
                        'error': str(e),
                        'responsive': False
                    }
            
            # Overall health assessment
            unhealthy_agents = [
                aid for aid, status in health_status['agents'].items() 
                if not status.get('responsive', True)
            ]
            
            if len(unhealthy_agents) > len(self.agents) * 0.5:
                health_status['coordinator_status'] = 'critical'
            elif unhealthy_agents:
                health_status['coordinator_status'] = 'degraded'
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                'coordinator_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    # Helper methods
    async def _activate_agent(self, agent_id: str):
        """Activate specific agent"""
        if agent_id in self.agents:
            self.agent_info[agent_id].status = AgentStatus.ACTIVE
            self.agent_info[agent_id].last_activity = datetime.now()
            self.logger.info(f"Agent {agent_id} activated")
    
    async def _deactivate_agent(self, agent_id: str):
        """Deactivate specific agent"""
        if agent_id in self.agents:
            self.agent_info[agent_id].status = AgentStatus.INACTIVE
            self.logger.info(f"Agent {agent_id} deactivated")
    
    async def _validate_task(self, task: AgentTask) -> bool:
        """Validate task structure and requirements"""
        try:
            # Basic validation
            if not task.task_id or not task.agent_id or not task.description:
                return False
            
            # Check if agent exists
            if task.agent_id not in self.agents:
                return False
            
            # Check dependencies
            for dep_id in task.dependencies:
                if dep_id not in self.active_tasks and dep_id not in [t.task_id for t in self.task_history]:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _execute_task(self, task: AgentTask):
        """Execute individual task"""
        try:
            start_time = datetime.now()
            
            # Wait for dependencies
            await self._wait_for_dependencies(task)
            
            # Execute task
            agent = self.agents[task.agent_id]
            task_query = f"""
            Task: {task.description}
            Priority: {task.priority.value}
            Context: {json.dumps(task.context, indent=2)}
            
            Please complete this task according to your role and expertise.
            """
            
            result = await agent.process_query(task_query)
            
            # Update task
            task.status = "completed"
            task.result = {'response': result, 'completion_time': datetime.now()}
            
            # Update statistics
            completion_time = (datetime.now() - start_time).total_seconds()
            self._update_task_stats(task, completion_time, True)
            
            # Move to history
            self.task_history.append(task)
            del self.active_tasks[task.task_id]
            
            # Update agent status
            self.agent_info[task.agent_id].status = AgentStatus.ACTIVE
            self.agent_info[task.agent_id].current_task = None
            self.agent_info[task.agent_id].task_queue_size = max(0, 
                self.agent_info[task.agent_id].task_queue_size - 1)
            
            self.logger.info(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            # Handle task failure
            task.status = "failed"
            task.error = str(e)
            
            completion_time = (datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0
            self._update_task_stats(task, completion_time, False)
            
            self.task_history.append(task)
            del self.active_tasks[task.task_id]
            
            # Update agent status
            if task.agent_id in self.agent_info:
                self.agent_info[task.agent_id].status = AgentStatus.ERROR
                self.agent_info[task.agent_id].current_task = None
            
            self.logger.error(f"Task {task.task_id} failed: {str(e)}")
    
    async def _wait_for_dependencies(self, task: AgentTask):
        """Wait for task dependencies to complete"""
        if not task.dependencies:
            return
        
        max_wait_time = 300  # 5 minutes
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < max_wait_time:
            pending_deps = []
            for dep_id in task.dependencies:
                if dep_id in self.active_tasks:
                    pending_deps.append(dep_id)
            
            if not pending_deps:
                break
            
            await asyncio.sleep(1)
        
        if pending_deps:
            raise TimeoutError(f"Dependencies not completed: {pending_deps}")
    
    def _update_task_stats(self, task: AgentTask, completion_time: float, success: bool):
        """Update coordination statistics"""
        self.coordination_stats['total_tasks'] += 1
        
        if success:
            self.coordination_stats['completed_tasks'] += 1
        else:
            self.coordination_stats['failed_tasks'] += 1
        
        # Update average completion time
        current_avg = self.coordination_stats['avg_completion_time']
        total_tasks = self.coordination_stats['total_tasks']
        
        if current_avg == 0:
            self.coordination_stats['avg_completion_time'] = completion_time
        else:
            self.coordination_stats['avg_completion_time'] = (
                (current_avg * (total_tasks - 1)) + completion_time
            ) / total_tasks
        
        # Update agent utilization
        agent_id = task.agent_id
        if agent_id not in self.coordination_stats['agent_utilization']:
            self.coordination_stats['agent_utilization'][agent_id] = {
                'tasks_completed': 0,
                'avg_completion_time': 0,
                'success_rate': 0
            }
        
        agent_stats = self.coordination_stats['agent_utilization'][agent_id]
        agent_stats['tasks_completed'] += 1
        
        if success:
            # Update success rate
            current_success_rate = agent_stats['success_rate']
            tasks_completed = agent_stats['tasks_completed']
            agent_stats['success_rate'] = (
                (current_success_rate * (tasks_completed - 1)) + 1
            ) / tasks_completed
        
        # Update agent completion time
        current_agent_avg = agent_stats['avg_completion_time']
        if current_agent_avg == 0:
            agent_stats['avg_completion_time'] = completion_time
        else:
            agent_stats['avg_completion_time'] = (
                (current_agent_avg * (agent_stats['tasks_completed'] - 1)) + completion_time
            ) / agent_stats['tasks_completed']
    
    # Background monitoring tasks
    async def _task_monitor(self):
        """Monitor task execution and handle timeouts"""
        while True:
            try:
                current_time = datetime.now()
                timed_out_tasks = []
                
                for task_id, task in self.active_tasks.items():
                    task_age = (current_time - task.assigned_at).total_seconds()
                    if task_age > self.task_timeout:
                        timed_out_tasks.append(task_id)
                
                # Handle timed out tasks
                for task_id in timed_out_tasks:
                    task = self.active_tasks[task_id]
                    task.status = "timeout"
                    task.error = "Task execution timeout"
                    
                    self.task_history.append(task)
                    del self.active_tasks[task_id]
                    
                    # Reset agent status
                    if task.agent_id in self.agent_info:
                        self.agent_info[task.agent_id].status = AgentStatus.ACTIVE
                        self.agent_info[task.agent_id].current_task = None
                    
                    self.logger.warning(f"Task {task_id} timed out")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Task monitor error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _performance_monitor(self):
        """Monitor system performance and optimization"""
        while True:
            try:
                # Performance monitoring logic here
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Performance monitor error: {str(e)}")
                await asyncio.sleep(600)
    
    async def _health_monitor(self):
        """Monitor agent and system health"""
        while True:
            try:
                # Health monitoring logic here
                health_status = await self.get_system_health()
                
                # Log health issues
                if health_status['coordinator_status'] != 'healthy':
                    self.logger.warning(f"System health: {health_status['coordinator_status']}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Health monitor error: {str(e)}")
                await asyncio.sleep(120)
    
    async def _complete_pending_tasks(self):
        """Complete or cancel pending tasks during shutdown"""
        if not self.active_tasks:
            return
        
        self.logger.info(f"Completing {len(self.active_tasks)} pending tasks...")
        
        # Wait for tasks to complete (with timeout)
        wait_time = 30
        start_time = datetime.now()
        
        while self.active_tasks and (datetime.now() - start_time).total_seconds() < wait_time:
            await asyncio.sleep(1)
        
        # Cancel remaining tasks
        for task_id, task in self.active_tasks.items():
            task.status = "cancelled"
            task.error = "System shutdown"
            self.task_history.append(task)
        
        self.active_tasks.clear()
    
    async def _save_coordinator_state(self):
        """Save coordinator state for recovery"""
        try:
            state = {
                'coordination_stats': self.coordination_stats,
                'agent_info': {
                    aid: asdict(info) for aid, info in self.agent_info.items()
                },
                'task_history_count': len(self.task_history),
                'shutdown_time': datetime.now().isoformat()
            }
            
            # Save to memory manager or file
            await self.memory_manager.store_system_state('coordinator_state', state)
            
        except Exception as e:
            self.logger.error(f"Failed to save coordinator state: {str(e)}")


# Utility functions for easy coordinator usage
async def create_coordinator(config: Optional[Dict[str, Any]] = None) -> AgentCoordinator:
    """Create and start agent coordinator"""
    if config is None:
        config = get_config()
    
    coordinator = AgentCoordinator(config)
    await coordinator.start_coordinator()
    return coordinator


async def create_simple_task(agent_id: str, description: str, 
                           priority: str = "normal", context: Optional[Dict] = None) -> AgentTask:
    """Create a simple agent task"""
    return AgentTask(
        task_id=str(uuid.uuid4()),
        agent_id=agent_id,
        task_type="general",
        description=description,
        priority=TaskPriority(priority),
        assigned_at=datetime.now(),
        context=context or {}
    )


# Example usage
async def example_coordination():
    """Example of how to use the agent coordinator"""
    # Create coordinator
    coordinator = await create_coordinator()
    
    try:
        # Assign individual task
        task = await create_simple_task(
            agent_id="ceo_agent",
            description="Analyze Q4 performance and create strategic plan for next year",
            priority="high",
            context={"quarter": "Q4", "year": 2024}
        )
        
        task_id = await coordinator.assign_task(task)
        print(f"Task assigned: {task_id}")
        
        # Coordinate multiple agents
        coordination_request = {
            'type': 'collaborative',
            'agents': ['ceo_agent', 'cfo_agent', 'cto_agent'],
            'objective': 'Develop comprehensive business strategy for 2025',
            'context': {
                'budget_range': '10M-50M',
                'target_growth': '200%',
                'focus_areas': ['AI', 'expansion', 'efficiency']
            }
        }
        
        coordination_result = await coordinator.coordinate_agents(coordination_request)
        print(f"Coordination result: {coordination_result['success']}")
        
        # Get system status
        status = await coordinator.get_agent_status()
        print(f"Active agents: {status['active_agents']}")
        
    finally:
        # Cleanup
        await coordinator.stop_coordinator()


if __name__ == "__main__":
    asyncio.run(example_coordination())