"""
Stable Diffusion Agent Module

This module implements an agent for image generation and manipulation tasks
through Ollama, using vision-language models as a proxy for diffusion-based tasks.
"""

import asyncio
import base64
import io
import logging
import os
from typing import Dict, List, Any, Optional, Union, BinaryIO, Tuple
from PIL import Image

from ..core.engine import CoreEngine
from ..models.ollama_client import OllamaClient
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class StableDiffusionAgent:
    """
    Image Generation Agent for the Ollama agent framework.
    
    Responsible for:
    - Text-to-image generation (using vision-language models)
    - Image-to-image transformation
    - Style transfer
    
    Note: Ollama does not natively support Stable Diffusion. This implementation
    uses vision-language models to simulate similar functionality.
    """
    
    def __init__(self, 
                 engine: CoreEngine,
                 ollama_client: OllamaClient,
                 settings: Optional[Settings] = None):
        """
        Initialize the Image Generation Agent.
        
        Args:
            engine: Core Engine instance
            ollama_client: Ollama Client instance
            settings: Configuration settings
        """
        self.engine = engine
        self.ollama_client = ollama_client
        self.settings = settings or Settings()
        self.agent_type = "image_generation"
        self.capabilities = [
            "text_to_image",
            "image_to_image",
            "style_transfer"
        ]
        self.models = {}
        self.default_model = self.settings.get("models", "default_image_gen", "bakllava:7b")
        logger.info("Image Generation Agent initialized")
        
    async def initialize(self, resource_profile: Dict[str, Any]):
        """
        Initialize the agent with resource profile.
        
        Args:
            resource_profile: Resource availability information
        """
        logger.info(f"Initializing Image Generation Agent with resource profile: {resource_profile}")
        
        is_low_resource = resource_profile.get("resource_tier") == "low"
        
        if is_low_resource:
            logger.info("Using low-resource configuration for Image Generation Agent")
            self.default_model = "bakllava:7b"
        
        await self.engine.register_agent("image_gen_agent", self)
        await self._check_models()
        
    async def shutdown(self):
        """Shutdown the agent and cleanup resources."""
        logger.info("Shutting down Image Generation Agent")
        await self.ollama_client.stop()
        
    async def _check_models(self):
        """Check if required models are available in Ollama."""
        logger.info("Checking available image generation models")
        
        try:
            models = await self.ollama_client.list_models()
            default_model_available = any(m.get("name", "").startswith(self.default_model) for m in models)
            
            if not default_model_available:
                logger.warning(f"Default model {self.default_model} not available")
            else:
                logger.info(f"Default model {self.default_model} is available")
                
            self.models = {
                m.get("name"): m for m in models 
                if any(vlm in m.get("name", "").lower() for vlm in ["bakllava", "llava"])
            }
            
            logger.info(f"Found {len(self.models)} image-capable models: {list(self.models.keys())}")
            
        except Exception as e:
            logger.exception(f"Error checking models: {e}")
            
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
        
        try:
            if task_type == "text_to_image":
                return await self.generate_image(
                    prompt=task.get("inputs", {}).get("prompt"),
                    negative_prompt=task.get("inputs", {}).get("negative_prompt"),
                    width=task.get("parameters", {}).get("width", 512),
                    height=task.get("parameters", {}).get("height", 512),
                    model=task.get("parameters", {}).get("model", self.default_model)
                )
            elif task_type == "image_to_image":
                return await self.transform_image(
                    image=task.get("inputs", {}).get("image"),
                    prompt=task.get("inputs", {}).get("prompt"),
                    strength=task.get("parameters", {}).get("strength", 0.7),
                    model=task.get("parameters", {}).get("model", self.default_model)
                )
            elif task_type == "style_transfer":
                return await self.style_transfer(
                    image=task.get("inputs", {}).get("image"),
                    style=task.get("inputs", {}).get("style"),
                    model=task.get("parameters", {}).get("model", self.default_model)
                )
            else:
                logger.error(f"Unsupported task type: {task_type}")
                raise ValueError(f"Unsupported task type: {task_type}")
                
        except Exception as e:
            logger.exception(f"Error processing task {task_type}: {e}")
            return {"error": str(e), "task_id": task.get("id")}
            
    async def get_resource_requirements(self, task: Dict[str, Any]) -> Dict[str, float]:
        """
        Get resource requirements for a task.
        
        Args:
            task: Task information
            
        Returns:
            Dictionary of resource requirements
        """
        requirements = {
            "memory_gb": 4.0,
            "vram_gb": 6.0,
            "cpu_percent": 60.0,
            "gpu_percent": 90.0
        }
        
        width = task.get("parameters", {}).get("width", 512)
        height = task.get("parameters", {}).get("height", 512)
        resolution_factor = (width * height) / (512 * 512)
        requirements["vram_gb"] *= min(2.0, resolution_factor)
        
        model = task.get("parameters", {}).get("model", self.default_model)
        if "34b" in model:
            requirements["vram_gb"] = 12.0
            
        return requirements
        
    async def generate_image(self, 
                            prompt: str,
                            negative_prompt: Optional[str] = None,
                            width: int = 512,
                            height: int = 512,
                            model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate an image from a text prompt using a vision-language model.
        
        Args:
            prompt: Text prompt describing the desired image
            negative_prompt: Text describing what to avoid (used in prompt engineering)
            width: Image width (informational, not used directly)
            height: Image height (informational, not used directly)
            model: Model to use (defaults to agent's default model)
            
        Returns:
            Dictionary containing the generated image (simulated)
        """
        logger.info(f"Generating image with prompt: {prompt[:50]}...")
        
        if model is None:
            model = self.default_model
            
        width, height = self._constrain_dimensions(width, height)
        
        try:
            full_prompt = f"Generate an image: {prompt}"
            if negative_prompt:
                full_prompt += f". Avoid: {negative_prompt}"
                
            start_time = asyncio.get_event_loop().time()
            response = await self.ollama_client.generate(
                model=model,
                prompt=full_prompt,
                options={
                    "temperature": 0.7,
                    "max_tokens": 512
                }
            )
            end_time = asyncio.get_event_loop().time()
            
            # Simulate image generation (since Ollama doesn't generate images)
            image_data = self._simulate_image_output(response.get("response", ""))
            
            import random
            seed = random.randint(1, 1000000)
            
            result = {
                "image": image_data,
                "seed": seed,
                "processing_time": round(end_time - start_time, 2),
                "model": model
            }
            
            logger.info(f"Image generation completed in {result['processing_time']}s")
            return result
            
        except Exception as e:
            logger.exception(f"Error in image generation: {e}")
            return {
                "error": str(e),
                "message": "Failed to generate image",
                "model": model
            }
            
    async def transform_image(self,
                             image: Union[str, bytes, BinaryIO],
                             prompt: str,
                             strength: float = 0.7,
                             model: Optional[str] = None) -> Dict[str, Any]:
        """
        Transform an existing image based on a prompt.
        
        Args:
            image: Input image data (file path, bytes, or file object)
            prompt: Text prompt describing the desired transformation
            strength: Strength of the transformation (used in prompt engineering)
            model: Model to use (defaults to agent's default model)
            
        Returns:
            Dictionary containing the transformed image (simulated)
        """
        logger.info(f"Transforming image with prompt: {prompt[:50]}...")
        
        if model is None:
            model = self.default_model
            
        try:
            images = [image] if image else []
            full_prompt = f"Transform this image with the following instructions: {prompt}. Transformation strength: {strength}."
            
            start_time = asyncio.get_event_loop().time()
            response = await self.ollama_client.generate(
                model=model,
                prompt=full_prompt,
                images=images,
                options={
                    "temperature": 0.7,
                    "max_tokens": 512
                }
            )
            end_time = asyncio.get_event_loop().time()
            
            image_data = self._simulate_image_output(response.get("response", ""))
            
            import random
            seed = random.randint(1, 1000000)
            
            result = {
                "image": image_data,
                "seed": seed,
                "processing_time": round(end_time - start_time, 2),
                "model": model
            }
            
            logger.info(f"Image transformation completed in {result['processing_time']}s")
            return result
            
        except Exception as e:
            logger.exception(f"Error in image transformation: {e}")
            return {
                "error": str(e),
                "message": "Failed to transform image",
                "model": model
            }
            
    async def style_transfer(self,
                            image: Union[str, bytes, BinaryIO],
                            style: str,
                            model: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply a style to an image.
        
        Args:
            image: Input image data (file path, bytes, or file object)
            style: Style to apply (e.g., "anime", "oil painting", "sketch")
            model: Model to use (defaults to agent's default model)
            
        Returns:
            Dictionary containing the styled image
        """
        logger.info(f"Applying style '{style}' to image")
        
        prompt = f"Apply {style} style to this image. Create a {style}-style version."
        return await self.transform_image(
            image=image,
            prompt=prompt,
            strength=0.8,
            model=model
        )
            
    def _simulate_image_output(self, text: str) -> str:
        """
        Simulate image output by creating a placeholder image.
        
        Args:
            text: Text response from model (used for logging, not image creation)
            
        Returns:
            Base64-encoded placeholder image
        """
        logger.warning("Ollama does not support image generation; returning placeholder image")
        
        width, height = 512, 512
        image = Image.new('RGB', (width, height))
        
        for x in range(width):
            for y in range(height):
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = int(255 * (x + y) / (width + height))
                image.putpixel((x, y), (r, g, b))
                
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        return base64.b64encode(image_bytes).decode("utf-8")
        
    async def _process_image_input(self, image: Union[str, bytes, BinaryIO]) -> bytes:
        """
        Process image input into bytes.
        
        Args:
            image: Image data (file path, bytes, or file object)
            
        Returns:
            Image bytes
        """
        if isinstance(image, str):
            if os.path.exists(image):
                with open(image, "rb") as f:
                    return f.read()
            else:
                raise ValueError(f"Image file not found: {image}")
                
        elif isinstance(image, bytes):
            return image
            
        elif hasattr(image, "read"):
            return image.read()
            
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")
            
    def _constrain_dimensions(self, width: int, height: int) -> Tuple[int, int]:
        """
        Constrain image dimensions based on available resources.
        
        Args:
            width: Requested width
            height: Requested height
            
        Returns:
            Tuple of (width, height)
        """
        max_resolution = self.settings.get("models", "max_image_resolution", 512)
        aspect_ratio = width / height
        
        if width > max_resolution or height > max_resolution:
            if aspect_ratio > 1:
                width = max_resolution
                height = int(width / aspect_ratio)
            else:
                height = max_resolution
                width = int(height * aspect_ratio)
                
        width = max(64, (width // 8) * 8)
        height = max(64, (height // 8) * 8)
        
        return width, height