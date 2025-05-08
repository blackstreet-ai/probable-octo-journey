#!/usr/bin/env python
"""
Test script for extracting narration from enhanced script.

This script tests the extraction of narration elements from the enhanced script,
focusing on hooks, key points, transitions, etc. while ignoring visual descriptions.
"""

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('test_extract_narration')

# Load environment variables
load_dotenv()

# Import the VoiceoverAgent
from agents.voiceover import VoiceoverAgent


def test_extract_narration(job_id: str) -> None:
    """
    Test extracting narration from enhanced script.
    
    Args:
        job_id: The ID of the job with the enhanced script
    """
    # Set up job directory
    job_dir = Path(f"./assets/job_{job_id}")
    
    if not job_dir.exists():
        raise ValueError(f"Job directory not found: {job_dir}")
    
    # Load enhanced script
    script_dir = job_dir / "script"
    script_files = list(script_dir.glob("narration_script_enhanced*.md"))
    
    if not script_files:
        raise ValueError("No enhanced script file found in the job directory")
    
    # Use the latest enhanced script file
    script_file = sorted(script_files)[-1]
    
    with open(script_file, "r") as f:
        enhanced_script = f.read()
    
    logger.info(f"Loaded enhanced script from {script_file}")
    
    # Initialize the VoiceoverAgent
    voiceover_agent = VoiceoverAgent()
    
    # Test the narration extraction
    logger.info("Extracting narration from enhanced script...")
    narration_paragraphs = voiceover_agent._extract_from_enhanced_script(enhanced_script)
    
    # Print the extracted narration
    print("\n" + "=" * 80)
    print(f"EXTRACTED NARRATION FROM ENHANCED SCRIPT (Total: {len(narration_paragraphs)} paragraphs)")
    print("=" * 80)
    
    for i, paragraph in enumerate(narration_paragraphs):
        print(f"\n{i+1}. {paragraph}")
    
    print("\n" + "=" * 80)
    print("These paragraphs would be used for voiceover generation, ignoring visual descriptions.")
    print("=" * 80)


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test extracting narration from enhanced script',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--job-id', '-j',
        required=True,
        help='ID of the job with the enhanced script'
    )
    
    args = parser.parse_args()
    
    try:
        # Extract narration
        test_extract_narration(args.job_id)
        return 0
        
    except Exception as e:
        logger.error(f"Failed to extract narration: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        print("Check the logs for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
