"""
Tests for the Timeline Builder functionality.

This module contains tests for the TimelineBuilder class and related functionality.
"""

import os
import json
import pytest
from pathlib import Path
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

from ai_video_pipeline.tools.timeline_builder import TimelineBuilder
from ai_video_pipeline.agents.timeline_builder_agent import TimelineBuilderAgent


@pytest.fixture
def sample_asset_manifest():
    """Create a sample asset manifest for testing."""
    return {
        "job_id": "test_job_123",
        "created_at": "2025-05-04T10:00:00Z",
        "updated_at": "2025-05-04T10:30:00Z",
        "script": {
            "title": "Test Video Project",
            "sections": [
                {
                    "id": "section_1",
                    "text": "This is the first section of the test script."
                },
                {
                    "id": "section_2",
                    "text": "This is the second section of the test script."
                }
            ]
        },
        "assets": {
            "images": [
                {
                    "id": "image_section_1_abc1",
                    "path": "/Users/gary/Desktop/ai-video-automation-01/assets/images/image1.png",
                    "type": "image",
                    "section_id": "section_1",
                    "metadata": {
                        "prompt": "A beautiful landscape",
                        "dimensions": {
                            "width": 1920,
                            "height": 1080
                        }
                    }
                },
                {
                    "id": "image_section_2_abc2",
                    "path": "/Users/gary/Desktop/ai-video-automation-01/assets/images/image2.png",
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
            ],
            "videos": [
                {
                    "id": "video_section_1_def1",
                    "path": "/Users/gary/Desktop/ai-video-automation-01/assets/videos/video1.mp4",
                    "type": "video",
                    "section_id": "section_1",
                    "metadata": {
                        "prompt": "Flowing water in a stream",
                        "dimensions": {
                            "width": 1920,
                            "height": 1080
                        },
                        "duration_seconds": 10.0,
                        "fps": 30
                    }
                }
            ],
            "audio": [
                {
                    "id": "audio_voiceover_ghi1",
                    "path": "/Users/gary/Desktop/ai-video-automation-01/assets/audio/voiceover.wav",
                    "type": "audio",
                    "metadata": {
                        "type": "voiceover",
                        "duration_seconds": 15.0,
                        "text_content": "This is the voiceover for the test video."
                    }
                },
                {
                    "id": "audio_music_ghi2",
                    "path": "/Users/gary/Desktop/ai-video-automation-01/assets/audio/music.wav",
                    "type": "audio",
                    "metadata": {
                        "type": "music",
                        "duration_seconds": 30.0
                    }
                }
            ]
        },
        "metadata": {
            "total_assets": 5,
            "total_size_bytes": 15000000
        }
    }


@pytest.fixture
def timeline_builder():
    """Create a TimelineBuilder instance for testing."""
    return TimelineBuilder()


class TestTimelineBuilder:
    """Test suite for the TimelineBuilder class."""

    def test_init(self, timeline_builder):
        """Test the initialization of the TimelineBuilder."""
        assert timeline_builder is not None
        assert timeline_builder.output_dir is not None

    def test_calculate_total_duration(self, timeline_builder, sample_asset_manifest):
        """Test the calculation of total duration from assets."""
        duration = timeline_builder._calculate_total_duration(sample_asset_manifest)
        
        # Expected duration: 10s (video) + 5s * 2 (images) = 20s
        # But audio is 30s, so it should use the longer duration
        assert duration == 30.0

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=MagicMock)
    def test_create_fcpxml(self, mock_open, mock_exists, timeline_builder, sample_asset_manifest, tmp_path):
        """Test the creation of an FCPXML file."""
        # Setup mocks
        mock_exists.return_value = True
        
        # Create a temporary output path
        output_path = tmp_path / "test_output.fcpxml"
        
        # Call the method
        result_path = timeline_builder.create_fcpxml(
            asset_manifest=sample_asset_manifest,
            output_path=output_path
        )
        
        # Check the result
        assert result_path == output_path
        mock_open.assert_called_once()
        
        # Get the XML content that was written
        xml_content = mock_open.return_value.__enter__.return_value.write.call_args[0][0]
        
        # Parse the XML and check key elements
        root = ET.fromstring(xml_content)
        
        # Check FCPXML version
        assert root.tag == "fcpxml"
        assert root.get("version") == "1.9"
        
        # Check resources
        resources = root.find("resources")
        assert resources is not None
        
        # Check format
        format_elem = resources.find("format")
        assert format_elem is not None
        assert format_elem.get("id") == "r1"
        
        # Check library and event
        library = root.find("library")
        assert library is not None
        event = library.find("event")
        assert event is not None
        assert "AI Video Project - test_job_123" in event.get("name")
        
        # Check project
        project = event.find("project")
        assert project is not None
        assert project.get("name") == "Test Video Project"
        
        # Check sequence and spine
        sequence = project.find("sequence")
        assert sequence is not None
        spine = sequence.find("spine")
        assert spine is not None
        
        # Check for video and audio clips
        video_clips = spine.findall("video")
        assert len(video_clips) >= 2  # At least one video and one image
        
        audio_clips = spine.findall("audio")
        assert len(audio_clips) >= 1  # At least one audio clip

    @patch('json.dump')
    def test_generate_mix_request(self, mock_json_dump, timeline_builder, sample_asset_manifest, tmp_path):
        """Test the generation of a mix request JSON file."""
        # Create a temporary output path
        output_path = tmp_path / "test_mix_request.json"
        
        # Setup mock to capture the mix request data
        def capture_mix_request(data, file_obj, **kwargs):
            self.captured_mix_request = data
        mock_json_dump.side_effect = capture_mix_request
        
        # Call the method
        result_path = timeline_builder.generate_mix_request(
            asset_manifest=sample_asset_manifest,
            output_path=output_path
        )
        
        # Check the result
        assert result_path == output_path
        mock_json_dump.assert_called_once()
        
        # Access the captured mix request data
        mix_request = self.captured_mix_request
        
        # Check project ID
        assert mix_request["project_id"] == "test_job_123"
        
        # Check voiceover path
        assert mix_request["voiceover"]["path"] == "/Users/gary/Desktop/ai-video-automation-01/assets/audio/voiceover.wav"
        
        # Check music path
        assert mix_request["music"]["path"] == "/Users/gary/Desktop/ai-video-automation-01/assets/audio/music.wav"
        
        # Check output settings
        assert "target_lufs" in mix_request["output"]
        assert mix_request["output"]["target_lufs"] == -14.0
        
        # Check timeline information
        assert "timeline" in mix_request
        assert "total_duration" in mix_request["timeline"]
        assert mix_request["timeline"]["total_duration"] == 30.0

    @patch('xml.etree.ElementTree.parse')
    @patch('os.path.exists')
    def test_validate_fcpxml_valid(self, mock_exists, mock_parse, timeline_builder, tmp_path):
        """Test validation of a valid FCPXML file."""
        # Setup mock to return True for file existence check
        mock_exists.return_value = True
        
        # Create a mock XML tree and root
        mock_root = MagicMock()
        mock_root.tag = "fcpxml"
        mock_root.get.return_value = "1.9"
        
        # Create mock resources section with proper findall behavior
        mock_resources = MagicMock()
        mock_formats = [MagicMock()]
        mock_assets = [MagicMock()]
        mock_resources.findall.side_effect = lambda tag: mock_formats if tag == "format" else mock_assets
        
        # Create mock library section
        mock_library = MagicMock()
        mock_events = [MagicMock()]
        mock_library.findall.return_value = mock_events
        
        # Create mock project section
        mock_project = MagicMock()
        mock_events[0].findall.return_value = [mock_project]
        
        # Create mock sequence section
        mock_sequence = MagicMock()
        mock_project.findall.return_value = [mock_sequence]
        
        # Create mock spine section
        mock_spine = MagicMock()
        mock_sequence.findall.return_value = [mock_spine]
        
        # Create mock clips
        mock_clips = [MagicMock()]
        mock_spine.findall.return_value = mock_clips
        
        # Setup mock find method for root element
        mock_root.find.side_effect = lambda tag: mock_resources if tag == "resources" else mock_library
        
        # Setup mock findall method for root element to handle asset reference checks
        mock_root.findall = MagicMock(return_value=[])
        
        # Setup mock tree
        mock_tree = MagicMock()
        mock_tree.getroot.return_value = mock_root
        mock_parse.return_value = mock_tree
        
        # Create a temporary file path
        fcpxml_path = tmp_path / "valid.fcpxml"
        
        # Call the method
        result = timeline_builder.validate_fcpxml(fcpxml_path)
        
        # Check the result
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_fcpxml_nonexistent(self, timeline_builder, tmp_path):
        """Test validation of a non-existent FCPXML file."""
        # Create a non-existent file path
        fcpxml_path = tmp_path / "nonexistent.fcpxml"
        
        # Call the method
        result = timeline_builder.validate_fcpxml(fcpxml_path)
        
        # Check the result
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "File not found" in result["errors"][0]


