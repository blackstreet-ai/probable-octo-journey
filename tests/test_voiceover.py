#!/usr/bin/env python
"""
Unit tests for the VoiceoverAgent.

This module contains tests for the VoiceoverAgent class, which is responsible
for synthesizing narration from video scripts using ElevenLabs or equivalent TTS services.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from agents.voiceover import VoiceoverAgent


class TestVoiceoverAgent:
    """Tests for the VoiceoverAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a VoiceoverAgent instance for testing."""
        # Mock the OpenAI client and assistant creation
        with patch('agents.voiceover.OpenAI'), \
             patch.object(VoiceoverAgent, '_load_prompts'), \
             patch.object(VoiceoverAgent, '_create_assistant'):
            agent = VoiceoverAgent()
            # Set mock prompts
            agent.prompts = {
                "system": "You are VoiceoverAgent",
                "user_extract_narration": "Extract narration from script: {script}",
                "user_optimize_narration": "Optimize narration for voice synthesis: {narration}"
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
**NARRATION:** Welcome to our exploration of the future of artificial intelligence. In this video, we'll examine how AI is poised to transform our world.

**VISUAL:** Show a montage of futuristic AI applications.

## Scene 2: Current State of AI
**NARRATION:** Today's AI systems can already perform impressive tasks, from generating creative content to diagnosing diseases.

**VISUAL:** Display examples of AI applications.
"""
        }

    @pytest.mark.asyncio
    async def test_extract_narration(self, agent, mock_context):
        """Test the extract_narration method."""
        # Mock the OpenAI API calls
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages:
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            # Create a realistic narration extraction response
            narration_content = """
Welcome to our exploration of the future of artificial intelligence. In this video, we'll examine how AI is poised to transform our world.

Today's AI systems can already perform impressive tasks, from generating creative content to diagnosing diseases.
"""
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=narration_content))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.extract_narration(mock_context)
            
            # Assertions
            assert result is not None
            assert "narration" in result
            assert result["narration"] == narration_content
            assert "future of artificial intelligence" in result["narration"]
            assert "Today's AI systems" in result["narration"]
            
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
    async def test_optimize_narration(self, agent, mock_context):
        """Test the optimize_narration method."""
        # Add narration to context
        mock_context["narration"] = """
Welcome to our exploration of the future of artificial intelligence. In this video, we'll examine how AI is poised to transform our world.

Today's AI systems can already perform impressive tasks, from generating creative content to diagnosing diseases.
"""
        
        # Mock the OpenAI API calls
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages:
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            # Create a realistic optimized narration response
            optimized_narration = """
Welcome to our exploration of the future of AI. We'll examine how artificial intelligence is transforming our world.

Today's AI systems perform impressive tasks - from creating content to diagnosing diseases.
"""
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=optimized_narration))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.optimize_narration(mock_context)
            
            # Assertions
            assert result is not None
            assert "optimized_narration" in result
            assert result["optimized_narration"] == optimized_narration
            assert "exploration of the future of AI" in result["optimized_narration"]
            assert "Today's AI systems perform" in result["optimized_narration"]
            
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
    async def test_synthesize_audio(self, agent, mock_context):
        """Test the synthesize_audio method."""
        # Add optimized narration to context
        mock_context["optimized_narration"] = """
Welcome to our exploration of the future of AI. We'll examine how artificial intelligence is transforming our world.

Today's AI systems perform impressive tasks - from creating content to diagnosing diseases.
"""
        
        # Mock the ElevenLabs API call
        with patch('agents.voiceover.requests.post') as mock_post, \
             patch('builtins.open', MagicMock()), \
             patch('pathlib.Path.mkdir', MagicMock()), \
             patch('os.environ.get', return_value='fake_api_key'):
            
            # Configure mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'fake_audio_data'
            mock_post.return_value = mock_response
            
            # Call the method
            result = await agent.synthesize_audio(mock_context)
            
            # Assertions
            assert result is not None
            assert "audio_path" in result
            assert result["audio_path"].endswith(".mp3")
            assert mock_context["job_id"] in result["audio_path"]
            
            # Verify API call
            mock_post.assert_called_once()
            # Check that the API endpoint was called with the correct parameters
            args, kwargs = mock_post.call_args
            assert "elevenlabs.io" in args[0]
            assert "text" in kwargs["json"]
            assert mock_context["optimized_narration"] in kwargs["json"]["text"]

    @pytest.mark.asyncio
    async def test_synthesize_audio_api_error(self, agent, mock_context):
        """Test the synthesize_audio method when the API returns an error."""
        # Add optimized narration to context
        mock_context["optimized_narration"] = "Test narration"
        
        # Mock the ElevenLabs API call to return an error
        with patch('agents.voiceover.requests.post') as mock_post, \
             patch('os.environ.get', return_value='fake_api_key'):
            
            # Configure mock response
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"detail": "Invalid API key"}
            mock_post.return_value = mock_response
            
            # Call the method and expect an exception
            with pytest.raises(Exception) as excinfo:
                await agent.synthesize_audio(mock_context)
            
            # Assertions
            assert "ElevenLabs API error" in str(excinfo.value)
            assert "Invalid API key" in str(excinfo.value)
            
            # Verify API call
            mock_post.assert_called_once()

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
