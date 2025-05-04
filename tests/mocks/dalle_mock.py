#!/usr/bin/env python
"""
Mock implementation of the OpenAI DALL-E API for testing.

This module provides mock classes and functions to simulate the DALL-E API
responses without making actual API calls during testing.
"""

from typing import Dict, Any, Optional, List, Union
import json
import base64
from pathlib import Path
import hashlib


class MockDalleImage:
    """Mock image object returned by DALL-E API."""

    def __init__(self, b64_json: Optional[str] = None, url: Optional[str] = None):
        """
        Initialize a mock DALL-E image.

        Args:
            b64_json: Base64-encoded image data
            url: URL to the generated image
        """
        self.b64_json = b64_json
        self.url = url
        self.revised_prompt = None


class MockDalleResponse:
    """Mock response object for DALL-E API requests."""

    def __init__(
        self, 
        created: int = 1714521600,
        data: Optional[List[MockDalleImage]] = None
    ):
        """
        Initialize a mock DALL-E response.

        Args:
            created: Unix timestamp for when the response was created
            data: List of image data objects
        """
        self.created = created
        self.data = data or []


class MockDalle:
    """Mock implementation of the OpenAI DALL-E API."""

    def __init__(self, valid_api_key: str = "sk-valid-openai-key"):
        """
        Initialize the mock DALL-E API.

        Args:
            valid_api_key: API key that will be considered valid
        """
        self.valid_api_key = valid_api_key
        
        # Store history of requests for verification in tests
        self.request_history = []
        
        # Default mock image data (a small 1x1 transparent PNG)
        self.default_b64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate the API key.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        return api_key == self.valid_api_key or api_key.startswith("sk-")

    def _generate_deterministic_image(self, prompt: str) -> str:
        """
        Generate a deterministic base64 image based on the prompt.
        
        This ensures that the same prompt always generates the same "image"
        which is useful for testing.

        Args:
            prompt: The prompt to generate an image for

        Returns:
            Base64-encoded image data
        """
        # Use the prompt to seed a deterministic "image"
        # In a real implementation, you might want to use a small static image file
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        return self.default_b64_image + prompt_hash[:8]

    def generate(
        self,
        api_key: str,
        prompt: str,
        model: str = "dall-e-3",
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard",
        response_format: str = "b64_json"
    ) -> MockDalleResponse:
        """
        Mock the OpenAI Images.generate endpoint.

        Args:
            api_key: API key for authentication
            prompt: Text prompt to generate image from
            model: Model to use (dall-e-2 or dall-e-3)
            n: Number of images to generate
            size: Size of the generated images
            quality: Quality of the generated images
            response_format: Format of the response (url or b64_json)

        Returns:
            Mock response with image data
        """
        self.request_history.append({
            "endpoint": "images.generate",
            "api_key": api_key,
            "prompt": prompt,
            "model": model,
            "n": n,
            "size": size,
            "quality": quality,
            "response_format": response_format
        })
        
        if not self._validate_api_key(api_key):
            raise ValueError("Invalid API key")
        
        # Generate mock images
        images = []
        for _ in range(n):
            image = MockDalleImage()
            
            if response_format == "b64_json":
                image.b64_json = self._generate_deterministic_image(prompt)
            else:  # url
                image.url = f"https://mock-dalle-api.example.com/images/{hashlib.md5(prompt.encode('utf-8')).hexdigest()}.png"
            
            images.append(image)
        
        return MockDalleResponse(
            created=1714521600,  # Example timestamp
            data=images
        )


# Helper function to create a mock OpenAI client with DALL-E functionality
def create_mock_openai_client():
    """
    Create a mock OpenAI client with DALL-E functionality.

    Returns:
        Mock OpenAI client object
    """
    mock_dalle = MockDalle()
    
    class MockOpenAIClient:
        """Mock OpenAI client with DALL-E functionality."""
        
        def __init__(self):
            """Initialize the mock OpenAI client."""
            self.images = self.MockImagesClient(mock_dalle)
        
        class MockImagesClient:
            """Mock images client for DALL-E API."""
            
            def __init__(self, dalle_mock):
                """
                Initialize the mock images client.
                
                Args:
                    dalle_mock: The MockDalle instance to use
                """
                self.dalle_mock = dalle_mock
            
            def generate(self, **kwargs):
                """
                Mock the images.generate method.
                
                Args:
                    **kwargs: Arguments for image generation
                
                Returns:
                    Mock DALL-E response
                """
                return self.dalle_mock.generate(
                    api_key="sk-mock-key",  # Not used in this context
                    prompt=kwargs.get("prompt", ""),
                    model=kwargs.get("model", "dall-e-3"),
                    n=kwargs.get("n", 1),
                    size=kwargs.get("size", "1024x1024"),
                    quality=kwargs.get("quality", "standard"),
                    response_format=kwargs.get("response_format", "b64_json")
                )
    
    return MockOpenAIClient()
