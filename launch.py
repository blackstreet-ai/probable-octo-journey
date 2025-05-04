#!/usr/bin/env python
"""
CLI entrypoint for the AI Video Automation Pipeline.

This module provides a command-line interface for running the
AI Video Automation Pipeline.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from pipeline import create_video_from_topic
from config import validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('launch')


async def main():
    """
    Main entry point for the CLI.
    
    Parses command-line arguments, validates configuration, and runs the video creation pipeline.
    Handles errors and provides appropriate feedback to the user.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description='AI Video Automation Pipeline',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--topic', '-t',
        required=True,
        help='Topic or idea for the video'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        help='Directory to save output files'
    )
    
    parser.add_argument(
        '--publish', '-p',
        action='store_true',
        help='Publish the video to YouTube after creation'
    )
    
    parser.add_argument(
        '--notify', '-n',
        action='store_true',
        help='Send notifications about the process'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate configuration
    logger.info("Validating configuration...")
    if not validate_config():
        logger.error("Invalid configuration. Please check your .env file and ensure all required values are set.")
        print("\nError: Configuration validation failed. Please check the logs for details.")
        return 1
    logger.info("Configuration validated successfully")
    
    try:
        # Run the pipeline
        logger.info(f"Starting video creation pipeline for topic: '{args.topic}'")
        logger.info(f"Options: output_dir={args.output_dir}, publish={args.publish}, notify={args.notify}")
        
        result = await create_video_from_topic(
            topic=args.topic,
            output_dir=args.output_dir,
            publish=args.publish,
            notify=args.notify
        )
        
        # Print summary
        output_path = Path(result['output_dir'])
        video_path = output_path / 'video' / 'final_video.mp4'
        
        print("\n" + "=" * 50)
        print(f"Video creation completed successfully!")
        print(f"Job ID: {result['job_id']}")
        print(f"Output directory: {output_path}")
        
        if video_path.exists():
            print(f"Video file: {video_path}")
        
        if args.publish and 'youtube_url' in result:
            print(f"YouTube URL: {result['youtube_url']}")
        
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        print("Check the logs for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
