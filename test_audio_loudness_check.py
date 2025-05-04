#!/usr/bin/env python3
"""
Test script for the audio loudness check CI tool.

This script demonstrates how to use the audio loudness check script
to verify that mixed audio files meet the -14 LUFS standard.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function."""
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the audio loudness check script
    check_script = os.path.join(project_root, "ci", "check_audio_loudness.py")
    
    # Path to the mixed audio directory
    mixed_dir = os.path.join(project_root, "assets", "audio", "mixed")
    
    # Check if the mixed audio directory exists
    if not os.path.isdir(mixed_dir):
        logger.error(f"Mixed audio directory does not exist: {mixed_dir}")
        return 1
    
    # Check if there are any audio files in the mixed directory
    audio_files = list(Path(mixed_dir).glob("*.wav")) + list(Path(mixed_dir).glob("*.mp3"))
    
    if not audio_files:
        logger.error(f"No audio files found in {mixed_dir}")
        return 1
    
    logger.info(f"Found {len(audio_files)} audio files in {mixed_dir}")
    
    # Check each audio file individually
    for audio_file in audio_files:
        logger.info(f"Checking {audio_file}...")
        
        # Run the check script on the audio file
        cmd = [
            "python3", check_script,
            "--file", str(audio_file),
            "--target", "-14.0",
            "--tolerance", "1.0"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"PASS: {result.stdout.strip()}")
            else:
                logger.warning(f"FAIL: {result.stdout.strip()}")
                
        except Exception as e:
            logger.error(f"Error checking {audio_file}: {e}")
    
    # Now check the entire directory
    logger.info(f"\nChecking entire directory: {mixed_dir}...")
    
    cmd = [
        "python3", check_script,
        "--directory", mixed_dir,
        "--target", "-14.0",
        "--tolerance", "1.0"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Directory check PASSED:\n{result.stdout.strip()}")
        else:
            logger.warning(f"Directory check FAILED:\n{result.stdout.strip()}")
            
    except Exception as e:
        logger.error(f"Error checking directory {mixed_dir}: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
