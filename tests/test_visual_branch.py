"""
Tests for the Visual Branch components.

This module contains tests for the Prompt-Designer, Image-Gen, and Video-Gen agents,
as well as the Asset-Librarian.
"""

import os
import json
import pytest
from pathlib import Path
import asyncio
from typing import Dict, Any, List

from ai_video_pipeline.agents.prompt_designer import PromptDesignerAgent
from ai_video_pipeline.agents.image_gen import ImageGenAgent
from ai_video_pipeline.agents.video_gen import VideoGenAgent
from ai_video_pipeline.tools.asset_librarian import AssetLibrarian
from ai_video_pipeline.tools.falai import FalAIAPI
from ai_video_pipeline.config.settings import settings


@pytest.fixture
def script_sections() -> List[Dict[str, Any]]:
    """Fixture for sample script sections."""
    return [
        {
            "section_id": "section_1",
            "title": "Introduction",
            "content": "# The Future of AI\n\nArtificial intelligence is transforming our world in ways we never imagined.",
            "duration_seconds": 10,
            "visuals": "Futuristic cityscape with holographic displays showing AI systems at work."
        },
        {
            "section_id": "section_2",
            "title": "AI in Healthcare",
            "content": "AI is revolutionizing healthcare with faster diagnoses and personalized treatments.",
            "duration_seconds": 15,
            "visuals": "Doctor using AI interface to analyze medical scans."
        }
    ]


@pytest.fixture
def style_guide() -> Dict[str, Any]:
    """Fixture for a sample style guide."""
    return {
        "artistic_style": "photorealistic",
        "mood": "optimistic",
        "lighting": "bright",
        "camera_angle": "wide shot",
        "color_palette": "vibrant"
    }


@pytest.fixture
def test_job_id() -> str:
    """Fixture for a test job ID."""
    return "test_job_123"


@pytest.fixture
def asset_librarian(test_job_id) -> AssetLibrarian:
    """Fixture for an AssetLibrarian instance."""
    # Use a temporary directory for testing
    test_assets_dir = Path(settings.assets_dir) / "test"
    os.makedirs(test_assets_dir, exist_ok=True)
    
    # Create test subdirectories
    for subdir in ["images", "videos", "audio"]:
        os.makedirs(test_assets_dir / subdir, exist_ok=True)
    
    # Create a test manifest path
    manifest_path = test_assets_dir / "test_manifest.json"
    
    # Return an AssetLibrarian instance
    librarian = AssetLibrarian(manifest_path=manifest_path, job_id=test_job_id)
    
    # Yield the librarian for the test
    yield librarian
    
    # Clean up after the test
    if os.path.exists(manifest_path):
        os.remove(manifest_path)


@pytest.mark.asyncio
async def test_prompt_designer_agent(script_sections, style_guide):
    """Test that the Prompt-Designer Agent creates valid prompts."""
    # Arrange
    agent = PromptDesignerAgent()
    
    # Act
    prompts = await agent.create_prompts(script_sections, style_guide)
    
    # Assert
    assert len(prompts) == len(script_sections)
    for i, prompt in enumerate(prompts):
        assert prompt.section_id == script_sections[i]["section_id"]
        assert prompt.positive_prompt is not None and len(prompt.positive_prompt) > 0
        assert prompt.negative_prompt is not None
        assert prompt.style.artistic_style == style_guide["artistic_style"]
        assert prompt.style.mood == style_guide["mood"]


@pytest.mark.asyncio
async def test_prompt_designer_format_for_falai(script_sections, style_guide):
    """Test that the Prompt-Designer can format prompts for fal.ai."""
    # Arrange
    agent = PromptDesignerAgent()
    prompts = await agent.create_prompts(script_sections, style_guide)
    
    # Act
    formatted_prompt = agent.format_for_falai(prompts[0])
    
    # Assert
    assert "prompt" in formatted_prompt
    assert "negative_prompt" in formatted_prompt
    assert "section_id" in formatted_prompt
    assert formatted_prompt["section_id"] == script_sections[0]["section_id"]
    assert style_guide["artistic_style"] in formatted_prompt["prompt"]


