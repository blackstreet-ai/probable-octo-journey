#!/usr/bin/env python
"""
Test the VoiceoverAgent with real ElevenLabs API integration.

This test verifies that the VoiceoverAgent can successfully connect to the
ElevenLabs API and generate voiceover audio.
"""

import os
import sys
import pytest
from pathlib import Path
import logging
from dotenv import load_dotenv

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file
load_dotenv()

from agents.voiceover import VoiceoverAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.integration
def test_voiceover_agent_real_api():
    """Test the VoiceoverAgent with real ElevenLabs API integration."""
    # Skip test if no API key is available
    if not os.environ.get("ELEVENLABS_API_KEY"):
        pytest.skip("ElevenLabs API key not available")
    
    # Initialize the agent
    agent = VoiceoverAgent()
    
    # Get available voices
    available_voices = agent._get_available_voices()
    assert len(available_voices) > 0, "No voices available from ElevenLabs API"
    
    # Use the first available voice
    voice_id = available_voices[0].voice_id
    logger.info(f"Using voice: {available_voices[0].name} ({voice_id})")
    
    # Test text to synthesize
    test_text = "This is a test of the ElevenLabs API integration. The quick brown fox jumps over the lazy dog."
    
    # Synthesize speech
    output_path = agent._synthesize_speech(
        text=test_text,
        voice_id=voice_id,
        stability=0.5,
        clarity=0.75,
        style=0.0
    )
    
    # Verify the output file exists and has content
    assert Path(output_path).exists(), f"Output file {output_path} does not exist"
    assert Path(output_path).stat().st_size > 0, f"Output file {output_path} is empty"
    
    logger.info(f"Successfully generated audio file: {output_path}")
    return output_path

if __name__ == "__main__":
    # Run the test directly if this script is executed
    output_path = test_voiceover_agent_real_api()
    print(f"Generated audio file: {output_path}")
