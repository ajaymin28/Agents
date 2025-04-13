"""
Tool Agent Module

This module implements the Tool Agent that handles integration with
external tools through the Model Context Protocol (MCP).
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from ..core.engine import CoreEngine
from ..mcp.mcp_client import MCPClient
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class ToolAgent:
    """
    Tool Agent for the Ollama agent framework.
    
    Responsible for:
    - Integrating with external tools via MCP
    - Discovering and registering tools
    - Executing tool operations
    - Handling tool results
    """
    
    def __init__(self, 
                engine: CoreEngine,
                mcp_client: MCPClient,
                settings: Optional[Settings] = None):
        """
        Initialize the Tool Agent.
        
        Args:
            engine: Core Engine instance
            mcp_client: MCP Client instance
            settings: Configuration settings
        """
        self.engine = engine
        self.mcp_client = mcp_client
        self.settings = settings or Settings()
        self.agent_type = "tool"
        self.capabilities = [
            "tool_execution",
            "web_search",
            "sequential_thinking",
            "memory_management"
        ]
        logger.info("Tool Agent initialized")
        
    async def initialize(self, resource_profile: Dict[str, Any]):
        """
        Initialize the agent with resource profile.
        
        Args:
            resource_profile: Resource availability information
        """
        logger.info(f"Initializing Tool Agent with resource profile: {resource_profile}")
        
        # Check if we're in a low-resource environment
        is_low_resource = resource_profile.get("resource_tier") == "low"
        
        if is_low_resource and not self.settings.get("agents", "tool_enabled", True):
            logger.info("Tool Agent disabled in low-resource mode")
            return
        
        # Register with the engine
        await self.engine.register_agent("tool_agent", self)
        
        # Discover available tools
        await self._discover_tools()
        
    async def shutdown(self):
        """Shutdown the agent and cleanup resources."""
        logger.info("Shutting down Tool Agent")
        # Nothing specific to clean up
        
    async def _discover_tools(self):
        """Discover available tools through MCP client."""
        logger.info("Discovering available tools")
        
        # This will use the MCP client to discover tools
        await self.mcp_client.discover_tools()
        
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
        
        if task_type == "tool_execution":
            return await self.execute_tool(
                tool_id=task.get("inputs", {}).get("tool_id"),
                parameters=task.get("inputs", {}).get("parameters", {})
            )
        elif task_type == "web_search":
            return await self.web_search(
                query=task.get("inputs", {}).get("query")
            )
        elif task_type == "sequential_thinking":
            return await self.sequential_thinking(
                problem=task.get("inputs", {}).get("problem"),
                context=task.get("inputs", {}).get("context", {})
            )
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
        # Tool agent has minimal resource requirements
        # as it mainly delegates to external tools
        requirements = {
            "memory_gb": 0.5,
            "vram_gb": 0.1,
            "cpu_percent": 20.0,
            "gpu_percent": 5.0
        }
        
        return requirements
        
    async def execute_tool(self, 
                         tool_id: str, 
                         parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with parameters.
        
        Args:
            tool_id: ID of the tool to execute
            parameters: Parameters for the tool
            
        Returns:
            Tool execution result
        """
        logger.info(f"Executing tool: {tool_id}")
        
        try:
            # Invoke the tool through MCP client
            start_time = asyncio.get_event_loop().time()
            result = await self.mcp_client.invoke_tool(tool_id, parameters)
            end_time = asyncio.get_event_loop().time()
            
            # Add processing time
            result["processing_time"] = round(end_time - start_time, 2)
            
            logger.info(f"Tool execution completed in {result['processing_time']}s")
            return result
            
        except Exception as e:
            logger.exception(f"Error executing tool {tool_id}: {e}")
            return {
                "error": str(e),
                "message": f"Failed to execute tool {tool_id}"
            }
            
    async def web_search(self, query: str) -> Dict[str, Any]:
        """
        Perform a web search.
        
        Args:
            query: Search query
            
        Returns:
            Search results
        """
        logger.info(f"Performing web search: {query}")
        
        try:
            # Find a web search tool
            search_tool = await self.mcp_client.get_tool_by_capability("web_search")
            
            if not search_tool:
                logger.warning("No web search tool found")
                return {
                    "error": "No web search tool available",
                    "message": "Failed to perform web search"
                }
                
            # Execute the search
            start_time = asyncio.get_event_loop().time()
            result = await self.mcp_client.invoke_tool(
                search_tool.get("id"),
                {"query": query}
            )
            end_time = asyncio.get_event_loop().time()
            
            # Process results
            search_results = result.get("results", [])
            
            processed_results = {
                "items": search_results,
                "processing_time": round(end_time - start_time, 2)
            }
            
            logger.info(f"Web search completed in {processed_results['processing_time']}s")
            return processed_results
            
        except Exception as e:
            logger.exception(f"Error in web search: {e}")
            return {
                "error": str(e),
                "message": "Failed to perform web search"
            }
            
    async def sequential_thinking(self, 
                               problem: str, 
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform sequential thinking on a problem.
        
        Args:
            problem: Problem to solve
            context: Additional context
            
        Returns:
            Thinking process and solution
        """
        logger.info(f"Performing sequential thinking on problem: {problem}")
        
        try:
            # Find a sequential thinking tool
            thinking_tool = await self.mcp_client.get_tool_by_capability("sequential_thinking")
            
            if not thinking_tool:
                logger.warning("No sequential thinking tool found")
                return {
                    "error": "No sequential thinking tool available",
                    "message": "Failed to perform sequential thinking"
                }
                
            # Execute the thinking process
            start_time = asyncio.get_event_loop().time()
            result = await self.mcp_client.invoke_tool(
                thinking_tool.get("id"),
                {
                    "problem": problem,
                    "context": context
                }
            )
            end_time = asyncio.get_event_loop().time()
            
            # Add processing time
            result["processing_time"] = round(end_time - start_time, 2)
            
            logger.info(f"Sequential thinking completed in {result['processing_time']}s")
            return result
            
        except Exception as e:
            logger.exception(f"Error in sequential thinking: {e}")
            return {
                "error": str(e),
                "message": "Failed to perform sequential thinking"
            }
