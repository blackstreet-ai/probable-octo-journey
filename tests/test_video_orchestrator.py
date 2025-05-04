#!/usr/bin/env python
"""
Unit tests for the VideoOrchestratorAgent.

This module contains tests for the VideoOrchestratorAgent class, which is responsible
for coordinating all sub-agents and managing the workflow of the AI Video Automation Pipeline.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from agents.video_orchestrator import VideoOrchestratorAgent


class TestVideoOrchestratorAgent:
    """Tests for the VideoOrchestratorAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a VideoOrchestratorAgent instance for testing."""
        # Mock the OpenAI client and assistant creation
        with patch('agents.video_orchestrator.OpenAI'), \
             patch.object(VideoOrchestratorAgent, '_load_prompts'), \
             patch.object(VideoOrchestratorAgent, '_create_assistant'):
            agent = VideoOrchestratorAgent()
            # Set mock prompts
            agent.prompts = {
                "system": "You are VideoOrchestratorAgent",
                "user_initialize": "Initialize a new video creation job with topic: {topic}",
                "user_review_script": "Review the script: {script}",
                "user_review_video": "Review the video for job {job_id}"
            }
            # Set mock assistant ID
            agent.assistant_id = "test_assistant_id"
            return agent

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        return {
            'job_id': 'test_job_123',
            'topic': 'Test Video Topic',
            'output_dir': '/tmp/test_output',
            'script': 'This is a test script for the video.',
            'start_time': 1620000000
        }

    @pytest.mark.asyncio
    async def test_initialize_job(self, agent, mock_context):
        """Test the initialize_job method."""
        # Mock the OpenAI API calls
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages, \
             patch('builtins.open', MagicMock()):
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value="Test assistant response"))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.initialize_job(mock_context)
            
            # Assertions
            assert result is not None
            assert "manifest" in result
            assert "thread_id" in result
            assert "manifest_path" in result
            assert result["thread_id"] == "test_thread_id"
            assert result["manifest"]["job_id"] == mock_context["job_id"]
            assert result["manifest"]["topic"] == mock_context["topic"]
            assert result["manifest"]["status"] == "initialized"
            
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
    async def test_review_script_approved(self, agent, mock_context):
        """Test the review_script method with an approved script."""
        # Add manifest to context
        mock_context["manifest"] = {
            "job_id": mock_context["job_id"],
            "topic": mock_context["topic"],
            "status": "initialized",
            "steps": [
                {"name": "script_creation", "status": "pending"},
                {"name": "asset_generation", "status": "pending"},
                {"name": "video_assembly", "status": "pending"},
                {"name": "quality_control", "status": "pending"},
                {"name": "publishing", "status": "pending"}
            ]
        }
        mock_context["manifest_path"] = "/tmp/test_output/manifest.json"
        
        # Mock the OpenAI API calls
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages, \
             patch('builtins.open', MagicMock()):
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value="The script is approved. It has good structure and flow."))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.review_script(mock_context)
            
            # Assertions
            assert result is not None
            assert "script_approved" in result
            assert "script_feedback" in result
            assert "manifest" in result
            assert result["script_approved"] is True
            assert "approved" in result["script_feedback"].lower()
            assert result["manifest"]["steps"][0]["status"] == "completed"
            assert result["manifest"]["steps"][1]["status"] == "in_progress"
            
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
    async def test_review_script_not_approved(self, agent, mock_context):
        """Test the review_script method with a script that is not approved."""
        # Add manifest to context
        mock_context["manifest"] = {
            "job_id": mock_context["job_id"],
            "topic": mock_context["topic"],
            "status": "initialized",
            "steps": [
                {"name": "script_creation", "status": "pending"},
                {"name": "asset_generation", "status": "pending"},
                {"name": "video_assembly", "status": "pending"},
                {"name": "quality_control", "status": "pending"},
                {"name": "publishing", "status": "pending"}
            ]
        }
        mock_context["manifest_path"] = "/tmp/test_output/manifest.json"
        
        # Mock the OpenAI API calls
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages, \
             patch('builtins.open', MagicMock()):
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value="The script is not approved. It needs more structure and better flow."))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.review_script(mock_context)
            
            # Assertions
            assert result is not None
            assert "script_approved" in result
            assert "script_feedback" in result
            assert "manifest" in result
            assert result["script_approved"] is False
            assert "not approved" in result["script_feedback"].lower()
            assert result["manifest"]["steps"][0]["status"] == "completed"
            assert result["manifest"]["steps"][1]["status"] == "blocked"
            
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
    async def test_review_video(self, agent, mock_context):
        """Test the review_video method."""
        # Add manifest and video info to context
        mock_context["manifest"] = {
            "job_id": mock_context["job_id"],
            "topic": mock_context["topic"],
            "status": "in_progress",
            "steps": [
                {"name": "script_creation", "status": "completed"},
                {"name": "asset_generation", "status": "completed"},
                {"name": "video_assembly", "status": "completed"},
                {"name": "quality_control", "status": "pending"},
                {"name": "publishing", "status": "pending"}
            ]
        }
        mock_context["manifest_path"] = "/tmp/test_output/manifest.json"
        mock_context["video_duration"] = 180
        mock_context["video_resolution"] = "1920x1080"
        mock_context["audio_quality"] = "high"
        
        # Mock the OpenAI API calls
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages, \
             patch('builtins.open', MagicMock()):
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value="The video is approved. It has good quality and matches the script."))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.review_video(mock_context)
            
            # Assertions
            assert result is not None
            assert "video_approved" in result
            assert "video_feedback" in result
            assert "manifest" in result
            assert result["video_approved"] is True
            assert "approved" in result["video_feedback"].lower()
            assert result["manifest"]["steps"][3]["status"] == "completed"
            assert result["manifest"]["steps"][4]["status"] == "in_progress"
            
            # Verify API calls
            mock_create_thread.assert_called_once()
            mock_create_message.assert_called_once()
            mock_create_run.assert_called_once_with(
                thread_id="test_thread_id",
                assistant_id=agent.assistant_id
            )
            mock_wait_for_run.assert_called_once_with("test_thread_id", "test_run_id")
            mock_list_messages.assert_called_once_with(thread_id="test_thread_id")

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
