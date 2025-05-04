"""
Video-Gen Agent module.

This module implements the Video-Gen Agent, which is responsible for
generating videos from text prompts using the fal.ai API.
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


class VideoGenerationResult(BaseModel):
    """
    Result of a video generation operation.
    
    Args:
        section_id: ID of the script section this video corresponds to
        prompt: The prompt used to generate the video
        file_path: Path to the generated video file
        width: Width of the video in pixels
        height: Height of the video in pixels
        num_frames: Number of frames in the video
        fps: Frames per second
        duration_seconds: Duration of the video in seconds
        seed: Seed used for generation (for reproducibility)
    """
    section_id: str
    prompt: str
    file_path: str
    width: int
    height: int
    num_frames: int
    fps: int
    duration_seconds: float
    seed: int
    negative_prompt: Optional[str] = None
    mock: bool = False


class VideoGenAgent:
    """
    Video-Gen Agent that generates videos from text prompts using the fal.ai API.
    """
    
    def __init__(self, name: str = "Video-Gen"):
        """
        Initialize the Video-Gen Agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.agent = Agent(
            name=name,
            instructions=(
                "You are the Video-Gen Agent responsible for generating high-quality "
                "videos from text prompts. Your job is to take optimized prompts and "
                "transform them into compelling video clips using the fal.ai API."
            ),
        )
        
        # Initialize the fal.ai API client
        self.falai = FalAIAPI()
        
        # Ensure the videos directory exists
        os.makedirs(settings.video_dir, exist_ok=True)
    
    async def generate_videos(
        self,
        prompts: List[Dict[str, Any]],
        width: int = 512,
        height: int = 512,
        num_frames: int = 24,
        fps: int = 8,
        mock_mode: bool = True,
        max_concurrent: int = 2
    ) -> List[VideoGenerationResult]:
        """
        Generate videos from a list of prompts.
        
        Args:
            prompts: List of prompts to generate videos from
            width: Width of the generated videos
            height: Height of the generated videos
            num_frames: Number of frames to generate
            fps: Frames per second
            mock_mode: If True, create placeholder files instead of making API calls
            max_concurrent: Maximum number of concurrent API calls
            
        Returns:
            List[VideoGenerationResult]: List of video generation results
        """
        results = []
        
        # Define a semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Define a coroutine to generate a single video
        async def generate_single_video(prompt_data):
            async with semaphore:
                section_id = prompt_data.get("section_id", "unknown")
                prompt = prompt_data.get("prompt", "")
                negative_prompt = prompt_data.get("negative_prompt", "")
                
                try:
                    # Generate a filename based on the section ID
                    filename = f"video_{section_id}_{len(results)}.mp4"
                    output_path = settings.video_dir / filename
                    
                    # Generate the video
                    result = self.falai.generate_video(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        num_frames=num_frames,
                        fps=fps,
                        output_path=output_path,
                        mock_mode=mock_mode
                    )
                    
                    # Create a VideoGenerationResult
                    return VideoGenerationResult(
                        section_id=section_id,
                        prompt=prompt,
                        file_path=result["video_path"],
                        width=result["width"],
                        height=result["height"],
                        num_frames=result["num_frames"],
                        fps=result["fps"],
                        duration_seconds=result["duration_seconds"],
                        seed=result["seed"],
                        negative_prompt=negative_prompt,
                        mock=result.get("mock", False)
                    )
                    
                except FalAIError as e:
                    logger.error(f"Failed to generate video for section {section_id}: {str(e)}")
                    # Return a placeholder result in case of error
                    return VideoGenerationResult(
                        section_id=section_id,
                        prompt=prompt,
                        file_path=str(settings.video_dir / f"error_{section_id}.mp4"),
                        width=width,
                        height=height,
                        num_frames=num_frames,
                        fps=fps,
                        duration_seconds=num_frames / fps,
                        seed=0,
                        negative_prompt=negative_prompt,
                        mock=True
                    )
        
        # Create tasks for all prompts
        tasks = [generate_single_video(prompt) for prompt in prompts]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def generate_video_for_section(
        self,
        section_id: str,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        num_frames: int = 24,
        fps: int = 8,
        mock_mode: bool = True
    ) -> VideoGenerationResult:
        """
        Generate a single video for a script section.
        
        Args:
            section_id: ID of the script section
            prompt: Text prompt for video generation
            negative_prompt: Text prompt for elements to avoid
            width: Width of the generated video
            height: Height of the generated video
            num_frames: Number of frames to generate
            fps: Frames per second
            mock_mode: If True, create a placeholder file instead of making an API call
            
        Returns:
            VideoGenerationResult: Result of the video generation
        """
        try:
            # Generate a filename based on the section ID
            filename = f"video_{section_id}.mp4"
            output_path = settings.video_dir / filename
            
            # Generate the video
            result = self.falai.generate_video(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_frames=num_frames,
                fps=fps,
                output_path=output_path,
                mock_mode=mock_mode
            )
            
            # Create a VideoGenerationResult
            return VideoGenerationResult(
                section_id=section_id,
                prompt=prompt,
                file_path=result["video_path"],
                width=result["width"],
                height=result["height"],
                num_frames=result["num_frames"],
                fps=result["fps"],
                duration_seconds=result["duration_seconds"],
                seed=result["seed"],
                negative_prompt=negative_prompt,
                mock=result.get("mock", False)
            )
            
        except FalAIError as e:
            logger.error(f"Failed to generate video for section {section_id}: {str(e)}")
            # Return a placeholder result in case of error
            return VideoGenerationResult(
                section_id=section_id,
                prompt=prompt,
                file_path=str(settings.video_dir / f"error_{section_id}.mp4"),
                width=width,
                height=height,
                num_frames=num_frames,
                fps=fps,
                duration_seconds=num_frames / fps,
                seed=0,
                negative_prompt=negative_prompt,
                mock=True
            )
