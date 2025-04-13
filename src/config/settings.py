"""
Settings Module

This module provides configuration settings for the Ollama agent framework,
with support for different resource profiles and deployment environments.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Settings:
    """
    Settings for the Ollama agent framework.
    
    Responsible for:
    - Loading configuration from files or environment
    - Providing settings for different components
    - Adapting settings based on resource availability
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Settings.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        # Default settings
        self.settings = {
            # Core settings
            "core": {
                "log_level": "INFO",
                "max_concurrent_tasks": 10,
                "task_timeout": 300,  # seconds
            },
            
            # Model settings
            "models": {
                "default_vlm": "llava-1.5-7b",
                "default_sd": "sd-1.5",
                "quantization": "4-bit",
                "max_batch_size": 4,
                "max_context_length": 2048,
                "max_image_resolution": 512,
            },
            
            # Agent settings
            "agents": {
                "coordinator_enabled": True,
                "vlm_enabled": True,
                "sd_enabled": True,
                "tool_enabled": True,
            },
            
            # API settings
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "enable_cors": True,
                "allowed_origins": ["*"],
                "rate_limit": 100,  # requests per minute
            },
            
            # Ollama settings
            "ollama": {
                "base_url": "http://localhost:11434",
                "timeout": 60,
                "streaming": True,
            },
            
            # MCP settings
            "mcp": {
                "enabled": True,
                "smithery_api_key": os.environ.get("SMITHERY_API_KEY", ""),
                "max_tools": 10,
            },
            
            # Plugin settings
            "plugins": {
                "enabled": True,
                "auto_discover": True,
                "plugin_dir": "plugins",
                "max_plugins": 20,
            },
            
            # Resource settings
            "resources": {
                "memory_limit_mb": 4096,
                "vram_limit_mb": 4096,
                "cpu_limit_percent": 80,
                "gpu_limit_percent": 80,
            }
        }
        
        # Load configuration from file if provided
        if config_path:
            self._load_from_file(config_path)
            
        # Override with environment variables
        self._load_from_env()
        
        logger.info("Settings initialized")
        
    def _load_from_file(self, config_path: str):
        """
        Load settings from a JSON file.
        
        Args:
            config_path: Path to configuration file
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Update settings with file values
            self._update_nested_dict(self.settings, config)
            logger.info(f"Loaded settings from {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading settings from {config_path}: {e}")
            
    def _load_from_env(self):
        """Load settings from environment variables."""
        # Environment variables should be in format OLLAMA_AGENT_SECTION_KEY
        # For example: OLLAMA_AGENT_API_PORT=8080
        prefix = "OLLAMA_AGENT_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and split into parts
                parts = key[len(prefix):].lower().split('_')
                
                if len(parts) >= 2:
                    section = parts[0]
                    setting_key = '_'.join(parts[1:])
                    
                    # Convert value to appropriate type
                    if value.isdigit():
                        value = int(value)
                    elif value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.replace('.', '', 1).isdigit():
                        value = float(value)
                        
                    # Update setting
                    if section in self.settings and setting_key in self.settings[section]:
                        self.settings[section][setting_key] = value
                        logger.debug(f"Updated setting from environment: {section}.{setting_key} = {value}")
                        
    def _update_nested_dict(self, d: Dict, u: Dict):
        """
        Update a nested dictionary with values from another dictionary.
        
        Args:
            d: Dictionary to update
            u: Dictionary with new values
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
                
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            section: Section name
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value
        """
        if section in self.settings and key in self.settings[section]:
            return self.settings[section][key]
        return default
        
    def set(self, section: str, key: str, value: Any):
        """
        Set a setting value.
        
        Args:
            section: Section name
            key: Setting key
            value: New value
        """
        if section not in self.settings:
            self.settings[section] = {}
            
        self.settings[section][key] = value
        logger.debug(f"Updated setting: {section}.{key} = {value}")
        
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get all settings in a section.
        
        Args:
            section: Section name
            
        Returns:
            Dictionary of settings in the section
        """
        return self.settings.get(section, {}).copy()
        
    def apply_low_resource_settings(self):
        """Apply settings optimized for low-resource environments (≤4GB VRAM)."""
        logger.info("Applying low-resource settings")
        
        # Update model settings
        self.settings["models"]["quantization"] = "4-bit"
        self.settings["models"]["max_batch_size"] = 1
        self.settings["models"]["max_context_length"] = 1024
        self.settings["models"]["max_image_resolution"] = 336
        
        # Update resource limits
        self.settings["resources"]["memory_limit_mb"] = 3072
        self.settings["resources"]["vram_limit_mb"] = 3072
        
        # Disable some features
        self.settings["agents"]["tool_enabled"] = False
        
        # Reduce concurrency
        self.settings["core"]["max_concurrent_tasks"] = 1
        
        # Update Ollama settings
        self.settings["ollama"]["streaming"] = True  # Streaming reduces memory usage
        
    def apply_standard_settings(self):
        """Apply settings for standard resource environments (>4GB VRAM)."""
        logger.info("Applying standard resource settings")
        
        # Update model settings
        self.settings["models"]["quantization"] = "8-bit"
        self.settings["models"]["max_batch_size"] = 4
        self.settings["models"]["max_context_length"] = 2048
        self.settings["models"]["max_image_resolution"] = 512
        
        # Update resource limits
        self.settings["resources"]["memory_limit_mb"] = 8192
        self.settings["resources"]["vram_limit_mb"] = 6144
        
        # Enable all features
        self.settings["agents"]["tool_enabled"] = True
        
        # Increase concurrency
        self.settings["core"]["max_concurrent_tasks"] = 4
        
    def apply_high_resource_settings(self):
        """Apply settings for high-resource environments (>8GB VRAM)."""
        logger.info("Applying high-resource settings")
        
        # Update model settings
        self.settings["models"]["quantization"] = "16-bit"
        self.settings["models"]["max_batch_size"] = 8
        self.settings["models"]["max_context_length"] = 4096
        self.settings["models"]["max_image_resolution"] = 1024
        
        # Update resource limits
        self.settings["resources"]["memory_limit_mb"] = 16384
        self.settings["resources"]["vram_limit_mb"] = 12288
        
        # Enable all features
        self.settings["agents"]["tool_enabled"] = True
        
        # Increase concurrency
        self.settings["core"]["max_concurrent_tasks"] = 10
        
    def save_to_file(self, file_path: str):
        """
        Save current settings to a file.
        
        Args:
            file_path: Path to save settings to
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
                
            logger.info(f"Saved settings to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving settings to {file_path}: {e}")
