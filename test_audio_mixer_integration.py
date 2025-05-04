"""
Audio-Mixer Integration Test Script

This script tests the Audio-Mixer agent by mixing voice and music tracks
with ducking and loudness normalization.
"""

import os
import sys
import logging
import asyncio
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

# Import the Audio-Mixer agent
from ai_video_pipeline.agents.audio_mixer import AudioMixerAgent, MixParams


async def test_audio_mixer():
    """Test the Audio-Mixer agent with real audio files."""
    logger.info("Testing Audio-Mixer agent...")
    
    # Create an instance of the Audio-Mixer agent
    agent = AudioMixerAgent()
    
    # Check if ffmpeg is available
    if not agent.ffmpeg_available:
        logger.error("ffmpeg is not available. Cannot run the test.")
        return False
    
    # Find the most recent voice file in the assets/audio directory
    voice_dir = Path(os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        "assets",
        "audio"
    )))
    
    # Find the most recent music file in the assets/audio/music directory
    music_dir = Path(os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        "assets",
        "audio",
        "music"
    )))
    
    # Get the most recent voice file (mp3 or wav)
    voice_files = list(voice_dir.glob("*.mp3")) + list(voice_dir.glob("*.wav"))
    voice_files = [f for f in voice_files if f.is_file() and not str(f).endswith(".placeholder")]
    
    if not voice_files:
        logger.error("No voice files found in assets/audio directory.")
        return False
    
    voice_file = str(max(voice_files, key=os.path.getmtime))
    logger.info(f"Using voice file: {voice_file}")
    
    # Get the most recent music file (mp3 or wav)
    music_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    music_files = [f for f in music_files if f.is_file() and not str(f).endswith(".placeholder")]
    
    if not music_files:
        logger.error("No music files found in assets/audio/music directory.")
        return False
    
    music_file = str(max(music_files, key=os.path.getmtime))
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
