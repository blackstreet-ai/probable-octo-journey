"""
Music-Selector Integration Test Script

This script tests the Music-Selector agent by selecting music tracks
with various parameters and displaying the results.
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

# Import the Music-Selector agent
from ai_video_pipeline.agents.music_selector import MusicSelectorAgent, MusicParams


async def test_music_selector():
    """Test the Music-Selector agent with various parameters."""
    logger.info("Testing Music-Selector agent...")
    
    # Create an instance of the Music-Selector agent
    agent = MusicSelectorAgent()
    
    # Test 1: Default parameters
    logger.info("Test 1: Selecting music with default parameters...")
    result = await agent.select_music()
    logger.info(f"Selected track: {result.track.title} by {result.track.artist}")
    logger.info(f"Genre: {result.track.genre}, Tags: {', '.join(result.track.tags)}")
    logger.info(f"File path: {result.track.file_path}")
    logger.info(f"Duration: {result.track.duration_seconds} seconds")
    logger.info(f"License: {result.track.license}")
    logger.info(f"Source: {result.track.source_url}")
    logger.info("---")
    
    # Test 2: Upbeat, energetic music
    logger.info("Test 2: Selecting upbeat, energetic music...")
    params = MusicParams(
        mood="happy",
        genre="pop",
        keywords=["upbeat", "energetic"],
        tempo=120
    )
    result = await agent.select_music(params)
    logger.info(f"Selected track: {result.track.title} by {result.track.artist}")
    logger.info(f"Genre: {result.track.genre}, Tags: {', '.join(result.track.tags)}")
    logger.info(f"File path: {result.track.file_path}")
    logger.info(f"Duration: {result.track.duration_seconds} seconds")
    logger.info(f"License: {result.track.license}")
    logger.info(f"Source: {result.track.source_url}")
    logger.info("---")
    
    # Test 3: Dramatic, orchestral music
    logger.info("Test 3: Selecting dramatic, orchestral music...")
    params = MusicParams(
        mood="dramatic",
        genre="orchestral",
        keywords=["epic", "trailer"],
        tempo=90
    )
    result = await agent.select_music(params)
    logger.info(f"Selected track: {result.track.title} by {result.track.artist}")
    logger.info(f"Genre: {result.track.genre}, Tags: {', '.join(result.track.tags)}")
    logger.info(f"File path: {result.track.file_path}")
    logger.info(f"Duration: {result.track.duration_seconds} seconds")
    logger.info(f"License: {result.track.license}")
    logger.info(f"Source: {result.track.source_url}")
    logger.info("---")
    
    # Test 4: Calm, ambient music
    logger.info("Test 4: Selecting calm, ambient music...")
    params = MusicParams(
        mood="calm",
        genre="ambient",
        keywords=["relaxing", "meditation"],
        duration=180.0
    )
    result = await agent.select_music(params)
    logger.info(f"Selected track: {result.track.title} by {result.track.artist}")
    logger.info(f"Genre: {result.track.genre}, Tags: {', '.join(result.track.tags)}")
    logger.info(f"File path: {result.track.file_path}")
    logger.info(f"Duration: {result.track.duration_seconds} seconds")
    logger.info(f"License: {result.track.license}")
    logger.info(f"Source: {result.track.source_url}")
    
    logger.info("Music-Selector agent test completed successfully!")
    return True


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    try:
        # Run the async test function
        asyncio.run(test_music_selector())
        print("\nTest completed successfully!")
        print("You can check the generated placeholder files in the assets/audio/music directory.")
    except Exception as e:
        logger.error(f"Error testing Music-Selector agent: {e}", exc_info=True)
        sys.exit(1)
