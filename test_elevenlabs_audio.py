#!/usr/bin/env python
"""
Simple test script for ElevenLabs audio generation.

This script tests the ElevenLabs audio generation functionality directly
using the AssetGenerator utility.
"""

import logging
import os
import sys
from pathlib import Path

from tools.asset_generator import AssetGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("elevenlabs_test")


def test_elevenlabs_audio():
    """Test the ElevenLabs audio generation functionality."""
    logger.info("Starting ElevenLabs audio generation test")
    
    # Create a test job ID
    job_id = "test_elevenlabs"
    
    # Create output directory
    output_dir = Path(__file__).parent / "assets" / f"job_{job_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create asset directories
    asset_dirs = AssetGenerator.ensure_asset_directories(str(output_dir))
    
    try:
        # Get available voices
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))
            voices = client.voices.get_all()
            voice_id = voices.voices[0].voice_id if voices.voices else None
            logger.info(f"Found {len(voices.voices)} voices from ElevenLabs")
            logger.info(f"Using voice ID: {voice_id}")
        except Exception as e:
            logger.warning(f"Could not fetch available voices: {str(e)}")
            logger.warning("Using default voice ID from environment variable")
            voice_id = os.environ.get("DEFAULT_VOICE_ID")
        
        if not voice_id:
            logger.error("No voice ID available. Please set DEFAULT_VOICE_ID in environment")
            return False
        
        # Generate audio for a test paragraph
        test_text = "This is a test of the ElevenLabs audio generation system. We're verifying that audio assets can be properly generated."
        audio_path = os.path.join(asset_dirs["audio"], "test_elevenlabs.mp3")
        
        logger.info(f"Generating audio for text: '{test_text}'")
        audio_file = AssetGenerator.generate_audio_from_elevenlabs(
            text=test_text,
            output_path=audio_path,
            voice_id=voice_id
        )
        
        logger.info(f"Audio generated successfully: {audio_file}")
        
        # Get audio duration
        duration = AssetGenerator.get_audio_duration(audio_file)
        logger.info(f"Audio duration: {duration} seconds")
        
        # Verify that the audio file exists and has a reasonable duration
        if not os.path.exists(audio_file):
            logger.error(f"Audio file does not exist: {audio_file}")
            return False
        
        if duration <= 0:
            logger.error(f"Audio duration is not valid: {duration}")
            return False
        
        logger.info("ElevenLabs audio generation test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"ElevenLabs audio generation test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Run the test
    result = test_elevenlabs_audio()
    
    # Exit with appropriate status code
    sys.exit(0 if result else 1)