@pytest.mark.asyncio
async def test_image_gen_agent(script_sections):
    """Test that the Image-Gen Agent generates images."""
    # Arrange
    agent = ImageGenAgent()
    prompts = [
        {
            "section_id": section["section_id"],
            "prompt": section["visuals"] or section["title"],
            "negative_prompt": "blurry, distorted, text"
        }
        for section in script_sections
    ]
    
    # Act
    results = await agent.generate_images(prompts, mock_mode=True)
    
    # Assert
    assert len(results) == len(prompts)
    for i, result in enumerate(results):
        assert result.section_id == prompts[i]["section_id"]
        assert result.prompt == prompts[i]["prompt"]
        assert os.path.exists(result.file_path)
        assert result.width > 0
        assert result.height > 0


@pytest.mark.asyncio
async def test_video_gen_agent(script_sections):
    """Test that the Video-Gen Agent generates videos."""
    # Arrange
    agent = VideoGenAgent()
    prompts = [
        {
            "section_id": section["section_id"],
            "prompt": section["visuals"] or section["title"],
            "negative_prompt": "blurry, distorted, text"
        }
        for section in script_sections
    ]
    
    # Act
    results = await agent.generate_videos(prompts, mock_mode=True)
    
    # Assert
    assert len(results) == len(prompts)
    for i, result in enumerate(results):
        assert result.section_id == prompts[i]["section_id"]
        assert result.prompt == prompts[i]["prompt"]
        assert os.path.exists(result.file_path)
        assert result.width > 0
        assert result.height > 0
        assert result.duration_seconds > 0
        assert result.fps > 0


def test_asset_librarian_add_image(asset_librarian):
    """Test that the Asset-Librarian can add images."""
    # Arrange
    image_path = settings.images_dir / "test_image.png"
    with open(image_path, "w") as f:
        f.write("# Test image")
    
    # Act
    asset = asset_librarian.add_image(
        image_path=image_path,
        section_id="section_1",
        prompt="Test prompt",
        width=1024,
        height=1024
    )
    
    # Assert
    assert asset["id"].startswith("image_")
    assert asset["path"] == str(image_path)
    assert asset["section_id"] == "section_1"
    assert "metadata" in asset
    assert "prompt" in asset["metadata"]
    assert "dimensions" in asset["metadata"]
    
    # Verify the manifest was updated
    manifest = asset_librarian.get_manifest()
    assert len(manifest["assets"]["images"]) == 1
    assert manifest["assets"]["images"][0]["id"] == asset["id"]


def test_asset_librarian_add_video(asset_librarian):
    """Test that the Asset-Librarian can add videos."""
    # Arrange
    video_path = settings.video_dir / "test_video.mp4"
    with open(video_path, "w") as f:
        f.write("# Test video")
    
    # Act
    asset = asset_librarian.add_video(
        video_path=video_path,
        section_id="section_1",
        prompt="Test prompt",
        width=512,
        height=512,
        duration_seconds=10.0,
        fps=24
    )
    
    # Assert
    assert asset["id"].startswith("video_")
    assert asset["path"] == str(video_path)
    assert asset["section_id"] == "section_1"
    assert "metadata" in asset
    assert "prompt" in asset["metadata"]
    assert "dimensions" in asset["metadata"]
    assert "duration_seconds" in asset["metadata"]
    assert "fps" in asset["metadata"]
    
    # Verify the manifest was updated
    manifest = asset_librarian.get_manifest()
    assert len(manifest["assets"]["videos"]) == 1
    assert manifest["assets"]["videos"][0]["id"] == asset["id"]


