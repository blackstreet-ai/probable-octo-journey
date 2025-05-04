"""
Image-Gen Agent module.

This module implements the Image-Gen Agent, which is responsible for
generating images from text prompts using the fal.ai API.
"""

from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import os
import asyncio
import logging
from pydantic import BaseModel, Field

from ai_video_pipeline.tools.falai import FalAIAPI, FalAIError
from ai_video_pipeline.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

# Mock Agent class for testing without OpenAI Agents SDK
class Agent:
    def __init__(self, name, instructions=None, handoffs=None):
        self.name = name
        self.instructions = instructions
        self.handoffs = handoffs or []


class ImageGenerationResult(BaseModel):
    """
    Result of an image generation operation.
    
    Args:
        section_id: ID of the script section this image corresponds to
        prompt: The prompt used to generate the image
        file_path: Path to the generated image file
        width: Width of the image in pixels
        height: Height of the image in pixels
        seed: Seed used for generation (for reproducibility)
    """
    section_id: str
    prompt: str
    file_path: str
    width: int
    height: int
    seed: int
    negative_prompt: Optional[str] = None
    mock: bool = False


class ImageGenAgent:
    """
    Image-Gen Agent that generates images from text prompts using the fal.ai API.
    """
    
    def __init__(self, name: str = "Image-Gen"):
        """
        Initialize the Image-Gen Agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.agent = Agent(
            name=name,
            instructions=(
                "You are the Image-Gen Agent responsible for generating high-quality "
                "images from text prompts. Your job is to take optimized prompts and "
                "transform them into compelling visuals using the fal.ai API."
            ),
        )
        
        # Initialize the fal.ai API client
        self.falai = FalAIAPI()
        
        # Ensure the images directory exists
        os.makedirs(settings.images_dir, exist_ok=True)
    
    async def generate_images(
        self,
        prompts: List[Dict[str, Any]],
        width: int = 1024,
        height: int = 1024,
        mock_mode: bool = True,
        max_concurrent: int = 3
    ) -> List[ImageGenerationResult]:
        """
        Generate images from a list of prompts.
        
        Args:
            prompts: List of prompts to generate images from
            width: Width of the generated images
            height: Height of the generated images
            mock_mode: If True, create placeholder files instead of making API calls
            max_concurrent: Maximum number of concurrent API calls
            
        Returns:
            List[ImageGenerationResult]: List of image generation results
        """
        results = []
        
        # Define a semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Define a coroutine to generate a single image
        async def generate_single_image(prompt_data):
            async with semaphore:
                section_id = prompt_data.get("section_id", "unknown")
                prompt = prompt_data.get("prompt", "")
                negative_prompt = prompt_data.get("negative_prompt", "")
                
                try:
                    # Generate a filename based on the section ID
                    filename = f"image_{section_id}_{len(results)}.png"
                    output_path = settings.images_dir / filename
                    
                    # Generate the image
                    result = self.falai.generate_image(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        output_path=output_path,
                        mock_mode=mock_mode
                    )
                    
                    # Create an ImageGenerationResult
                    return ImageGenerationResult(
                        section_id=section_id,
                        prompt=prompt,
                        file_path=result["image_path"],
                        width=result["width"],
                        height=result["height"],
                        seed=result["seed"],
                        negative_prompt=negative_prompt,
                        mock=result.get("mock", False)
                    )
                    
                except FalAIError as e:
                    logger.error(f"Failed to generate image for section {section_id}: {str(e)}")
                    # Return a placeholder result in case of error
                    return ImageGenerationResult(
                        section_id=section_id,
                        prompt=prompt,
                        file_path=str(settings.images_dir / f"error_{section_id}.png"),
                        width=width,
                        height=height,
                        seed=0,
                        negative_prompt=negative_prompt,
                        mock=True
                    )
        
        # Create tasks for all prompts
        tasks = [generate_single_image(prompt) for prompt in prompts]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def generate_image_for_section(
        self,
        section_id: str,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        mock_mode: bool = True
    ) -> ImageGenerationResult:
        """
        Generate a single image for a script section.
        
        Args:
            section_id: ID of the script section
            prompt: Text prompt for image generation
            negative_prompt: Text prompt for elements to avoid
            width: Width of the generated image
            height: Height of the generated image
            mock_mode: If True, create a placeholder file instead of making an API call
            
        Returns:
            ImageGenerationResult: Result of the image generation
        """
        try:
            # Generate a filename based on the section ID
            filename = f"image_{section_id}.png"
            output_path = settings.images_dir / filename
            
            # Generate the image
            result = self.falai.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                output_path=output_path,
                mock_mode=mock_mode
            )
            
            # Create an ImageGenerationResult
            return ImageGenerationResult(
                section_id=section_id,
                prompt=prompt,
                file_path=result["image_path"],
                width=result["width"],
                height=result["height"],
                seed=result["seed"],
                negative_prompt=negative_prompt,
                mock=result.get("mock", False)
            )
            
        except FalAIError as e:
            logger.error(f"Failed to generate image for section {section_id}: {str(e)}")
            # Return a placeholder result in case of error
            return ImageGenerationResult(
                section_id=section_id,
                prompt=prompt,
                file_path=str(settings.images_dir / f"error_{section_id}.png"),
                width=width,
                height=height,
                seed=0,
                negative_prompt=negative_prompt,
                mock=True
            )
