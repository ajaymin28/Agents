"""
Coordinator Agent Module

This module implements the Coordinator Agent that orchestrates tasks
between specialized agents in the Ollama agent framework.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from ..core.engine import CoreEngine
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class CoordinatorAgent:
    """
    Coordinator Agent for the Ollama agent framework.
    
    Responsible for:
    - Task delegation to specialized agents
    - Result aggregation from multiple agents
    - Multi-step workflow orchestration
    - Conflict resolution between agents
    """
    
    def __init__(self, 
                engine: CoreEngine,
                settings: Optional[Settings] = None):
        """
        Initialize the Coordinator Agent.
        
        Args:
            engine: Core Engine instance
            settings: Configuration settings
        """
        self.engine = engine
        self.settings = settings or Settings()
        self.agent_type = "coordinator"
        self.capabilities = [
            "task_delegation",
            "result_aggregation",
            "workflow_orchestration"
        ]
        logger.info("Coordinator Agent initialized")
        
    async def initialize(self, resource_profile: Dict[str, Any]):
        """
        Initialize the agent with resource profile.
        
        Args:
            resource_profile: Resource availability information
        """
        logger.info(f"Initializing Coordinator Agent with resource profile: {resource_profile}")
        
        # Register with the engine
        await self.engine.register_agent("coordinator_agent", self)
        
    async def shutdown(self):
        """Shutdown the agent and cleanup resources."""
        logger.info("Shutting down Coordinator Agent")
        # Nothing specific to clean up
        
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task assigned to this agent.
        
        Args:
            task: Task information
            
        Returns:
            Task result
        """
        task_type = task.get("type")
        logger.info(f"Processing {task_type} task: {task.get('id')}")
        
        if task_type == "multi_agent_task":
            return await self.process_multi_agent_task(task)
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
            
    async def get_resource_requirements(self, task: Dict[str, Any]) -> Dict[str, float]:
        """
        Get resource requirements for a task.
        
        Args:
            task: Task information
            
        Returns:
            Dictionary of resource requirements
        """
        # Coordinator itself has minimal resource requirements
        # as it mainly delegates work to other agents
        requirements = {
            "memory_gb": 0.5,
            "vram_gb": 0.1,
            "cpu_percent": 10.0,
            "gpu_percent": 5.0
        }
        
        return requirements
        
    async def coordinate_task(self, task: Dict[str, Any], agent_ids: List[str]) -> Dict[str, Any]:
        """
        Coordinate a task across multiple agents.
        
        Args:
            task: Task to coordinate
            agent_ids: List of agent IDs to involve
            
        Returns:
            Combined result from all agents
        """
        logger.info(f"Coordinating task {task.get('id')} across {len(agent_ids)} agents")
        
        # Extract steps if this is a multi-step task
        steps = task.get("inputs", {}).get("steps", [])
        
        if steps:
            # Process multi-step workflow
            return await self._process_workflow(task, steps)
        else:
            # Process parallel task
            return await self._process_parallel(task, agent_ids)
            
    async def process_multi_agent_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a multi-agent task.
        
        Args:
            task: Task information
            
        Returns:
            Task result
        """
        logger.info(f"Processing multi-agent task: {task.get('id')}")
        
        # Extract steps
        steps = task.get("inputs", {}).get("steps", [])
        
        if not steps:
            raise ValueError("Multi-agent task requires steps")
            
        # Process workflow
        return await self._process_workflow(task, steps)
        
    async def _process_workflow(self, task: Dict[str, Any], steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a multi-step workflow.
        
        Args:
            task: Parent task
            steps: List of workflow steps
            
        Returns:
            Combined result from all steps
        """
        logger.info(f"Processing workflow with {len(steps)} steps")
        
        results = []
        step_results = {}
        
        # Process steps sequentially
        for i, step in enumerate(steps):
            logger.info(f"Processing workflow step {i+1}/{len(steps)}")
            
            # Get agent and action
            agent_id = step.get("agent")
            action = step.get("action")
            parameters = step.get("parameters", {})
            
            if not agent_id or not action:
                raise ValueError(f"Step {i+1} missing agent or action")
                
            # Get agent
            agent = self.engine.agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent not found: {agent_id}")
                
            # Prepare step inputs
            step_inputs = {
                "action": action,
                "parameters": parameters
            }
            
            # Add results from previous steps if referenced
            for param_key, param_value in parameters.items():
                if isinstance(param_value, str) and param_value.startswith("$result."):
                    # Extract step index and result key
                    parts = param_value[8:].split(".")
                    if len(parts) >= 2:
                        try:
                            ref_step = int(parts[0])
                            ref_key = parts[1]
                            
                            if ref_step < i and ref_step in step_results:
                                # Replace with actual value from previous step
                                if ref_key in step_results[ref_step]:
                                    step_inputs["parameters"][param_key] = step_results[ref_step][ref_key]
                        except (ValueError, IndexError):
                            logger.warning(f"Invalid result reference: {param_value}")
            
            # Create step task
            step_task = {
                "id": f"{task.get('id')}_step{i+1}",
                "type": action,
                "inputs": step_inputs,
                "parameters": parameters
            }
            
            # Process step
            try:
                step_result = await agent.process_task(step_task)
                
                # Store result for this step
                step_results[i] = step_result
                
                # Add to results list
                results.append({
                    "agent": agent_id,
                    "action": action,
                    "status": "completed",
                    "result": step_result
                })
                
            except Exception as e:
                logger.exception(f"Error in workflow step {i+1}: {e}")
                
                # Add error to results
                results.append({
                    "agent": agent_id,
                    "action": action,
                    "status": "failed",
                    "error": str(e)
                })
                
                # Decide whether to continue or abort
                if step.get("critical", False):
                    logger.warning(f"Critical step {i+1} failed, aborting workflow")
                    break
        
        # Calculate total processing time
        total_time = sum(
            step.get("result", {}).get("processing_time", 0) 
            for step in results 
            if step.get("status") == "completed"
        )
        
        return {
            "steps": results,
            "processing_time": total_time
        }
        
    async def _process_parallel(self, task: Dict[str, Any], agent_ids: List[str]) -> Dict[str, Any]:
        """
        Process a task in parallel across multiple agents.
        
        Args:
            task: Task to process
            agent_ids: List of agent IDs to involve
            
        Returns:
            Combined result from all agents
        """
        logger.info(f"Processing task {task.get('id')} in parallel across {len(agent_ids)} agents")
        
        results = []
        tasks = []
        
        # Create subtasks for each agent
        for agent_id in agent_ids:
            agent = self.engine.agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent not found: {agent_id}")
                continue
                
            # Create subtask
            subtask = {
                "id": f"{task.get('id')}_{agent_id}",
                "type": task.get("type"),
                "inputs": task.get("inputs", {}),
                "parameters": task.get("parameters", {})
            }
            
            # Add to tasks list
            tasks.append((agent_id, agent, subtask))
            
        # Process subtasks in parallel
        async def process_subtask(agent_id, agent, subtask):
            try:
                result = await agent.process_task(subtask)
                return {
                    "agent": agent_id,
                    "status": "completed",
                    "result": result
                }
            except Exception as e:
                logger.exception(f"Error in parallel subtask for agent {agent_id}: {e}")
                return {
                    "agent": agent_id,
                    "status": "failed",
                    "error": str(e)
                }
                
        # Run all subtasks
        subtask_results = await asyncio.gather(
            *[process_subtask(agent_id, agent, subtask) for agent_id, agent, subtask in tasks],
            return_exceptions=True
        )
        
        # Process results
        for result in subtask_results:
            if isinstance(result, Exception):
                logger.error(f"Unhandled exception in parallel processing: {result}")
                continue
                
            results.append(result)
            
        # Calculate total processing time
        total_time = max(
            result.get("result", {}).get("processing_time", 0) 
            for result in results 
            if result.get("status") == "completed"
        ) if results else 0
        
        return {
            "results": results,
            "processing_time": total_time
        }
        
    async def _resolve_conflicts(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolve conflicts between agent results.
        
        Args:
            results: List of results from different agents
            
        Returns:
            Resolved result
        """
        logger.info(f"Resolving conflicts between {len(results)} results")
        
        # Simple conflict resolution strategy:
        # 1. Filter out failed results
        # 2. If only one result remains, use it
        # 3. If multiple results, use the one with highest confidence
        # 4. If no confidence scores, merge results
        
        # Filter out failed results
        successful_results = [r for r in results if r.get("status") == "completed"]
        
        if not successful_results:
            return {"error": "All agent results failed"}
            
        if len(successful_results) == 1:
            return successful_results[0].get("result", {})
            
        # Check for confidence scores
        results_with_confidence = [
            r for r in successful_results 
            if "confidence" in r.get("result", {})
        ]
        
        if results_with_confidence:
            # Use result with highest confidence
            best_result = max(
                results_with_confidence,
                key=lambda r: r.get("result", {}).get("confidence", 0)
            )
            return best_result.get("result", {})
            
        # Merge results
        merged_result = {}
        for r in successful_results:
            merged_result.update(r.get("result", {}))
            
        return merged_result
