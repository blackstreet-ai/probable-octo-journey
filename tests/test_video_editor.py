#!/usr/bin/env python
"""
Unit tests for the VideoEditorAgent.

This module contains tests for the VideoEditorAgent class, which is responsible
for assembling the final video from visuals, voiceover, and music.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from agents.video_editor import VideoEditorAgent


class TestVideoEditorAgent:
    """Tests for the VideoEditorAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a VideoEditorAgent instance for testing."""
        # Mock the OpenAI client and assistant creation
        with patch('agents.video_editor.OpenAI'), \
             patch.object(VideoEditorAgent, '_load_prompts'), \
             patch.object(VideoEditorAgent, '_create_assistant'):
            agent = VideoEditorAgent()
            # Set mock prompts
            agent.prompts = {
                "system": "You are VideoEditorAgent",
                "user_create_edit_plan": "Create an edit plan for the script: {script}, with visuals: {visual_assets}",
                "user_assemble_video": "Assemble the video according to the edit plan: {edit_plan}"
            }
            # Set mock assistant ID
            agent.assistant_id = "test_assistant_id"
            return agent

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        return {
            'job_id': 'test_job_123',
            'output_dir': '/tmp/test_output',
            'script': """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence.

**VISUAL:** Show a montage of futuristic AI applications.

## Scene 2: Current State of AI
**NARRATION:** Today's AI systems can already perform impressive tasks.

**VISUAL:** Display examples of AI applications.
""",
            'visual_assets': [
                '/tmp/test_output/test_job_123/visuals/image_1.png',
                '/tmp/test_output/test_job_123/visuals/image_2.png',
                '/tmp/test_output/test_job_123/visuals/image_3.png',
                '/tmp/test_output/test_job_123/visuals/image_4.png'
            ],
            'audio_path': '/tmp/test_output/test_job_123/audio/voiceover.mp3',
            'processed_music_file': '/tmp/test_output/test_job_123/music/processed.mp3'
        }

    @pytest.mark.asyncio
    async def test_create_edit_plan(self, agent, mock_context):
        """Test the create_edit_plan method."""
        # Mock the OpenAI API calls
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages, \
             patch('builtins.open', MagicMock()), \
             patch('pathlib.Path.mkdir', MagicMock()):
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            # Create a realistic edit plan response
            edit_plan = """
# Edit Plan for "The Future of AI"

## Scene 1: Introduction (0:00 - 0:15)
- **Visuals**: Start with image_1.png (futuristic AI applications)
- **Audio**: Voiceover introduction
- **Transitions**: Fade in from black
- **Effects**: Subtle zoom in on the image

## Scene 2: Current State of AI (0:15 - 0:30)
- **Visuals**: Transition to image_2.png, followed by image_3.png
- **Audio**: Continue voiceover about current AI systems
- **Transitions**: Smooth cross-dissolve between images
- **Effects**: Subtle pan across images

## Final Scene (0:30 - 0:40)
- **Visuals**: End with image_4.png
- **Audio**: Conclusion voiceover with music fade up
- **Transitions**: Fade to black
- **Effects**: Add title overlay "The Future of AI"

## Technical Specifications
- Resolution: 1920x1080
- Frame rate: 30fps
- Audio: 48kHz stereo
- Background music: Fade in at 0:15, full volume by 0:30
"""
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=edit_plan))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.create_edit_plan(mock_context)
            
            # Assertions
            assert result is not None
            assert "edit_plan" in result
            assert "edit_plan_path" in result
            assert result["edit_plan"] == edit_plan
            assert "Scene 1: Introduction" in result["edit_plan"]
            assert "Technical Specifications" in result["edit_plan"]
            
            # Verify API calls
            mock_create_thread.assert_called_once()
            mock_create_message.assert_called_once()
            mock_create_run.assert_called_once_with(
                thread_id="test_thread_id",
                assistant_id=agent.assistant_id
            )
            mock_wait_for_run.assert_called_once_with("test_thread_id", "test_run_id")
            mock_list_messages.assert_called_once_with(thread_id="test_thread_id")

    @pytest.mark.asyncio
    async def test_assemble_video(self, agent, mock_context):
        """Test the assemble_video method."""
        # Add edit plan to context
        mock_context["edit_plan"] = """
# Edit Plan for "The Future of AI"

## Scene 1: Introduction (0:00 - 0:15)
- **Visuals**: Start with image_1.png (futuristic AI applications)
- **Audio**: Voiceover introduction
- **Transitions**: Fade in from black
- **Effects**: Subtle zoom in on the image

## Scene 2: Current State of AI (0:15 - 0:30)
- **Visuals**: Transition to image_2.png, followed by image_3.png
- **Audio**: Continue voiceover about current AI systems
- **Transitions**: Smooth cross-dissolve between images
- **Effects**: Subtle pan across images

## Final Scene (0:30 - 0:40)
- **Visuals**: End with image_4.png
- **Audio**: Conclusion voiceover with music fade up
- **Transitions**: Fade to black
- **Effects**: Add title overlay "The Future of AI"

