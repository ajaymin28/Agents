# Stable Diffusion Integration Research

## Overview
Stable Diffusion is a deep learning text-to-image model that can generate detailed images based on text descriptions. Integrating Stable Diffusion with Ollama allows for a powerful combination of language models and image generation capabilities.

## Integration Approaches

### 1. RESTful API Server
- The [Dublit-Development/ollama-api](https://github.com/Dublit-Development/ollama-api) project provides a Flask server that integrates both Ollama and Stable Diffusion
- Deploys a RESTful API that can handle both text interactions with LLMs and image generation
- Supports features like:
  - Dynamic model selection
  - Text-to-image generation via Stable Diffusion
  - VLM analysis with models like LLaVA
  - Chat interface for multiple LLMs

### 2. Stable Diffusion Prompt Generator with Ollama
- The `brxce/stable-diffusion-prompt-generator` model can be run through Ollama
- This model is fine-tuned on 74k Stable Diffusion prompts
- Converts simple input text to optimized Stable Diffusion prompts
- These prompts can then be passed to Stable Diffusion for better image generation

### 3. Connecting Automatic1111 WebUI with Open WebUI
- Automatic1111 is a popular web interface for Stable Diffusion
- Open WebUI is a frontend for Ollama
- These can be connected to create a workflow where:
  1. User interacts with LLM through Open WebUI
  2. LLM generates optimized prompts for Stable Diffusion
  3. Prompts are sent to Automatic1111 to generate images

## Python API Integration

### AUTOMATIC1111 API Client (sdwebuiapi)
- Python library `webuiapi` provides a client for the Stable Diffusion WebUI API
- Installation: `pip install webuiapi`
- Supports key operations:
  - txt2img: Generate images from text prompts
  - img2img: Modify existing images based on prompts
  - inpainting: Edit specific parts of images
  - upscaling: Enhance image resolution
- Example usage:
```python
import webuiapi

# Create API client
api = webuiapi.WebUIApi()

# Generate image from text
result = api.txt2img(
    prompt="cute squirrel",
    negative_prompt="ugly, out of frame",
    seed=1003,
    styles=["anime"],
    cfg_scale=7
)

# Access the generated image
image = result.image

# Image-to-image transformation
result2 = api.img2img(
    images=[image], 
    prompt="cute cat", 
    seed=5555, 
    cfg_scale=6.5, 
    denoising_strength=0.6
)
```

### Ollama Python Client
- Official Python library for Ollama: `ollama-python`
- Can be used to interact with Ollama models including the Stable Diffusion prompt generator
- Example usage with Stable Diffusion prompt generator:
```python
import ollama

# Generate optimized prompt
response = ollama.chat(
    model='brxce/stable-diffusion-prompt-generator',
    messages=[
        {
            'role': 'user',
            'content': 'A futuristic city with flying cars'
        }
    ]
)

# Extract the optimized prompt
optimized_prompt = response['message']['content']

# This prompt can then be passed to Stable Diffusion
```

## Integration Architecture Considerations

### 1. API Communication
- Ollama API runs on port 11434 by default
- Stable Diffusion WebUI API requires enabling with `--api` flag
- Both can be accessed via HTTP requests

### 2. Authentication
- Stable Diffusion WebUI supports basic authentication with `--api-auth user:pass`
- Should be used over HTTPS in production for security

### 3. Resource Requirements
- Both Ollama and Stable Diffusion are resource-intensive
- Recommended hardware:
  - 32GB+ RAM
  - NVIDIA GPU with 8GB+ VRAM
  - 50GB+ storage

### 4. Deployment Options
- Docker containers for isolation and easier deployment
- Flask/FastAPI server as a middleware between components
- Cloudflare Workers for serverless deployment of the frontend

## Implementation Strategy
1. Set up Ollama with required models (VLMs and Stable Diffusion prompt generator)
2. Set up Stable Diffusion with API access enabled
3. Create a middleware service to coordinate between them
4. Implement a user interface for interaction
5. Add deployment configuration for freeware services
