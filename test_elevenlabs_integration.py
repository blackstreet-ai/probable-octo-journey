"""
ElevenLabs Integration Test Script

This script tests the ElevenLabs API integration by generating a simple
voice clip using the real API.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the ElevenLabs API wrapper
from ai_video_pipeline.tools.elevenlabs import ElevenLabsAPI, VoiceSettings
from ai_video_pipeline.config.settings import settings


def test_elevenlabs_api():
    """Test the ElevenLabs API integration."""
    logger.info("Testing ElevenLabs API integration...")
    
    # Create an instance of the ElevenLabsAPI
    api = ElevenLabsAPI()
    
    # List available voices
    logger.info("Listing available voices...")
    voices = api.list_voices()
    logger.info(f"Found {len(voices.get('voices', []))} voices")
    
    # Get the default voice
    default_voice = api.get_default_voice()
    voice_id = default_voice.get("voice_id")
    voice_name = default_voice.get("name")
    logger.info(f"Using voice: {voice_name} (ID: {voice_id})")
    
    # Create voice settings
    voice_settings = VoiceSettings(
        stability=0.75,
        similarity_boost=0.75,
        use_speaker_boost=True
    )
    
    # Generate a test audio clip
    test_text = "Hello! This is a test of the ElevenLabs API integration. If you can hear this, the integration is working correctly."
    
    logger.info(f"Generating test audio with voice {voice_id}...")
    output_path = api.synthesize_speech(
        text=test_text,
        voice_id=voice_id,
        voice_settings=voice_settings
    )
    
    logger.info(f"Test audio generated successfully: {output_path}")
    logger.info("ElevenLabs API integration test completed successfully!")
    
    return output_path


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    try:
        output_path = test_elevenlabs_api()
        print(f"\nTest completed successfully! Audio file saved to: {output_path}")
        print("You can play this file to verify the voice synthesis is working correctly.")
    except Exception as e:
        logger.error(f"Error testing ElevenLabs API: {e}", exc_info=True)
        sys.exit(1)
