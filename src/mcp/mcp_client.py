"""
MCP Client Module

This module implements the Model Context Protocol (MCP) client for
integrating with Smithery.ai tools and other MCP-compatible services.
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional, Union, Callable

import aiohttp

from ..config.settings import Settings

logger = logging.getLogger(__name__)

class MCPClient:
    """
    MCP Client for the Ollama agent framework.
    
    Responsible for:
    - Connecting to MCP servers
    - Discovering available tools
    - Invoking tools with parameters
    - Handling authentication and sessions
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the MCP Client.
        
        Args:
            settings: Configuration settings
        """
        self.settings = settings or Settings()
        self.session = None
        self.tools = {}
        self.smithery_api_key = self.settings.get("mcp", "smithery_api_key", "")
        self.smithery_base_url = "https://api.smithery.ai/v1"
        self.connections = {}
        logger.info("MCP Client initialized")
        
    async def start(self):
        """Start the MCP Client."""
        logger.info("Starting MCP Client")
        self.session = aiohttp.ClientSession()
        
        # Discover available tools
        if self.settings.get("mcp", "enabled", True):
            await self.discover_tools()
            
        logger.info("MCP Client started")
        
    async def stop(self):
        """Stop the MCP Client and cleanup resources."""
        logger.info("Stopping MCP Client")
        
        # Close all connections
        for server_id, connection in self.connections.items():
            try:
                await connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection to {server_id}: {e}")
                
        # Close session
        if self.session:
            await self.session.close()
            self.session = None
            
        logger.info("MCP Client stopped")
        
    async def discover_tools(self):
        """Discover available tools from Smithery.ai registry."""
        logger.info("Discovering available MCP tools")
        
        if not self.smithery_api_key:
            logger.warning("No Smithery API key provided, skipping tool discovery")
            return
            
        if not self.session:
            await self.start()
            
        try:
            headers = {
                "Authorization": f"Bearer {self.smithery_api_key}",
                "Content-Type": "application/json"
            }
            
            async with self.session.get(
                f"{self.smithery_base_url}/tools",
                headers=headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Process tools
                tools = data.get("tools", [])
                for tool in tools:
                    tool_id = tool.get("id")
                    if tool_id:
                        self.tools[tool_id] = tool
                        
                logger.info(f"Discovered {len(tools)} MCP tools")
                
        except Exception as e:
            logger.exception(f"Error discovering MCP tools: {e}")
            
    async def get_tool_by_capability(self, capability: str) -> Optional[Dict[str, Any]]:
        """
        Find a tool that provides a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            Tool information or None if not found
        """
        for tool_id, tool in self.tools.items():
            capabilities = tool.get("capabilities", [])
            if capability in capabilities:
                return tool
                
        return None
        
    async def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all tools in a specific category.
        
        Args:
            category: Category to search for
            
        Returns:
            List of tools in the category
        """
        return [
            tool for tool in self.tools.values()
            if tool.get("category") == category
        ]
        
    async def invoke_tool(self, 
                        tool_id: str, 
                        parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke an MCP tool with parameters.
        
        Args:
            tool_id: ID of the tool to invoke
            parameters: Parameters for the tool
            
        Returns:
            Tool result
        """
        logger.info(f"Invoking MCP tool: {tool_id}")
        
        if not self.smithery_api_key:
            raise ValueError("No Smithery API key provided")
            
        if not self.session:
            await self.start()
            
        try:
            headers = {
                "Authorization": f"Bearer {self.smithery_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "tool_id": tool_id,
                "parameters": parameters
            }
            
            async with self.session.post(
                f"{self.smithery_base_url}/invoke",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                logger.info(f"MCP tool {tool_id} invocation completed")
                return result
                
        except Exception as e:
            logger.exception(f"Error invoking MCP tool {tool_id}: {e}")
            return {
                "error": str(e),
                "message": f"Failed to invoke tool {tool_id}"
            }
            
    async def connect_to_server(self, server_id: str, url: str) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            server_id: Unique identifier for the server
            url: Server URL
            
        Returns:
            True if connection successful, False otherwise
        """
        logger.info(f"Connecting to MCP server: {server_id} at {url}")
        
        if not self.session:
            await self.start()
            
        try:
            # In a real implementation, we would establish a WebSocket connection
            # For now, we'll just simulate a connection
            self.connections[server_id] = {
                "url": url,
                "connected": True
            }
            
            logger.info(f"Connected to MCP server: {server_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Error connecting to MCP server {server_id}: {e}")
            return False
            
    async def disconnect_from_server(self, server_id: str) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            server_id: Unique identifier for the server
            
        Returns:
            True if disconnection successful, False otherwise
        """
        logger.info(f"Disconnecting from MCP server: {server_id}")
        
        if server_id not in self.connections:
            logger.warning(f"Not connected to MCP server: {server_id}")
            return False
            
        try:
            # In a real implementation, we would close the WebSocket connection
            # For now, we'll just simulate disconnection
            del self.connections[server_id]
            
            logger.info(f"Disconnected from MCP server: {server_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Error disconnecting from MCP server {server_id}: {e}")
            return False
            
    async def register_capability(self, 
                                capability: str, 
                                handler: Callable) -> bool:
        """
        Register a capability with a handler function.
        
        Args:
            capability: Capability to register
            handler: Function to handle capability requests
            
        Returns:
            True if registration successful, False otherwise
        """
        logger.info(f"Registering capability: {capability}")
        
        # In a real implementation, we would register with the MCP server
        # For now, we'll just log the registration
        logger.info(f"Registered capability: {capability}")
        return True
        
    async def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for tools matching a query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching tools
        """
        logger.info(f"Searching for MCP tools: {query}")
        
        if not self.smithery_api_key:
            logger.warning("No Smithery API key provided, skipping tool search")
            return []
            
        if not self.session:
            await self.start()
            
        try:
            headers = {
                "Authorization": f"Bearer {self.smithery_api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "query": query
            }
            
            async with self.session.get(
                f"{self.smithery_base_url}/tools/search",
                headers=headers,
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Process tools
                tools = data.get("tools", [])
                logger.info(f"Found {len(tools)} MCP tools matching query: {query}")
                return tools
                
        except Exception as e:
            logger.exception(f"Error searching MCP tools: {e}")
            return []
