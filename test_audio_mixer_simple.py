"""
Simple Audio-Mixer Test Script

This script tests the Audio-Mixer agent with a simple approach that doesn't
rely on the placeholder files created by the Music-Selector agent.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
import tempfile
import subprocess
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the Audio-Mixer agent
from ai_video_pipeline.agents.audio_mixer import AudioMixerAgent, MixParams


def create_test_audio_files():
    """Create test audio files using ffmpeg."""
    # Create directories
    assets_dir = Path(os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        "assets",
        "audio",
        "test"
    )))
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a test voice file (sine wave at 440 Hz)
    voice_file = assets_dir / "test_voice.wav"
    voice_cmd = [
        "ffmpeg", "-y", "-f", "lavfi", 
        "-i", "sine=frequency=440:duration=5", 
        "-ar", "44100", "-ac", "1",
        str(voice_file)
    ]
    
    # Create a test music file (sine wave at 220 Hz)
    music_file = assets_dir / "test_music.wav"
    music_cmd = [
        "ffmpeg", "-y", "-f", "lavfi", 
        "-i", "sine=frequency=220:duration=10", 
        "-ar", "44100", "-ac", "2",
        str(music_file)
    ]
    
    logger.info("Creating test voice file...")
    subprocess.run(voice_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    logger.info("Creating test music file...")
    subprocess.run(music_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    return str(voice_file), str(music_file)


async def test_audio_mixer():
    """Test the Audio-Mixer agent with test audio files."""
    logger.info("Testing Audio-Mixer agent...")
    
    # Create an instance of the Audio-Mixer agent
    agent = AudioMixerAgent()
    
    # Check if ffmpeg is available
    if not agent.ffmpeg_available:
        logger.error("ffmpeg is not available. Cannot run the test.")
        return False
    
    # Create test audio files
    try:
        voice_file, music_file = create_test_audio_files()
    except Exception as e:
        logger.error(f"Error creating test audio files: {e}")
        return False
    
    logger.info(f"Using voice file: {voice_file}")
    logger.info(f"Using music file: {music_file}")
    
    # Create output directory if it doesn't exist
    output_dir = Path(os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        "assets",
        "audio",
        "mixed"
    )))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test 1: Default mix parameters
    logger.info("Test 1: Mixing with default parameters...")
    params = MixParams(
        voice_file=voice_file,
        music_file=music_file,
        output_file=str(output_dir / "mixed_default.wav")
    )
    
    result = await agent.mix_audio(params)
    logger.info(f"Mix completed: {result.output_file}")
    logger.info(f"Duration: {result.duration_seconds:.2f} seconds")
    logger.info(f"Loudness: {result.loudness_lufs:.2f} LUFS")
    logger.info("---")
    
    # Test 2: More aggressive ducking
    logger.info("Test 2: Mixing with more aggressive ducking...")
    params = MixParams(
        voice_file=voice_file,
        music_file=music_file,
        output_file=str(output_dir / "mixed_aggressive_ducking.wav"),
        duck_percent=80.0,  # More aggressive ducking
        duck_attack_ms=100,  # Faster attack
        duck_release_ms=300  # Faster release
    )
    
    result = await agent.mix_audio(params)
    logger.info(f"Mix completed: {result.output_file}")
    logger.info(f"Duration: {result.duration_seconds:.2f} seconds")
    logger.info(f"Loudness: {result.loudness_lufs:.2f} LUFS")
    logger.info("---")
    
    # Test 3: Different loudness target
    logger.info("Test 3: Mixing with different loudness target...")
    params = MixParams(
        voice_file=voice_file,
        music_file=music_file,
        output_file=str(output_dir / "mixed_louder.wav"),
        target_lufs=-12.0,  # Louder than default
        voice_gain_db=2.0,   # Boost voice
        music_gain_db=-8.0   # Reduce music
    )
    
    result = await agent.mix_audio(params)
    logger.info(f"Mix completed: {result.output_file}")
    logger.info(f"Duration: {result.duration_seconds:.2f} seconds")
    logger.info(f"Loudness: {result.loudness_lufs:.2f} LUFS")
    
    logger.info("Audio-Mixer agent test completed successfully!")
    return True


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    try:
        # Run the async test function
        asyncio.run(test_audio_mixer())
        print("\nTest completed successfully!")
        print("You can listen to the mixed audio files in the assets/audio/mixed directory.")
    except Exception as e:
        logger.error(f"Error testing Audio-Mixer agent: {e}", exc_info=True)
        sys.exit(1)
