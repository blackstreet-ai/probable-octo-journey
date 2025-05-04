"""
Tests for the Motion QC Agent.

This module contains tests for the Motion QC Agent and related functionality.
"""

import os
import json
import pytest
from pathlib import Path
import numpy as np
import cv2
from unittest.mock import patch, MagicMock, mock_open

from ai_video_pipeline.agents.motion_qc import MotionQCAgent


@pytest.fixture
def sample_asset_manifest():
    """Create a sample asset manifest for testing."""
    return {
        "job_id": "test_job_123",
        "created_at": "2025-05-04T10:00:00Z",
        "updated_at": "2025-05-04T10:30:00Z",
        "assets": {
            "videos": [
                {
                    "id": "video_section_1_def1",
                    "path": "/path/to/video1.mp4",
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
                },
                {
                    "id": "video_section_2_def2",
                    "path": "/path/to/video2.mp4",
                    "type": "video",
                    "section_id": "section_2",
                    "metadata": {
                        "prompt": "City skyline at sunset",
                        "dimensions": {
                            "width": 1280,
                            "height": 720
                        },
                        "duration_seconds": 5.0,
                        "fps": 30
                    }
                }
            ]
        }
    }


@pytest.fixture
def motion_qc_agent():
    """Create a MotionQCAgent instance for testing."""
    return MotionQCAgent()


