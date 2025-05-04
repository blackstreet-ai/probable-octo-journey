#!/usr/bin/env python
"""
Unit tests for the VisualComposerAgent.

This module contains tests for the VisualComposerAgent class, which is responsible
for generating visuals based on video scripts and ensuring visual consistency.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from agents.visual_composer import VisualComposerAgent


class TestVisualComposerAgent:
    """Tests for the VisualComposerAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a VisualComposerAgent instance for testing."""
        # Mock the OpenAI client and assistant creation
        with patch('agents.visual_composer.OpenAI'), \
             patch.object(VisualComposerAgent, '_load_prompts'), \
             patch.object(VisualComposerAgent, '_create_assistant'):
            agent = VisualComposerAgent()
            # Set mock prompts
            agent.prompts = {
                "system": "You are VisualComposerAgent",
                "user_extract_visual_descriptions": "Extract visual descriptions from script: {script}",
                "user_generate_visuals": "Generate visuals for the following descriptions: {visual_descriptions}"
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

**VISUAL:** Show a montage of futuristic AI applications - smart cities, advanced robotics, and holographic interfaces.

## Scene 2: Current State of AI
**NARRATION:** Today's AI systems can already perform impressive tasks.

**VISUAL:** Display split-screen examples of AI applications in healthcare, art, and business.
"""
        }

    @pytest.mark.asyncio
    async def test_extract_visual_descriptions(self, agent, mock_context):
        """Test the extract_visual_descriptions method."""
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
            
            # Create a realistic visual descriptions extraction response
            visual_descriptions = """
1. Montage of futuristic AI applications:
   - Smart city with interconnected systems, traffic management, and environmental monitoring
   - Advanced humanoid robots interacting with humans in everyday scenarios
   - Holographic interfaces showing data visualization and user interaction

2. Split-screen examples of AI applications:
   - Healthcare: AI analyzing medical scans and assisting in surgery
   - Art: AI generating paintings, music compositions, and creative designs
   - Business: AI analyzing market trends and automating customer service
"""
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=visual_descriptions))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.extract_visual_descriptions(mock_context)
            
            # Assertions
            assert result is not None
            assert "visual_descriptions" in result
            assert result["visual_descriptions"] == visual_descriptions
            assert "Smart city" in result["visual_descriptions"]
            assert "Healthcare: AI analyzing medical scans" in result["visual_descriptions"]
            
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
    async def test_generate_visuals(self, agent, mock_context):
        """Test the generate_visuals method."""
        # Add visual descriptions to context
        mock_context["visual_descriptions"] = """
1. Montage of futuristic AI applications:
   - Smart city with interconnected systems
   - Advanced humanoid robots interacting with humans
   - Holographic interfaces showing data visualization

2. Split-screen examples of AI applications:
   - Healthcare: AI analyzing medical scans
   - Art: AI generating paintings
   - Business: AI analyzing market trends
"""
        
        # Mock the OpenAI API calls and DALL-E image generation
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages, \
             patch.object(agent.client.images, 'generate') as mock_generate_image, \
             patch('builtins.open', MagicMock()), \
             patch('pathlib.Path.mkdir', MagicMock()), \
             patch('base64.b64decode', return_value=b'fake_image_data'):
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            # Create a realistic image prompts response
            image_prompts = """
1. "A futuristic smart city with interconnected systems, aerial view, digital twin visualization, high-tech infrastructure, clean energy, 4K detailed render"

2. "Advanced humanoid robots interacting with humans in everyday scenarios, collaborative workspace, photorealistic, warm lighting, 4K detailed render"

3. "Holographic interface displaying complex data visualization, user interacting with floating 3D elements, blue and purple color scheme, 4K detailed render"

4. "Split-screen showing AI in healthcare (medical scan analysis), art (AI painting), and business (market trend analysis), professional, clean design, 4K detailed render"
"""
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=image_prompts))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Mock DALL-E image generation
            mock_image_response = MagicMock()
            mock_image_response.data = [
                MagicMock(b64_json="fake_base64_image")
            ]
            mock_generate_image.return_value = mock_image_response
            
            # Call the method
            result = await agent.generate_visuals(mock_context)
            
            # Assertions
            assert result is not None
            assert "image_prompts" in result
            assert "visual_assets" in result
            assert result["image_prompts"] == image_prompts
            assert len(result["visual_assets"]) > 0
            assert all(asset.endswith(".png") for asset in result["visual_assets"])
            assert all(mock_context["job_id"] in asset for asset in result["visual_assets"])
            
            # Verify API calls
            mock_create_thread.assert_called_once()
            mock_create_message.assert_called_once()
            mock_create_run.assert_called_once_with(
                thread_id="test_thread_id",
                assistant_id=agent.assistant_id
            )
            mock_wait_for_run.assert_called_once_with("test_thread_id", "test_run_id")
            mock_list_messages.assert_called_once_with(thread_id="test_thread_id")
            assert mock_generate_image.call_count > 0

    @pytest.mark.asyncio
    async def test_generate_visuals_dall_e_error(self, agent, mock_context):
        """Test the generate_visuals method when DALL-E returns an error."""
        # Add visual descriptions to context
        mock_context["visual_descriptions"] = "Test visual description"
        
        # Mock the OpenAI API calls and DALL-E image generation error
        with patch.object(agent, '_wait_for_run') as mock_wait_for_run, \
             patch.object(agent.client.beta.threads, 'create') as mock_create_thread, \
             patch.object(agent.client.beta.threads.messages, 'create') as mock_create_message, \
             patch.object(agent.client.beta.threads.runs, 'create') as mock_create_run, \
             patch.object(agent.client.beta.threads.messages, 'list') as mock_list_messages, \
             patch.object(agent.client.images, 'generate') as mock_generate_image, \
             patch('pathlib.Path.mkdir', MagicMock()):
            
            # Configure mocks
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_create_thread.return_value = mock_thread
            
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_create_run.return_value = mock_run
            
            mock_wait_for_run.return_value = mock_run
            
            # Create a simple image prompt
            image_prompts = "Test image prompt"
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=image_prompts))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Mock DALL-E image generation error
            mock_generate_image.side_effect = Exception("DALL-E API error: Content policy violation")
            
            # Call the method and expect an exception
            with pytest.raises(Exception) as excinfo:
                await agent.generate_visuals(mock_context)
            
            # Assertions
            assert "DALL-E API error" in str(excinfo.value)
            
            # Verify API calls
            mock_create_thread.assert_called_once()
            mock_create_message.assert_called_once()
            mock_create_run.assert_called_once_with(
                thread_id="test_thread_id",
                assistant_id=agent.assistant_id
            )
            mock_wait_for_run.assert_called_once_with("test_thread_id", "test_run_id")
            mock_list_messages.assert_called_once_with(thread_id="test_thread_id")
            mock_generate_image.assert_called_once()

    def test_extract_image_prompts(self, agent):
        """Test the _extract_image_prompts method."""
        # Test with valid image prompts text
        image_prompts_text = """
1. "A futuristic smart city with interconnected systems"
2. "Advanced humanoid robots interacting with humans"
3. "Holographic interface displaying complex data visualization"
"""
        prompts = agent._extract_image_prompts(image_prompts_text)
        assert len(prompts) == 3
        assert "futuristic smart city" in prompts[0]
        assert "humanoid robots" in prompts[1]
        assert "Holographic interface" in prompts[2]
        
        # Test with different format
        image_prompts_text = """
Prompt 1: A futuristic smart city with interconnected systems
Prompt 2: Advanced humanoid robots interacting with humans
"""
        prompts = agent._extract_image_prompts(image_prompts_text)
        assert len(prompts) == 2
        assert "futuristic smart city" in prompts[0]
        assert "humanoid robots" in prompts[1]
        
        # Test with no prompts
        image_prompts_text = "No valid prompts here"
        prompts = agent._extract_image_prompts(image_prompts_text)
        assert len(prompts) == 1
        assert prompts[0] == "No valid prompts here"

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
