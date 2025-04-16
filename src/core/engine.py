"""
Core Engine Module

This module implements the central engine that manages agent lifecycle, task routing,
and system resources for the Ollama agent framework.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable

from ..utils.resource_monitor import ResourceMonitor
from ..core.communication_bus import CommunicationBus
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class CoreEngine:
    """
    Core Engine for the Ollama agent framework.
    
    Responsible for:
    - Managing agent lifecycle
    - Task routing and scheduling
    - System resource management
    - Agent state management
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the Core Engine.
        
        Args:
            settings: Configuration settings for the engine
        """
        self.settings = settings or Settings()
        self.agents = {}
        self.tasks = {}
        self.communication_bus = CommunicationBus()
        self.resource_monitor = ResourceMonitor()
        self.event_handlers = {}
        logger.info("Core Engine initialized")
        
    async def start(self):
        """Start the Core Engine and initialize components."""
        logger.info("Starting Core Engine")
        await self.resource_monitor.start()
        # Initialize resource-aware configuration
        await self._configure_for_available_resources()
        logger.info("Core Engine started")
        
    async def stop(self):
        """Stop the Core Engine and cleanup resources."""
        logger.info("Stopping Core Engine")
        await self.resource_monitor.stop()
        # Gracefully shutdown all agents
        for agent_id, agent in self.agents.items():
            logger.info(f"Shutting down agent: {agent_id}")
            await agent.shutdown()
        logger.info("Core Engine stopped")
        
    async def register_agent(self, agent_id: str, agent: Any):
        """
        Register an agent with the Core Engine.
        
        Args:
            agent_id: Unique identifier for the agent
            agent: Agent instance to register
        """
        logger.info(f"Registering agent: {agent_id}")
        # Check if agent is already registered
        if agent_id in self.agents:
            logger.warning(f"Agent already registered: {agent_id}")
            return False
    
        self.agents[agent_id] = agent
        # Initialize agent with current resource constraints
        resource_profile = await self.resource_monitor.get_resource_profile()
        await agent.initialize(resource_profile)
        
    async def unregister_agent(self, agent_id: str):
        """
        Unregister an agent from the Core Engine.
        
        Args:
            agent_id: Unique identifier for the agent to unregister
        """
        if agent_id in self.agents:
            logger.info(f"Unregistering agent: {agent_id}")
            await self.agents[agent_id].shutdown()
            del self.agents[agent_id]
        
    async def create_task(self, task_type: str, inputs: Dict[str, Any], 
                         parameters: Dict[str, Any]) -> str:
        """
        Create a new task to be processed by agents.
        
        Args:
            task_type: Type of task to create
            inputs: Input data for the task
            parameters: Parameters for task execution
            
        Returns:
            task_id: Unique identifier for the created task
        """
        import uuid
        task_id = str(uuid.uuid4())
        
        logger.info(f"Creating task: {task_id} of type: {task_type}")
        
        # Create task object
        task = {
            "id": task_id,
            "type": task_type,
            "inputs": inputs,
            "parameters": parameters,
            "status": "pending",
            "created_at": asyncio.get_event_loop().time(),
            "agent_assignments": []
        }
        
        self.tasks[task_id] = task
        
        # Schedule task for processing
        asyncio.create_task(self._process_task(task_id))
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status of a task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Task status information
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        return {
            "id": task_id,
            "status": self.tasks[task_id]["status"],
            "created_at": self.tasks[task_id]["created_at"],
            "result": self.tasks[task_id].get("result")
        }
    
    async def _process_task(self, task_id: str):
        """
        Process a task by routing it to appropriate agents.
        
        Args:
            task_id: Unique identifier for the task to process
        """
        task = self.tasks[task_id]
        task["status"] = "processing"
        
        try:
            # Determine which agent(s) should handle this task
            agent_ids = await self._route_task(task)
            
            if not agent_ids:
                logger.warning(f"No suitable agents found for task: {task_id}")
                task["status"] = "failed"
                task["error"] = "No suitable agents available"
                return
            
            # For multi-agent tasks, use coordinator
            if len(agent_ids) > 1:
                logger.info(f"Multi-agent task: {task_id}, using coordinator")
                result = await self._coordinate_multi_agent_task(task, agent_ids)
            else:
                # Single agent task
                agent_id = agent_ids[0]
                logger.info(f"Assigning task: {task_id} to agent: {agent_id}")
                agent = self.agents[agent_id]
                result = await agent.process_task(task)
            
            # Update task with result
            task["status"] = "completed"
            task["result"] = result
            task["completed_at"] = asyncio.get_event_loop().time()
            
            # Publish task completion event
            await self._publish_event("task_completed", {
                "task_id": task_id,
                "result": result
            })
            
        except Exception as e:
            logger.exception(f"Error processing task: {task_id}")
            task["status"] = "failed"
            task["error"] = str(e)
            
            # Publish task failure event
            await self._publish_event("task_failed", {
                "task_id": task_id,
                "error": str(e)
            })
    
    async def _route_task(self, task: Dict[str, Any]) -> List[str]:
        """
        Route a task to appropriate agent(s) based on task type and available resources.
        
        Args:
            task: Task to route
            
        Returns:
            List of agent IDs that should process this task
        """
        task_type = task["type"]
        suitable_agents = []
        
        # Check each agent's capabilities
        for agent_id, agent in self.agents.items():
            if task_type in agent.capabilities:
                # Check if agent has enough resources
                if await self._check_agent_resources(agent_id, task):
                    suitable_agents.append(agent_id)
        
        return suitable_agents
    
    async def _check_agent_resources(self, agent_id: str, task: Dict[str, Any]) -> bool:
        """
        Check if an agent has sufficient resources to handle a task.
        
        Args:
            agent_id: Agent to check
            task: Task to process
            
        Returns:
            True if agent has sufficient resources, False otherwise
        """
        agent = self.agents[agent_id]
        resource_requirements = await agent.get_resource_requirements(task)
        available_resources = await self.resource_monitor.get_available_resources()
        
        # Check each resource type
        for resource_type, required in resource_requirements.items():
            if resource_type not in available_resources:
                logger.warning(f"Resource type not monitored: {resource_type}")
                continue
                
            if required > available_resources[resource_type]:
                logger.info(f"Agent {agent_id} lacks sufficient {resource_type} for task")
                return False
        
        return True
    
    async def _coordinate_multi_agent_task(self, task: Dict[str, Any], 
                                          agent_ids: List[str]) -> Dict[str, Any]:
        """
        Coordinate a task that requires multiple agents.
        
        Args:
            task: Task to coordinate
            agent_ids: List of agent IDs to involve
            
        Returns:
            Combined result from all agents
        """
        # Find coordinator agent
        coordinator = None
        for agent_id, agent in self.agents.items():
            if "coordinator" in agent.agent_type:
                coordinator = agent
                break
        
        if not coordinator:
            raise RuntimeError("No coordinator agent available for multi-agent task")
        
        # Let coordinator handle the multi-agent task
        return await coordinator.coordinate_task(task, agent_ids)
    
    async def _configure_for_available_resources(self):
        """Configure the system based on available resources."""
        resources = await self.resource_monitor.get_resource_profile()
        logger.info(f"Configuring for available resources: {resources}")
        
        # Determine if we're in a low-resource environment
        is_low_resource = resources.get("vram_gb", float("inf")) <= 4.0
        
        if is_low_resource:
            logger.info("Detected low-resource environment (≤4GB VRAM)")
            # Apply low-resource configuration
            self.settings.apply_low_resource_settings()
        else:
            logger.info(f"Standard resource environment: {resources.get('vram_gb')}GB VRAM")
            # Apply standard configuration
            self.settings.apply_standard_settings()
    
    async def register_event_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: Type of event to handle
            handler: Callback function to invoke when event occurs
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
    
    async def _publish_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Publish an event to registered handlers.
        
        Args:
            event_type: Type of event to publish
            event_data: Data associated with the event
        """
        if event_type not in self.event_handlers:
            return
        
        for handler in self.event_handlers[event_type]:
            try:
                await handler(event_data)
            except Exception as e:
                logger.exception(f"Error in event handler for {event_type}: {e}")
