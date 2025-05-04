#!/usr/bin/env python3
"""
Test script for the Visual Branch components.

This script tests the integration of the Prompt-Designer, Image-Gen, and Video-Gen agents
with the Asset-Librarian.
"""

import asyncio
import json
import os
import logging
from pathlib import Path

from ai_video_pipeline.agents.executive import ExecutiveAgent
from ai_video_pipeline.agents.scriptwriter import ScriptwriterAgent
from ai_video_pipeline.agents.prompt_designer import PromptDesignerAgent
from ai_video_pipeline.agents.image_gen import ImageGenAgent
from ai_video_pipeline.agents.video_gen import VideoGenAgent
from ai_video_pipeline.tools.asset_librarian import AssetLibrarian
from ai_video_pipeline.config.settings import settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_visual_branch():
    """Test the Visual Branch components."""
    logger.info("Testing Visual Branch components...")
    
    # Initialize agents
    executive = ExecutiveAgent()
    scriptwriter = ScriptwriterAgent()
    prompt_designer = PromptDesignerAgent()
    image_gen = ImageGenAgent()
    video_gen = VideoGenAgent()
    
    # Initialize Asset Librarian
    job_id = f"test_visual_branch_{os.urandom(4).hex()}"
    asset_librarian = AssetLibrarian(job_id=job_id)
    
    # Step 1: Create job specification
    logger.info("1. Creating job specification...")
    topic = "The future of artificial intelligence"
    job_result = await executive.run(topic)
    job_spec = job_result["job_spec"]
    logger.info(f"Job spec created: {json.dumps(job_spec, indent=2)}")
    
    # Step 2: Generate script
    logger.info("2. Generating script...")
    script = await scriptwriter.create_script(topic, job_spec)
    logger.info(f"Script created with {len(script.sections)} sections")
    
    # Convert script sections to a list of dictionaries for further processing
    script_sections = []
    for section in script.sections:
        # Use model_dump() instead of dict() for Pydantic v2 compatibility
        if hasattr(section, 'model_dump'):
            script_sections.append(section.model_dump())
        else:
            script_sections.append(section.dict())
    
    # Step 3: Generate prompts
    logger.info("3. Generating prompts...")
    style_guide = {
        "artistic_style": "photorealistic",
        "mood": "optimistic",
        "lighting": "bright",
        "camera_angle": "wide shot",
        "color_palette": "vibrant"
    }
    prompts = await prompt_designer.create_prompts(script_sections, style_guide)
    
    logger.info(f"Generated {len(prompts)} prompts")
    for i, prompt in enumerate(prompts):
        logger.info(f"Prompt {i+1}: {prompt.positive_prompt[:50]}...")
    
    # Convert prompts to a list of dictionaries for the image and video generators
    formatted_prompts = []
    for prompt in prompts:
        # Format the prompt for fal.ai
        formatted_prompt = prompt_designer.format_for_falai(prompt)
        formatted_prompts.append(formatted_prompt)
    
    # Step 4: Generate images
    logger.info("4. Generating images...")
    image_results = await image_gen.generate_images(
        prompts=formatted_prompts,
        width=1024,
        height=1024,
        mock_mode=True  # Use mock mode to avoid actual API calls
    )
    
    logger.info(f"Generated {len(image_results)} images")
    for i, result in enumerate(image_results):
        logger.info(f"Image {i+1}: {result.file_path}")
        
        # Add the image to the asset librarian
        asset_librarian.add_image(
            image_path=result.file_path,
            section_id=result.section_id,
            prompt=result.prompt,
            width=result.width,
            height=result.height,
            additional_metadata={"seed": result.seed, "mock": result.mock}
        )
    
    # Step 5: Generate videos
    logger.info("5. Generating videos...")
    video_results = await video_gen.generate_videos(
        prompts=formatted_prompts,
        width=512,
        height=512,
        num_frames=24,
        fps=8,
        mock_mode=True  # Use mock mode to avoid actual API calls
    )
    
    logger.info(f"Generated {len(video_results)} videos")
    for i, result in enumerate(video_results):
        logger.info(f"Video {i+1}: {result.file_path}")
        
        # Add the video to the asset librarian
        asset_librarian.add_video(
            video_path=result.file_path,
            section_id=result.section_id,
            prompt=result.prompt,
            width=result.width,
            height=result.height,
            duration_seconds=result.duration_seconds,
            fps=result.fps,
            additional_metadata={"seed": result.seed, "mock": result.mock}
        )
    
    # Step 6: Export the asset manifest
    logger.info("6. Exporting asset manifest...")
    manifest_path = asset_librarian.export_manifest()
    logger.info(f"Asset manifest exported to: {manifest_path}")
    
    # Print a summary of the assets
    manifest = asset_librarian.get_manifest()
    logger.info(f"Asset summary:")
    logger.info(f"  - Total assets: {manifest['metadata']['total_assets']}")
    logger.info(f"  - Images: {len(manifest['assets']['images'])}")
    logger.info(f"  - Videos: {len(manifest['assets']['videos'])}")
    
    logger.info("Test completed successfully!")
    return {
        "job_spec": job_spec,
        "script": script.model_dump() if hasattr(script, 'model_dump') else script.dict(),
        "prompts": [p.model_dump() if hasattr(p, 'model_dump') else p.dict() for p in prompts],
        "images": [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in image_results],
        "videos": [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in video_results],
        "manifest_path": str(manifest_path)
    }


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_visual_branch())
    
    # Save the result to a file
    output_path = Path("visual_branch_test_result.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nTest result saved to {output_path}")
