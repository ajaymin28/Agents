# Ollama API Research

## Overview
Ollama is a platform that allows running large language models (LLMs) locally. It provides a REST API for interacting with these models, making it easy to integrate them into applications.

## API Endpoints

### Core Endpoints
- `/api/generate` - Generate a completion for a given prompt
- `/api/chat` - Generate a chat completion
- `/api/embeddings` - Generate embeddings for text

### Model Management
- `/api/create` - Create a model
- `/api/list` - List local models
- `/api/show` - Show model information
- `/api/copy` - Copy a model
- `/api/delete` - Delete a model
- `/api/pull` - Pull a model
- `/api/push` - Push a model
- `/api/running` - List running models

### System
- `/api/version` - Get version information

## Model Naming Convention
Models follow a `model:tag` format, where:
- `model` can have an optional namespace (e.g., `example/model`)
- `tag` is optional and defaults to `latest`

Examples: `orca-mini:3b-q4_1`, `llama3:70b`

## Key Features

### Multimodal Support
- Supports multimodal models like LLaVA
- Can process images by passing base64-encoded images in the request

### Structured Output
- Supports JSON output format
- Can enforce output structure using JSON schema

### Advanced Parameters
- `format`: Output format (json or JSON schema)
- `options`: Model parameters like temperature
- `system`: System message override
- `template`: Prompt template override
- `stream`: Control streaming behavior
- `raw`: Control prompt formatting
- `keep_alive`: Control model memory management

## VLM (Vision Language Model) Support
- Ollama supports multimodal models like LLaVA that can process both text and images
- Images can be passed as base64-encoded strings in the request
- This enables vision-based tasks like image description, visual question answering, etc.

## Performance Metrics
- Response includes detailed performance metrics:
  - `total_duration`: Total time for generation
  - `load_duration`: Time spent loading the model
  - `prompt_eval_count`: Number of tokens in prompt
  - `prompt_eval_duration`: Time evaluating prompt
  - `eval_count`: Number of tokens in response
  - `eval_duration`: Time generating response

## Integration Considerations
- Local deployment means all processing happens on the user's machine
- Need to consider model size and hardware requirements
- Streaming responses for better user experience
- Error handling for model loading failures
