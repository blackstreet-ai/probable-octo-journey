"""
Tests for the Thumbnail Creator Agent.

This module contains tests for the Thumbnail Creator Agent and related functionality.
"""

import os
import json
import pytest
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont
from unittest.mock import patch, MagicMock, mock_open

from ai_video_pipeline.agents.thumbnail_creator import ThumbnailCreatorAgent


@pytest.fixture
def sample_asset_manifest():
    """Create a sample asset manifest for testing."""
    return {
        "job_id": "test_job_123",
        "created_at": "2025-05-04T10:00:00Z",
        "updated_at": "2025-05-04T10:30:00Z",
        "script": {
            "title": "Test Video Title",
            "sections": [
                {
                    "id": "section_1",
                    "heading": "Introduction to Testing",
                    "text": "This is the first section of the test script."
                },
                {
                    "id": "section_2",
                    "heading": "Advanced Testing Techniques",
                    "text": "This is the second section of the test script."
                }
            ]
        },
        "assets": {
            "images": [
                {
                    "id": "image_hero_abc1",
                    "path": "/path/to/hero_image.png",
                    "type": "image",
                    "section_id": "section_1",
                    "metadata": {
                        "prompt": "A hero image for the video",
                        "type": "hero",
                        "dimensions": {
                            "width": 1920,
                            "height": 1080
                        }
                    }
                },
                {
                    "id": "image_section_2_abc2",
                    "path": "/path/to/image2.png",
                    "type": "image",
                    "section_id": "section_2",
                    "metadata": {
                        "prompt": "A cityscape at night",
                        "dimensions": {
                            "width": 1920,
                            "height": 1080
                        }
                    }
                }
            ]
        }
    }


@pytest.fixture
def thumbnail_creator_agent():
    """Create a ThumbnailCreatorAgent instance for testing."""
    return ThumbnailCreatorAgent()


@pytest.fixture
def sample_image():
    """Create a sample PIL Image for testing."""
    # Create a simple gradient image
    width, height = 1280, 720
    image = Image.new('RGB', (width, height))
    pixels = image.load()
    
    for i in range(width):
        for j in range(height):
            r = int(255 * i / width)
            g = int(255 * j / height)
            b = 128
            pixels[i, j] = (r, g, b)
    
    return image


