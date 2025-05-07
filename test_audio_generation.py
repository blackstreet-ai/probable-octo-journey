#!/usr/bin/env python
"""
Test script for audio asset generation in the AI Video Automation Pipeline.

This script tests the audio generation functionality by running a simplified version
of the pipeline that focuses specifically on the audio asset generation process.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from agents.voiceover import VoiceoverAgent
from tools.asset_generator import AssetGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("audio_generation_test")


async def test_audio_generation():
    """Test the audio generation functionality."""
    logger.info("Starting audio generation test")
    
    # Create a test job ID
    job_id = "test_audio"
    
    # Create output directory
    output_dir = Path(__file__).parent / "assets" / f"job_{job_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create asset directories
    asset_dirs = AssetGenerator.ensure_asset_directories(str(output_dir))
    
    # Create a sample script with narration
    script = """
    # Video Script: The Future of AI
    
    ## Scene 1
    NARRATION: Artificial intelligence has evolved rapidly over the past decade.
    VISUAL: A timeline showing the evolution of AI from simple algorithms to complex neural networks.
    
    ## Scene 2
    NARRATION: Today, AI powers everything from smartphones to autonomous vehicles.
    VISUAL: A split screen showing various AI applications in daily life.
    
    ## Scene 3
    NARRATION: But what does the future hold for this transformative technology?
    VISUAL: A futuristic cityscape with integrated AI systems visible throughout.
    """
    
    # Create a test context
    context = {
        "job_id": job_id,
        "output_dir": str(output_dir),
        "script": script
    }
    
    # Create a manifest file
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({
            "job_id": job_id,
            "status": "in_progress",
            "script": script
        }, f, indent=2)
    
    try:
        # Test direct audio generation using AssetGenerator
        logger.info("Testing direct audio generation with AssetGenerator...")
        
        # Get available voices
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))
            voices = client.voices.get_all()
            voice_id = voices.voices[0].voice_id if voices.voices else None
            logger.info(f"Using voice ID: {voice_id}")
        except Exception as e:
            logger.warning(f"Could not fetch available voices: {str(e)}")
            logger.warning("Using default voice ID from environment variable")
            voice_id = os.environ.get("DEFAULT_VOICE_ID")
        
        if not voice_id:
            logger.error("No voice ID available. Please set DEFAULT_VOICE_ID in environment")
            return False
        
        # Generate audio for a single paragraph
        test_text = "This is a test of the audio generation system using ElevenLabs."
        audio_path = os.path.join(asset_dirs["audio"], "test_direct.mp3")
        
        direct_audio_path = AssetGenerator.generate_audio_from_elevenlabs(
            text=test_text,
            output_path=audio_path,
            voice_id=voice_id
        )
        
        logger.info(f"Direct audio generation result: {direct_audio_path}")
        assert os.path.exists(direct_audio_path), f"Audio file does not exist: {direct_audio_path}"
        
        # Get audio duration
        duration = AssetGenerator.get_audio_duration(direct_audio_path)
        logger.info(f"Audio duration: {duration} seconds")
        
        # Initialize the VoiceoverAgent
        logger.info("Testing audio generation with VoiceoverAgent...")
        voiceover_agent = VoiceoverAgent()
        
        # Generate voiceover
        result = await voiceover_agent.synthesize_audio(context)
        
        # Log the results
        logger.info(f"Generated voiceover: {result['voiceover_path']}")
        logger.info(f"Voiceover duration: {result['voiceover_duration']} seconds")
        logger.info(f"Voiceover paragraphs: {result['voiceover_paragraphs']}")
        
        # Verify that the audio file exists
        assert os.path.exists(result["voiceover_path"]), f"Voiceover file does not exist: {result['voiceover_path']}"
        
        # Verify that the audio duration is reasonable
        assert result["voiceover_duration"] > 0, "Voiceover duration should be greater than 0"
        
        logger.info("Audio generation test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Audio generation test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_audio_generation())
    
    # Exit with appropriate status code
    sys.exit(0 if result else 1)
