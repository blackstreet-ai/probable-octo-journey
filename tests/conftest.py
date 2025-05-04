#!/usr/bin/env python
"""
Pytest configuration file for the AI Video Automation Pipeline tests.

This module contains fixtures and configuration for pytest to use in all test files.
"""

import os
import pytest
from unittest.mock import patch
from pathlib import Path

from tests.mocks.elevenlabs_mock import mock_elevenlabs_get, mock_elevenlabs_post
from tests.mocks.dalle_mock import create_mock_openai_client


@pytest.fixture(autouse=True)
def mock_env_vars():
    """
    Mock environment variables for testing.
    
    This fixture is automatically used in all tests to provide mock API keys
    and other environment variables needed for testing.
    """
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'sk-test-openai-key',
        'ELEVENLABS_API_KEY': 'test-elevenlabs-key',
        'YOUTUBE_CLIENT_SECRETS_FILE': '/path/to/client_secrets.json',
        'YOUTUBE_CREDENTIALS_FILE': '/path/to/credentials.json',
        'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX',
        'SLACK_CHANNEL': '#test-channel'
    }):
        yield


@pytest.fixture
def mock_elevenlabs_api():
    """
    Mock the ElevenLabs API for testing.
    
    This fixture patches the requests module to intercept calls to the ElevenLabs API
    and return mock responses instead.
    """
    with patch('requests.get', side_effect=mock_elevenlabs_get), \
         patch('requests.post', side_effect=mock_elevenlabs_post):
        yield


@pytest.fixture
def mock_openai_client():
    """
    Mock the OpenAI client for testing.
    
    This fixture creates a mock OpenAI client with DALL-E functionality
    that can be used in tests instead of the real client.
    """
    return create_mock_openai_client()


@pytest.fixture
def mock_dalle_api():
    """
    Mock the DALL-E API for testing.
    
    This fixture patches the OpenAI client to intercept calls to the DALL-E API
    and return mock responses instead.
    """
    mock_client = create_mock_openai_client()
    with patch('openai.OpenAI', return_value=mock_client):
        yield mock_client


@pytest.fixture
def test_output_dir(tmp_path):
    """
    Create a temporary directory for test outputs.
    
    This fixture creates a temporary directory structure for test outputs
    that mimics the structure used in the real application.
    
    Args:
        tmp_path: Pytest fixture that provides a temporary directory

    Returns:
        Path to the test output directory
    """
    # Create directory structure
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(exist_ok=True)
    
    # Create subdirectories
    (output_dir / "scripts").mkdir(exist_ok=True)
    (output_dir / "audio").mkdir(exist_ok=True)
    (output_dir / "music").mkdir(exist_ok=True)
    (output_dir / "visuals").mkdir(exist_ok=True)
    (output_dir / "videos").mkdir(exist_ok=True)
    (output_dir / "reports").mkdir(exist_ok=True)
    
    return output_dir


@pytest.fixture
def sample_script():
    """
    Provide a sample script for testing.
    
    Returns:
        A sample video script in the format used by the application
    """
    return """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence. In this video, we'll examine how AI is poised to transform our world.

**VISUAL:** Show a montage of futuristic AI applications - smart cities, advanced robotics, and holographic interfaces.

## Scene 2: Current State of AI
**NARRATION:** Today's AI systems can already perform impressive tasks, from generating creative content to diagnosing diseases with remarkable accuracy.

**VISUAL:** Display split-screen examples of AI applications in healthcare, art, and business.

## Scene 3: Conclusion
**NARRATION:** The future of AI holds tremendous potential. By embracing responsible development, we can ensure these technologies benefit humanity.

**VISUAL:** End with an inspiring image of diverse people collaborating with AI tools to solve global challenges.

**CALL TO ACTION:** Subscribe to our channel for more insights on emerging technologies.
"""


@pytest.fixture
def sample_job_context(test_output_dir, sample_script):
    """
    Provide a sample job context for testing.
    
    This fixture creates a sample job context that can be used in tests
    to simulate a job being processed by the pipeline.
    
    Args:
        test_output_dir: Fixture that provides a temporary output directory
        sample_script: Fixture that provides a sample script

    Returns:
        A sample job context dictionary
    """
    job_id = "test_job_123"
    job_dir = test_output_dir / job_id
    job_dir.mkdir(exist_ok=True)
    
    return {
        "job_id": job_id,
        "topic": "The Future of AI",
        "audience": "technology enthusiasts",
        "tone": "informative and engaging",
        "output_dir": str(job_dir),
        "script": sample_script,
        "start_time": 1620000000,
        "manifest": {
            "job_id": job_id,
            "topic": "The Future of AI",
            "status": "in_progress",
            "steps": [
                {"name": "script_creation", "status": "completed"},
                {"name": "asset_generation", "status": "in_progress"},
                {"name": "video_assembly", "status": "pending"},
                {"name": "quality_control", "status": "pending"},
                {"name": "publishing", "status": "pending"}
            ]
        },
        "manifest_path": str(job_dir / "manifest.json")
    }