class TestThumbnailCreatorAgent:
    """Test suite for the ThumbnailCreatorAgent class."""

    def test_init(self, thumbnail_creator_agent):
        """Test the initialization of the ThumbnailCreatorAgent."""
        assert thumbnail_creator_agent is not None
        assert thumbnail_creator_agent.default_width == 1280
        assert thumbnail_creator_agent.default_height == 720
        assert hasattr(thumbnail_creator_agent, 'default_font_path')

    @patch('os.makedirs')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._select_hero_image')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._extract_headline_from_script')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._create_thumbnail')
    def test_run_with_explicit_headline(
        self, mock_create_thumbnail, mock_extract_headline_from_script, 
        mock_select_hero_image, mock_makedirs, 
        thumbnail_creator_agent, sample_asset_manifest, tmp_path
    ):
        """Test run method with explicit headline."""
        # Setup mocks
        hero_image_path = Path("/path/to/hero_image.png")
        mock_select_hero_image.return_value = hero_image_path
        
        output_path = tmp_path / "thumbnail.png"
        mock_create_thumbnail.return_value = output_path
        
        # Call the method with explicit headline
        headline = "Custom Headline Text"
        result = thumbnail_creator_agent.run(
            asset_manifest=sample_asset_manifest,
            headline=headline,
            output_path=output_path
        )
        
        # Check the result
        assert result["status"] == "success"
        assert result["thumbnail_path"] == str(output_path)
        assert result["hero_image_path"] == str(hero_image_path)
        assert result["headline"] == headline
        
        # Verify method calls
        mock_select_hero_image.assert_called_once_with(sample_asset_manifest)
        mock_extract_headline_from_script.assert_not_called()  # Should not be called when headline is provided
        mock_create_thumbnail.assert_called_once_with(
            hero_image_path,
            headline,
            output_path
        )

    @patch('os.makedirs')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._select_hero_image')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._extract_headline_from_script')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._create_thumbnail')
    def test_run_with_extracted_headline(
        self, mock_create_thumbnail, mock_extract_headline, 
        mock_select_hero_image, mock_makedirs, 
        thumbnail_creator_agent, sample_asset_manifest, tmp_path
    ):
        """Test run method with headline extracted from script."""
        # Setup mocks
        hero_image_path = Path("/path/to/hero_image.png")
        mock_select_hero_image.return_value = hero_image_path
        
        extracted_headline = "Extracted Headline from Script"
        mock_extract_headline.return_value = extracted_headline
        
        output_path = tmp_path / "thumbnail.png"
        mock_create_thumbnail.return_value = output_path
        
        # Call the method without explicit headline
        result = thumbnail_creator_agent.run(
            asset_manifest=sample_asset_manifest,
            output_path=output_path
        )
        
        # Check the result
        assert result["status"] == "success"
        assert result["thumbnail_path"] == str(output_path)
        assert result["hero_image_path"] == str(hero_image_path)
        assert result["headline"] == extracted_headline
        
        # Verify method calls
        mock_select_hero_image.assert_called_once_with(sample_asset_manifest)
        mock_extract_headline.assert_called_once_with(sample_asset_manifest)
        mock_create_thumbnail.assert_called_once_with(
            hero_image_path,
            extracted_headline,
            output_path
        )

    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._select_hero_image')
    def test_run_no_hero_image(
        self, mock_select_hero_image, 
        thumbnail_creator_agent, sample_asset_manifest
    ):
        """Test run method when no hero image is found."""
        # Setup mock to return None (no hero image found)
        mock_select_hero_image.return_value = None
        
        # Call the method
        result = thumbnail_creator_agent.run(sample_asset_manifest)
        
        # Check the result
        assert result["status"] == "error"
        assert "No suitable hero image found" in result["message"]

    def test_extract_headline_from_script_title(self, thumbnail_creator_agent, sample_asset_manifest):
        """Test extracting headline from script title."""
        # Call the method
        headline = thumbnail_creator_agent._extract_headline_from_script(sample_asset_manifest)
        
        # Check the result
        assert headline == "Test Video Title"

    def test_extract_headline_from_script_section(self, thumbnail_creator_agent):
        """Test extracting headline from script section heading."""
        # Create manifest with no title but with section headings
        manifest = {
            "script": {
                "sections": [
                    {
                        "heading": "First Section Heading",
                        "text": "Section content"
                    }
                ]
            }
        }
        
        # Call the method
        headline = thumbnail_creator_agent._extract_headline_from_script(manifest)
        
        # Check the result
        assert headline == "First Section Heading"

    def test_extract_headline_from_script_text(self, thumbnail_creator_agent):
        """Test extracting headline from script section text."""
        # Create manifest with no title or headings but with section text
        manifest = {
            "script": {
                "sections": [
                    {
                        "text": "This is the first sentence. This is the second sentence."
                    }
                ]
            }
        }
        
        # Call the method
        headline = thumbnail_creator_agent._extract_headline_from_script(manifest)
        
        # Check the result
        assert headline == "This is the first sentence"

    def test_extract_headline_default(self, thumbnail_creator_agent):
        """Test extracting headline when no script data is available."""
        # Create empty manifest
        manifest = {}
        
        # Call the method
        headline = thumbnail_creator_agent._extract_headline_from_script(manifest)
        
        # Check the result
        assert headline == "Video Thumbnail"

    def test_select_hero_image_explicit(self, thumbnail_creator_agent, sample_asset_manifest):
        """Test selecting hero image with explicit hero image in manifest."""
        # Call the method
        hero_image = thumbnail_creator_agent._select_hero_image(sample_asset_manifest)
        
        # Check the result
        assert hero_image is not None
        assert str(hero_image) == "/path/to/hero_image.png"

    def test_select_hero_image_fallback(self, thumbnail_creator_agent):
        """Test selecting hero image with fallback to first image."""
        # Create manifest with no explicit hero images
        manifest = {
            "assets": {
                "images": [
                    {
                        "id": "image_1",
                        "path": "/path/to/image1.png",
                        "metadata": {}
                    },
                    {
                        "id": "image_2",
                        "path": "/path/to/image2.png",
                        "metadata": {}
                    }
                ]
            }
        }
        
        # Call the method
        hero_image = thumbnail_creator_agent._select_hero_image(manifest)
        
        # Check the result
        assert hero_image is not None
        assert str(hero_image) == "/path/to/image1.png"

    def test_select_hero_image_no_images(self, thumbnail_creator_agent):
        """Test selecting hero image when no images are available."""
        # Create manifest with no images
        manifest = {"assets": {}}
        
        # Call the method
        hero_image = thumbnail_creator_agent._select_hero_image(manifest)
        
        # Check the result
        assert hero_image is None

    @patch('PIL.Image.open')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._resize_image')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._enhance_image')
    @patch('ai_video_pipeline.agents.thumbnail_creator.ThumbnailCreatorAgent._add_text_overlay')
    @patch('os.makedirs')
    def test_create_thumbnail(
        self, mock_makedirs, mock_add_text, mock_enhance, 
        mock_resize, mock_image_open, 
        thumbnail_creator_agent, sample_image, tmp_path
    ):
        """Test creating a thumbnail."""
        # Setup mocks
        mock_image_open.return_value = sample_image
        mock_resize.return_value = sample_image
        mock_enhance.return_value = sample_image
        mock_add_text.return_value = sample_image
        
        # Setup test data
        image_path = Path("/path/to/image.png")
        headline = "Test Headline"
        output_path = tmp_path / "thumbnail.png"
        
        # Call the method
        result = thumbnail_creator_agent._create_thumbnail(
            image_path,
            headline,
            output_path
        )
        
        # Check the result
        assert result == output_path
        
        # Verify method calls
        mock_image_open.assert_called_once_with(image_path)
        mock_resize.assert_called_once_with(sample_image, thumbnail_creator_agent.default_width, thumbnail_creator_agent.default_height)
        mock_enhance.assert_called_once_with(sample_image)
        mock_add_text.assert_called_once_with(sample_image, headline)
        mock_makedirs.assert_called_once()

    def test_resize_image_wider(self, thumbnail_creator_agent, sample_image):
        """Test resizing an image that is wider than the target aspect ratio."""
        # Create a wide image (2:1 aspect ratio)
        wide_image = Image.new('RGB', (2000, 1000))
        
        # Call the method
        result = thumbnail_creator_agent._resize_image(wide_image, 1280, 720)
        
        # Check the result
        assert result.width == 1280
        assert result.height == 720

    def test_resize_image_taller(self, thumbnail_creator_agent, sample_image):
        """Test resizing an image that is taller than the target aspect ratio."""
        # Create a tall image (1:2 aspect ratio)
        tall_image = Image.new('RGB', (1000, 2000))
        
        # Call the method
        result = thumbnail_creator_agent._resize_image(tall_image, 1280, 720)
        
        # Check the result
        assert result.width == 1280
        assert result.height == 720

    def test_enhance_image(self, thumbnail_creator_agent, sample_image):
        """Test enhancing an image."""
        # Call the method
        result = thumbnail_creator_agent._enhance_image(sample_image)
        
        # Check the result
        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size

    @patch('PIL.ImageDraw.Draw')
    @patch('PIL.ImageFont.truetype')
    def test_add_text_overlay(self, mock_truetype, mock_draw, thumbnail_creator_agent, sample_image):
        """Test adding text overlay to an image."""
        # Setup mocks
        mock_font = MagicMock()
        mock_font.getlength.return_value = 100
        mock_font.size = 40
        mock_truetype.return_value = mock_font
        
        # Mock the Draw object
        mock_draw_instance = MagicMock()
        mock_draw.return_value = mock_draw_instance
        
        # Call the method
        with patch.object(thumbnail_creator_agent, '_wrap_text', return_value="Test Headline"):
            with patch.object(thumbnail_creator_agent, '_get_text_dimensions', return_value=(100, 40)):
                result = thumbnail_creator_agent._add_text_overlay(sample_image, "Test Headline")
        
        # Check the result
        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size
        
        # Verify font was loaded
        mock_truetype.assert_called_once()

    def test_wrap_text(self, thumbnail_creator_agent):
        """Test wrapping text to fit within max width."""
        # Create mock font
        mock_font = MagicMock()
        mock_font.getlength.side_effect = lambda text: len(text) * 10  # 10 pixels per character
        
        # Call the method with long text
        text = "This is a long text that should be wrapped to multiple lines for better display"
        result = thumbnail_creator_agent._wrap_text(text, mock_font, 300)
        
        # Check the result
        assert "\n" in result
        lines = result.split("\n")
        assert len(lines) > 1
        
        # Each line should be less than max width
        for line in lines:
            assert mock_font.getlength(line) <= 300

    def test_get_text_dimensions(self, thumbnail_creator_agent):
        """Test getting dimensions of multiline text."""
        # Create mock font
        mock_font = MagicMock()
        mock_font.getlength.side_effect = lambda text: len(text) * 10  # 10 pixels per character
        mock_font.size = 20
        
        # Call the method with multiline text
        text = "Line 1\nLine 2\nLine 3"
        width, height = thumbnail_creator_agent._get_text_dimensions(text, mock_font)
        
        # Check the result
        assert width == 60  # Length of "Line X" * 10
        assert height == 3 * int(20 * 1.2)  # 3 lines * line height
