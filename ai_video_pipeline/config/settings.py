"""
Configuration settings for the AI Video Pipeline.

This module loads environment variables and provides configuration settings
for the various components of the pipeline.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class Settings:
    """
    Settings class for the AI Video Pipeline.
    
    This class provides access to configuration settings and API keys
    for the various components of the pipeline.
    """
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # Project paths
        self.base_dir = Path(__file__).parent.parent.parent
        self.assets_dir = self.base_dir / "assets"
        self.audio_dir = self.assets_dir / "audio"
        self.images_dir = self.assets_dir / "images"
        self.video_dir = self.assets_dir / "video"
        
        # Ensure asset directories exist
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        
        # API keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "")
        self.falai_api_key = os.getenv("FALAI_API_KEY", "")
        
        # Default settings
        self.default_voice_id = os.getenv("DEFAULT_VOICE_ID", "default")
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-4")
    
    def validate(self) -> bool:
        """
        Validate that all required settings are present.
        
        Returns:
            bool: True if all required settings are present, False otherwise
        """
        # For the initial implementation, we'll just check if the OpenAI API key is set
        return bool(self.openai_api_key)
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dict[str, Any]: Configuration for the agent
        """
        # This is a stub implementation that will be expanded in future sprints
        return {
            "model": self.default_model,
            "temperature": 0.7,
            "max_tokens": 4000,
        }


# Create a singleton instance
settings = Settings()
