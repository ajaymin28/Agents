"""
Plugin Base Module

This module defines the base class and decorators for creating plugins
in the Ollama agent framework.
"""

import asyncio
import inspect
import logging
from typing import Dict, List, Any, Optional, Callable, ClassVar, Type

logger = logging.getLogger(__name__)

def plugin(cls):
    """
    Decorator to mark a class as a plugin.
    
    Args:
        cls: Class to mark as a plugin
        
    Returns:
        Modified class
    """
    cls.is_plugin = True
    return cls

def capability(name: str):
    """
    Decorator to register a method as a capability.
    
    Args:
        name: Capability name
        
    Returns:
        Decorator function
    """
    def decorator(func):
        func.is_capability = True
        func.capability_name = name
        return func
    return decorator

class PluginBase:
    """
    Base class for plugins in the Ollama agent framework.
    
    All plugins should inherit from this class and use the @plugin decorator.
    """
    
    is_plugin: ClassVar[bool] = False
    dependencies: ClassVar[List[str]] = []
    
    def __init__(self, engine):
        """
        Initialize the plugin.
        
        Args:
            engine: Core Engine instance
        """
        self.engine = engine
        self.capabilities = []
        self._discover_capabilities()
        logger.info(f"Plugin {self.__class__.__name__} initialized")
        
    def _discover_capabilities(self):
        """Discover capabilities provided by this plugin."""
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "is_capability") and method.is_capability:
                self.capabilities.append(method.capability_name)
                
    async def initialize(self):
        """
        Initialize the plugin.
        
        This method is called when the plugin is loaded.
        Override this method to perform initialization tasks.
        """
        pass
        
    async def shutdown(self):
        """
        Shutdown the plugin.
        
        This method is called when the plugin is unloaded.
        Override this method to perform cleanup tasks.
        """
        pass
        
    async def get_info(self) -> Dict[str, Any]:
        """
        Get information about the plugin.
        
        Returns:
            Dictionary containing plugin information
        """
        return {
            "name": self.__class__.__name__,
            "capabilities": self.capabilities,
            "dependencies": self.__class__.dependencies
        }
