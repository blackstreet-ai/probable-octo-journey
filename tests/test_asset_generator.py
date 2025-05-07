#!/usr/bin/env python
"""
Tests for the AssetGenerator utility.

This module contains tests for the asset generation functionality.
"""

import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tools.asset_generator import AssetGenerator


class TestAssetGenerator(unittest.TestCase):
    """Test cases for the AssetGenerator utility."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(__file__).parent / "test_assets"
        self.test_dir.mkdir(exist_ok=True)
        
        # Create test job directory
        self.job_dir = self.test_dir / "job_test"
        self.job_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_ensure_asset_directories(self):
        """Test ensuring asset directories exist."""
        # Call the method
        asset_dirs = AssetGenerator.ensure_asset_directories(str(self.job_dir))
        
        # Check that all expected directories were created
        expected_dirs = ["images", "audio", "video", "music", "timeline"]
        for dir_name in expected_dirs:
            dir_path = self.job_dir / dir_name
            self.assertTrue(dir_path.exists(), f"Directory {dir_name} was not created")
            self.assertTrue(dir_path.is_dir(), f"{dir_name} is not a directory")
            
        # Check that the returned paths are correct
        for dir_name in expected_dirs:
            expected_path = str(self.job_dir / dir_name)
            self.assertEqual(asset_dirs[dir_name], expected_path)

    @patch("tools.asset_generator.requests.get")
    def test_download_and_save_image(self, mock_get):
        """Test downloading and saving an image."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Create a simple test image in memory
        from PIL import Image
        import io
        
        # Create a test image
        image = Image.new("RGB", (100, 100), color="red")
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        
        # Set the content of the mock response
        mock_response.content = image_bytes.getvalue()
        
        # Call the method
        output_path = str(self.job_dir / "test_image.png")
        result = AssetGenerator.download_and_save_image("http://example.com/image.png", output_path)
        
        # Check the result
        self.assertEqual(result, output_path)
        self.assertTrue(Path(output_path).exists())
        
        # Verify the mock was called correctly
        mock_get.assert_called_once_with("http://example.com/image.png")

    def test_create_placeholder_image(self):
        """Test creating a placeholder image."""
        # Call the method
        output_path = str(self.job_dir / "placeholder.png")
        result = AssetGenerator.create_placeholder_image("Test placeholder", output_path)
        
        # Check the result
        self.assertEqual(result, output_path)
        self.assertTrue(Path(output_path).exists())
        
        # Verify the image has the correct dimensions
        from PIL import Image
        image = Image.open(output_path)
        self.assertEqual(image.size, (1024, 1024))

    @patch("openai.OpenAI")
    def test_generate_image_from_dalle(self, mock_openai):
        """Test generating an image using DALL-E."""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock the response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(url="http://example.com/generated.png")]
        mock_client.images.generate.return_value = mock_response
        
        # Mock the download_and_save_image method
        with patch.object(AssetGenerator, "download_and_save_image") as mock_download:
            mock_download.return_value = str(self.job_dir / "generated.png")
            
            # Call the method
            output_path = str(self.job_dir / "generated.png")
            result = AssetGenerator.generate_image_from_dalle(
                "Test prompt", output_path, "Test style", api_key="test_key"
            )
            
            # Check the result
            self.assertEqual(result, output_path)
            
            # Verify the mocks were called correctly
            mock_openai.assert_called_once_with(api_key="test_key")
            mock_client.images.generate.assert_called_once()
            mock_download.assert_called_once_with(
                "http://example.com/generated.png", output_path
            )

    def test_copy_assets_to_output(self):
        """Test copying assets to output directory."""
        # Create some test files
        source_dir = self.test_dir / "source"
        source_dir.mkdir(exist_ok=True)
        
        test_files = ["file1.txt", "file2.txt", "file3.txt"]
        for filename in test_files:
            with open(source_dir / filename, "w") as f:
                f.write("test content")
        
        # Call the method
        output_dir = self.test_dir / "output"
        result = AssetGenerator.copy_assets_to_output(
            str(source_dir), str(output_dir), "test_files"
        )
        
        # Check the result
        self.assertEqual(len(result), len(test_files))
        for filename in test_files:
            output_path = output_dir / filename
            self.assertTrue(output_path.exists())
            self.assertIn(str(output_path), result)


if __name__ == "__main__":
    unittest.main()
