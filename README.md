# Ollama Agent Framework

A flexible agent framework for working with Ollama models, focusing on Vision Language Models (VLMs) and Stable Diffusion, with multi-agent support and optimizations for low-resource environments.

## Features

- **Multi-Agent Architecture**: Coordinate specialized agents for different tasks
- **VLM Integration**: Work with vision-language models through Ollama
- **Stable Diffusion Support**: Generate and manipulate images
- **Plugin System**: Easily extend functionality with custom plugins
- **MCP Tools Integration**: Connect to 4,500+ tools via Smithery.ai MCP
- **Low-Resource Mode**: Optimized for machines with only 4GB VRAM
- **RESTful API**: Comprehensive API for client applications

## Requirements

- Python 3.8+
- Ollama (running locally or on a remote server)
- 4GB+ VRAM for full functionality (specialized low-resource mode available)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ollama-agent-project.git
cd ollama-agent-project

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

1. Ensure Ollama is running and has the required models:
```bash
ollama pull llava-1.5-7b
ollama pull sd-1.5
```

2. Start the agent server:
```bash
python -m src.main
```

3. Access the API at http://localhost:8000

## Deployment Options

The framework supports multiple deployment options:

### Docker

```bash
docker-compose up -d
```

### Kubernetes

```bash
kubectl apply -f deployment/kubernetes/deployment.yaml
```

### Systemd Service

```bash
sudo cp deployment/systemd/ollama-agent.service /etc/systemd/system/
sudo systemctl enable ollama-agent
sudo systemctl start ollama-agent
```

### Cloud Platforms

Configurations are provided for:
- Google Cloud Run
- Heroku
- Any platform supporting Docker containers

## Architecture

The framework follows a modular architecture with the following components:

- **Core Engine**: Manages agent lifecycle and task routing
- **Model Layer**: Abstracts interaction with Ollama models
- **Plugin Manager**: Handles registration and lifecycle of plugins
- **MCP Connector**: Implements Model Context Protocol for tool integration
- **Communication Bus**: Facilitates inter-agent communication

## Low-Resource Mode

For machines with limited VRAM (4GB), the framework automatically:

- Uses 4-bit quantized models
- Reduces batch sizes and context lengths
- Implements CPU offloading for parts of computation
- Provides graceful degradation of capabilities

## API Documentation

API documentation is available at http://localhost:8000/api/docs when the server is running.

## Development

### Project Structure

```
ollama-agent-project/
├── src/
│   ├── core/          # Core engine and communication
│   ├── models/        # Model integration
│   ├── agents/        # Agent implementations
│   ├── plugins/       # Plugin system
│   ├── tools/         # Built-in tools
│   ├── mcp/           # MCP integration
│   ├── api/           # API endpoints
│   ├── utils/         # Utility functions
│   └── config/        # Configuration
├── tests/             # Test suite
├── docs/              # Documentation
├── scripts/           # Utility scripts
└── design/            # Design documents
```

### Creating Plugins

Plugins allow you to extend the framework with custom functionality. Here's a simple example:

```python
from src.plugins.plugin_base import PluginBase, plugin, capability

@plugin
class MyCustomPlugin(PluginBase):
    """My custom plugin for the Ollama agent framework."""
    
    async def initialize(self):
        """Initialize the plugin."""
        print("Initializing MyCustomPlugin")
        
    @capability("custom_capability")
    async def my_custom_function(self, param1, param2):
        """Implement a custom capability."""
        return {"result": f"Processed {param1} and {param2}"}
```

### Running Tests

```bash
pytest
```

## License

MIT

## Acknowledgements

- [Ollama](https://github.com/ollama/ollama) for the model serving framework
- [Smithery.ai](https://smithery.ai) for MCP tools integration
