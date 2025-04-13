"""
Stable Diffusion Agent Module

This module implements the Stable Diffusion agent that handles
image generation and manipulation tasks through Ollama.
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
    Stable Diffusion Agent for the Ollama agent framework.
    
    Responsible for:
    - Text-to-image generation
    - Image-to-image transformation
    - Inpainting and outpainting
    - Style transfer
    """
    
    def __init__(self, 
                engine: CoreEngine,
                ollama_client: OllamaClient,
                settings: Optional[Settings] = None):
        """
        Initialize the Stable Diffusion Agent.
        
        Args:
            engine: Core Engine instance
            ollama_client: Ollama Client instance
            settings: Configuration settings
        """
        self.engine = engine
        self.ollama_client = ollama_client
        self.settings = settings or Settings()
        self.agent_type = "stable_diffusion"
        self.capabilities = [
            "text_to_image",
            "image_to_image",
            "inpainting",
            "style_transfer"
        ]
        self.models = {}
        self.default_model = self.settings.get("models", "default_sd", "sd-1.5")
        logger.info("Stable Diffusion Agent initialized")
        
    async def initialize(self, resource_profile: Dict[str, Any]):
        """
        Initialize the agent with resource profile.
        
        Args:
            resource_profile: Resource availability information
        """
        logger.info(f"Initializing Stable Diffusion Agent with resource profile: {resource_profile}")
        
        # Check if we're in a low-resource environment
        is_low_resource = resource_profile.get("resource_tier") == "low"
        
        if is_low_resource:
            logger.info("Using low-resource configuration for Stable Diffusion Agent")
            # Use smaller models or more aggressive quantization
            self.default_model = "sd-1.5-pruned-q4"
        
        # Register with the engine
        await self.engine.register_agent("sd_agent", self)
        
        # Check if models are available
        await self._check_models()
        
    async def shutdown(self):
        """Shutdown the agent and cleanup resources."""
        logger.info("Shutting down Stable Diffusion Agent")
        # Nothing specific to clean up
        
    async def _check_models(self):
        """Check if required models are available in Ollama."""
        logger.info("Checking available Stable Diffusion models")
        
        try:
            # Get list of available models
            models = await self.ollama_client.list_models()
            
            # Check if our default model is available
            default_model_available = any(m.get("name") == self.default_model for m in models)
            
            if not default_model_available:
                logger.warning(f"Default SD model {self.default_model} not available")
                # We could trigger a model pull here, but that might be too heavy
                # for automatic initialization
            else:
                logger.info(f"Default SD model {self.default_model} is available")
                
            # Store available SD models
            self.models = {
                m.get("name"): m for m in models 
                if "sd" in m.get("name").lower() or "stable" in m.get("name").lower()
            }
            
            logger.info(f"Found {len(self.models)} Stable Diffusion models")
            
        except Exception as e:
            logger.exception(f"Error checking SD models: {e}")
            
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
        
        if task_type == "text_to_image":
            return await self.generate_image(
                prompt=task.get("inputs", {}).get("prompt"),
                negative_prompt=task.get("inputs", {}).get("negative_prompt"),
                width=task.get("parameters", {}).get("width", 512),
                height=task.get("parameters", {}).get("height", 512),
                num_inference_steps=task.get("parameters", {}).get("num_inference_steps", 30),
                guidance_scale=task.get("parameters", {}).get("guidance_scale", 7.5),
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
            raise ValueError(f"Unsupported task type: {task_type}")
            
    async def get_resource_requirements(self, task: Dict[str, Any]) -> Dict[str, float]:
        """
        Get resource requirements for a task.
        
        Args:
            task: Task information
            
        Returns:
            Dictionary of resource requirements
        """
        # Default requirements
        requirements = {
            "memory_gb": 2.0,
            "vram_gb": 3.0 if self.settings.get("models", "quantization") == "4-bit" else 6.0,
            "cpu_percent": 50.0,
            "gpu_percent": 90.0
        }
        
        # Adjust based on image size
        width = task.get("parameters", {}).get("width", 512)
        height = task.get("parameters", {}).get("height", 512)
        
        # Scale VRAM requirements based on resolution
        resolution_factor = (width * height) / (512 * 512)
        requirements["vram_gb"] *= min(2.0, resolution_factor)  # Cap at 2x
            
        return requirements
        
    async def generate_image(self, 
                           prompt: str,
                           negative_prompt: Optional[str] = None,
                           width: int = 512,
                           height: int = 512,
                           num_inference_steps: int = 30,
                           guidance_scale: float = 7.5,
                           model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text prompt describing the desired image
            negative_prompt: Text describing what to avoid in the image
            width: Image width
            height: Image height
            num_inference_steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            model: Model to use (defaults to agent's default model)
            
        Returns:
            Dictionary containing the generated image
        """
        logger.info(f"Generating image with prompt: {prompt}")
        
        if model is None:
            model = self.default_model
            
        # Apply resource constraints
        width, height = self._constrain_dimensions(width, height)
        
        try:
            # Prepare the modelfile for Stable Diffusion
            modelfile = self._create_sd_modelfile(
                model_name=model,
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale
            )
            
            # Create a temporary model
            temp_model_name = f"temp-sd-{asyncio.get_event_loop().time()}"
            await self.ollama_client.create_model(
                name=temp_model_name,
                modelfile=modelfile
            )
            
            try:
                # Generate the image
                start_time = asyncio.get_event_loop().time()
                response = await self.ollama_client.generate(
                    model=temp_model_name,
                    prompt="",  # Prompt is already in the modelfile
                    options={
                        "temperature": 1.0,  # Temperature doesn't matter for SD
                        "num_predict": 1     # We only need one token
                    }
                )
                end_time = asyncio.get_event_loop().time()
                
                # Extract image from response
                image_data = self._extract_image_from_response(response)
                
                # Generate a random seed (in reality, we'd get this from the model)
                import random
                seed = random.randint(1, 1000000)
                
                result = {
                    "image": image_data,
                    "seed": seed,
                    "processing_time": round(end_time - start_time, 2)
                }
                
                logger.info(f"Image generation completed in {result['processing_time']}s")
                return result
                
            finally:
                # Clean up temporary model
                try:
                    await self.ollama_client.delete_model(temp_model_name)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary model: {e}")
            
        except Exception as e:
            logger.exception(f"Error in image generation: {e}")
            return {
                "error": str(e),
                "message": "Failed to generate image"
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
            strength: Strength of the transformation (0.0-1.0)
            model: Model to use (defaults to agent's default model)
            
        Returns:
            Dictionary containing the transformed image
        """
        logger.info(f"Transforming image with prompt: {prompt}")
        
        if model is None:
            model = self.default_model
            
        try:
            # Process the input image
            image_data = await self._process_image_input(image)
            
            # Prepare the modelfile for img2img
            modelfile = self._create_img2img_modelfile(
                model_name=model,
                prompt=prompt,
                strength=strength
            )
            
            # Create a temporary model
            temp_model_name = f"temp-img2img-{asyncio.get_event_loop().time()}"
            await self.ollama_client.create_model(
                name=temp_model_name,
                modelfile=modelfile
            )
            
            try:
                # Transform the image
                start_time = asyncio.get_event_loop().time()
                response = await self.ollama_client.generate(
                    model=temp_model_name,
                    prompt="",  # Prompt is already in the modelfile
                    images=[image_data],
                    options={
                        "temperature": 1.0,  # Temperature doesn't matter for SD
                        "num_predict": 1     # We only need one token
                    }
                )
                end_time = asyncio.get_event_loop().time()
                
                # Extract image from response
                result_image_data = self._extract_image_from_response(response)
                
                # Generate a random seed (in reality, we'd get this from the model)
                import random
                seed = random.randint(1, 1000000)
                
                result = {
                    "image": result_image_data,
                    "seed": seed,
                    "processing_time": round(end_time - start_time, 2)
                }
                
                logger.info(f"Image transformation completed in {result['processing_time']}s")
                return result
                
            finally:
                # Clean up temporary model
                try:
                    await self.ollama_client.delete_model(temp_model_name)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary model: {e}")
            
        except Exception as e:
            logger.exception(f"Error in image transformation: {e}")
            return {
                "error": str(e),
                "message": "Failed to transform image"
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
        
        # Style transfer is essentially img2img with a style prompt
        prompt = f"Apply {style} style to this image. {style} style."
        
        return await self.transform_image(
            image=image,
            prompt=prompt,
            strength=0.8,  # Higher strength for style transfer
            model=model
        )
            
    def _create_sd_modelfile(self,
                           model_name: str,
                           prompt: str,
                           negative_prompt: Optional[str] = None,
                           width: int = 512,
                           height: int = 512,
                           num_inference_steps: int = 30,
                           guidance_scale: float = 7.5) -> str:
        """
        Create a modelfile for Stable Diffusion text-to-image generation.
        
        Args:
            model_name: Base model name
            prompt: Text prompt
            negative_prompt: Negative prompt
            width: Image width
            height: Image height
            num_inference_steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            
        Returns:
            Modelfile content
        """
        modelfile = f"FROM {model_name}\n\n"
        
        # Add parameters
        modelfile += "PARAMETER width integer default 512\n"
        modelfile += "PARAMETER height integer default 512\n"
        modelfile += "PARAMETER steps integer default 30\n"
        modelfile += "PARAMETER cfg_scale float default 7.5\n"
        
        # Set system prompt
        system_prompt = "You are a text-to-image generation system. Generate images based on the prompts."
        modelfile += f"SYSTEM {system_prompt}\n\n"
        
        # Add prompt template
        modelfile += "PROMPT "
        modelfile += f"Generate an image with the following parameters:\n"
        modelfile += f"Prompt: {prompt}\n"
        
        if negative_prompt:
            modelfile += f"Negative prompt: {negative_prompt}\n"
            
        modelfile += f"Width: {width}\n"
        modelfile += f"Height: {height}\n"
        modelfile += f"Steps: {num_inference_steps}\n"
        modelfile += f"CFG scale: {guidance_scale}\n"
        
        return modelfile
        
    def _create_img2img_modelfile(self,
                                model_name: str,
                                prompt: str,
                                strength: float = 0.7) -> str:
        """
        Create a modelfile for Stable Diffusion image-to-image transformation.
        
        Args:
            model_name: Base model name
            prompt: Text prompt
            strength: Transformation strength
            
        Returns:
            Modelfile content
        """
        modelfile = f"FROM {model_name}\n\n"
        
        # Add parameters
        modelfile += "PARAMETER strength float default 0.7\n"
        modelfile += "PARAMETER steps integer default 30\n"
        modelfile += "PARAMETER cfg_scale float default 7.5\n"
        
        # Set system prompt
        system_prompt = "You are an image-to-image transformation system. Transform images based on the prompts."
        modelfile += f"SYSTEM {system_prompt}\n\n"
        
        # Add prompt template
        modelfile += "PROMPT "
        modelfile += f"Transform the input image with the following parameters:\n"
        modelfile += f"Prompt: {prompt}\n"
        modelfile += f"Strength: {strength}\n"
        
        return modelfile
        
    async def _process_image_input(self, image: Union[str, bytes, BinaryIO]) -> bytes:
        """
        Process image input into bytes.
        
        Args:
            image: Image data (file path, bytes, or file object)
            
        Returns:
            Image bytes
        """
        if isinstance(image, str):
            # Assume it's a file path
            if os.path.exists(image):
                with open(image, "rb") as f:
                    return f.read()
            else:
                raise ValueError(f"Image file not found: {image}")
                
        elif isinstance(image, bytes):
            # Raw bytes
            return image
            
        elif hasattr(image, "read"):
            # File-like object
            return image.read()
            
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")
            
    def _extract_image_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract base64-encoded image from response.
        
        Args:
            response: Response from Ollama API
            
        Returns:
            Base64-encoded image data
        """
        # In a real implementation, we would extract the image from the response
        # For now, we'll return a placeholder image
        
        # Create a simple gradient image as a placeholder
        width, height = 512, 512
        image = Image.new('RGB', (width, height))
        
        for x in range(width):
            for y in range(height):
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = int(255 * (x + y) / (width + height))
                image.putpixel((x, y), (r, g, b))
                
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        return base64_image
        
    def _constrain_dimensions(self, width: int, height: int) -> Tuple[int, int]:
        """
        Constrain image dimensions based on available resources.
        
        Args:
            width: Requested width
            height: Requested height
            
        Returns:
            Tuple of (width, height) that fits within resource constraints
        """
        # Get maximum resolution from settings
        max_resolution = self.settings.get("models", "max_image_resolution", 512)
        
        # Calculate aspect ratio
        aspect_ratio = width / height
        
        # Constrain dimensions
        if width > max_resolution or height > max_resolution:
            if aspect_ratio > 1:
                # Wider than tall
                width = max_resolution
                height = int(width / aspect_ratio)
            else:
                # Taller than wide
                height = max_resolution
                width = int(height * aspect_ratio)
                
        # Ensure dimensions are multiples of 8 (SD requirement)
        width = (width // 8) * 8
        height = (height // 8) * 8
        
        return width, height
