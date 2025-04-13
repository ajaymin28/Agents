# API Endpoints Design

## Overview

This document outlines the API endpoints for the Ollama agent system, providing a standardized interface for client applications to interact with the agent's capabilities including VLM processing, Stable Diffusion image generation, and multi-agent coordination.

## API Design Principles

1. **RESTful Architecture**: Follow REST principles for resource-oriented endpoints
2. **Consistent Patterns**: Maintain consistent naming, parameter handling, and response formats
3. **Versioning**: Include API versioning to support backward compatibility
4. **Documentation**: Provide OpenAPI/Swagger documentation for all endpoints
5. **Error Handling**: Standardized error responses with meaningful codes and messages

## Base URL Structure

```
https://{host}/api/v1/
```

## Authentication

- Bearer token authentication
- API key authentication for service-to-service communication
- Rate limiting based on authentication tier

## Core Endpoints

### Agent Management

#### List Agents

```
GET /agents
```

Response:
```json
{
  "agents": [
    {
      "id": "coordinator",
      "type": "coordinator",
      "status": "active",
      "capabilities": ["task_delegation", "result_aggregation"]
    },
    {
      "id": "vlm_agent",
      "type": "vlm",
      "status": "active",
      "capabilities": ["image_understanding", "visual_qa"]
    }
  ]
}
```

#### Get Agent Status

```
GET /agents/{agent_id}
```

Response:
```json
{
  "id": "vlm_agent",
  "type": "vlm",
  "status": "active",
  "capabilities": ["image_understanding", "visual_qa"],
  "models": ["llava-1.5-7b"],
  "resource_usage": {
    "memory": "1.2GB",
    "vram": "3.5GB"
  }
}
```

#### Create Task

```
POST /tasks
```

Request:
```json
{
  "type": "visual_qa",
  "input": {
    "image_url": "https://example.com/image.jpg",
    "question": "What is shown in this image?"
  },
  "parameters": {
    "model": "llava-1.5-7b",
    "max_tokens": 100
  }
}
```

Response:
```json
{
  "task_id": "task_12345",
  "status": "processing",
  "created_at": "2025-04-13T22:30:00Z",
  "estimated_completion": "2025-04-13T22:30:10Z"
}
```

#### Get Task Status

```
GET /tasks/{task_id}
```

Response:
```json
{
  "task_id": "task_12345",
  "status": "completed",
  "created_at": "2025-04-13T22:30:00Z",
  "completed_at": "2025-04-13T22:30:08Z",
  "result": {
    "answer": "The image shows a mountain landscape with a lake.",
    "confidence": 0.92
  }
}
```

### VLM Endpoints

#### Image Understanding

```
POST /vlm/understand
```

Request:
```json
{
  "image": "base64_encoded_image_data",
  "prompt": "Describe this image in detail."
}
```

Response:
```json
{
  "description": "The image shows a scenic mountain landscape with snow-capped peaks reflecting in a clear blue lake. In the foreground, there are pine trees and a small wooden dock extending into the water.",
  "tags": ["mountains", "lake", "nature", "landscape"],
  "processing_time": 1.2
}
```

#### Visual Question Answering

```
POST /vlm/qa
```

Request:
```json
{
  "image": "base64_encoded_image_data",
  "question": "What color is the car in this image?"
}
```

Response:
```json
{
  "answer": "The car in the image is red.",
  "confidence": 0.95,
  "processing_time": 0.8
}
```

### Stable Diffusion Endpoints

#### Generate Image

```
POST /sd/generate
```

Request:
```json
{
  "prompt": "A futuristic city with flying cars and neon lights",
  "negative_prompt": "blurry, low quality",
  "width": 512,
  "height": 512,
  "num_inference_steps": 30,
  "guidance_scale": 7.5
}
```

Response:
```json
{
  "image": "base64_encoded_image_data",
  "seed": 42,
  "processing_time": 3.5
}
```

#### Image-to-Image

```
POST /sd/img2img
```

Request:
```json
{
  "image": "base64_encoded_image_data",
  "prompt": "Convert this landscape to winter scene with snow",
  "strength": 0.7,
  "guidance_scale": 7.5
}
```

Response:
```json
{
  "image": "base64_encoded_image_data",
  "seed": 123,
  "processing_time": 2.8
}
```

### Multi-Agent Endpoints

#### Collaborative Task

```
POST /multi-agent/task
```

Request:
```json
{
  "task": "Generate an image based on this description and then analyze it",
  "steps": [
    {
      "agent": "sd_agent",
      "action": "generate",
      "parameters": {
        "prompt": "A futuristic city with flying cars"
      }
    },
    {
      "agent": "vlm_agent",
      "action": "analyze",
      "parameters": {
        "aspects": ["objects", "style", "mood"]
      }
    }
  ]
}
```

