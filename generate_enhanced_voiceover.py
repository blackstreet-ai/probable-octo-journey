#!/usr/bin/env python
"""
Script for generating voiceover from enhanced narration script.

This script extracts narration from the enhanced script and generates voiceover audio
using the improved AssetGenerator with ElevenLabs voice handling.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('generate_enhanced_voiceover')

# Load environment variables
load_dotenv()

# Import the VoiceoverAgent and AssetGenerator
from agents.voiceover import VoiceoverAgent
from tools.asset_generator import AssetGenerator


async def generate_enhanced_voiceover(job_id: str) -> Dict[str, Any]:
    """
    Generate voiceover from enhanced narration script.
    
    Args:
        job_id: The ID of the job with the enhanced script
        
    Returns:
        Dict[str, Any]: Results of voiceover generation
    """
    # Set up job directory
    job_dir = Path(f"./assets/job_{job_id}")
    
    if not job_dir.exists():
        raise ValueError(f"Job directory not found: {job_dir}")
    
    # Load manifest
    manifest_path = job_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Manifest file not found: {manifest_path}")
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    
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
    
    # Extract narration from enhanced script
    logger.info("Extracting narration from enhanced script...")
    narration_paragraphs = voiceover_agent._extract_from_enhanced_script(enhanced_script)
    logger.info(f"Extracted {len(narration_paragraphs)} narration paragraphs")
    
    # Create asset directories
    asset_dirs = AssetGenerator.ensure_asset_directories(str(job_dir))
    logger.info(f"Asset directories: {asset_dirs}")
    
    # Get available voices from ElevenLabs
    try:
        available_voices = AssetGenerator.get_available_elevenlabs_voices()
        if available_voices:
            logger.info(f"Found {len(available_voices)} available voices:")
            for i, voice in enumerate(available_voices[:5]):  # Show first 5 voices
                logger.info(f"  {i+1}. {voice['name']} (ID: {voice['voice_id']})")
            
            # Use voice ID from environment or let the AssetGenerator pick the first available voice
            voice_id = os.environ.get("DEFAULT_VOICE_ID")
            if voice_id:
                # Verify that the voice ID exists in available voices
                voice_exists = any(v["voice_id"] == voice_id for v in available_voices)
                if not voice_exists:
                    logger.warning(f"Voice ID {voice_id} not found in available voices, using first available voice")
                    voice_id = available_voices[0]["voice_id"]
            else:
                voice_id = available_voices[0]["voice_id"]
                logger.info(f"Using first available voice: {available_voices[0]['name']} (ID: {voice_id})")
        else:
            logger.warning("No voices available from ElevenLabs, using placeholder audio")
            voice_id = None
    except Exception as e:
        logger.warning(f"Failed to get available voices: {str(e)}")
        voice_id = None
    
    # Generate audio for each paragraph
    audio_files = []
    for i, paragraph in enumerate(narration_paragraphs):
        try:
            # Skip empty paragraphs or section headers
            if not paragraph or paragraph.startswith("Section:"):
                continue
                
            # Generate a unique filename
            audio_filename = f"narration_{i+1:02d}.mp3"
            audio_path = os.path.join(asset_dirs['audio'], audio_filename)
            
            logger.info(f"Generating audio for paragraph {i+1}/{len(narration_paragraphs)}: {paragraph[:50]}...")
            generated_audio = AssetGenerator.generate_audio_from_elevenlabs(paragraph, audio_path, voice_id)
            audio_files.append(generated_audio)
            logger.info(f"Successfully generated audio: {generated_audio}")
            
            # Add a small delay to avoid rate limiting
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed to generate audio for paragraph {i+1}: {str(e)}")
            # Create a placeholder audio file instead
            placeholder_audio_path = os.path.join(asset_dirs['audio'], f"placeholder_{i+1:02d}.mp3")
            placeholder_audio = AssetGenerator.create_placeholder_audio(placeholder_audio_path, 3.0)
            audio_files.append(placeholder_audio)
    
    # Combine all audio files into a single voiceover file
    if audio_files:
        combined_audio_path = os.path.join(asset_dirs['audio'], "voiceover_combined.mp3")
        try:
            combined_audio = AssetGenerator.combine_audio_files(audio_files, combined_audio_path)
            logger.info(f"Combined {len(audio_files)} audio files into {combined_audio}")
        except Exception as e:
            logger.error(f"Failed to combine audio files: {str(e)}")
            combined_audio = audio_files[0] if audio_files else None
    else:
        combined_audio = None
    
    # Update manifest with voiceover information
    manifest["voiceover"] = {
        "audio_files": audio_files,
        "combined_audio": combined_audio,
        "completed_at": "2025-05-07T21:10:00.000"
    }
    
    # Save updated manifest
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    logger.info("Voiceover generation completed successfully!")
    
    return {
        "job_id": job_id,
        "audio_files": audio_files,
        "voiceover_path": combined_audio,
        "manifest": manifest
    }


async def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate voiceover from enhanced narration script',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--job-id', '-j',
        required=True,
        help='ID of the job with the enhanced script'
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
    
    try:
        # Generate voiceover
        result = await generate_enhanced_voiceover(args.job_id)
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"Voiceover generation completed successfully!")
        print(f"Job ID: {args.job_id}")
        
        if 'voiceover_path' in result:
            print(f"Combined voiceover: {result['voiceover_path']}")
            
        if 'audio_files' in result:
            print(f"Generated {len(result['audio_files'])} audio files")
            
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate voiceover: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        print("Check the logs for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
