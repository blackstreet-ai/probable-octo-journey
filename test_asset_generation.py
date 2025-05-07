#!/usr/bin/env python
"""
Test script for asset generation in the AI Video Automation Pipeline.

This script tests the asset generation functionality by running a simplified version
of the pipeline that focuses specifically on the visual asset generation process.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from agents.visual_composer import VisualComposerAgent
from tools.asset_generator import AssetGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("asset_generation_test")


async def test_asset_generation():
    """Test the asset generation functionality."""
    logger.info("Starting asset generation test")
    
    # Create a test job ID
    job_id = "test_assets"
    
    # Create output directory
    output_dir = Path(__file__).parent / "assets" / f"job_{job_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a sample script with visual descriptions
    script = """
    # Video Script: The Future of AI
    
    ## Scene 1
    NARRATION: Artificial intelligence has evolved rapidly over the past decade.
    VISUAL: A timeline showing the evolution of AI from simple algorithms to complex neural networks. Include visual representations of machine learning models becoming more sophisticated over time.
    
    ## Scene 2
    NARRATION: Today, AI powers everything from smartphones to autonomous vehicles.
    VISUAL: A split screen showing various AI applications in daily life - a smart home system, autonomous car navigating traffic, and a person using voice assistant on their phone.
    
    ## Scene 3
    NARRATION: But what does the future hold for this transformative technology?
    VISUAL: A futuristic cityscape with integrated AI systems visible throughout - smart buildings, transportation networks, and people interacting with holographic interfaces.
    """
    
    # Create a test context
    context = {
        "job_id": job_id,
        "output_dir": str(output_dir),
        "script": script,
        "visual_style": "Modern, clean, and slightly futuristic",
        "color_palette": "Blue and purple gradient with white accents"
    }
    
    # Create a manifest file
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({
            "job_id": job_id,
            "status": "in_progress",
            "script": script
        }, f, indent=2)
    
    # Initialize the VisualComposerAgent
    visual_composer = VisualComposerAgent()
    
    try:
        # Generate visuals
        logger.info("Generating visuals...")
        result = await visual_composer.generate_visuals(context)
        
        # Log the results
        logger.info(f"Generated {result['visual_count']} images")
        for image in result["images"]:
            logger.info(f"Image for scene {image['scene_number']}: {image['output_path']}")
        
        # Verify that the images exist
        for image in result["images"]:
            assert os.path.exists(image["output_path"]), f"Image file does not exist: {image['output_path']}"
        
        # Verify that the manifest was updated
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            assert "visuals" in manifest, "Manifest does not contain visuals section"
            assert manifest["visuals"]["count"] == result["visual_count"], "Image count mismatch"
        
        logger.info("Asset generation test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Asset generation test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_asset_generation())
    
    # Exit with appropriate status code
    sys.exit(0 if result else 1)
