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
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

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
    
    # Default voice settings
    DEFAULT_VOICE_SETTINGS = {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    }
    
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
    def generate_audio_from_elevenlabs(
        text: str,
        output_path: str,
        voice_id: str,
        api_key: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None,
        model_id: str = "eleven_turbo_v2_5"
    ) -> str:
        """
        Generate audio using ElevenLabs API.
        
        Args:
            text: The text to synthesize
            output_path: Path to save the generated audio
            voice_id: The ID of the voice to use
            api_key: ElevenLabs API key (defaults to environment variable)
            voice_settings: Voice settings (stability, clarity, etc.)
            model_id: ElevenLabs model ID
            
        Returns:
            str: Path to the generated audio file
        """
        try:
            from elevenlabs import VoiceSettings
            from elevenlabs.client import ElevenLabs
            
            # Get API key from environment if not provided
            if not api_key:
                api_key = os.environ.get("ELEVENLABS_API_KEY")
                if not api_key:
                    raise ValueError("ElevenLabs API key not found")
            
            # Initialize ElevenLabs client
            client = ElevenLabs(api_key=api_key)
            
            # Use default voice settings if not provided
            if not voice_settings:
                voice_settings = AssetGenerator.DEFAULT_VOICE_SETTINGS
            
            # Configure voice settings
            settings = VoiceSettings(
                stability=voice_settings.get("stability", 0.5),
                similarity_boost=voice_settings.get("similarity_boost", 0.75),
                style=voice_settings.get("style", 0.0),
                use_speaker_boost=voice_settings.get("use_speaker_boost", True),
                speed=voice_settings.get("speed", 1.0)
            )
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Generate audio using ElevenLabs SDK
            response = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format="mp3_44100_128",
                voice_settings=settings
            )
            
            # Save the audio to a file
            with open(output_path, "wb") as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Successfully generated audio to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate audio with ElevenLabs: {str(e)}")
            # Create a placeholder audio file instead
            return AssetGenerator.create_placeholder_audio(output_path)
    
    @staticmethod
    def create_placeholder_audio(output_path: str, duration: float = 3.0) -> str:
        """
        Create a placeholder silent audio file.
        
        Args:
            output_path: Path to save the generated audio
            duration: Duration of the silent audio in seconds
            
        Returns:
            str: Path to the generated audio file
        """
        try:
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Use ffmpeg to generate silent audio
            subprocess.run([
                "ffmpeg",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo:d={duration}",
                "-c:a", "libmp3lame",
                "-b:a", "128k",
                "-y",  # Overwrite output file if it exists
                output_path
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            logger.info(f"Created placeholder audio at {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to create placeholder audio: {str(e)}")
            # Create an empty file as a last resort
            with open(output_path, "wb") as f:
                pass
            return output_path
    
    @staticmethod
    def combine_audio_files(audio_files: List[str], output_path: str) -> str:
        """
        Combine multiple audio files into a single file.
        
        Args:
            audio_files: List of audio file paths to combine
            output_path: Path to save the combined audio
            
        Returns:
            str: Path to the combined audio file
        """
        try:
            if not audio_files:
                raise ValueError("No audio files provided")
                
            if len(audio_files) == 1:
                # Only one file, just copy it
                shutil.copy2(audio_files[0], output_path)
                return output_path
            
            # Create a temporary file list for ffmpeg
            temp_dir = os.path.dirname(output_path)
            file_list_path = os.path.join(temp_dir, "file_list.txt")
            
            with open(file_list_path, "w") as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file}'\n")
            
            # Use ffmpeg to concatenate the audio files
            subprocess.run([
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", file_list_path,
                "-c", "copy",
                "-y",  # Overwrite output file if it exists
                output_path
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Clean up the temporary file list
            os.remove(file_list_path)
            
            logger.info(f"Combined {len(audio_files)} audio files to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to combine audio files: {str(e)}")
            raise
    
    @staticmethod
    def get_audio_duration(audio_path: str) -> float:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            float: Duration of the audio in seconds
        """
        try:
            # Use ffprobe to get the duration
            result = subprocess.run([
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_path
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Parse the JSON output
            output = json.loads(result.stdout)
            duration = float(output["format"]["duration"])
            
            return duration
            
        except Exception as e:
            logger.error(f"Failed to get audio duration: {str(e)}")
            return 0.0
    
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
