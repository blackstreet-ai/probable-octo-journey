#!/usr/bin/env python
"""
Direct test script for the AssetGenerator utility.

This script directly tests the AssetGenerator utility for both image and audio generation
to identify any issues with the asset generation process.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
import uuid

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('test_asset_generator')

# Load environment variables
load_dotenv()

# Import the AssetGenerator
from tools.asset_generator import AssetGenerator

def test_asset_generator():
    """Test the AssetGenerator utility directly."""
    # Create a test directory
    test_dir = Path("./test_assets")
    test_dir.mkdir(exist_ok=True)
    
    # Create asset directories
    asset_dirs = AssetGenerator.ensure_asset_directories(str(test_dir))
    
    # Print configuration
    logger.info(f"Using output directory: {test_dir}")
    logger.info(f"Asset directories: {asset_dirs}")
    logger.info(f"OpenAI API Key present: {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")
    logger.info(f"ElevenLabs API Key present: {'Yes' if os.environ.get('ELEVENLABS_API_KEY') else 'No'}")
    
    # Test image generation
    try:
        logger.info("Testing image generation...")
        prompt = "A beautiful landscape with renewable energy sources like solar panels and wind turbines"
        image_filename = f"{uuid.uuid4()}.png"
        image_path = os.path.join(asset_dirs['images'], image_filename)
        generated_image = AssetGenerator.generate_image_from_dalle(prompt, image_path)
        logger.info(f"Successfully generated image: {generated_image}")
    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}", exc_info=True)
    
    # Test audio generation
    try:
        logger.info("Testing audio generation...")
        text = "This is a test of the audio generation functionality using ElevenLabs."
        voice_id = os.environ.get("DEFAULT_VOICE_ID")
        if not voice_id:
            logger.warning("No DEFAULT_VOICE_ID found, using default voice from ElevenLabs")
            # Use a default voice ID from ElevenLabs if none is provided
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default voice ID
        
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_path = os.path.join(asset_dirs['audio'], audio_filename)
        generated_audio = AssetGenerator.generate_audio_from_elevenlabs(text, audio_path, voice_id)
        logger.info(f"Successfully generated audio: {generated_audio}")
    except Exception as e:
        logger.error(f"Audio generation failed: {str(e)}", exc_info=True)
    
    # Test placeholder generation
    try:
        logger.info("Testing placeholder generation...")
        placeholder_image_filename = f"placeholder_{uuid.uuid4()}.png"
        placeholder_image_path = os.path.join(asset_dirs['images'], placeholder_image_filename)
        placeholder_image = AssetGenerator.create_placeholder_image("Test Placeholder Image", placeholder_image_path)
        logger.info(f"Successfully generated placeholder image: {placeholder_image}")
        
        placeholder_audio_filename = f"placeholder_{uuid.uuid4()}.mp3"
        placeholder_audio_path = os.path.join(asset_dirs['audio'], placeholder_audio_filename)
        placeholder_audio = AssetGenerator.create_placeholder_audio(placeholder_audio_path, 3.5)  # 3.5 seconds
        logger.info(f"Successfully generated placeholder audio: {placeholder_audio}")
    except Exception as e:
        logger.error(f"Placeholder generation failed: {str(e)}", exc_info=True)
    
    logger.info("Asset generator test completed")

if __name__ == "__main__":
    test_asset_generator()
