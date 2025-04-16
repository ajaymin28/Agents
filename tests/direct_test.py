import asyncio
import base64
from PIL import Image
import io
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath('.'))

# Import the necessary classes
from src.models.ollama_client import OllamaClient
from src.agents.vlm_agent import VLMAgent
from src.core.engine import CoreEngine
from src.config.settings import Settings

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def test_vlm():
    # Initialize components
    settings = Settings()
    engine = CoreEngine(settings)
    ollama_client = OllamaClient(
        base_url=settings.get("ollama", "base_url", "http://localhost:11434") ,
        timeout=settings.get("ollama", "timeout", 60)
    )
    
    # Start the Ollama client
    await ollama_client.start()
    
    # Create VLM agent
    vlm_agent = VLMAgent(engine, ollama_client, settings)
    
    # Initialize with a simple resource profile
    resource_profile = {
        "cpu_cores": 4,
        "memory_gb": 8.0,
        "has_gpu": False,
        "resource_tier": "medium"
    }
    
    # Initialize the agent
    await vlm_agent.initialize(resource_profile)
    
    # Replace with the path to your test image
    image_path =  "C:/Users/ASUS/Pictures/vlcsnap-2024-11-09-20h02m47s848.png"  # Update this with your image path
    
    # Create a task for image understanding
    task = {
        "id": "test-task",
        "type": "image_understanding",
        "inputs": {
            "image": image_path,
            "prompt": "Describe this image in detail."
        },
        "parameters": {
            "model": "llava:7b-v1.5-q4_0"  # Use the model you have available
        }
    }
    
    print("Processing image understanding task...")
    
    # Process the task
    result = await vlm_agent.process_task(task)
    
    print("\nResult:")
    import json
    print(json.dumps(result, indent=2))
    
    # Clean up
    await ollama_client.stop()

# Run the test
if __name__ == "__main__":
    asyncio.run(test_vlm())
