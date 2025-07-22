#!/usr/bin/env python3
"""
Test script for OpenAI-compatible API endpoints

Usage:
    python test_openai_api.py
"""

import requests
import json
import base64
from PIL import Image
from io import BytesIO


def test_openai_image_generation():
    """Test the OpenAI-compatible image generation endpoint"""
    
    # API endpoint (adjust URL as needed)
    url = "http://localhost:8000/v1/images/generations"
    
    # Test request payload
    payload = {
        "prompt": "A beautiful sunset over mountains, digital art",
        "n": 1,
        "size": "512x512",
        "response_format": "b64_json"
    }
    
    print("Testing OpenAI-compatible image generation...")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Generated {len(result['data'])} image(s)")
            print(f"Created timestamp: {result['created']}")
            
            # Save the generated image
            if result['data'] and result['data'][0].get('b64_json'):
                image_data = base64.b64decode(result['data'][0]['b64_json'])
                image = Image.open(BytesIO(image_data))
                image.save("generated_image.png")
                print("💾 Image saved as 'generated_image.png'")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_models_endpoint():
    """Test the models listing endpoint"""
    
    url = "http://localhost:8000/v1/models"
    
    print("\nTesting models endpoint...")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Models endpoint working!")
            print(f"Available models: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_health_endpoint():
    """Test the health check endpoint"""
    
    url = "http://localhost:8000/health"
    
    print("\nTesting health endpoint...")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Health endpoint working!")
            print(f"Status: {result}")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_legacy_endpoint():
    """Test the original /imagine endpoint"""
    
    url = "http://localhost:8000/imagine"
    params = {
        "prompt": "A cute cat playing with yarn",
        "img_size": 512
    }
    
    print("\nTesting legacy /imagine endpoint...")
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            print("✅ Legacy endpoint working!")
            print(f"Response content type: {response.headers.get('content-type')}")
            print(f"Response size: {len(response.content)} bytes")
            
            # Save the image
            with open("legacy_image.png", "wb") as f:
                f.write(response.content)
            print("💾 Image saved as 'legacy_image.png'")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Testing OpenAI-compatible API endpoints")
    print("=" * 50)
    
    # Test all endpoints
    test_health_endpoint()
    test_models_endpoint()
    test_legacy_endpoint()
    test_openai_image_generation()
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!")
    print("\nTo use with OpenAI client libraries, set your base URL to:")
    print("http://localhost:8000")
    print("\nExample with openai-python:")
    print("""
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000",
    api_key="dummy"  # Not used but required
)

response = client.images.generate(
    model="stable-diffusion-v1-5",
    prompt="A beautiful landscape",
    size="512x512",
    n=1
)
    """) 