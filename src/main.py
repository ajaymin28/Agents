"""
Main Application Module

This module provides the entry point for the Ollama agent framework.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, List, Any, Optional

from .core.engine import CoreEngine
from .core.communication_bus import CommunicationBus
from .utils.resource_monitor import ResourceMonitor
from .config.settings import Settings
from .models.ollama_client import OllamaClient
from .agents.vlm_agent import VLMAgent
from .agents.stable_diffusion_agent import StableDiffusionAgent
from .agents.coordinator_agent import CoordinatorAgent
from .agents.tool_agent import ToolAgent
from .mcp.mcp_client import MCPClient
from .plugins.plugin_manager import PluginManager
from .api.server import APIServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class Application:
    """
    Main application class for the Ollama agent framework.
    
    Responsible for:
    - Initializing and coordinating all components
    - Managing application lifecycle
    - Handling configuration
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the application.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        # Load settings
        self.settings = Settings(config_path)
        
        # Initialize components
        self.communication_bus = CommunicationBus()
        self.resource_monitor = ResourceMonitor()
        self.engine = CoreEngine(self.settings)
        self.engine.resource_monitor = self.resource_monitor

        self.ollama_client = OllamaClient(
            base_url=self.settings.get("ollama", "base_url", "http://localhost:11434"),
            timeout=self.settings.get("ollama", "timeout", 60)
        )
        self.mcp_client = MCPClient(self.settings)
        self.plugin_manager = PluginManager(self.engine, self.settings)
        self.api_server = APIServer(self.engine, self.settings)
        
        # Initialize agents
        self.vlm_agent = VLMAgent(self.engine, self.ollama_client, self.settings)
        self.sd_agent = StableDiffusionAgent(self.engine, self.ollama_client, self.settings)
        self.coordinator_agent = CoordinatorAgent(self.engine, self.settings)
        self.tool_agent = ToolAgent(self.engine, self.mcp_client, self.settings)
        
        logger.info("Application initialized")
        
    async def start(self):
        """Start the application and all components."""
        logger.info("Starting application")
        
        # Start core components
        await self.communication_bus.start()
        await self.resource_monitor.start()
        await self.engine.start()
        
        # Start clients
        await self.ollama_client.start()
        await self.mcp_client.start()
        
        # Start plugin manager
        await self.plugin_manager.start()
        
        # Get resource profile
        resource_profile = await self.resource_monitor.get_resource_profile()
        logger.info(f"Resource profile: {resource_profile}")
        
        # Apply appropriate settings based on resource tier
        if resource_profile.get("resource_tier") == "low":
            logger.info("Applying low-resource settings")
            self.settings.apply_low_resource_settings()
        elif resource_profile.get("resource_tier") == "medium":
            logger.info("Applying standard settings")
            self.settings.apply_standard_settings()
        else:
            logger.info("Applying high-resource settings")
            self.settings.apply_high_resource_settings()
    
        # Make sure each agent is only initialized once
        if not hasattr(self.coordinator_agent, '_initialized'):
            await self.coordinator_agent.initialize(resource_profile)
            self.coordinator_agent._initialized = True
            
        if not hasattr(self.vlm_agent, '_initialized'):
            await self.vlm_agent.initialize(resource_profile)
            self.vlm_agent._initialized = True
            
        if not hasattr(self.sd_agent, '_initialized'):
            await self.sd_agent.initialize(resource_profile)
            self.sd_agent._initialized = True
            
        if not hasattr(self.tool_agent, '_initialized'):
            await self.tool_agent.initialize(resource_profile)
            self.tool_agent._initialized = True
        
        # Start API server
        await self.api_server.start()
        
        logger.info("Application started")
        
    async def stop(self):
        """Stop the application and all components."""
        logger.info("Stopping application")
        
        # Stop API server
        await self.api_server.stop()
        
        # Stop agents
        await self.tool_agent.shutdown()
        await self.sd_agent.shutdown()
        await self.vlm_agent.shutdown()
        await self.coordinator_agent.shutdown()
        
        # Stop plugin manager
        await self.plugin_manager.stop()
        
        # Stop clients
        await self.mcp_client.stop()
        await self.ollama_client.stop()
        
        # Stop core components
        await self.engine.stop()
        await self.resource_monitor.stop()
        await self.communication_bus.stop()
        
        logger.info("Application stopped")
        
    def run(self):
        """Run the application (blocking)."""
        # Start the application
        asyncio.run(self.start())
        
        # Run the API server (blocking)
        self.api_server.run()
        
        # This will only be reached when the API server is stopped
        asyncio.run(self.stop())

# Entry point
if __name__ == "__main__":
    # Get configuration path from command line arguments
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    import platform
    if platform.system()=='Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Create and run application
    app = Application(config_path)
    app.run()
