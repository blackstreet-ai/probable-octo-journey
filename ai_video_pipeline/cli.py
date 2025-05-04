"""
Command-line interface for the AI Video Pipeline.

This module provides a command-line interface for running the video generation
pipeline with various options and configurations.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from ai_video_pipeline.main import run_pipeline
from ai_video_pipeline.config.settings import settings


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="AI Video Pipeline - Generate videos from text prompts"
    )
    
    # Required arguments
    parser.add_argument(
        "--topic", 
        type=str, 
        required=True,
        help="Topic for the video"
    )
    
    # Optional arguments
    parser.add_argument(
        "--title",
        type=str,
        help="Title for the video (default: auto-generated from topic)"
    )
    parser.add_argument(
        "--tone",
        type=str,
        default="informative",
        choices=["informative", "entertaining", "educational", "dramatic", "professional"],
        help="Tone for the video content"
    )
    parser.add_argument(
        "--runtime",
        type=int,
        default=60,
        help="Target runtime in seconds"
    )
    parser.add_argument(
        "--platform",
        type=str,
        default="YouTube",
        choices=["YouTube", "TikTok", "Instagram", "Twitter", "LinkedIn"],
        help="Target platform for the video"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for generated assets (default: ./assets)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def setup_environment(args: argparse.Namespace) -> None:
    """
    Set up the environment based on command-line arguments.
    
    Args:
        args: Parsed command-line arguments
    """
    # Set output directory if specified
    if args.output_dir:
        output_dir = Path(args.output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Update settings
        settings.assets_dir = output_dir
        settings.audio_dir = output_dir / "audio"
        settings.images_dir = output_dir / "images"
        settings.video_dir = output_dir / "video"
        
        # Ensure directories exist
        os.makedirs(settings.audio_dir, exist_ok=True)
        os.makedirs(settings.images_dir, exist_ok=True)
        os.makedirs(settings.video_dir, exist_ok=True)


async def main() -> int:
    """
    Main entry point for the command-line interface.
    
    Returns:
        int: Exit code
    """
    # Parse command-line arguments
    args = parse_args()
    
    # Set up the environment
    setup_environment(args)
    
    # Validate settings
    if not settings.validate():
        print("Error: Missing required API keys. Please check your .env file.")
        return 1
    
    try:
        # Run the pipeline
        result = await run_pipeline(args.topic)
        
        # Print the result
        if args.verbose:
            print(json.dumps(result, indent=2))
        else:
            print(f"Pipeline completed successfully.")
            print(f"Asset manifest: {result['asset_manifest']}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
