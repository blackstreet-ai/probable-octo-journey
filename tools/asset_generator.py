#!/usr/bin/env python
"""
Asset Generator: Utilities for generating and managing assets for AI videos.

This module provides functions to generate, process, and manage various types of assets
including images, audio, and video elements.
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Configure logging
logger = logging.getLogger(__name__)

class AssetGenerator:
    """
    Utility class for generating and managing assets for AI videos.
    
    This class provides methods to generate, process, and manage various types of assets
    including images, audio, and video elements.
    """
    
    @staticmethod
    def ensure_asset_directories(job_dir: str) -> Dict[str, str]:
        """
        Ensure all necessary asset directories exist for a job.
        
        Args:
            job_dir: The job directory path
            
        Returns:
            Dict[str, str]: Dictionary of asset directory paths
        """
        job_path = Path(job_dir)
        
        # Define asset subdirectories
        asset_dirs = {
            "images": job_path / "images",
            "audio": job_path / "audio",
            "video": job_path / "video",
            "music": job_path / "music",
            "timeline": job_path / "timeline",
        }
        
        # Create directories
        for dir_path in asset_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Return string paths
        return {k: str(v) for k, v in asset_dirs.items()}
    
    @staticmethod
    def generate_image_from_dalle(
        prompt: str, 
        output_path: str, 
        style: str = "Modern and clean", 
        size: str = "1024x1024",
        api_key: Optional[str] = None
    ) -> str:
        """
        Generate an image using DALL-E API.
        
        Args:
            prompt: The prompt for image generation
            output_path: Path to save the generated image
            style: The visual style for the image
            size: Image size (e.g., "1024x1024")
            api_key: OpenAI API key (defaults to environment variable)
            
        Returns:
            str: Path to the generated image
        """
        from openai import OpenAI
        
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found")
        
        client = OpenAI(api_key=api_key)
        
        try:
            # Enhance the prompt with style information
            enhanced_prompt = f"{prompt} Style: {style}"
            
            # Generate the image using DALL-E
            response = client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality="standard",
                n=1
            )
            
            # Get the image URL
            image_url = response.data[0].url
            
            # Download and save the image
            return AssetGenerator.download_and_save_image(image_url, output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate image with DALL-E: {str(e)}")
            # Create a placeholder image instead
            return AssetGenerator.create_placeholder_image(prompt, output_path)
    
    @staticmethod
    def download_and_save_image(url: str, output_path: str) -> str:
        """
        Download an image from a URL and save it to the specified path.
        
        Args:
            url: The URL of the image to download
            output_path: Path to save the downloaded image
            
        Returns:
            str: Path to the saved image
        """
        try:
            # Download the image
            response = requests.get(url)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Open the image
            image = Image.open(BytesIO(response.content))
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the image
            image.save(output_path)
            
            logger.info(f"Image saved to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to download and save image: {str(e)}")
            raise
    
    @staticmethod
    def create_placeholder_image(
        text: str, 
        output_path: str, 
        size: Tuple[int, int] = (1024, 1024),
        bg_color: Tuple[int, int, int] = (240, 240, 240),
        text_color: Tuple[int, int, int] = (0, 0, 0)
    ) -> str:
        """
        Create a placeholder image with text.
        
        Args:
            text: The text to display on the image
            output_path: Path to save the generated image
            size: Image dimensions (width, height)
            bg_color: Background color (R, G, B)
            text_color: Text color (R, G, B)
            
        Returns:
            str: Path to the generated image
        """
        try:
            # Create a blank image
            image = Image.new("RGB", size, color=bg_color)
            draw = ImageDraw.Draw(image)
            
            # Add text (wrapped)
            lines = []
            words = text.split()
            current_line = ""
            for word in words:
                if len(current_line + " " + word) <= 40:
                    current_line += " " + word if current_line else word
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            # Draw text lines
            y_position = size[1] // 3
            for line in lines:
                draw.text((size[0] // 2, y_position), line, fill=text_color, anchor="mm")
                y_position += 30
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the image
            image.save(output_path)
            
            logger.info(f"Placeholder image saved to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to create placeholder image: {str(e)}")
            raise

    @staticmethod
    def copy_assets_to_output(source_dir: str, output_dir: str, asset_type: str) -> List[str]:
        """
        Copy assets from source directory to output directory.
        
        Args:
            source_dir: Source directory containing assets
            output_dir: Output directory to copy assets to
            asset_type: Type of assets (e.g., "images", "audio")
            
        Returns:
            List[str]: List of paths to copied assets
        """
        source_path = Path(source_dir)
        output_path = Path(output_dir)
        
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get all files in source directory
        files = list(source_path.glob("*.*"))
        
        # Copy files to output directory
        copied_files = []
        for file in files:
            output_file = output_path / file.name
            shutil.copy2(file, output_file)
            copied_files.append(str(output_file))
            
        logger.info(f"Copied {len(copied_files)} {asset_type} to {output_dir}")
        return copied_files
