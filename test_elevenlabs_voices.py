#!/usr/bin/env python
"""
Test script for ElevenLabs voice handling.

This script tests the improved ElevenLabs voice handling in the AssetGenerator utility.
"""

import logging
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('test_elevenlabs_voices')

# Load environment variables
load_dotenv()

# Import the AssetGenerator
from tools.asset_generator import AssetGenerator


def test_elevenlabs_voices():
    """Test the ElevenLabs voice handling in the AssetGenerator utility."""
    # Create a test directory
    test_dir = Path("./test_assets")
    test_dir.mkdir(exist_ok=True)
    
    # Create asset directories
    asset_dirs = AssetGenerator.ensure_asset_directories(str(test_dir))
    
    # Print configuration
    logger.info(f"Using output directory: {test_dir}")
    logger.info(f"ElevenLabs API Key present: {'Yes' if os.environ.get('ELEVENLABS_API_KEY') else 'No'}")
    
    # Get available voices
    try:
        logger.info("Fetching available voices from ElevenLabs...")
        voices = AssetGenerator.get_available_elevenlabs_voices()
        
        if voices:
            logger.info(f"Found {len(voices)} available voices:")
            for i, voice in enumerate(voices):
                logger.info(f"  {i+1}. {voice['name']} (ID: {voice['voice_id']})")
                
            # Test audio generation with the first available voice
            voice_id = voices[0]["voice_id"]
            voice_name = voices[0]["name"]
            logger.info(f"Testing audio generation with voice: {voice_name} (ID: {voice_id})...")
            
            text = "This is a test of the ElevenLabs audio generation with automatic voice selection."
            audio_filename = f"test_voice_{uuid.uuid4()}.mp3"
            audio_path = os.path.join(asset_dirs['audio'], audio_filename)
            
            generated_audio = AssetGenerator.generate_audio_from_elevenlabs(text, audio_path, voice_id)
            logger.info(f"Successfully generated audio: {generated_audio}")
            
            # Test automatic voice selection
            logger.info("Testing audio generation with automatic voice selection...")
            text = "This is a test of the ElevenLabs audio generation with automatic voice selection."
            audio_filename = f"test_auto_voice_{uuid.uuid4()}.mp3"
            audio_path = os.path.join(asset_dirs['audio'], audio_filename)
            
            generated_audio = AssetGenerator.generate_audio_from_elevenlabs(text, audio_path)
            logger.info(f"Successfully generated audio with automatic voice selection: {generated_audio}")
            
        else:
            logger.warning("No voices available from ElevenLabs")
            
            # Test fallback to placeholder audio
            logger.info("Testing fallback to placeholder audio...")
            text = "This should create a placeholder audio file since no voices are available."
            audio_filename = f"test_placeholder_{uuid.uuid4()}.mp3"
            audio_path = os.path.join(asset_dirs['audio'], audio_filename)
            
            generated_audio = AssetGenerator.generate_audio_from_elevenlabs(text, audio_path)
            logger.info(f"Created placeholder audio: {generated_audio}")
            
    except Exception as e:
        logger.error(f"Error testing ElevenLabs voices: {str(e)}", exc_info=True)
    
    logger.info("ElevenLabs voice test completed")


if __name__ == "__main__":
    test_elevenlabs_voices()
