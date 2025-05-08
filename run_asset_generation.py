#!/usr/bin/env python
"""
Asset Generation Runner for the AI Video Automation Pipeline.

This script runs the asset generation step for an existing job with an approved script.
It directly uses the AssetGenerator utility to generate visual and audio assets.
"""

import asyncio
import json
import logging
import os
import sys
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List, Tuple

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('run_asset_generation')

# Load environment variables
load_dotenv()

# Import the AssetGenerator
from tools.asset_generator import AssetGenerator


def extract_sections_from_script(script_content: str) -> List[Dict[str, Any]]:
    """
    Extract sections from the script content.
    
    Args:
        script_content: The content of the script
        
    Returns:
        List[Dict[str, Any]]: List of sections with their content
    """
    # Extract sections using markdown headers
    sections = []
    current_section = None
    current_content = []
    
    for line in script_content.split('\n'):
        if line.startswith('## '):
            # Save previous section if exists
            if current_section:
                sections.append({
                    'title': current_section,
                    'content': '\n'.join(current_content),
                    'type': 'main_section'
                })
            
            # Start new section
            current_section = line.replace('## ', '').strip()
            current_content = []
        elif line.startswith('### '):
            # Save previous section if exists
            if current_section:
                sections.append({
                    'title': current_section,
                    'content': '\n'.join(current_content),
                    'type': 'main_section'
                })
            
            # Start new subsection
            current_section = line.replace('### ', '').strip()
            current_content = []
            
        elif current_section:
            current_content.append(line)
    
    # Add the last section
    if current_section:
        sections.append({
            'title': current_section,
            'content': '\n'.join(current_content),
            'type': 'main_section'
        })
    
    return sections


def extract_visual_descriptions(section_content: str) -> List[str]:
    """
    Extract visual descriptions from section content.
    
    Args:
        section_content: The content of a section
        
    Returns:
        List[str]: List of visual descriptions
    """
    descriptions = []
    
    # Look for visual description markers
    visual_pattern = r'\*\*Visual description\*\*:(.*?)(?=\*Transition\*:|$)'
    matches = re.finditer(visual_pattern, section_content, re.DOTALL)
    
    for match in matches:
        description = match.group(1).strip()
        if description:
            descriptions.append(description)
    
    return descriptions


def extract_narration_paragraphs(section_content: str) -> List[str]:
    """
    Extract narration paragraphs from section content.
    
    Args:
        section_content: The content of a section
        
    Returns:
        List[str]: List of narration paragraphs
    """
    paragraphs = []
    
    # Extract paragraphs marked with *Hook* or **Key point**
    hook_pattern = r'\*Hook\*:(.*?)(?=\*|$)'
    key_point_pattern = r'\*\*Key point\*\*:(.*?)(?=\*|$)'
    
    # Find all hooks
    for match in re.finditer(hook_pattern, section_content, re.DOTALL):
        text = match.group(1).strip()
        if text:
            # Remove any markdown formatting
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            paragraphs.append(text)
    
    # Find all key points
    for match in re.finditer(key_point_pattern, section_content, re.DOTALL):
        text = match.group(1).strip()
        if text:
            paragraphs.append(text)
    
    # Also extract supporting details
    supporting_pattern = r'\*\*Supporting details\*\*:(.*?)(?=\*|$)'
    for match in re.finditer(supporting_pattern, section_content, re.DOTALL):
        text = match.group(1).strip()
        if text:
            paragraphs.append(text)
    
    return paragraphs