class TestMotionQCAgent:
    """Test suite for the MotionQCAgent class."""

    def test_init(self, motion_qc_agent):
        """Test the initialization of the MotionQCAgent."""
        assert motion_qc_agent is not None
        assert motion_qc_agent.min_duration_seconds == 1.0
        assert motion_qc_agent.max_duration_seconds == 60.0
        assert motion_qc_agent.target_aspect_ratio == 16/9
        assert motion_qc_agent.aspect_ratio_tolerance == 0.05
        assert motion_qc_agent.duplicate_frame_threshold == 0.98
        assert motion_qc_agent.frozen_frame_sequence_threshold == 15

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('ai_video_pipeline.agents.motion_qc.MotionQCAgent._check_duration')
    @patch('ai_video_pipeline.agents.motion_qc.MotionQCAgent._check_aspect_ratio')
    @patch('ai_video_pipeline.agents.motion_qc.MotionQCAgent._check_duplicate_frames')
    def test_run(self, mock_check_duplicate_frames, mock_check_aspect_ratio, 
                 mock_check_duration, mock_json_dump, mock_file_open, 
                 motion_qc_agent, sample_asset_manifest, tmp_path):
        """Test the run method of the MotionQCAgent."""
        # Setup mocks
        mock_check_duration.return_value = {"status": "pass", "duration": 10.0}
        mock_check_aspect_ratio.return_value = {"status": "pass", "aspect_ratio": 16/9}
        mock_check_duplicate_frames.return_value = {"status": "pass"}
        
        # Create a temporary output path
        output_path = tmp_path / "qc_report.json"
        
        # Call the method
        result = motion_qc_agent.run(
            asset_manifest=sample_asset_manifest,
            output_path=output_path
        )
        
        # Check the result
        assert result["status"] == "pass"
        assert len(result["issues"]) == 0
        assert len(result["warnings"]) == 0
        assert "asset_checks" in result
        assert len(result["asset_checks"]) == 2
        
        # Verify method calls
        assert mock_check_duration.call_count == 2
        assert mock_check_aspect_ratio.call_count == 2
        assert mock_check_duplicate_frames.call_count == 2
        
        # Check if report was saved
        mock_file_open.assert_called_once_with(output_path, "w")
        mock_json_dump.assert_called_once()

    @patch('cv2.VideoCapture')
    def test_check_duration_from_metadata(self, mock_video_capture, motion_qc_agent):
        """Test duration check using metadata."""
        # Setup test data
        video_path = "/path/to/video.mp4"
        metadata = {"duration_seconds": 10.0}
        
        # Call the method
        result = motion_qc_agent._check_duration(video_path, metadata)
        
        # Check the result
        assert result["status"] == "pass"
        assert result["duration"] == 10.0
        
        # Verify that VideoCapture was not called
        mock_video_capture.assert_not_called()

    @patch('cv2.VideoCapture')
    def test_check_duration_from_video(self, mock_video_capture, motion_qc_agent):
        """Test duration check using OpenCV."""
        # Setup mock
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: 30.0 if prop == cv2.CAP_PROP_FPS else 300 if prop == cv2.CAP_PROP_FRAME_COUNT else 0
        mock_video_capture.return_value = mock_cap
        
        # Setup test data
        video_path = "/path/to/video.mp4"
        metadata = {}  # No duration in metadata
        
        # Call the method
        result = motion_qc_agent._check_duration(video_path, metadata)
        
        # Check the result
        assert result["status"] == "pass"
        assert result["duration"] == 10.0  # 300 frames / 30 fps = 10 seconds
        
        # Verify that VideoCapture was called
        mock_video_capture.assert_called_once_with(video_path)
        mock_cap.release.assert_called_once()

    @patch('cv2.VideoCapture')
    def test_check_duration_too_short(self, mock_video_capture, motion_qc_agent):
        """Test duration check for a video that's too short."""
        # Setup test data
        video_path = "/path/to/video.mp4"
        metadata = {"duration_seconds": 0.5}  # Less than min_duration_seconds
        
        # Call the method
        result = motion_qc_agent._check_duration(video_path, metadata)
        
        # Check the result
        assert result["status"] == "fail"
        assert "below minimum threshold" in result["message"]
        assert result["duration"] == 0.5
        
        # Verify that VideoCapture was not called
        mock_video_capture.assert_not_called()

    @patch('cv2.VideoCapture')
    def test_check_aspect_ratio_from_metadata(self, mock_video_capture, motion_qc_agent):
        """Test aspect ratio check using metadata."""
        # Setup test data
        video_path = "/path/to/video.mp4"
        metadata = {"dimensions": {"width": 1920, "height": 1080}}
        
        # Call the method
        result = motion_qc_agent._check_aspect_ratio(video_path, metadata)
        
        # Check the result
        assert result["status"] == "pass"
        assert result["aspect_ratio"] == 1920/1080
        assert result["dimensions"]["width"] == 1920
        assert result["dimensions"]["height"] == 1080
        
        # Verify that VideoCapture was not called
        mock_video_capture.assert_not_called()

    @patch('cv2.VideoCapture')
    def test_check_aspect_ratio_from_video(self, mock_video_capture, motion_qc_agent):
        """Test aspect ratio check using OpenCV."""
        # Setup mock
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: 1920.0 if prop == cv2.CAP_PROP_FRAME_WIDTH else 1080.0 if prop == cv2.CAP_PROP_FRAME_HEIGHT else 0
        mock_video_capture.return_value = mock_cap
        
        # Setup test data
        video_path = "/path/to/video.mp4"
        metadata = {}  # No dimensions in metadata
        
        # Call the method
        result = motion_qc_agent._check_aspect_ratio(video_path, metadata)
        
        # Check the result
        assert result["status"] == "pass"
        assert result["aspect_ratio"] == 1920/1080
        assert result["dimensions"]["width"] == 1920
        assert result["dimensions"]["height"] == 1080
        
        # Verify that VideoCapture was called
        mock_video_capture.assert_called_once_with(video_path)
        mock_cap.release.assert_called_once()

    @patch('cv2.VideoCapture')
    def test_check_aspect_ratio_mismatch(self, mock_video_capture, motion_qc_agent):
        """Test aspect ratio check for a video with non-standard aspect ratio."""
        # Setup test data
        video_path = "/path/to/video.mp4"
        metadata = {"dimensions": {"width": 1440, "height": 1080}}  # 4:3 ratio
        
        # Call the method
        result = motion_qc_agent._check_aspect_ratio(video_path, metadata)
        
        # Check the result
        assert result["status"] == "warning"
        assert "differs from target" in result["message"]
        assert result["aspect_ratio"] == 1440/1080
        
        # Verify that VideoCapture was not called
        mock_video_capture.assert_not_called()

    @patch('cv2.VideoCapture')
    @patch('cv2.cvtColor')
    @patch('cv2.resize')
    def test_check_duplicate_frames_no_duplicates(self, mock_resize, mock_cvtcolor, 
                                                mock_video_capture, motion_qc_agent):
        """Test duplicate frame check with no duplicates."""
        # Setup mocks
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        
        # Create sequence of different frames
        frames = []
        for i in range(10):
            frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            frames.append(frame)
        
        # Setup read to return frames then False
        mock_cap.read.side_effect = [(True, frame) for frame in frames] + [(False, None)]
        mock_video_capture.return_value = mock_cap
        
        # Setup cvtColor to return grayscale frames
        mock_cvtcolor.side_effect = lambda frame, _: frame.mean(axis=2).astype(np.uint8)
        
        # Setup resize to return the same frame
        mock_resize.side_effect = lambda frame, size: frame
        
        # Setup test data
        video_path = "/path/to/video.mp4"
        
        # Call the method
        result = motion_qc_agent._check_duplicate_frames(video_path)
        
        # Check the result
        assert result["status"] == "pass"
        assert "duplicate_sequences" not in result
        
        # Verify that VideoCapture was called
        mock_video_capture.assert_called_once_with(video_path)
        mock_cap.release.assert_called_once()

    def test_calculate_frame_similarity(self, motion_qc_agent):
        """Test frame similarity calculation."""
        # Create two identical frames
        frame1 = np.ones((100, 100), dtype=np.uint8) * 128
        frame2 = np.ones((100, 100), dtype=np.uint8) * 128
        
        # Calculate similarity
        similarity = motion_qc_agent._calculate_frame_similarity(frame1, frame2)
        
        # Check the result
        assert similarity == 1.0
        
        # Create two different frames
        frame3 = np.ones((100, 100), dtype=np.uint8) * 0
        frame4 = np.ones((100, 100), dtype=np.uint8) * 255
        
        # Calculate similarity
        similarity = motion_qc_agent._calculate_frame_similarity(frame3, frame4)
        
        # Check the result
        assert similarity == 0.0
