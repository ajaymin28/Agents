"""
VLM Agent Module

This module implements the Vision Language Model agent that handles
image understanding and visual question answering tasks.
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, Union, BinaryIO

from ..core.engine import CoreEngine
from ..models.ollama_client import OllamaClient
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class VLMAgent:
    """
    Vision Language Model Agent for the Ollama agent framework.
    
    Responsible for:
    - Image understanding
    - Visual question answering
    - Image captioning
    - Visual reasoning
    """
    
    def __init__(self, 
                engine: CoreEngine,
                ollama_client: OllamaClient,
                settings: Optional[Settings] = None):
        """
        Initialize the VLM Agent.
        
        Args:
            engine: Core Engine instance
            ollama_client: Ollama Client instance
            settings: Configuration settings
        """
        self.engine = engine
        self.ollama_client = ollama_client
        self.settings = settings or Settings()
        self.agent_type = "vlm"
        self.capabilities = [
            "image_understanding",
            "visual_qa",
            "image_captioning",
            "visual_reasoning"
        ]
        self.models = {}
        self.default_model = self.settings.get("models", "default_vlm", "llava-1.5-7b")
        logger.info("VLM Agent initialized")
        
    async def initialize(self, resource_profile: Dict[str, Any]):
        """
        Initialize the agent with resource profile.
        
        Args:
            resource_profile: Resource availability information
        """
        logger.info(f"Initializing VLM Agent with resource profile: {resource_profile}")
        
        # Check if we're in a low-resource environment
        is_low_resource = resource_profile.get("resource_tier") == "low"
        
        if is_low_resource:
            logger.info("Using low-resource configuration for VLM Agent")
            # Use smaller models or more aggressive quantization
            self.default_model = "llava-1.5-7b-q4"
        
        # Register with the engine
        await self.engine.register_agent("vlm_agent", self)
        
        # Check if models are available
        await self._check_models()
        
    async def shutdown(self):
        """Shutdown the agent and cleanup resources."""
        logger.info("Shutting down VLM Agent")
        # Nothing specific to clean up
        
    async def _check_models(self):
        """Check if required models are available in Ollama."""
        logger.info("Checking available VLM models")
        
        try:
            # Get list of available models
            models = await self.ollama_client.list_models()
            
            # Check if our default model is available
            default_model_available = any(m.get("name") == self.default_model for m in models)
            
            if not default_model_available:
                logger.warning(f"Default VLM model {self.default_model} not available")
                # We could trigger a model pull here, but that might be too heavy
                # for automatic initialization
            else:
                logger.info(f"Default VLM model {self.default_model} is available")
                
            # Store available VLM models
            self.models = {
                m.get("name"): m for m in models 
                if "llava" in m.get("name").lower() or "cogvlm" in m.get("name").lower()
            }
            
            logger.info(f"Found {len(self.models)} VLM models")
            
        except Exception as e:
            logger.exception(f"Error checking VLM models: {e}")
            
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
        
        if task_type == "image_understanding":
            return await self.understand_image(
                image=task.get("inputs", {}).get("image"),
                prompt=task.get("inputs", {}).get("prompt", "Describe this image in detail."),
                model=task.get("parameters", {}).get("model", self.default_model)
            )
        elif task_type == "visual_qa":
            return await self.visual_qa(
                image=task.get("inputs", {}).get("image"),
                question=task.get("inputs", {}).get("question"),
                model=task.get("parameters", {}).get("model", self.default_model)
            )
        elif task_type == "image_captioning":
            return await self.caption_image(
                image=task.get("inputs", {}).get("image"),
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
            "vram_gb": 3.5 if self.settings.get("models", "quantization") == "4-bit" else 7.0,
            "cpu_percent": 50.0,
            "gpu_percent": 80.0
        }
        
        # Adjust based on model
        model = task.get("parameters", {}).get("model", self.default_model)
        if "13b" in model:
            requirements["vram_gb"] *= 1.5
        elif "70b" in model:
            requirements["vram_gb"] *= 3.0
            
        return requirements
        
    async def understand_image(self, 
                              image: Union[str, bytes, BinaryIO],
                              prompt: str = "Describe this image in detail.",
                              model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a detailed understanding of an image.
        
        Args:
            image: Image data (file path, bytes, or file object)
            prompt: Text prompt to guide the understanding
            model: Model to use (defaults to agent's default model)
            
        Returns:
            Dictionary containing the understanding result
        """
        logger.info(f"Understanding image with prompt: {prompt}")
        
        if model is None:
            model = self.default_model
            
        try:
            # Process the image
            images = [image] if image else []
            
            # Generate understanding
            start_time = asyncio.get_event_loop().time()
            response = await self.ollama_client.generate(
                model=model,
                prompt=prompt,
                images=images,
                options={
                    "temperature": 0.1,  # Low temperature for more factual responses
                    "num_predict": 1024  # Limit response length
                }
            )
            end_time = asyncio.get_event_loop().time()
            
            # Extract and process the response
            description = response.get("response", "")
            
            # Extract tags from the description
            tags = self._extract_tags(description)
            
            result = {
                "description": description,
                "tags": tags,
                "processing_time": round(end_time - start_time, 2)
            }
            
            logger.info(f"Image understanding completed in {result['processing_time']}s")
            return result
            
        except Exception as e:
            logger.exception(f"Error in image understanding: {e}")
            return {
                "error": str(e),
                "description": "Failed to understand image"
            }
            
    async def visual_qa(self,
                       image: Union[str, bytes, BinaryIO],
                       question: str,
                       model: Optional[str] = None) -> Dict[str, Any]:
        """
        Answer a question about an image.
        
        Args:
            image: Image data (file path, bytes, or file object)
            question: Question to answer about the image
            model: Model to use (defaults to agent's default model)
            
        Returns:
            Dictionary containing the answer
        """
        logger.info(f"Visual QA with question: {question}")
        
        if model is None:
            model = self.default_model
            
        try:
            # Process the image
            images = [image] if image else []
            
            # Generate answer
            start_time = asyncio.get_event_loop().time()
            response = await self.ollama_client.generate(
                model=model,
                prompt=f"Answer this question about the image: {question}",
                images=images,
                options={
                    "temperature": 0.1,  # Low temperature for more factual responses
                    "num_predict": 512   # Limit response length
                }
            )
            end_time = asyncio.get_event_loop().time()
            
            # Extract and process the response
            answer = response.get("response", "")
            
            # Estimate confidence based on response
            confidence = self._estimate_confidence(answer)
            
            result = {
                "answer": answer,
                "confidence": confidence,
                "processing_time": round(end_time - start_time, 2)
            }
            
            logger.info(f"Visual QA completed in {result['processing_time']}s")
            return result
            
        except Exception as e:
            logger.exception(f"Error in visual QA: {e}")
            return {
                "error": str(e),
                "answer": "Failed to answer question about image"
            }
            
    async def caption_image(self,
                          image: Union[str, bytes, BinaryIO],
                          model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a caption for an image.
        
        Args:
            image: Image data (file path, bytes, or file object)
            model: Model to use (defaults to agent's default model)
            
        Returns:
            Dictionary containing the caption
        """
        logger.info("Generating image caption")
        
        if model is None:
            model = self.default_model
            
        try:
            # Process the image
            images = [image] if image else []
            
            # Generate caption
            start_time = asyncio.get_event_loop().time()
            response = await self.ollama_client.generate(
                model=model,
                prompt="Generate a concise caption for this image.",
                images=images,
                options={
                    "temperature": 0.2,
                    "num_predict": 100  # Short caption
                }
            )
            end_time = asyncio.get_event_loop().time()
            
            # Extract and process the response
            caption = response.get("response", "").strip()
            
            result = {
                "caption": caption,
                "processing_time": round(end_time - start_time, 2)
            }
            
            logger.info(f"Image captioning completed in {result['processing_time']}s")
            return result
            
        except Exception as e:
            logger.exception(f"Error in image captioning: {e}")
            return {
                "error": str(e),
                "caption": "Failed to generate caption"
            }
            
    def _extract_tags(self, text: str) -> List[str]:
        """
        Extract relevant tags from a description.
        
        Args:
            text: Text to extract tags from
            
        Returns:
            List of extracted tags
        """
        # This is a simple implementation that could be improved
        # with NLP techniques like entity extraction
        common_nouns = [
            "person", "people", "man", "woman", "child", "building", "car",
            "animal", "dog", "cat", "bird", "tree", "mountain", "ocean",
            "river", "city", "street", "food", "computer", "phone"
        ]
        
        # Convert to lowercase and split into words
        words = text.lower().split()
        
        # Remove punctuation
        words = [word.strip(".,;:!?()[]{}\"'") for word in words]
        
        # Find common nouns in the text
        tags = [word for word in words if word in common_nouns]
        
        # Remove duplicates while preserving order
        seen = set()
        tags = [tag for tag in tags if not (tag in seen or seen.add(tag))]
        
        return tags[:10]  # Limit to 10 tags
        
    def _estimate_confidence(self, text: str) -> float:
        """
        Estimate confidence level based on answer text.
        
        Args:
            text: Answer text
            
        Returns:
            Confidence score between 0 and 1
        """
        # This is a heuristic approach that could be improved
        
        # Check for uncertainty markers
        uncertainty_phrases = [
            "i'm not sure", "uncertain", "can't tell", "difficult to say",
            "might be", "possibly", "perhaps", "maybe", "could be",
            "i don't know", "unclear", "hard to determine"
        ]
        
        text_lower = text.lower()
        
        # Start with high confidence
        confidence = 0.9
        
        # Reduce confidence for each uncertainty marker
        for phrase in uncertainty_phrases:
            if phrase in text_lower:
                confidence -= 0.1
                
        # Check for definitive statements
        certainty_phrases = [
            "definitely", "certainly", "clearly", "obviously",
            "without doubt", "absolutely", "undoubtedly"
        ]
        
        # Increase confidence for definitive statements
        for phrase in certainty_phrases:
            if phrase in text_lower:
                confidence += 0.05
                
        # Ensure confidence is between 0.1 and 1.0
        return max(0.1, min(1.0, confidence))