def test_asset_librarian_get_assets_by_section(asset_librarian):
    """Test that the Asset-Librarian can get assets by section."""
    # Arrange
    # Add an image and a video for section_1
    image_path = settings.images_dir / "test_image.png"
    with open(image_path, "w") as f:
        f.write("# Test image")
    
    video_path = settings.video_dir / "test_video.mp4"
    with open(video_path, "w") as f:
        f.write("# Test video")
    
    asset_librarian.add_image(
        image_path=image_path,
        section_id="section_1",
        prompt="Test prompt"
    )
    
    asset_librarian.add_video(
        video_path=video_path,
        section_id="section_1",
        prompt="Test prompt"
    )
    
    # Add an image for section_2
    image2_path = settings.images_dir / "test_image2.png"
    with open(image2_path, "w") as f:
        f.write("# Test image 2")
    
    asset_librarian.add_image(
        image_path=image2_path,
        section_id="section_2",
        prompt="Test prompt 2"
    )
    
    # Act
    section1_assets = asset_librarian.get_assets_by_section("section_1")
    section2_assets = asset_librarian.get_assets_by_section("section_2")
    
    # Assert
    assert len(section1_assets) == 2
    assert len(section2_assets) == 1
    
    # Verify the assets are of the correct type
    section1_types = [asset["type"] for asset in section1_assets]
    assert "image" in section1_types
    assert "video" in section1_types
    
    assert section2_assets[0]["type"] == "image"


def test_asset_librarian_export_manifest(asset_librarian):
    """Test that the Asset-Librarian can export the manifest."""
    # Arrange
    # Add some assets
    image_path = settings.images_dir / "test_image.png"
    with open(image_path, "w") as f:
        f.write("# Test image")
    
    asset_librarian.add_image(
        image_path=image_path,
        section_id="section_1",
        prompt="Test prompt"
    )
    
    # Act
    export_path = asset_librarian.export_manifest()
    
    # Assert
    assert os.path.exists(export_path)
    
    # Verify the exported manifest contains the correct data
    with open(export_path, "r") as f:
        exported_manifest = json.load(f)
    
    assert exported_manifest["job_id"] == asset_librarian.manifest["job_id"]
    assert len(exported_manifest["assets"]["images"]) == 1
    assert exported_manifest["assets"]["images"][0]["section_id"] == "section_1"


@pytest.mark.asyncio
async def test_falai_api_mock_mode():
    """Test that the fal.ai API works in mock mode."""
    # Arrange
    api = FalAIAPI()
    
    # Act - Generate an image
    image_result = api.generate_image(
        prompt="A beautiful landscape",
        negative_prompt="blurry, distorted",
        width=1024,
        height=1024,
        mock_mode=True
    )
    
    # Act - Generate a video
    video_result = api.generate_video(
        prompt="A beautiful landscape with moving clouds",
        negative_prompt="blurry, distorted",
        num_frames=24,
        width=512,
        height=512,
        fps=8,
        mock_mode=True
    )
    
    # Assert
    assert "image_path" in image_result
    assert os.path.exists(image_result["image_path"])
    assert "mock" in image_result and image_result["mock"] is True
    
    assert "video_path" in video_result
    assert os.path.exists(video_result["video_path"])
    assert "mock" in video_result and video_result["mock"] is True
    assert "duration_seconds" in video_result
    assert video_result["duration_seconds"] == video_result["num_frames"] / video_result["fps"]


# Edge case test
@pytest.mark.asyncio
async def test_prompt_designer_empty_content():
    """Test that the Prompt-Designer handles empty content gracefully."""
    # Arrange
    agent = PromptDesignerAgent()
    empty_sections = [
        {
            "section_id": "empty_section",
            "title": "",
            "content": "",
            "duration_seconds": 5,
            "visuals": ""
        }
    ]
    
    # Act
    prompts = await agent.create_prompts(empty_sections)
    
    # Assert
    assert len(prompts) == 1
    assert prompts[0].section_id == "empty_section"
    assert prompts[0].positive_prompt == ": "  # Title + content with minimal formatting
    assert prompts[0].negative_prompt is not None


# Failure case test
@pytest.mark.asyncio
async def test_image_gen_agent_handles_errors():
    """Test that the Image-Gen Agent handles errors gracefully."""
    # Arrange
    agent = ImageGenAgent()
    
    # Create a prompt with an invalid section_id to simulate an error
    invalid_prompts = [
        {
            "section_id": "",  # Empty section_id
            "prompt": "This should cause an error",
            "negative_prompt": "blurry"
        }
    ]
    
    # Act - This should not raise an exception
    results = await agent.generate_images(invalid_prompts, mock_mode=True)
    
    # Assert - We should still get a result, but it might have default values
    assert len(results) == 1
    assert results[0].section_id == "unknown"  # Default value
    assert "error" in results[0].file_path  # Error indicator in filename
