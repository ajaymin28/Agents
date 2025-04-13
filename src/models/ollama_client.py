"""
Ollama Client Module

This module provides a client for interacting with the Ollama API,
supporting both text generation and vision-language model capabilities.
"""

import aiohttp
import asyncio
import base64
import json
import logging
import os
from typing import Dict, List, Any, Optional, Union, BinaryIO

logger = logging.getLogger(__name__)

class OllamaClient:
    """
    Client for interacting with Ollama API.
    
    Responsible for:
    - Sending requests to Ollama API
    - Handling model loading/unloading
    - Processing text and image inputs
    - Streaming responses
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 60):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: Base URL for Ollama API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = None
        logger.info(f"Ollama client initialized with base URL: {base_url}")
        
    async def start(self):
        """Start the client session."""
        logger.info("Starting Ollama client")
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        logger.info("Ollama client started")
        
    async def stop(self):
        """Stop the client session."""
        logger.info("Stopping Ollama client")
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Ollama client stopped")
        
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.
        
        Returns:
            List of model information dictionaries
        """
        logger.info("Listing Ollama models")
        
        if not self.session:
            await self.start()
            
        async with self.session.get(f"{self.base_url}/api/tags") as response:
            response.raise_for_status()
            data = await response.json()
            logger.info(f"Found {len(data.get('models', []))} Ollama models")
            return data.get("models", [])
            
    async def generate(self, 
                      model: str, 
                      prompt: str, 
                      system: Optional[str] = None,
                      images: Optional[List[Union[str, bytes, BinaryIO]]] = None,
                      options: Optional[Dict[str, Any]] = None,
                      stream: bool = False) -> Union[Dict[str, Any], asyncio.Queue]:
        """
        Generate a response from a model.
        
        Args:
            model: Model name
            prompt: Text prompt
            system: System prompt
            images: List of images (file paths, bytes, or file objects)
            options: Model options
            stream: Whether to stream the response
            
        Returns:
            Response dictionary or asyncio.Queue for streaming
        """
        logger.info(f"Generating response with model: {model}")
        
        if not self.session:
            await self.start()
            
        # Prepare request payload
        payload = {
            "model": model,
            "prompt": prompt,
        }
        
        if system:
            payload["system"] = system
            
        if options:
            payload["options"] = options
            
        # Process images if provided
        if images:
            payload["images"] = await self._process_images(images)
            
        # Set up streaming if requested
        if stream:
            return await self._stream_generate(payload)
        else:
            # Single response
            async with self.session.post(f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(f"Generated response with {len(result.get('response', ''))} characters")
                return result
                
    async def _stream_generate(self, payload: Dict[str, Any]) -> asyncio.Queue:
        """
        Stream a response from a model.
        
        Args:
            payload: Request payload
            
        Returns:
            Queue containing response chunks
        """
        logger.info("Streaming response")
        
        # Create queue for streaming
        queue = asyncio.Queue()
        
        # Start streaming task
        asyncio.create_task(self._stream_task(queue, payload))
        
        return queue
        
    async def _stream_task(self, queue: asyncio.Queue, payload: Dict[str, Any]):
        """
        Task for streaming responses.
        
        Args:
            queue: Queue to put response chunks into
            payload: Request payload
        """
        try:
            async with self.session.post(f"{self.base_url}/api/generate", 
                                        json=payload, 
                                        timeout=aiohttp.ClientTimeout(total=None)) as response:
                response.raise_for_status()
                
                # Process the streaming response
                async for line in response.content:
                    if not line.strip():
                        continue
                        
                    try:
                        chunk = json.loads(line)
                        await queue.put(chunk)
                        
                        # Check if this is the final chunk
                        if chunk.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse streaming response: {line}")
                        
        except Exception as e:
            logger.exception(f"Error in streaming task: {e}")
            # Put error in queue
            await queue.put({"error": str(e)})
            
        finally:
            # Mark end of stream
            await queue.put(None)
            
    async def _process_images(self, images: List[Union[str, bytes, BinaryIO]]) -> List[str]:
        """
        Process images for API request.
        
        Args:
            images: List of images (file paths, bytes, or file objects)
            
        Returns:
            List of base64-encoded images
        """
        processed_images = []
        
        for image in images:
            if isinstance(image, str):
                # Assume it's a file path
                if os.path.exists(image):
                    with open(image, "rb") as f:
                        image_data = f.read()
                        encoded = base64.b64encode(image_data).decode("utf-8")
                        processed_images.append(encoded)
                else:
                    logger.warning(f"Image file not found: {image}")
                    
            elif isinstance(image, bytes):
                # Raw bytes
                encoded = base64.b64encode(image).decode("utf-8")
                processed_images.append(encoded)
                
            elif hasattr(image, "read"):
                # File-like object
                image_data = image.read()
                if isinstance(image_data, str):
                    image_data = image_data.encode("utf-8")
                encoded = base64.b64encode(image_data).decode("utf-8")
                processed_images.append(encoded)
                
            else:
                logger.warning(f"Unsupported image type: {type(image)}")
                
        logger.info(f"Processed {len(processed_images)} images")
        return processed_images
        
    async def chat(self, 
                  model: str, 
                  messages: List[Dict[str, str]], 
                  images: Optional[List[Union[str, bytes, BinaryIO]]] = None,
                  options: Optional[Dict[str, Any]] = None,
                  stream: bool = False) -> Union[Dict[str, Any], asyncio.Queue]:
        """
        Chat with a model.
        
        Args:
            model: Model name
            messages: List of message dictionaries
            images: List of images (file paths, bytes, or file objects)
            options: Model options
            stream: Whether to stream the response
            
        Returns:
            Response dictionary or asyncio.Queue for streaming
        """
        logger.info(f"Chatting with model: {model}")
        
        if not self.session:
            await self.start()
            
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
        }
        
        if options:
            payload["options"] = options
            
        # Process images if provided
        if images:
            # For chat API, images need to be added to the last user message
            processed_images = await self._process_images(images)
            
            # Find the last user message
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "user":
                    if "images" not in payload:
                        payload["images"] = processed_images
                    break
                    
        # Set up streaming if requested
        if stream:
            return await self._stream_chat(payload)
        else:
            # Single response
            async with self.session.post(f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(f"Chat response received")
                return result
                
    async def _stream_chat(self, payload: Dict[str, Any]) -> asyncio.Queue:
        """
        Stream a chat response.
        
        Args:
            payload: Request payload
            
        Returns:
            Queue containing response chunks
        """
        logger.info("Streaming chat response")
        
        # Create queue for streaming
        queue = asyncio.Queue()
        
        # Start streaming task
        asyncio.create_task(self._stream_chat_task(queue, payload))
        
        return queue
        
    async def _stream_chat_task(self, queue: asyncio.Queue, payload: Dict[str, Any]):
        """
        Task for streaming chat responses.
        
        Args:
            queue: Queue to put response chunks into
            payload: Request payload
        """
        try:
            async with self.session.post(f"{self.base_url}/api/chat", 
                                        json=payload, 
                                        timeout=aiohttp.ClientTimeout(total=None)) as response:
                response.raise_for_status()
                
                # Process the streaming response
                async for line in response.content:
                    if not line.strip():
                        continue
                        
                    try:
                        chunk = json.loads(line)
                        await queue.put(chunk)
                        
                        # Check if this is the final chunk
                        if chunk.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse streaming response: {line}")
                        
        except Exception as e:
            logger.exception(f"Error in streaming task: {e}")
            # Put error in queue
            await queue.put({"error": str(e)})
            
        finally:
            # Mark end of stream
            await queue.put(None)
            
    async def pull_model(self, model: str) -> asyncio.Queue:
        """
        Pull a model.
        
        Args:
            model: Model name
            
        Returns:
            Queue containing progress updates
        """
        logger.info(f"Pulling model: {model}")
        
        if not self.session:
            await self.start()
            
        # Create queue for progress updates
        queue = asyncio.Queue()
        
        # Start pull task
        asyncio.create_task(self._pull_model_task(queue, model))
        
        return queue
        
    async def _pull_model_task(self, queue: asyncio.Queue, model: str):
        """
        Task for pulling a model.
        
        Args:
            queue: Queue to put progress updates into
            model: Model name
        """
        try:
            payload = {"name": model}
            
            async with self.session.post(f"{self.base_url}/api/pull", 
                                        json=payload, 
                                        timeout=aiohttp.ClientTimeout(total=None)) as response:
                response.raise_for_status()
                
                # Process the streaming response
                async for line in response.content:
                    if not line.strip():
                        continue
                        
                    try:
                        update = json.loads(line)
                        await queue.put(update)
                        
                        # Check if this is the final update
                        if update.get("status") == "success":
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse pull update: {line}")
                        
        except Exception as e:
            logger.exception(f"Error in pull task: {e}")
            # Put error in queue
            await queue.put({"error": str(e)})
            
        finally:
            # Mark end of stream
            await queue.put(None)
            
    async def create_model(self, 
                         name: str, 
                         modelfile: str) -> Dict[str, Any]:
        """
        Create a model from a Modelfile.
        
        Args:
            name: Name for the new model
            modelfile: Contents of the Modelfile
            
        Returns:
            Response dictionary
        """
        logger.info(f"Creating model: {name}")
        
        if not self.session:
            await self.start()
            
        payload = {
            "name": name,
            "modelfile": modelfile
        }
        
        async with self.session.post(f"{self.base_url}/api/create", json=payload) as response:
            response.raise_for_status()
            result = await response.json()
            logger.info(f"Model created: {name}")
            return result
            
    async def delete_model(self, model: str) -> Dict[str, Any]:
        """
        Delete a model.
        
        Args:
            model: Model name
            
        Returns:
            Response dictionary
        """
        logger.info(f"Deleting model: {model}")
        
        if not self.session:
            await self.start()
            
        payload = {"name": model}
        
        async with self.session.delete(f"{self.base_url}/api/delete", json=payload) as response:
            response.raise_for_status()
            result = await response.json()
            logger.info(f"Model deleted: {model}")
            return result
            
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get information about a model.
        
        Args:
            model: Model name
            
        Returns:
            Model information dictionary
        """
        logger.info(f"Getting info for model: {model}")
        
        if not self.session:
            await self.start()
            
        async with self.session.post(f"{self.base_url}/api/show", json={"name": model}) as response:
            response.raise_for_status()
            result = await response.json()
            logger.info(f"Got info for model: {model}")
            return result
            
    async def check_ollama_status(self) -> bool:
        """
        Check if Ollama is running.
        
        Returns:
            True if Ollama is running, False otherwise
        """
        logger.info("Checking Ollama status")
        
        if not self.session:
            await self.start()
            
        try:
            async with self.session.get(f"{self.base_url}/api/version") as response:
                response.raise_for_status()
                version_info = await response.json()
                logger.info(f"Ollama is running, version: {version_info.get('version', 'unknown')}")
                return True
        except Exception as e:
            logger.warning(f"Ollama is not running: {e}")
            return False
