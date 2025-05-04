#!/usr/bin/env python
"""
Mock implementation of the ElevenLabs API for testing.

This module provides mock classes and functions to simulate the ElevenLabs API
responses without making actual API calls during testing.
"""

from typing import Dict, Any, Optional, List, Union
import json
import base64
from pathlib import Path


class MockElevenLabsResponse:
    """Mock response object for ElevenLabs API requests."""

    def __init__(
        self, 
        status_code: int = 200, 
        content: bytes = b'', 
        json_data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a mock response.

        Args:
            status_code: HTTP status code
            content: Response content as bytes
            json_data: JSON response data
        """
        self.status_code = status_code
        self._content = content
        self._json_data = json_data or {}

    @property
    def content(self) -> bytes:
        """Get response content."""
        return self._content

    def json(self) -> Dict[str, Any]:
        """Get JSON response data."""
        return self._json_data


class MockElevenLabs:
    """Mock implementation of the ElevenLabs API."""

    def __init__(self, valid_api_key: str = "valid-eleven-api-key"):
        """
        Initialize the mock ElevenLabs API.

        Args:
            valid_api_key: API key that will be considered valid
        """
        self.valid_api_key = valid_api_key
        self.voices = self._get_default_voices()
        self.user_subscription = self._get_default_subscription()
        
        # Store history of requests for verification in tests
        self.request_history = []

    def _get_default_voices(self) -> List[Dict[str, Any]]:
        """Get default list of mock voices."""
        return [
            {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Rachel",
                "category": "premade",
                "description": "A professional female voice with a smooth and clear delivery.",
                "preview_url": "https://api.elevenlabs.io/v1/voices/21m00Tcm4TlvDq8ikWAM/preview"
            },
            {
                "voice_id": "AZnzlk1XvdvUeBnXmlld",
                "name": "Domi",
                "category": "premade",
                "description": "A professional male voice with a warm and engaging tone.",
                "preview_url": "https://api.elevenlabs.io/v1/voices/AZnzlk1XvdvUeBnXmlld/preview"
            },
            {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",
                "name": "Bella",
                "category": "premade",
                "description": "A professional female voice with an expressive and dynamic style.",
                "preview_url": "https://api.elevenlabs.io/v1/voices/EXAVITQu4vr4xnSDxMaL/preview"
            }
        ]

    def _get_default_subscription(self) -> Dict[str, Any]:
        """Get default mock subscription data."""
        return {
            "status": "active",
            "tier": "pro",
            "character_count": 500000,
            "character_limit": 1000000,
            "next_character_count_reset_unix": 1714521600,  # Example timestamp
            "voice_limit": 10,
            "can_extend_character_limit": True
        }

    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate the API key.

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        return api_key == self.valid_api_key

    def get_voices(self, api_key: str) -> MockElevenLabsResponse:
        """
        Mock the GET /v1/voices endpoint.

        Args:
            api_key: API key for authentication

        Returns:
            Mock response with voices data
        """
        self.request_history.append({"endpoint": "get_voices", "api_key": api_key})
        
        if not self._validate_api_key(api_key):
            return MockElevenLabsResponse(
                status_code=401,
                json_data={"detail": "Invalid API key"}
            )
        
        return MockElevenLabsResponse(
            status_code=200,
            json_data={"voices": self.voices}
        )

    def get_user_subscription(self, api_key: str) -> MockElevenLabsResponse:
        """
        Mock the GET /v1/user/subscription endpoint.

        Args:
            api_key: API key for authentication

        Returns:
            Mock response with subscription data
        """
        self.request_history.append({"endpoint": "get_user_subscription", "api_key": api_key})
        
        if not self._validate_api_key(api_key):
            return MockElevenLabsResponse(
                status_code=401,
                json_data={"detail": "Invalid API key"}
            )
        
        return MockElevenLabsResponse(
            status_code=200,
            json_data={"subscription": self.user_subscription}
        )

    def text_to_speech(
        self, 
        api_key: str, 
        voice_id: str, 
        text: str, 
        model_id: str = "eleven_monolingual_v1"
    ) -> MockElevenLabsResponse:
        """
        Mock the POST /v1/text-to-speech/{voice_id} endpoint.

        Args:
            api_key: API key for authentication
            voice_id: ID of the voice to use
            text: Text to convert to speech
            model_id: ID of the model to use

        Returns:
            Mock response with audio content
        """
        self.request_history.append({
            "endpoint": "text_to_speech",
            "api_key": api_key,
            "voice_id": voice_id,
            "text": text,
            "model_id": model_id
        })
        
        if not self._validate_api_key(api_key):
            return MockElevenLabsResponse(
                status_code=401,
                json_data={"detail": "Invalid API key"}
            )
        
        # Check if voice_id exists
        voice_exists = any(voice["voice_id"] == voice_id for voice in self.voices)
        if not voice_exists:
            return MockElevenLabsResponse(
                status_code=404,
                json_data={"detail": f"Voice {voice_id} not found"}
            )
        
        # Generate mock audio data - just a placeholder
        # In a real implementation, you might want to use a small static audio file
        mock_audio = b'MOCK_AUDIO_DATA_' + text[:20].encode('utf-8')
        
        return MockElevenLabsResponse(
            status_code=200,
            content=mock_audio
        )


# Helper function to patch requests.post for ElevenLabs API calls
def mock_elevenlabs_post(url: str, **kwargs) -> MockElevenLabsResponse:
    """
    Mock function for requests.post calls to ElevenLabs API.

    Args:
        url: URL being called
        **kwargs: Additional arguments passed to requests.post

    Returns:
        Mock response
    """
    mock_api = MockElevenLabs()
    headers = kwargs.get('headers', {})
    api_key = headers.get('xi-api-key', '')
    
    if "text-to-speech" in url:
        # Extract voice_id from URL
        voice_id = url.split('/')[-1]
        json_data = kwargs.get('json', {})
        text = json_data.get('text', '')
        model_id = json_data.get('model_id', 'eleven_monolingual_v1')
        
        return mock_api.text_to_speech(api_key, voice_id, text, model_id)
    
    return MockElevenLabsResponse(
        status_code=404,
        json_data={"detail": "Endpoint not mocked"}
    )


# Helper function to patch requests.get for ElevenLabs API calls
def mock_elevenlabs_get(url: str, **kwargs) -> MockElevenLabsResponse:
    """
    Mock function for requests.get calls to ElevenLabs API.

    Args:
        url: URL being called
        **kwargs: Additional arguments passed to requests.get

    Returns:
        Mock response
    """
    mock_api = MockElevenLabs()
    headers = kwargs.get('headers', {})
    api_key = headers.get('xi-api-key', '')
    
    if "/v1/voices" in url:
        return mock_api.get_voices(api_key)
    elif "/v1/user/subscription" in url:
        return mock_api.get_user_subscription(api_key)
    
    return MockElevenLabsResponse(
        status_code=404,
        json_data={"detail": "Endpoint not mocked"}
    )
