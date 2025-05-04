"""
Thumbnail Creator Agent module.

This module implements the Thumbnail Creator Agent, which auto-composes
thumbnail images using hero images and headline text.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import os
import logging
import json
from pathlib import Path
import tempfile
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from datetime import datetime
import uuid

from ai_video_pipeline.config.settings import settings

logger = logging.getLogger(__name__)


class ThumbnailCreatorAgent:
    """
    Thumbnail Creator Agent for generating video thumbnails.
    
    This agent is responsible for:
    1. Selecting the best hero image from available assets
    2. Adding headline text overlays
    3. Applying visual enhancements for better thumbnails
    4. Saving the final thumbnail in appropriate formats
    """
    
    def __init__(self):
        """Initialize the Thumbnail Creator Agent."""
        self.output_dir = settings.images_dir / "thumbnails"
        self.default_width = 1280
        self.default_height = 720
        self.default_font_path = str(Path(__file__).parent.parent / "assets" / "fonts" / "OpenSans-Bold.ttf")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Try to load default font, use system font if not available
        try:
            # Check if default font exists
            if not os.path.exists(self.default_font_path):
                # Use system font as fallback
                if os.path.exists("/System/Library/Fonts/Helvetica.ttc"):
                    self.default_font_path = "/System/Library/Fonts/Helvetica.ttc"
                elif os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
                    self.default_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                else:
                    logger.warning("Could not find a suitable font, text rendering may fail")
        except Exception as e:
            logger.warning(f"Error checking font paths: {str(e)}")
    
    def run(
        self,
        asset_manifest: Dict[str, Any],
        headline: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Run the Thumbnail Creator Agent to generate a thumbnail.
        
        Args:
            asset_manifest: Asset manifest with image references
            headline: Optional headline text to overlay on the thumbnail
            output_path: Optional path to save the thumbnail
            
        Returns:
            Dict[str, Any]: Result with paths to the generated thumbnail
        """
        logger.info("Running Thumbnail Creator Agent")
        
        # Get headline from script if not provided
        if headline is None:
            headline = self._extract_headline_from_script(asset_manifest)
        
        # Select the best hero image
        hero_image_path = self._select_hero_image(asset_manifest)
        
        if hero_image_path is None:
            return {
                "status": "error",
                "message": "No suitable hero image found in asset manifest"
            }
        
        # Generate thumbnail
        try:
            # Create output path if not provided
            if output_path is None:
                project_id = asset_manifest.get("job_id", f"project_{uuid.uuid4().hex[:8]}")
                output_path = self.output_dir / f"{project_id}_thumbnail.png"
            
            # Create the thumbnail
            thumbnail_path = self._create_thumbnail(
                hero_image_path,
                headline,
                output_path
            )
            
            return {
                "status": "success",
                "thumbnail_path": str(thumbnail_path),
                "hero_image_path": str(hero_image_path),
                "headline": headline
            }
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {str(e)}")
            return {
                "status": "error",
                "message": f"Error creating thumbnail: {str(e)}",
                "hero_image_path": str(hero_image_path),
                "headline": headline
            }
    
    def _extract_headline_from_script(self, asset_manifest: Dict[str, Any]) -> str:
        """
        Extract headline from script in asset manifest.
        
        Args:
            asset_manifest: Asset manifest with script
            
        Returns:
            str: Headline text
        """
        # Default headline if none found
        default_headline = "Video Thumbnail"
        
        # Try to get script from manifest
        if "script" not in asset_manifest:
            return default_headline
        
        script = asset_manifest["script"]
        
        # Check for title in script
        if "title" in script:
            return script["title"]
        
        # Check for sections in script
        if "sections" in script and len(script["sections"]) > 0:
            first_section = script["sections"][0]
            
            # Check for heading in first section
            if "heading" in first_section:
                return first_section["heading"]
            
            # Use first line of text as headline
            if "text" in first_section:
                text = first_section["text"]
                # Get first sentence or first 50 characters
                first_sentence = text.split(".")[0].strip()
                if len(first_sentence) > 50:
                    return first_sentence[:47] + "..."
                return first_sentence
        
        return default_headline
    
    def _select_hero_image(self, asset_manifest: Dict[str, Any]) -> Optional[Path]:
        """
        Select the best hero image from available assets.
        
        Args:
            asset_manifest: Asset manifest with image references
            
        Returns:
            Optional[Path]: Path to the selected hero image
        """
        # Check if there are image assets
        if "assets" not in asset_manifest or "images" not in asset_manifest["assets"]:
            return None
        
        images = asset_manifest["assets"]["images"]
        
        if not images:
            return None
        
        # Look for images with "hero" in the metadata or ID
        hero_images = []
        for image in images:
            if "path" not in image:
                continue
                
            # Check if it's marked as a hero image
            is_hero = False
            if "id" in image and "hero" in image["id"].lower():
                is_hero = True
            
            if "metadata" in image:
                metadata = image["metadata"]
                if "type" in metadata and "hero" in metadata["type"].lower():
                    is_hero = True
                if "prompt" in metadata and "hero" in metadata["prompt"].lower():
                    is_hero = True
            
            if is_hero:
                hero_images.append(image)
        
        # If hero images found, use the first one
        if hero_images:
            return Path(hero_images[0]["path"])
        
        # Otherwise, use the first image in the manifest
        return Path(images[0]["path"])
    
    def _create_thumbnail(
        self,
        image_path: Path,
        headline: str,
        output_path: Path
    ) -> Path:
        """
        Create a thumbnail with text overlay.
        
        Args:
            image_path: Path to the hero image
            headline: Headline text to overlay
            output_path: Path to save the thumbnail
            
        Returns:
            Path: Path to the created thumbnail
        """
        # Open the image
        img = Image.open(image_path)
        
        # Resize to thumbnail dimensions
        img = self._resize_image(img, self.default_width, self.default_height)
        
        # Apply enhancements
        img = self._enhance_image(img)
        
        # Add text overlay
        if headline:
            img = self._add_text_overlay(img, headline)
        
        # Save the thumbnail
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        
        return output_path
    
    def _resize_image(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """
        Resize image to target dimensions with cropping if needed.
        
        Args:
            img: PIL Image to resize
            width: Target width
            height: Target height
            
        Returns:
            Image.Image: Resized image
        """
        # Calculate aspect ratios
        img_aspect = img.width / img.height
        target_aspect = width / height
        
        # Resize and crop to maintain aspect ratio
        if img_aspect > target_aspect:
            # Image is wider than target
            new_height = height
            new_width = int(new_height * img_aspect)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Crop to target width
            left = (new_width - width) // 2
            img = img.crop((left, 0, left + width, height))
        else:
            # Image is taller than target
            new_width = width
            new_height = int(new_width / img_aspect)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Crop to target height
            top = (new_height - height) // 2
            img = img.crop((0, top, width, top + height))
        
        return img
    
    def _enhance_image(self, img: Image.Image) -> Image.Image:
        """
        Apply visual enhancements to make the image more appealing as a thumbnail.
        
        Args:
            img: PIL Image to enhance
            
        Returns:
            Image.Image: Enhanced image
        """
        # Increase contrast slightly
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        
        # Increase saturation slightly
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.2)
        
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.3)
        
        return img
    
    def _add_text_overlay(self, img: Image.Image, text: str) -> Image.Image:
        """
        Add text overlay to the image.
        
        Args:
            img: PIL Image to add text to
            text: Text to add
            
        Returns:
            Image.Image: Image with text overlay
        """
        # Create a copy of the image
        result = img.copy()
        draw = ImageDraw.Draw(result)
        
        # Calculate text size and position
        try:
            # Try to load font
            font_size = int(img.height * 0.08)  # 8% of image height
            font = ImageFont.truetype(self.default_font_path, font_size)
            
            # Wrap text if needed
            wrapped_text = self._wrap_text(text, font, img.width * 0.9)
            
            # Calculate text dimensions
            text_width, text_height = self._get_text_dimensions(wrapped_text, font)
            
            # Position text at bottom with padding
            padding = int(img.height * 0.05)  # 5% of image height
            position = ((img.width - text_width) // 2, img.height - text_height - padding)
            
            # Add shadow for better readability
            shadow_offset = int(font_size * 0.05)
            for offset_x, offset_y in [(0, 0), (shadow_offset, shadow_offset)]:
                # Draw shadow first (black with alpha)
                if offset_x > 0 or offset_y > 0:
                    draw.text(
                        (position[0] + offset_x, position[1] + offset_y),
                        wrapped_text,
                        font=font,
                        fill=(0, 0, 0, 180)
                    )
            
            # Draw main text (white)
            draw.text(
                position,
                wrapped_text,
                font=font,
                fill=(255, 255, 255, 255)
            )
            
        except Exception as e:
            logger.warning(f"Error adding text overlay: {str(e)}")
            # Fallback to simple text if font loading fails
            draw.text(
                (img.width // 20, img.height * 4 // 5),
                text,
                fill=(255, 255, 255)
            )
        
        return result
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: float) -> str:
        """
        Wrap text to fit within max width.
        
        Args:
            text: Text to wrap
            font: Font to use for measuring
            max_width: Maximum width in pixels
            
        Returns:
            str: Wrapped text with newlines
        """
        words = text.split()
        wrapped_lines = []
        current_line = []
        
        for word in words:
            # Add word to current line
            current_line.append(word)
            
            # Check if current line exceeds max width
            line_width = font.getlength(" ".join(current_line))
            if line_width > max_width:
                # Remove last word and add line to wrapped lines
                if len(current_line) > 1:
                    current_line.pop()
                    wrapped_lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Single word is too long, keep it anyway
                    wrapped_lines.append(" ".join(current_line))
                    current_line = []
        
        # Add remaining words
        if current_line:
            wrapped_lines.append(" ".join(current_line))
        
        return "\n".join(wrapped_lines)
    
    def _get_text_dimensions(self, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        """
        Get dimensions of multiline text.
        
        Args:
            text: Text to measure (can include newlines)
            font: Font to use for measuring
            
        Returns:
            Tuple[int, int]: Width and height of text
        """
        lines = text.split("\n")
        max_width = 0
        total_height = 0
        
        for line in lines:
            width = font.getlength(line)
            max_width = max(max_width, width)
            
            # Approximate height as 1.2x font size per line
            line_height = int(font.size * 1.2)
            total_height += line_height
        
        return (int(max_width), total_height)
