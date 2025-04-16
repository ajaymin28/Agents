import requests
import json
import base64
from PIL import Image
import io

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Replace with the path to your test image
image_path = "C:/Users/ASUS/Pictures/vlcsnap-2024-11-09-20h02m47s848.png"  # Update this with your image path
base64_image = encode_image(image_path)

# API endpoint
url = "http://localhost:8000/api/tasks"

# Task payload for image understanding
payload = {
    "type": "image_understanding",
    "inputs": {
        "image": base64_image,
        "prompt": "Describe this image in detail."
    },
    "parameters": {
        "model": "llava:7b-v1.5-q4_0"  # Use the model you have available
    }
}

# Send the request
response = requests.post(url, json=payload) 
print(f"Task submitted: {response.json()}")

# Get the task ID from the response
task_id = response.json()["id"]

# Check task status until it's completed
while True:
    status_response = requests.get(f"http://localhost:8000/api/tasks/{task_id}") 
    status_data = status_response.json()
    print(f"Task status: {status_data['status']}")
    
    if status_data['status'] == 'completed':
        print("\nResult:")
        print(json.dumps(status_data['result'], indent=2))
        break
    elif status_data['status'] == 'failed':
        print(f"Task failed: {status_data.get('error', 'Unknown error')}")
        break
        
    import time
    time.sleep(2)  # Wait 2 seconds before checking again
