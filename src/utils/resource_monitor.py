"""
Resource Monitor Module

This module monitors system resources and provides information about available
resources to the Core Engine for resource-aware decision making.
"""

import asyncio
import logging
import os
import platform
import psutil
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    Resource Monitor for the Ollama agent framework.
    
    Responsible for:
    - Monitoring system resources (CPU, memory, GPU, VRAM)
    - Providing resource profiles for decision making
    - Alerting when resources are constrained
    """
    
    def __init__(self, monitoring_interval: float = 5.0):
        """
        Initialize the Resource Monitor.
        
        Args:
            monitoring_interval: Interval in seconds between resource checks
        """
        self.monitoring_interval = monitoring_interval
        self.monitoring_task = None
        self.resources = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_available_gb": 0.0,
            "gpu_percent": 0.0,
            "vram_percent": 0.0,
            "vram_available_gb": 0.0,
            "disk_percent": 0.0,
            "disk_available_gb": 0.0
        }
        self.has_gpu = False
        self._detect_gpu()
        logger.info("Resource Monitor initialized")
        
    async def start(self):
        """Start resource monitoring."""
        logger.info("Starting Resource Monitor")
        # Initial resource check
        await self._check_resources()
        # Start periodic monitoring
        self.monitoring_task = asyncio.create_task(self._monitor_resources())
        logger.info("Resource Monitor started")
        
    async def stop(self):
        """Stop resource monitoring."""
        logger.info("Stopping Resource Monitor")
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        logger.info("Resource Monitor stopped")
        
    async def get_resource_profile(self) -> Dict[str, Any]:
        """
        Get the current resource profile.
        
        Returns:
            Dictionary containing resource information
        """
        # Ensure we have up-to-date information
        await self._check_resources()
        
        # Create profile based on available resources
        profile = {
            "cpu_cores": psutil.cpu_count(logical=True),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "has_gpu": self.has_gpu
        }
        
        # Add GPU information if available
        if self.has_gpu:
            profile["vram_gb"] = round(self.resources["vram_available_gb"], 2)
            
        # Determine resource tier
        if self.has_gpu and self.resources["vram_available_gb"] <= 4.0:
            profile["resource_tier"] = "low"
        elif self.has_gpu and self.resources["vram_available_gb"] <= 8.0:
            profile["resource_tier"] = "medium"
        elif self.has_gpu and self.resources["vram_available_gb"] > 8.0:
            profile["resource_tier"] = "high"
        else:
            # CPU-only system
            if profile["memory_gb"] <= 4.0:
                profile["resource_tier"] = "low"
            elif profile["memory_gb"] <= 16.0:
                profile["resource_tier"] = "medium"
            else:
                profile["resource_tier"] = "high"
                
        return profile
        
    async def get_available_resources(self) -> Dict[str, float]:
        """
        Get currently available resources.
        
        Returns:
            Dictionary containing available resource amounts
        """
        # Ensure we have up-to-date information
        await self._check_resources()
        
        available = {
            "cpu_percent": 100.0 - self.resources["cpu_percent"],
            "memory_gb": self.resources["memory_available_gb"],
            "disk_gb": self.resources["disk_available_gb"]
        }
        
        if self.has_gpu:
            available["gpu_percent"] = 100.0 - self.resources["gpu_percent"]
            available["vram_gb"] = self.resources["vram_available_gb"]
            
        return available
        
    def _detect_gpu(self):
        """Detect if a GPU is available and what type."""
        try:
            # Try to import GPU libraries
            import torch
            if torch.cuda.is_available():
                self.has_gpu = True
                logger.info(f"CUDA GPU detected: {torch.cuda.get_device_name(0)}")
                return
                
            # Try ROCm/HIP for AMD GPUs
            if hasattr(torch, 'hip') and torch.hip.is_available():
                self.has_gpu = True
                logger.info("ROCm/HIP GPU detected")
                return
                
        except ImportError:
            pass
            
        try:
            # Try TensorFlow
            import tensorflow as tf
            gpus = tf.config.list_physical_devices('GPU')
            if gpus:
                self.has_gpu = True
                logger.info(f"TensorFlow GPU detected: {len(gpus)} device(s)")
                return
                
        except ImportError:
            pass
            
        # No GPU detected
        logger.info("No GPU detected, running in CPU-only mode")
        self.has_gpu = False
        
    async def _check_resources(self):
        """Check current resource usage."""
        # CPU and memory
        self.resources["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        self.resources["memory_percent"] = mem.percent
        self.resources["memory_available_gb"] = mem.available / (1024**3)
        
        # Disk
        disk = psutil.disk_usage('/')
        self.resources["disk_percent"] = disk.percent
        self.resources["disk_available_gb"] = disk.free / (1024**3)
        
        # GPU if available
        if self.has_gpu:
            await self._check_gpu_resources()
            
    async def _check_gpu_resources(self):
        """Check GPU resource usage."""
        try:
            # Try PyTorch first
            import torch
            if torch.cuda.is_available():
                # Get VRAM usage
                torch.cuda.synchronize()
                vram_allocated = torch.cuda.memory_allocated(0) / (1024**3)
                vram_reserved = torch.cuda.memory_reserved(0) / (1024**3)
                vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                
                self.resources["vram_percent"] = (vram_allocated / vram_total) * 100
                self.resources["vram_available_gb"] = vram_total - vram_allocated
                
                # Estimate GPU utilization
                # This is not perfect but gives a rough idea
                self.resources["gpu_percent"] = (vram_reserved / vram_total) * 100
                return
                
        except (ImportError, AttributeError, RuntimeError):
            pass
            
        try:
            # Try nvidia-smi as fallback
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output
            output = result.stdout.strip().split(',')
            if len(output) >= 3:
                gpu_util = float(output[0].strip())
                vram_used = float(output[1].strip())
                vram_total = float(output[2].strip())
                
                self.resources["gpu_percent"] = gpu_util
                self.resources["vram_percent"] = (vram_used / vram_total) * 100
                self.resources["vram_available_gb"] = (vram_total - vram_used) / 1024  # Convert MB to GB
                return
                
        except (ImportError, subprocess.SubprocessError, ValueError, IndexError):
            pass
            
        # If we get here, we couldn't get GPU info
        # Set reasonable defaults
        self.resources["gpu_percent"] = 0.0
        self.resources["vram_percent"] = 0.0
        self.resources["vram_available_gb"] = 0.0
        
    async def _monitor_resources(self):
        """Periodically monitor resources."""
        while True:
            try:
                await self._check_resources()
                
                # Log resource usage
                logger.debug(f"Resource usage: CPU: {self.resources['cpu_percent']:.1f}%, "
                           f"Memory: {self.resources['memory_percent']:.1f}%, "
                           f"Disk: {self.resources['disk_percent']:.1f}%")
                
                if self.has_gpu:
                    logger.debug(f"GPU usage: {self.resources['gpu_percent']:.1f}%, "
                               f"VRAM: {self.resources['vram_percent']:.1f}%")
                    
                # Check for resource constraints
                await self._check_resource_constraints()
                
                # Wait for next check
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in resource monitoring: {e}")
                await asyncio.sleep(self.monitoring_interval)
                
    async def _check_resource_constraints(self):
        """Check for resource constraints and log warnings."""
        # CPU constraints
        if self.resources["cpu_percent"] > 90:
            logger.warning("CPU usage is very high (>90%)")
            
        # Memory constraints
        if self.resources["memory_percent"] > 90:
            logger.warning("Memory usage is very high (>90%)")
            
        # Disk constraints
        if self.resources["disk_percent"] > 90:
            logger.warning("Disk usage is very high (>90%)")
            
        # GPU constraints
        if self.has_gpu:
            if self.resources["gpu_percent"] > 90:
                logger.warning("GPU usage is very high (>90%)")
                
            if self.resources["vram_percent"] > 90:
                logger.warning("VRAM usage is very high (>90%)")