Response:
```json
{
  "task_id": "multi_task_789",
  "status": "processing",
  "created_at": "2025-04-13T22:35:00Z",
  "estimated_completion": "2025-04-13T22:35:30Z"
}
```

#### Get Collaborative Task Result

```
GET /multi-agent/task/{task_id}
```

Response:
```json
{
  "task_id": "multi_task_789",
  "status": "completed",
  "steps": [
    {
      "agent": "sd_agent",
      "action": "generate",
      "status": "completed",
      "result": {
        "image": "base64_encoded_image_data",
        "seed": 456
      }
    },
    {
      "agent": "vlm_agent",
      "action": "analyze",
      "status": "completed",
      "result": {
        "objects": ["flying cars", "skyscrapers", "neon signs"],
        "style": "cyberpunk",
        "mood": "futuristic, energetic"
      }
    }
  ],
  "processing_time": 5.2
}
```

### Plugin and Tool Endpoints

#### List Available Tools

```
GET /tools
```

Response:
```json
{
  "tools": [
    {
      "id": "web_search",
      "name": "Web Search",
      "description": "Search the web for information",
      "provider": "smithery.ai",
      "parameters": [
        {
          "name": "query",
          "type": "string",
          "required": true,
          "description": "Search query"
        }
      ]
    },
    {
      "id": "image_enhancer",
      "name": "Image Enhancer",
      "description": "Enhance image quality",
      "provider": "local",
      "parameters": [
        {
          "name": "image",
          "type": "binary",
          "required": true,
          "description": "Image to enhance"
        },
        {
          "name": "strength",
          "type": "float",
          "required": false,
          "default": 0.5,
          "description": "Enhancement strength"
        }
      ]
    }
  ]
}
```

#### Execute Tool

```
POST /tools/{tool_id}/execute
```

Request:
```json
{
  "parameters": {
    "query": "latest advancements in AI"
  }
}
```

Response:
```json
{
  "result": {
    "items": [
      {
        "title": "Recent Breakthrough in AI Research",
        "url": "https://example.com/ai-news",
        "snippet": "Researchers have announced a significant breakthrough..."
      }
    ]
  },
  "processing_time": 1.5
}
```

### System Management Endpoints

#### System Status

```
GET /system/status
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "3d 5h 12m",
  "resources": {
    "cpu_usage": 45,
    "memory_usage": 6.2,
    "gpu_usage": 80,
    "vram_usage": 3.8
  },
  "active_agents": 5,
  "pending_tasks": 2
}
```

#### Model Management

```
GET /models
```

Response:
```json
{
  "models": [
    {
      "id": "llava-1.5-7b",
      "type": "vlm",
      "status": "loaded",
      "size": "4.2GB",
      "quantization": "4-bit"
    },
    {
      "id": "sd-1.5",
      "type": "diffusion",
      "status": "loaded",
      "size": "2.8GB",
      "quantization": "4-bit"
    }
  ]
}
```

## Streaming Endpoints

### Stream Generation

```
POST /sd/generate/stream
```

This endpoint uses Server-Sent Events (SSE) to stream the generation process:

```
event: progress
data: {"step": 1, "total_steps": 30, "preview": "base64_encoded_preview"}

event: progress
data: {"step": 2, "total_steps": 30, "preview": "base64_encoded_preview"}

...

event: complete
data: {"image": "base64_encoded_final_image", "seed": 789, "processing_time": 4.2}
```

### Stream Task Progress

```
GET /tasks/{task_id}/stream
```

This endpoint uses SSE to stream task progress:

```
event: status
data: {"status": "processing", "progress": 0.2, "message": "Loading models"}

event: status
data: {"status": "processing", "progress": 0.5, "message": "Generating image"}

event: status
data: {"status": "processing", "progress": 0.8, "message": "Post-processing"}

event: complete
data: {"result": {"image": "base64_encoded_image", "analysis": {...}}}
```

## Error Handling

All endpoints use standard HTTP status codes and return error details in a consistent format:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "The requested resource was not found",
    "details": {
      "resource_type": "model",
      "resource_id": "nonexistent-model"
    }
  }
}
```

## API Documentation

The API will be documented using OpenAPI 3.0 specification, available at:

```
GET /api/docs
```

Interactive Swagger UI will be available at:

```
GET /api/docs/ui
```

## Low-Resource Considerations

For 4GB VRAM environments:

1. **Batch Size Limits**: Automatically adjust batch sizes based on available resources
2. **Resolution Constraints**: Enforce maximum resolution limits
3. **Queue Management**: Implement task queuing with priority handling
4. **Resource Monitoring**: Endpoints to check resource availability before submitting large tasks

## Conclusion

This API design provides a comprehensive interface for interacting with the Ollama agent system, supporting all the required functionality including VLM processing, Stable Diffusion image generation, multi-agent coordination, and tool integration. The design follows REST principles and includes considerations for streaming, error handling, and resource constraints.
