"""
fal.ai API wrapper for image and video generation.

This module provides a wrapper around the fal.ai API for image and video
generation functionality used by the Image-Gen and Video-Gen Agents.
"""

from typing import Dict, Any, Optional, List, Union, BinaryIO
import os
import json
import requests
import time
from pathlib import Path
import uuid
import base64
from io import BytesIO
import logging
from urllib.parse import urljoin

from ai_video_pipeline.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)


class FalAIError(Exception):
    """Exception raised for errors in the fal.ai API."""
    pass


class FalAIAPI:
    """
    Wrapper for the fal.ai API for image and video generation.
    
    This class provides methods to interact with the fal.ai API
    for generating images and videos from text prompts.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the fal.ai API wrapper.
        
        Args:
            api_key: Optional API key (defaults to environment variable)
        """
        self.api_key = api_key or settings.falai_api_key
        self.base_url = "https://api.fal.ai/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Key {self.api_key}"
        }
        
        # Endpoints
        self.image_endpoint = "/text-to-image/stable-diffusion-xl"
        self.video_endpoint = "/text-to-video/svd"
        
        # Create asset directories if they don't exist
        os.makedirs(settings.images_dir, exist_ok=True)
        os.makedirs(settings.video_dir, exist_ok=True)
    
    def _make_request(
        self, 
        endpoint: str, 
        payload: Dict[str, Any], 
        method: str = "POST",
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: int = 2
    ) -> Dict[str, Any]:
        """
        Make a request to the fal.ai API with retry logic.
        
        Args:
            endpoint: API endpoint
            payload: Request payload
            method: HTTP method
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            FalAIError: If the API request fails after all retries
        """
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(max_retries):
            try:
                if method.upper() == "POST":
                    response = requests.post(
                        url,
                        headers=self.headers,
                        json=payload,
                        timeout=timeout
                    )
                elif method.upper() == "GET":
                    response = requests.get(
                        url,
                        headers=self.headers,
                        params=payload,
                        timeout=timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise FalAIError(f"Failed to make request after {max_retries} attempts: {str(e)}")
    
    def _save_base64_image(self, base64_data: str, output_path: Path) -> None:
        """
        Save a base64-encoded image to a file.
        
        Args:
            base64_data: Base64-encoded image data
            output_path: Path to save the image
            
        Raises:
            FalAIError: If the image data cannot be decoded or saved
        """
        try:
            # Remove the data URL prefix if present
            if base64_data.startswith("data:image"):
                base64_data = base64_data.split(",")[1]
                
            # Decode the base64 data
            image_data = base64.b64decode(base64_data)
            
            # Save the image
            with open(output_path, "wb") as f:
                f.write(image_data)
                
        except Exception as e:
            raise FalAIError(f"Failed to save image: {str(e)}")
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        scheduler: str = "euler_a",
        output_path: Optional[Path] = None,
        mock_mode: bool = True  # For testing without API calls
    ) -> Dict[str, Any]:
        """
        Generate an image from a text prompt using fal.ai's Stable Diffusion XL.
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Text prompt for elements to avoid
            width: Width of the generated image
            height: Height of the generated image
            num_inference_steps: Number of inference steps
            guidance_scale: Guidance scale for the diffusion process
            seed: Random seed for reproducibility
            scheduler: Diffusion scheduler to use
            output_path: Optional path to save the image
            mock_mode: If True, create a placeholder file instead of making an API call
            
        Returns:
            Dict[str, Any]: Result of the image generation
            
        Raises:
            FalAIError: If the API request fails
        """
        # Generate a random seed if not provided
        if seed is None:
            seed = int(time.time())
        
        # If no output path is provided, create one in the assets directory
        if output_path is None:
            image_id = str(uuid.uuid4())[:8]
            output_path = settings.images_dir / f"image_{image_id}.png"
        
        # Ensure the parent directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # For testing without API calls
        if mock_mode:
            # Create a placeholder file
            with open(output_path, "w") as f:
                f.write(f"# This is a placeholder for the generated image\n")
                f.write(f"# Prompt: {prompt}\n")
                f.write(f"# Negative Prompt: {negative_prompt}\n")
                f.write(f"# Dimensions: {width}x{height}\n")
                f.write(f"# Seed: {seed}\n")
            
            return {
                "image_path": str(output_path),
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "seed": seed,
                "mock": True
            }
        
        # Prepare the API request payload
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
            "scheduler": scheduler,
            "output_format": "png"
        }
        
        try:
            # Make the API request
            response = self._make_request(self.image_endpoint, payload)
            
            # Extract the image data
            if "image" in response:
                # Save the image
                self._save_base64_image(response["image"], output_path)
                
                # Return the result
                return {
                    "image_path": str(output_path),
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "seed": seed,
                    "mock": False
                }
            else:
                raise FalAIError(f"No image data in response: {response}")
                
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            raise FalAIError(f"Image generation failed: {str(e)}")
    
    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 24,
        width: int = 512,
        height: int = 512,
        fps: int = 8,
        motion_bucket_id: int = 127,
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
        mock_mode: bool = True  # For testing without API calls
    ) -> Dict[str, Any]:
        """
        Generate a video from a text prompt using fal.ai's Stable Video Diffusion.
        
        Args:
            prompt: Text prompt for video generation
            negative_prompt: Text prompt for elements to avoid
            num_frames: Number of frames to generate
            width: Width of the generated video
            height: Height of the generated video
            fps: Frames per second
            motion_bucket_id: Motion bucket ID (controls motion intensity)
            seed: Random seed for reproducibility
            output_path: Optional path to save the video
            mock_mode: If True, create a placeholder file instead of making an API call
            
        Returns:
            Dict[str, Any]: Result of the video generation
            
        Raises:
            FalAIError: If the API request fails
        """
        # Generate a random seed if not provided
        if seed is None:
            seed = int(time.time())
        
        # If no output path is provided, create one in the assets directory
        if output_path is None:
            video_id = str(uuid.uuid4())[:8]
            output_path = settings.video_dir / f"video_{video_id}.mp4"
        
        # Ensure the parent directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # For testing without API calls
        if mock_mode:
            # Create a placeholder file
            with open(output_path, "w") as f:
                f.write(f"# This is a placeholder for the generated video\n")
                f.write(f"# Prompt: {prompt}\n")
                f.write(f"# Negative Prompt: {negative_prompt}\n")
                f.write(f"# Dimensions: {width}x{height}\n")
                f.write(f"# Frames: {num_frames} @ {fps} FPS\n")
                f.write(f"# Seed: {seed}\n")
            
            return {
                "video_path": str(output_path),
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "num_frames": num_frames,
                "fps": fps,
                "duration_seconds": num_frames / fps,
                "seed": seed,
                "mock": True
            }
        
        # Prepare the API request payload
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_frames": num_frames,
            "width": width,
            "height": height,
            "motion_bucket_id": motion_bucket_id,
            "seed": seed
        }
        
        try:
            # Make the API request
            response = self._make_request(self.video_endpoint, payload)
            
            # Extract the video data
            if "video" in response:
                # The response contains a URL to the generated video
                video_url = response["video"]
                
                # Download the video
                video_response = requests.get(video_url, timeout=30)
                video_response.raise_for_status()
                
                # Save the video
                with open(output_path, "wb") as f:
                    f.write(video_response.content)
                
                # Return the result
                return {
                    "video_path": str(output_path),
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "num_frames": num_frames,
                    "fps": fps,
                    "duration_seconds": num_frames / fps,
                    "seed": seed,
                    "mock": False
                }
            else:
                raise FalAIError(f"No video data in response: {response}")
                
        except Exception as e:
            logger.error(f"Video generation failed: {str(e)}")
            raise FalAIError(f"Video generation failed: {str(e)}")