## Technical Specifications
- Resolution: 1920x1080
- Frame rate: 30fps
- Audio: 48kHz stereo
- Background music: Fade in at 0:15, full volume by 0:30
"""
        
        # Mock the ffmpeg subprocess call
        with patch('agents.video_editor.subprocess.run') as mock_run, \
             patch('builtins.open', MagicMock()), \
             patch('pathlib.Path.mkdir', MagicMock()), \
             patch('os.path.exists', return_value=True), \
             patch('agents.video_editor.shutil.copy') as mock_copy:
            
            # Configure mock
            mock_run.return_value = MagicMock(returncode=0)
            
            # Call the method
            result = await agent.assemble_video(mock_context)
            
            # Assertions
            assert result is not None
            assert "video_path" in result
            assert "video_metadata" in result
            assert result["video_path"].endswith(".mp4")
            assert mock_context["job_id"] in result["video_path"]
            assert "resolution" in result["video_metadata"]
            assert "duration" in result["video_metadata"]
            assert "fps" in result["video_metadata"]
            
            # Verify ffmpeg call
            mock_run.assert_called()
            args, kwargs = mock_run.call_args_list[0]
            assert "ffmpeg" in args[0][0]
            assert "-i" in args[0]
            
            # Verify image copying
            assert mock_copy.call_count >= len(mock_context["visual_assets"])

    @pytest.mark.asyncio
    async def test_assemble_video_ffmpeg_error(self, agent, mock_context):
        """Test the assemble_video method when ffmpeg returns an error."""
        # Add edit plan to context
        mock_context["edit_plan"] = "Test edit plan"
        
        # Mock the ffmpeg subprocess call to return an error
        with patch('agents.video_editor.subprocess.run') as mock_run, \
             patch('pathlib.Path.mkdir', MagicMock()), \
             patch('os.path.exists', return_value=True), \
             patch('agents.video_editor.shutil.copy'):
            
            # Configure mock to return an error
            mock_run.return_value = MagicMock(returncode=1)
            
            # Call the method and expect an exception
            with pytest.raises(Exception) as excinfo:
                await agent.assemble_video(mock_context)
            
            # Assertions
            assert "FFmpeg processing failed" in str(excinfo.value)
            
            # Verify ffmpeg call
            mock_run.assert_called()

    def test_create_ffmpeg_command(self, agent, mock_context):
        """Test the _create_ffmpeg_command method."""
        # Add edit plan to context
        mock_context["edit_plan"] = """
# Edit Plan for "The Future of AI"

## Technical Specifications
- Resolution: 1920x1080
- Frame rate: 30fps
- Audio: 48kHz stereo
"""
        
        # Create temporary working directory and output path
        working_dir = "/tmp/test_output/test_job_123/working"
        output_path = "/tmp/test_output/test_job_123/final_video.mp4"
        
        # Call the method
        command = agent._create_ffmpeg_command(mock_context, working_dir, output_path)
        
        # Assertions
        assert isinstance(command, list)
        assert "ffmpeg" in command[0]
        assert "-i" in command
        assert output_path in command
        assert "-c:v" in command
        assert "-r" in command
        assert "30" in command  # fps from edit plan

    def test_extract_technical_specs(self, agent):
        """Test the _extract_technical_specs method."""
        # Test with valid edit plan
        edit_plan = """
# Edit Plan for "The Future of AI"

## Technical Specifications
- Resolution: 1920x1080
- Frame rate: 24fps
- Audio: 48kHz stereo
- Background music: Fade in at 0:15
"""
        specs = agent._extract_technical_specs(edit_plan)
        assert specs is not None
        assert specs["resolution"] == "1920x1080"
        assert specs["frame_rate"] == "24"
        assert specs["audio"] == "48kHz stereo"
        
        # Test with different format
        edit_plan = """
# Technical Details
Resolution: 1280x720
FPS: 30
Audio: 44.1kHz
"""
        specs = agent._extract_technical_specs(edit_plan)
        assert specs is not None
        assert specs["resolution"] == "1280x720"
        assert specs["frame_rate"] == "30"
        
        # Test with missing specs
        edit_plan = "No technical specifications here"
        specs = agent._extract_technical_specs(edit_plan)
        assert specs is not None
        assert "resolution" in specs
        assert specs["resolution"] == "1920x1080"  # Default value
        assert specs["frame_rate"] == "30"  # Default value

    def test_wait_for_run_completed(self, agent):
        """Test the _wait_for_run method when the run completes successfully."""
        with patch.object(agent.client.beta.threads.runs, 'retrieve') as mock_retrieve:
            # Configure mock to return a completed run
            mock_run = MagicMock()
            mock_run.status = "completed"
            mock_retrieve.return_value = mock_run
            
            # Call the method
            result = agent._wait_for_run("test_thread_id", "test_run_id")
            
            # Assertions
            assert result is mock_run
            mock_retrieve.assert_called_once_with(
                thread_id="test_thread_id",
                run_id="test_run_id"
            )

    def test_wait_for_run_failed(self, agent):
        """Test the _wait_for_run method when the run fails."""
        with patch.object(agent.client.beta.threads.runs, 'retrieve') as mock_retrieve, \
             patch('time.sleep', MagicMock()):
            # Configure mock to return a failed run
            mock_run = MagicMock()
            mock_run.status = "failed"
            mock_retrieve.return_value = mock_run
            
            # Call the method and expect an exception
            with pytest.raises(Exception) as excinfo:
                agent._wait_for_run("test_thread_id", "test_run_id")
            
            # Assertions
            assert "failed with status: failed" in str(excinfo.value)
            mock_retrieve.assert_called_once_with(
                thread_id="test_thread_id",
                run_id="test_run_id"
            )
