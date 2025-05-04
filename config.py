#!/usr/bin/env python
"""
Configuration loader for the AI Video Automation Pipeline.

This module loads environment variables and configuration settings
for the AI Video Automation Pipeline.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
ROOT_DIR = Path(__file__).parent.absolute()
ASSETS_DIR = os.getenv('ASSETS_DIR', str(ROOT_DIR / 'assets'))
LOGS_DIR = os.getenv('LOGS_DIR', str(ROOT_DIR / 'logs'))

# Create directories if they don't exist
Path(ASSETS_DIR).mkdir(exist_ok=True)
Path(LOGS_DIR).mkdir(exist_ok=True)

# API Keys and credentials
API_KEYS = {
    'openai': os.getenv('OPENAI_API_KEY'),
    'elevenlabs': os.getenv('ELEVENLABS_API_KEY'),
    'fal_ai_key': os.getenv('FAL_AI_KEY'),
    'fal_ai_secret': os.getenv('FAL_AI_SECRET'),
}

# YouTube configuration
YOUTUBE_CONFIG = {
    'client_secrets_file': os.getenv('YOUTUBE_CLIENT_SECRETS_FILE'),
    'credentials_file': os.getenv('YOUTUBE_CREDENTIALS_FILE'),
}

# Slack configuration
SLACK_CONFIG = {
    'webhook_url': os.getenv('SLACK_WEBHOOK_URL'),
    'channel': os.getenv('SLACK_CHANNEL', '#ai-video-automation'),
}

# Observability configuration
OBSERVABILITY_CONFIG = {
    'enabled': os.getenv('OBSERVABILITY_ENABLED', 'true').lower() == 'true',
    'event_log_file': os.getenv('EVENT_LOG_FILE', str(ROOT_DIR / 'logs' / 'events.jsonl')),
}

# Agent configuration
AGENT_CONFIG = {
    'model': os.getenv('AGENT_MODEL', 'gpt-4-turbo'),
    'temperature': float(os.getenv('AGENT_TEMPERATURE', '0.7')),
    'max_tokens': int(os.getenv('AGENT_MAX_TOKENS', '4096')),
}

def get_config() -> Dict[str, Any]:
    """Get the complete configuration as a dictionary.
    
    Returns:
        Dict[str, Any]: The complete configuration.
    """
    return {
        'api_keys': API_KEYS,
        'youtube': YOUTUBE_CONFIG,
        'slack': SLACK_CONFIG,
        'observability': OBSERVABILITY_CONFIG,
        'agent': AGENT_CONFIG,
        'assets_dir': ASSETS_DIR,
        'logs_dir': LOGS_DIR,
    }

def validate_config() -> bool:
    """Validate that all required configuration is present.
    
    Returns:
        bool: True if the configuration is valid, False otherwise.
    """
    # Check for required API keys
    if not API_KEYS['openai']:
        print("ERROR: OPENAI_API_KEY is not set in .env file")
        return False
    
    # Add more validation as needed
    
    return True
