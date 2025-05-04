"""
Tests for the Publish Manager Agent.

This module contains tests for the Publish Manager Agent and related functionality.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from ai_video_pipeline.agents.publish_manager import (
    PublishManagerAgent,
    YouTubeCredentials,
    VideoMetadata
)


@pytest.fixture
def sample_asset_manifest():
    """Create a sample asset manifest for testing."""
    return {
        "job_id": "test_job_123",
        "created_at": "2025-05-04T10:00:00Z",
        "updated_at": "2025-05-04T10:30:00Z",
        "script": {
            "title": "Test Video Title",
            "keywords": ["test", "video", "ai"],
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
            "videos": [
                {
                    "id": "video_final",
                    "path": "/path/to/final_video.mp4",
                    "type": "video",
                    "metadata": {
                        "duration_seconds": 60.0,
                        "resolution": "1920x1080"
                    }
                }
            ]
        }
    }


@pytest.fixture
def publish_manager_agent():
    """Create a PublishManagerAgent instance for testing."""
    return PublishManagerAgent()


class TestYouTubeCredentials:
    """Test suite for the YouTubeCredentials model."""

    def test_init(self):
        """Test the initialization of YouTubeCredentials."""
        creds = YouTubeCredentials(
            client_id="test_client_id",
            client_secret="test_client_secret",
            refresh_token="test_refresh_token"
        )
        
        assert creds.client_id == "test_client_id"
        assert creds.client_secret == "test_client_secret"
        assert creds.refresh_token == "test_refresh_token"
        assert creds.token_uri == "https://oauth2.googleapis.com/token"


class TestVideoMetadata:
    """Test suite for the VideoMetadata model."""

    def test_init_defaults(self):
        """Test the initialization of VideoMetadata with default values."""
        metadata = VideoMetadata(
            title="Test Video",
            description="Test Description"
        )
        
        assert metadata.title == "Test Video"
        assert metadata.description == "Test Description"
        assert metadata.tags == []
        assert metadata.category_id == "22"  # People & Blogs
        assert metadata.privacy_status == "unlisted"
        assert metadata.made_for_kids is False

    def test_init_custom(self):
        """Test the initialization of VideoMetadata with custom values."""
        metadata = VideoMetadata(
            title="Test Video",
            description="Test Description",
            tags=["test", "video"],
            category_id="10",  # Music
            privacy_status="private",
            made_for_kids=True
        )
        
        assert metadata.title == "Test Video"
        assert metadata.description == "Test Description"
        assert metadata.tags == ["test", "video"]
        assert metadata.category_id == "10"
        assert metadata.privacy_status == "private"
        assert metadata.made_for_kids is True


class TestPublishManagerAgent:
    """Test suite for the PublishManagerAgent class."""

    def test_init(self, publish_manager_agent):
        """Test the initialization of the PublishManagerAgent."""
        assert publish_manager_agent is not None
        assert publish_manager_agent.credentials_path is None
        assert publish_manager_agent.youtube_service is None

    @patch('os.environ.get')
    def test_load_credentials_from_env(self, mock_environ_get, publish_manager_agent):
        """Test loading credentials from environment variable."""
        # Mock environment variable
        mock_environ_get.return_value = json.dumps({
            "client_id": "env_client_id",
            "client_secret": "env_client_secret",
            "refresh_token": "env_refresh_token"
        })
        
        # Call the method
        creds = publish_manager_agent._load_credentials()
        
        # Check the result
        assert creds.client_id == "env_client_id"
        assert creds.client_secret == "env_client_secret"
        assert creds.refresh_token == "env_refresh_token"
        
        # Verify environment variable was checked
        mock_environ_get.assert_called_with('YOUTUBE_CREDENTIALS')

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_credentials_from_file(self, mock_json_load, mock_file_open, tmp_path):
        """Test loading credentials from file."""
        # Create a credentials file path
        creds_path = tmp_path / "youtube_creds.json"
        
        # Mock the JSON data
        mock_json_load.return_value = {
            "client_id": "file_client_id",
            "client_secret": "file_client_secret",
            "refresh_token": "file_refresh_token"
        }
        
        # Create agent with credentials path
        agent = PublishManagerAgent(credentials_path=creds_path)
        
        # Mock Path.exists to return True
        with patch.object(Path, 'exists', return_value=True):
            # Call the method
            creds = agent._load_credentials()
        
        # Check the result
        assert creds.client_id == "file_client_id"
        assert creds.client_secret == "file_client_secret"
        assert creds.refresh_token == "file_refresh_token"
        
        # Verify file was opened
        mock_file_open.assert_called_once_with(creds_path, 'r')
        mock_json_load.assert_called_once()

    @patch('os.environ.get')
    def test_load_credentials_error(self, mock_environ_get, publish_manager_agent):
        """Test error when credentials are not available."""
        # Mock environment variable to return None
        mock_environ_get.return_value = None
        
        # Call the method and check for error
        with pytest.raises(ValueError, match="YouTube credentials not found"):
            publish_manager_agent._load_credentials()

    @patch('ai_video_pipeline.agents.publish_manager.PublishManagerAgent._load_credentials')
    @patch('google.oauth2.credentials.Credentials')
    @patch('googleapiclient.discovery.build')
    def test_authenticate(self, mock_build, mock_credentials, mock_load_credentials, publish_manager_agent):
        """Test authentication with YouTube API."""
        # Mock credentials
        mock_load_credentials.return_value = YouTubeCredentials(
            client_id="test_client_id",
            client_secret="test_client_secret",
            refresh_token="test_refresh_token"
        )
        
        # Mock Credentials and build
        mock_credentials.return_value = "mock_credentials"
        mock_build.return_value = "mock_youtube_service"
        
        # Call the method
        publish_manager_agent._authenticate()
        
        # Check the result
        assert publish_manager_agent.youtube_service == "mock_youtube_service"
        
        # Verify method calls
        mock_load_credentials.assert_called_once()
        mock_credentials.assert_called_once_with(
            None,
            refresh_token="test_refresh_token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        mock_build.assert_called_once_with('youtube', 'v3', credentials="mock_credentials")

    @patch('ai_video_pipeline.agents.publish_manager.PublishManagerAgent._authenticate')
    @patch('ai_video_pipeline.agents.publish_manager.MediaFileUpload')
    def test_upload_video_success(self, mock_media_upload, mock_authenticate, publish_manager_agent):
        """Test successful video upload."""
        # Mock video path
        video_path = MagicMock()
        video_path.exists.return_value = True
        
        # Mock YouTube service
        mock_youtube = MagicMock()
        mock_videos = MagicMock()
        mock_insert = MagicMock()
        
        # Set up the mock chain
        publish_manager_agent.youtube_service = mock_youtube
        mock_youtube.videos.return_value = mock_videos
        mock_videos.insert.return_value = mock_insert
        
        # Mock the next_chunk method to return a completed response
        mock_insert.next_chunk.return_value = (None, {"id": "test_video_id"})
        
        # Mock MediaFileUpload
        mock_media_upload.return_value = "mock_media"
        
        # Create test metadata
        metadata = VideoMetadata(
            title="Test Video",
            description="Test Description",
            tags=["test", "video"]
        )
        
        # Call the method
        result = publish_manager_agent._upload_video(video_path, metadata)
        
        # Check the result
        assert result["status"] == "success"
        assert result["video_id"] == "test_video_id"
        assert result["video_url"] == "https://www.youtube.com/watch?v=test_video_id"
        assert "upload_time" in result
        assert "upload_duration_seconds" in result
        
        # Verify method calls
        video_path.exists.assert_called_once()
        mock_media_upload.assert_called_once_with(
            str(video_path),
            mimetype='video/*',
            resumable=True
        )
        mock_videos.insert.assert_called_once()

    @patch('ai_video_pipeline.agents.publish_manager.PublishManagerAgent._authenticate')
    def test_upload_video_file_not_found(self, mock_authenticate, publish_manager_agent):
        """Test video upload with file not found."""
        # Mock video path
        video_path = MagicMock()
        video_path.exists.return_value = False
        
        # Create test metadata
        metadata = VideoMetadata(
            title="Test Video",
            description="Test Description"
        )
        
        # Call the method and check for error
        with pytest.raises(ValueError, match="Video file not found"):
            publish_manager_agent._upload_video(video_path, metadata)

    @patch('ai_video_pipeline.agents.publish_manager.PublishManagerAgent._extract_metadata_from_manifest')
    @patch('ai_video_pipeline.agents.publish_manager.PublishManagerAgent._upload_video')
    def test_run_success(self, mock_upload_video, mock_extract_metadata, publish_manager_agent, 
                        sample_asset_manifest, tmp_path):
        """Test successful run method."""
        # Mock video path
        video_path = MagicMock()
        video_path.exists.return_value = True
        
        # Mock metadata extraction
        mock_metadata = VideoMetadata(
            title="Extracted Title",
            description="Extracted Description"
        )
        mock_extract_metadata.return_value = mock_metadata
        
        # Mock upload result
        mock_upload_result = {
            "status": "success",
            "video_id": "test_video_id",
            "video_url": "https://www.youtube.com/watch?v=test_video_id",
            "upload_time": "2025-05-04T12:00:00Z",
            "upload_duration_seconds": 10.5
        }
        mock_upload_video.return_value = mock_upload_result
        
        # Create output path
        output_path = tmp_path / "publish_report.json"
        
        # Call the method
        result = publish_manager_agent.run(
            video_path=video_path,
            asset_manifest=sample_asset_manifest,
            output_path=output_path
        )
        
        # Check the result
        assert result["status"] == "success"
        assert result["platform"] == "youtube"
        assert result["upload_result"] == mock_upload_result
        
        # Verify method calls
        mock_extract_metadata.assert_called_once_with(sample_asset_manifest)
        mock_upload_video.assert_called_once_with(video_path, mock_metadata)

    def test_run_video_not_found(self, publish_manager_agent, sample_asset_manifest):
        """Test run method with video file not found."""
        # Mock video path
        video_path = MagicMock()
        video_path.exists.return_value = False
        
        # Call the method
        result = publish_manager_agent.run(
            video_path=video_path,
            asset_manifest=sample_asset_manifest
        )
        
        # Check the result
        assert result["status"] == "error"
        assert "Video file not found" in result["message"]

    def test_extract_metadata_from_manifest(self, publish_manager_agent, sample_asset_manifest):
        """Test extracting metadata from asset manifest."""
        # Call the method
        metadata = publish_manager_agent._extract_metadata_from_manifest(sample_asset_manifest)
        
        # Check the result
        assert metadata.title == "Test Video Title"
        assert "Introduction to Testing" in metadata.description
        assert "Advanced Testing Techniques" in metadata.description
        assert metadata.tags == ["test", "video", "ai"]

    def test_extract_metadata_from_manifest_no_keywords(self, publish_manager_agent):
        """Test extracting metadata from manifest with no keywords."""
        # Create manifest with no keywords
        manifest = {
            "script": {
                "title": "No Keywords Video",
                "sections": [
                    {"heading": "Section 1", "text": "Text 1"},
                    {"heading": "Section 2", "text": "Text 2"}
                ]
            }
        }
        
        # Call the method
        metadata = publish_manager_agent._extract_metadata_from_manifest(manifest)
        
        # Check the result
        assert metadata.title == "No Keywords Video"
        assert metadata.tags == ["Section 1", "Section 2"]

    def test_extract_metadata_minimal_manifest(self, publish_manager_agent):
        """Test extracting metadata from minimal manifest."""
        # Create minimal manifest
        manifest = {"job_id": "minimal_job"}
        
        # Call the method
        metadata = publish_manager_agent._extract_metadata_from_manifest(manifest)
        
        # Check the result
        assert metadata.title == "Video minimal_job"
        assert "Generated with AI Video Automation Pipeline" in metadata.description
        assert metadata.tags == []
