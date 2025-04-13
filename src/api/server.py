"""
API Server Module

This module implements the RESTful API server for the Ollama agent framework.
"""

import asyncio
import logging
import os
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from ..core.engine import CoreEngine
from ..config.settings import Settings

logger = logging.getLogger(__name__)

# Define API models
class TaskRequest(BaseModel):
    type: str
    inputs: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}

class TaskResponse(BaseModel):
    id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ServerConfig:
    """Configuration for the API server."""
    
    def __init__(self, settings: Settings):
        """
        Initialize server configuration.
        
        Args:
            settings: Application settings
        """
        self.host = settings.get("api", "host", "0.0.0.0")
        self.port = settings.get("api", "port", 8000)
        self.enable_cors = settings.get("api", "enable_cors", True)
        self.allowed_origins = settings.get("api", "allowed_origins", ["*"])
        self.rate_limit = settings.get("api", "rate_limit", 100)

class APIServer:
    """
    API Server for the Ollama agent framework.
    
    Responsible for:
    - Exposing RESTful API endpoints
    - Handling HTTP requests
    - Routing requests to appropriate agents
    - Returning responses to clients
    """
    
    def __init__(self, 
                engine: CoreEngine,
                settings: Optional[Settings] = None):
        """
        Initialize the API Server.
        
        Args:
            engine: Core Engine instance
            settings: Configuration settings
        """
        self.engine = engine
        self.settings = settings or Settings()
        self.config = ServerConfig(self.settings)
        self.app = FastAPI(
            title="Ollama Agent API",
            description="API for the Ollama agent framework",
            version="1.0.0"
        )
        self.setup_middleware()
        self.setup_routes()
        logger.info("API Server initialized")
        
    def setup_middleware(self):
        """Set up middleware for the API server."""
        # Add CORS middleware if enabled
        if self.config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.allowed_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
    def setup_routes(self):
        """Set up API routes."""
        # Health check endpoint
        @self.app.get("/api/health")
        async def health_check():
            return {"status": "ok"}
            
        # Task submission endpoint
        @self.app.post("/api/tasks", response_model=TaskResponse)
        async def submit_task(task: TaskRequest):
            try:
                # Submit task to engine
                task_id = await self.engine.submit_task(
                    task_type=task.type,
                    inputs=task.inputs,
                    parameters=task.parameters
                )
                
                return {
                    "id": task_id,
                    "status": "submitted"
                }
            except Exception as e:
                logger.exception(f"Error submitting task: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Task status endpoint
        @self.app.get("/api/tasks/{task_id}", response_model=TaskResponse)
        async def get_task_status(task_id: str):
            try:
                # Get task status from engine
                status = await self.engine.get_task_status(task_id)
                
                return status
            except Exception as e:
                logger.exception(f"Error getting task status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Image upload endpoint
        @self.app.post("/api/upload/image")
        async def upload_image(file: UploadFile = File(...)):
            try:
                # Read image data
                image_data = await file.read()
                
                # Generate a unique filename
                filename = f"{asyncio.get_event_loop().time()}_{file.filename}"
                
                # Save image to temporary directory
                os.makedirs("temp", exist_ok=True)
                file_path = os.path.join("temp", filename)
                
                with open(file_path, "wb") as f:
                    f.write(image_data)
                    
                return {
                    "filename": filename,
                    "path": file_path,
                    "size": len(image_data)
                }
            except Exception as e:
                logger.exception(f"Error uploading image: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Available models endpoint
        @self.app.get("/api/models")
        async def get_models():
            try:
                # Get available models from engine
                models = await self.engine.get_available_models()
                
                return {"models": models}
            except Exception as e:
                logger.exception(f"Error getting models: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Available agents endpoint
        @self.app.get("/api/agents")
        async def get_agents():
            try:
                # Get available agents from engine
                agents = await self.engine.get_available_agents()
                
                return {"agents": agents}
            except Exception as e:
                logger.exception(f"Error getting agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Available plugins endpoint
        @self.app.get("/api/plugins")
        async def get_plugins():
            try:
                # Get available plugins from engine
                plugins = await self.engine.get_available_plugins()
                
                return {"plugins": plugins}
            except Exception as e:
                logger.exception(f"Error getting plugins: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # System status endpoint
        @self.app.get("/api/system/status")
        async def get_system_status():
            try:
                # Get system status from engine
                status = await self.engine.get_system_status()
                
                return status
            except Exception as e:
                logger.exception(f"Error getting system status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
    async def start(self):
        """Start the API server."""
        logger.info(f"Starting API Server on {self.config.host}:{self.config.port}")
        # Note: In a real implementation, we would start the server here
        # For this example, we'll just log that it's started
        logger.info("API Server started")
        
    async def stop(self):
        """Stop the API server."""
        logger.info("Stopping API Server")
        # Note: In a real implementation, we would stop the server here
        # For this example, we'll just log that it's stopped
        logger.info("API Server stopped")
        
    def run(self):
        """Run the API server (blocking)."""
        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port
        )