class TestTimelineBuilderAgent:
    """Test suite for the TimelineBuilderAgent class."""

    def test_init(self):
        """Test the initialization of the TimelineBuilderAgent."""
        agent = TimelineBuilderAgent()
        assert agent is not None
        assert agent.timeline_builder is not None

    @patch('ai_video_pipeline.tools.timeline_builder.TimelineBuilder.create_fcpxml')
    @patch('ai_video_pipeline.tools.timeline_builder.TimelineBuilder.generate_mix_request')
    @patch('ai_video_pipeline.tools.timeline_builder.TimelineBuilder.validate_fcpxml')
    def test_run(self, mock_validate, mock_generate_mix, mock_create_fcpxml, sample_asset_manifest):
        """Test the run method of the TimelineBuilderAgent."""
        # Setup mocks
        mock_create_fcpxml.return_value = Path("/path/to/output.fcpxml")
        mock_generate_mix.return_value = Path("/path/to/mix_request.json")
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        
        # Create agent
        agent = TimelineBuilderAgent()
        
        # Call the run method
        result = agent.run(sample_asset_manifest)
        
        # Check the result
        assert "fcpxml_path" in result
        assert "mix_request_path" in result
        assert "validation_result" in result
        assert result["validation_result"]["valid"] is True
        
        # Verify method calls
        mock_create_fcpxml.assert_called_once_with(
            asset_manifest=sample_asset_manifest,
            output_path=None
        )
        mock_generate_mix.assert_called_once_with(
            asset_manifest=sample_asset_manifest
        )
        mock_validate.assert_called_once_with(Path("/path/to/output.fcpxml"))
