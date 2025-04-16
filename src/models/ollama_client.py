"""
Ollama Client Module

This module provides a client for interacting with the Ollama API,
supporting both text generation and vision-language model capabilities.
"""

import ollama
import asyncio
import base64
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
        self.client = None
        logger.info(f"Ollama client initialized with base URL: {base_url}")
        
    async def start(self):
        """Start the client."""
        logger.info("Starting Ollama client")
        self.client = ollama.AsyncClient(host=self.base_url, timeout=self.timeout)
        logger.info("Ollama client started")
        
    async def stop(self):
        """Stop the client."""
        logger.info("Stopping Ollama client")
        self.client = None
        logger.info("Ollama client stopped")
        
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.
        
        Returns:
            List of model information dictionaries
        """
        logger.info("Listing Ollama models")
        
        if not self.client:
            await self.start()
            
        data = await self.client.list()
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
        
        if not self.client:
            await self.start()

        if not self.client:
            logger.error("Cannot generate: Client is not initialized")
            raise RuntimeError("Ollama client is not initialized")

        # Prepare request parameters
        params = {
            "model": model,
            "prompt": prompt,
        }
        
        if system:
            params["system"] = system
            
        if options:
            params["options"] = options
            
        # Process images if provided
        if images:
            params["images"] = await self._process_images(images)
            
        # Set up streaming if requested
        if stream:
            return await self._stream_generate(params)
        else:
            result = await self.client.generate(**params)
            logger.info(f"Generated response with {len(result.get('response', ''))} characters")
            return result
                
    async def _stream_generate(self, params: Dict[str, Any]) -> asyncio.Queue:
        """
        Stream a response from a model.
        
        Args:
            params: Request parameters
            
        Returns:
            Queue containing response chunks
        """
        logger.info("Streaming response")

        queue = asyncio.Queue()
        asyncio.create_task(self._stream_task(queue, params))
        return queue
        
    async def _stream_task(self, queue: asyncio.Queue, params: Dict[str, Any]):
        """
        Task for streaming responses.
        
        Args:
            queue: Queue to put response chunks into
            params: Request parameters
        """
        try:
            async for chunk in self.client.generate(**params, stream=True):
                await queue.put(chunk)
                if chunk.get("done", False):
                    break
        except Exception as e:
            logger.exception(f"Error in streaming task: {e}")
            await queue.put({"error": str(e)})
        finally:
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
            processed_images.append(image)
            # if isinstance(image, str):
            #     if os.path.exists(image):
            #         with open(image, "rb") as f:
            #             image_data = f.read()
            #             encoded = base64.b64encode(image_data).decode("utf-8")
            #             processed_images.append(encoded)
            #     else:
            #         logger.warning(f"Image file not found: {image}")
                    
            # elif isinstance(image, bytes):
            #     encoded = base64.b64encode(image).decode("utf-8")
            #     processed_images.append(encoded)
                
            # elif hasattr(image, "read"):
            #     image_data = image.read()
            #     if isinstance(image_data, str):
            #         image_data = image_data.encode("utf-8")
            #     encoded = base64.b64encode(image_data).decode("utf-8")
            #     processed_images.append(encoded)
                
            # else:
            #     logger.warning(f"Unsupported image type: {type(image)}")
                
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
        
        if not self.client:
            await self.start()
            
        params = {
            "model": model,
            "messages": messages,
        }
        
        if options:
            params["options"] = options
            
        if images:
            processed_images = await self._process_images(images)
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "user":
                    messages[i]["images"] = processed_images
                    break
                    
        if stream:
            return await self._stream_chat(params)
        else:
            result = await self.client.chat(**params)
            logger.info(f"Chat response received")
            return result
                
    async def _stream_chat(self, params: Dict[str, Any]) -> asyncio.Queue:
        """
        Stream a chat response.
        
        Args:
            params: Request parameters
            
        Returns:
            Queue containing response chunks
        """
        logger.info("Streaming chat response")
        
        queue = asyncio.Queue()
        asyncio.create_task(self._stream_chat_task(queue, params))
        return queue
        
    async def _stream_chat_task(self, queue: asyncio.Queue, params: Dict[str, Any]):
        """
        Task for streaming chat responses.
        
        Args:
            queue: Queue to put response chunks into
            params: Request parameters
        """
        try:
            async for chunk in self.client.chat(**params, stream=True):
                await queue.put(chunk)
                if chunk.get("done", False):
                    break
        except Exception as e:
            logger.exception(f"Error in streaming task: {e}")
            await queue.put({"error": str(e)})
        finally:
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
        
        if not self.client:
            await self.start()
            
        queue = asyncio.Queue()
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
            async for update in self.client.pull(model, stream=True):
                await queue.put(update)
                if update.get("status") == "success":
                    break
        except Exception as e:
            logger.exception(f"Error in pull task: {e}")
            await queue.put({"error": str(e)})
        finally:
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
        
        if not self.client:
            await self.start()
            
        result = await self.client.create(name, modelfile)
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
        
        if not self.client:
            await self.start()
            
        result = await self.client.delete(model)
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
        
        if not self.client:
            await self.start()
            
        result = await self.client.show(model)
        logger.info(f"Got info for model: {model}")
        return result
            
    async def check_ollama_status(self) -> bool:
        """
        Check if Ollama is running.
        
        Returns:
            True if Ollama is running, False otherwise
        """
        logger.info("Checking Ollama status")
        
        if not self.client:
            await self.start()
            
        try:
            await self.client.ps()  # Simple API call to check if server is responsive
            logger.info("Ollama is running")
            return True
        except Exception as e:
            logger.warning(f"Ollama is not running: {e}")
            return False