import asyncio
import aiohttp
import logging
import os
import base64
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_ollama_generate():
    """Test sending a POST request to Ollama's /api/generate endpoint with an image."""
    base_url = "http://127.0.0.1:11434"  # Default Ollama URL
    timeout = 60  # Timeout in seconds
    image_path = "C:/Users/ASUS/Pictures/vlcsnap-2024-11-09-20h02m47s848.png"  # Replace with your image path
    model = "llava:7b-v1.5-q4_0"  # Model name
    prompt = "Describe this image in detail."

    # Verify the image exists
    if not os.path.exists(image_path):
        logger.error(f"Image file does not exist: {image_path}")
        return

    # Read and encode the image
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
            encoded_image = base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to read or encode image: {e}")
        return

    # Prepare the payload
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [encoded_image],
        "options": {
            "temperature": 0.1,
            "num_predict": 1024
        }
    }

    # Create an aiohttp session
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        try:
            # Replicate the exact code block
            async with session.post(f"{base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                try:
                    response_json = await response.json()
                    print(response_json)
                except json.JSONDecodeError as e:
                    print(f"JSONDecodeError: {e}, Response Text: {response.text}")
                
                # logger.info(f"Generated response with {len(result.get('response', ''))} characters")
                # print("Image Description:", result.get("response", "No description returned"))
                # return result
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            logger.exception(f"Error during request: {e}")

# Run the test
if __name__ == "__main__":
    # Set Windows event loop policy if needed
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(test_ollama_generate())