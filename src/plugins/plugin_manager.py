"""
Plugin Manager Module

This module implements the Plugin Manager that handles the registration,
loading, and lifecycle management of plugins in the Ollama agent framework.
"""

import asyncio
import importlib
import importlib.util
import inspect
import logging
import os
import sys
from typing import Dict, List, Any, Optional, Callable, Type

from ..core.engine import CoreEngine
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class PluginManager:
    """
    Plugin Manager for the Ollama agent framework.
    
    Responsible for:
    - Discovering and loading plugins
    - Managing plugin lifecycle
    - Providing plugin registry
    - Handling plugin dependencies
    """
    
    def __init__(self, 
                engine: CoreEngine,
                settings: Optional[Settings] = None):
        """
        Initialize the Plugin Manager.
        
        Args:
            engine: Core Engine instance
            settings: Configuration settings
        """
        self.engine = engine
        self.settings = settings or Settings()
        self.plugins = {}
        self.plugin_instances = {}
        self.plugin_dir = self.settings.get("plugins", "plugin_dir", "plugins")
        self.auto_discover = self.settings.get("plugins", "auto_discover", True)
        logger.info("Plugin Manager initialized")
        
    async def start(self):
        """Start the Plugin Manager and load plugins."""
        logger.info("Starting Plugin Manager")
        
        # Discover and load plugins
        if self.auto_discover:
            await self.discover_plugins()
            
        logger.info("Plugin Manager started")
        
    async def stop(self):
        """Stop the Plugin Manager and unload plugins."""
        logger.info("Stopping Plugin Manager")
        
        # Unload all plugins
        for plugin_id in list(self.plugin_instances.keys()):
            await self.unload_plugin(plugin_id)
            
        logger.info("Plugin Manager stopped")
        
    async def discover_plugins(self):
        """Discover available plugins in the plugin directory."""
        logger.info(f"Discovering plugins in {self.plugin_dir}")
        
        # Ensure plugin directory exists
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir, exist_ok=True)
            logger.info(f"Created plugin directory: {self.plugin_dir}")
            return
            
        # Get absolute path
        plugin_dir = os.path.abspath(self.plugin_dir)
        
        # Add plugin directory to Python path
        if plugin_dir not in sys.path:
            sys.path.append(plugin_dir)
            
        # Find plugin modules
        for item in os.listdir(plugin_dir):
            item_path = os.path.join(plugin_dir, item)
            
            # Check if it's a directory with __init__.py
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
                # It's a package
                await self._load_plugin_package(item)
                
            # Check if it's a Python file
            elif item.endswith(".py") and not item.startswith("_"):
                # It's a module
                module_name = item[:-3]  # Remove .py extension
                await self._load_plugin_module(module_name)
                
        logger.info(f"Discovered {len(self.plugins)} plugins")
        
    async def _load_plugin_package(self, package_name: str):
        """
        Load a plugin package.
        
        Args:
            package_name: Name of the package
        """
        logger.info(f"Loading plugin package: {package_name}")
        
        try:
            # Import the package
            package = importlib.import_module(package_name)
            
            # Look for plugin class
            for attr_name in dir(package):
                attr = getattr(package, attr_name)
                
                # Check if it's a class and a plugin
                if inspect.isclass(attr) and hasattr(attr, "is_plugin") and attr.is_plugin:
                    # Register the plugin
                    plugin_id = f"{package_name}.{attr_name}"
                    self.plugins[plugin_id] = attr
                    logger.info(f"Registered plugin: {plugin_id}")
                    
        except Exception as e:
            logger.exception(f"Error loading plugin package {package_name}: {e}")
            
    async def _load_plugin_module(self, module_name: str):
        """
        Load a plugin module.
        
        Args:
            module_name: Name of the module
        """
        logger.info(f"Loading plugin module: {module_name}")
        
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Look for plugin class
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it's a class and a plugin
                if inspect.isclass(attr) and hasattr(attr, "is_plugin") and attr.is_plugin:
                    # Register the plugin
                    plugin_id = f"{module_name}.{attr_name}"
                    self.plugins[plugin_id] = attr
                    logger.info(f"Registered plugin: {plugin_id}")
                    
        except Exception as e:
            logger.exception(f"Error loading plugin module {module_name}: {e}")
            
    async def load_plugin(self, plugin_id: str) -> bool:
        """
        Load and initialize a plugin.
        
        Args:
            plugin_id: ID of the plugin to load
            
        Returns:
            True if plugin was loaded successfully, False otherwise
        """
        logger.info(f"Loading plugin: {plugin_id}")
        
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin not found: {plugin_id}")
            return False
            
        if plugin_id in self.plugin_instances:
            logger.warning(f"Plugin already loaded: {plugin_id}")
            return True
            
        try:
            # Get plugin class
            plugin_class = self.plugins[plugin_id]
            
            # Check dependencies
            if hasattr(plugin_class, "dependencies"):
                for dependency in plugin_class.dependencies:
                    if dependency not in self.plugin_instances:
                        # Try to load dependency
                        if not await self.load_plugin(dependency):
                            logger.warning(f"Failed to load dependency {dependency} for plugin {plugin_id}")
                            return False
                            
            # Create plugin instance
            plugin = plugin_class(self.engine)
            
            # Initialize plugin
            if hasattr(plugin, "initialize") and callable(plugin.initialize):
                await plugin.initialize()
                
            # Store plugin instance
            self.plugin_instances[plugin_id] = plugin
            
            logger.info(f"Plugin loaded: {plugin_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Error loading plugin {plugin_id}: {e}")
            return False
            
    async def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin.
        
        Args:
            plugin_id: ID of the plugin to unload
            
        Returns:
            True if plugin was unloaded successfully, False otherwise
        """
        logger.info(f"Unloading plugin: {plugin_id}")
        
        if plugin_id not in self.plugin_instances:
            logger.warning(f"Plugin not loaded: {plugin_id}")
            return False
            
        try:
            # Get plugin instance
            plugin = self.plugin_instances[plugin_id]
            
            # Check for dependent plugins
            dependent_plugins = []
            for pid, p in self.plugin_instances.items():
                if hasattr(p.__class__, "dependencies") and plugin_id in p.__class__.dependencies:
                    dependent_plugins.append(pid)
                    
            # Unload dependent plugins first
            for dependent in dependent_plugins:
                await self.unload_plugin(dependent)
                
            # Shutdown plugin
            if hasattr(plugin, "shutdown") and callable(plugin.shutdown):
                await plugin.shutdown()
                
            # Remove plugin instance
            del self.plugin_instances[plugin_id]
            
            logger.info(f"Plugin unloaded: {plugin_id}")
            return True
            
        except Exception as e:
            logger.exception(f"Error unloading plugin {plugin_id}: {e}")
            return False
            
    def get_plugin(self, plugin_id: str) -> Any:
        """
        Get a plugin instance.
        
        Args:
            plugin_id: ID of the plugin
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugin_instances.get(plugin_id)
        
    def get_plugins_by_capability(self, capability: str) -> List[Any]:
        """
        Get all plugins that provide a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of plugin instances
        """
        result = []
        
        for plugin_id, plugin in self.plugin_instances.items():
            if hasattr(plugin, "capabilities") and capability in plugin.capabilities:
                result.append(plugin)
                
        return result
        
    def register_plugin_class(self, plugin_class: Type) -> str:
        """
        Register a plugin class.
        
        Args:
            plugin_class: Plugin class to register
            
        Returns:
            Plugin ID
        """
        # Generate plugin ID
        module_name = plugin_class.__module__
        class_name = plugin_class.__name__
        plugin_id = f"{module_name}.{class_name}"
        
        # Register plugin
        self.plugins[plugin_id] = plugin_class
        
        logger.info(f"Registered plugin class: {plugin_id}")
        return plugin_id
        
    async def reload_plugin(self, plugin_id: str) -> bool:
        """
        Reload a plugin.
        
        Args:
            plugin_id: ID of the plugin to reload
            
        Returns:
            True if plugin was reloaded successfully, False otherwise
        """
        logger.info(f"Reloading plugin: {plugin_id}")
        
        # Unload plugin if loaded
        if plugin_id in self.plugin_instances:
            if not await self.unload_plugin(plugin_id):
                logger.warning(f"Failed to unload plugin {plugin_id}")
                return False
                
        # Reload module
        if "." in plugin_id:
            module_name = plugin_id.split(".")[0]
            try:
                # Reload module
                module = importlib.import_module(module_name)
                importlib.reload(module)
                
                # Rediscover plugin
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    # Check if it's a class and a plugin
                    if inspect.isclass(attr) and hasattr(attr, "is_plugin") and attr.is_plugin:
                        # Register the plugin
                        new_plugin_id = f"{module_name}.{attr_name}"
                        self.plugins[new_plugin_id] = attr
                        
                        # If this is the plugin we're reloading
                        if new_plugin_id == plugin_id:
                            # Load the plugin
                            return await self.load_plugin(plugin_id)
                            
            except Exception as e:
                logger.exception(f"Error reloading plugin module for {plugin_id}: {e}")
                return False
                
        return False
