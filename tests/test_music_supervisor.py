#!/usr/bin/env python
"""
Unit tests for the MusicSupervisorAgent.

This module contains tests for the MusicSupervisorAgent class, which is responsible
for selecting and processing background music for videos.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from agents.music_supervisor import MusicSupervisorAgent


class TestMusicSupervisorAgent:
    """Tests for the MusicSupervisorAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a MusicSupervisorAgent instance for testing."""
        # Mock the OpenAI client and assistant creation
        with patch('agents.music_supervisor.OpenAI'), \
             patch.object(MusicSupervisorAgent, '_load_prompts'), \
             patch.object(MusicSupervisorAgent, '_create_assistant'):
            agent = MusicSupervisorAgent()
            # Set mock prompts
            agent.prompts = {
                "system": "You are MusicSupervisorAgent",
                "user_select_music": "Select music for topic: {topic}, mood: {mood}, audience: {audience}",
                "user_process_music": "Process music file: {music_file} to match the script pacing and tone"
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
            'topic': 'The Future of AI',
            'mood': 'inspirational',
            'audience': 'technology enthusiasts',
            'script': """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence.

**VISUAL:** Show a montage of futuristic AI applications.
"""
        }

    @pytest.mark.asyncio
    async def test_select_music(self, agent, mock_context):
        """Test the select_music method."""
        # Mock the OpenAI API calls
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages, \
             patch('agents.music_supervisor.requests.get') as mock_get, \
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
            
            # Create a realistic music selection response
            music_selection = """
For "The Future of AI" with an inspirational mood targeting technology enthusiasts, I recommend:

1. "Digital Dawn" - A modern electronic track with uplifting synths and a progressive build that evokes technological optimism.
2. "Neural Networks" - An ambient composition with subtle piano melodies over electronic textures.
3. "Quantum Leap" - A cinematic electronic piece with orchestral elements that convey both wonder and technological advancement.

Recommended track: "Digital Dawn"
URL: https://example.com/royalty-free-music/digital-dawn.mp3
License: Creative Commons Attribution
"""
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=music_selection))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Mock the music file download
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'fake_audio_data'
            mock_get.return_value = mock_response
            
            # Call the method
            result = await agent.select_music(mock_context)
            
            # Assertions
            assert result is not None
            assert "music_selection" in result
            assert "music_file" in result
            assert result["music_selection"] == music_selection
            assert "Digital Dawn" in result["music_selection"]
            assert result["music_file"].endswith(".mp3")
            assert mock_context["job_id"] in result["music_file"]
            
            # Verify API calls
            mock_create_thread.assert_called_once()
            mock_create_message.assert_called_once()
            mock_create_run.assert_called_once_with(
                thread_id="test_thread_id",
                assistant_id=agent.assistant_id
            )
            mock_wait_for_run.assert_called_once_with("test_thread_id", "test_run_id")
            mock_list_messages.assert_called_once_with(thread_id="test_thread_id")
            mock_get.assert_called_once_with("https://example.com/royalty-free-music/digital-dawn.mp3", stream=True)

    @pytest.mark.asyncio
    async def test_process_music(self, agent, mock_context):
        """Test the process_music method."""
        # Add music file to context
        mock_context["music_file"] = "/tmp/test_output/test_job_123/music/original.mp3"
        mock_context["audio_duration"] = 120  # 2 minutes
        
        # Mock the ffmpeg subprocess call
        with patch('agents.music_supervisor.subprocess.run') as mock_run, \
             patch('builtins.open', MagicMock()), \
             patch('pathlib.Path.mkdir', MagicMock()), \
             patch('os.path.exists', return_value=True):
            
            # Configure mock
            mock_run.return_value = MagicMock(returncode=0)
            
            # Call the method
            result = await agent.process_music(mock_context)
            
            # Assertions
            assert result is not None
            assert "processed_music_file" in result
            assert result["processed_music_file"].endswith(".mp3")
            assert "processed" in result["processed_music_file"]
            assert mock_context["job_id"] in result["processed_music_file"]
            
            # Verify ffmpeg call
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert "ffmpeg" in args[0][0]
            assert "-i" in args[0]
            assert mock_context["music_file"] in args[0]
            assert "-t" in args[0]
            assert str(mock_context["audio_duration"]) in args[0]

    @pytest.mark.asyncio
    async def test_process_music_ffmpeg_error(self, agent, mock_context):
        """Test the process_music method when ffmpeg returns an error."""
        # Add music file to context
        mock_context["music_file"] = "/tmp/test_output/test_job_123/music/original.mp3"
        mock_context["audio_duration"] = 120  # 2 minutes
        
        # Mock the ffmpeg subprocess call to return an error
        with patch('agents.music_supervisor.subprocess.run') as mock_run, \
             patch('pathlib.Path.mkdir', MagicMock()), \
             patch('os.path.exists', return_value=True):
            
            # Configure mock to return an error
            mock_run.return_value = MagicMock(returncode=1)
            
            # Call the method and expect an exception
            with pytest.raises(Exception) as excinfo:
                await agent.process_music(mock_context)
            
            # Assertions
            assert "FFmpeg processing failed" in str(excinfo.value)
            
            # Verify ffmpeg call
            mock_run.assert_called_once()

    def test_extract_music_url(self, agent):
        """Test the _extract_music_url method."""
        # Test with a valid music selection text
        music_selection = """
Recommended track: "Digital Dawn"
URL: https://example.com/music/digital-dawn.mp3
License: Creative Commons Attribution
"""
        url = agent._extract_music_url(music_selection)
        assert url == "https://example.com/music/digital-dawn.mp3"
        
        # Test with a different URL format
        music_selection = """
Recommended track: "Neural Networks"
Download from: https://freemusicarchive.org/music/neural-networks.mp3
"""
        url = agent._extract_music_url(music_selection)
        assert url == "https://freemusicarchive.org/music/neural-networks.mp3"
        
        # Test with no URL
        music_selection = "Recommended track: 'Quantum Leap'"
        url = agent._extract_music_url(music_selection)
        assert url is None

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