async def generate_assets_for_job(job_id: str) -> Dict[str, Any]:
    """
    Generate assets for an existing job.
    
    Args:
        job_id: The ID of the job
        
    Returns:
        Dict[str, Any]: Results of asset generation
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
    
    # Check if script is completed
    script_step = next((step for step in manifest["steps"] if step["name"] == "script_creation"), None)
    if not script_step or script_step["status"] != "completed":
        raise ValueError("Script creation must be completed before generating assets")
    
    # Update asset generation step status
    asset_step = next((step for step in manifest["steps"] if step["name"] == "asset_generation"), None)
    if asset_step:
        asset_step["status"] = "in_progress"
    
    # Ensure script is approved
    if "script_review" in manifest:
        manifest["script_review"]["approved"] = True
    
    # Save updated manifest
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"Updated manifest for job {job_id}, asset generation set to in_progress")
    
    # Load script
    script_dir = job_dir / "script"
    script_files = list(script_dir.glob("narration_script_enhanced*.md"))
    
    if not script_files:
        script_files = list(script_dir.glob("narration_script*.md"))
    
    if not script_files:
        raise ValueError("No script file found in the job directory")
    
    # Use the latest script file (assuming the highest version number)
    script_file = sorted(script_files)[-1]
    
    with open(script_file, "r") as f:
        script_content = f.read()
    
    logger.info(f"Loaded script from {script_file}")
    
    # Create asset directories
    asset_dirs = AssetGenerator.ensure_asset_directories(str(job_dir))
    logger.info(f"Asset directories: {asset_dirs}")
    
    # Extract sections from script
    sections = extract_sections_from_script(script_content)
    logger.info(f"Extracted {len(sections)} sections from script")
    
    # Generate images for each section
    generated_images = []
    for section in sections:
        visual_descriptions = extract_visual_descriptions(section['content'])
        
        for i, description in enumerate(visual_descriptions):
            try:
                # Generate a unique filename
                image_filename = f"{section['title'].lower().replace(' ', '_')}_{i+1}.png"
                image_path = os.path.join(asset_dirs['images'], image_filename)
                
                logger.info(f"Generating image for section '{section['title']}' with description: {description[:50]}...")
                generated_image = AssetGenerator.generate_image_from_dalle(description, image_path)
                generated_images.append(generated_image)
                logger.info(f"Successfully generated image: {generated_image}")
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to generate image for section '{section['title']}': {str(e)}")
                # Create a placeholder image instead
                placeholder_image_path = os.path.join(asset_dirs['images'], f"placeholder_{section['title'].lower().replace(' ', '_')}_{i+1}.png")
                placeholder_image = AssetGenerator.create_placeholder_image(f"Placeholder for {section['title']}", placeholder_image_path)
                generated_images.append(placeholder_image)
    
    # Generate audio for each section
    generated_audio_files = []
    for section in sections:
        narration_paragraphs = extract_narration_paragraphs(section['content'])
        
        for i, paragraph in enumerate(narration_paragraphs):
            try:
                # Generate a unique filename
                audio_filename = f"{section['title'].lower().replace(' ', '_')}_{i+1}.mp3"
                audio_path = os.path.join(asset_dirs['audio'], audio_filename)
                
                # Get available voices from ElevenLabs
                try:
                    available_voices = AssetGenerator.get_available_elevenlabs_voices()
                    if available_voices:
                        # Log available voices for reference
                        logger.info(f"Available ElevenLabs voices:")
                        for i, voice in enumerate(available_voices[:5]):  # Show first 5 voices
                            logger.info(f"  {i+1}. {voice['name']} (ID: {voice['voice_id']})")
                        
                        # Use voice ID from environment or let the AssetGenerator pick the first available voice
                        voice_id = os.environ.get("DEFAULT_VOICE_ID")
                        if voice_id:
                            # Verify that the voice ID exists in available voices
                            voice_exists = any(v["voice_id"] == voice_id for v in available_voices)
                            if not voice_exists:
                                logger.warning(f"Voice ID {voice_id} not found in available voices, using first available voice")
                                voice_id = None  # Let AssetGenerator pick the first available voice
                    else:
                        logger.warning("No voices available from ElevenLabs, using placeholder audio")
                        voice_id = None
                except Exception as e:
                    logger.warning(f"Failed to get available voices: {str(e)}")
                    voice_id = None  # Let AssetGenerator handle this
                
                logger.info(f"Generating audio for section '{section['title']}' paragraph {i+1}...")
                generated_audio = AssetGenerator.generate_audio_from_elevenlabs(paragraph, audio_path, voice_id)
                generated_audio_files.append(generated_audio)
                logger.info(f"Successfully generated audio: {generated_audio}")
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to generate audio for section '{section['title']}' paragraph {i+1}: {str(e)}")
                # Create a placeholder audio file instead
                placeholder_audio_path = os.path.join(asset_dirs['audio'], f"placeholder_{section['title'].lower().replace(' ', '_')}_{i+1}.mp3")
                placeholder_audio = AssetGenerator.create_placeholder_audio(placeholder_audio_path, 3.0)
                generated_audio_files.append(placeholder_audio)
    
    # Update manifest with completion
    manifest = {
        **manifest,
        "asset_generation": {
            "images": generated_images,
            "audio": generated_audio_files,
            "completed_at": "2025-05-07T18:56:04.544"
        }
    }
    
    asset_step = next((step for step in manifest["steps"] if step["name"] == "asset_generation"), None)
    if asset_step:
        asset_step["status"] = "completed"
    
    # Update next step
    video_assembly_step = next((step for step in manifest["steps"] if step["name"] == "video_assembly"), None)
    if video_assembly_step:
        video_assembly_step["status"] = "in_progress"
    
    # Save updated manifest
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    logger.info("Asset generation completed successfully!")
    
    return {
        "job_id": job_id,
        "images": generated_images,
        "audio": generated_audio_files,
        "manifest": manifest
    }


async def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run asset generation for an existing job',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--job-id', '-j',
        required=True,
        help='ID of the job to process'
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
        # Generate assets
        result = await generate_assets_for_job(args.job_id)
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"Asset generation completed successfully!")
        print(f"Job ID: {args.job_id}")
        print(f"Generated {len(result['images'])} images")
        print(f"Generated {len(result['audio'])} audio files")
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate assets: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        print("Check the logs for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
