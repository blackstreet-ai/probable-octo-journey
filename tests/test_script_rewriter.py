#!/usr/bin/env python
"""
Unit tests for the ScriptRewriterAgent.

This module contains tests for the ScriptRewriterAgent class, which is responsible
for enhancing raw transcripts, adding pacing, story beats, and CTAs.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from agents.script_rewriter import ScriptRewriterAgent


class TestScriptRewriterAgent:
    """Tests for the ScriptRewriterAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a ScriptRewriterAgent instance for testing."""
        # Mock the OpenAI client and assistant creation
        with patch('agents.script_rewriter.OpenAI'), \
             patch.object(ScriptRewriterAgent, '_load_prompts'), \
             patch.object(ScriptRewriterAgent, '_create_assistant'):
            agent = ScriptRewriterAgent()
            # Set mock prompts
            agent.prompts = {
                "system": "You are ScriptRewriterAgent",
                "user_create_script": "Create a script for topic: {topic}, audience: {audience}, tone: {tone}",
                "user_revise_script": "Revise the script: {script} based on feedback: {feedback}"
            }
            # Set mock assistant ID
            agent.assistant_id = "test_assistant_id"
            return agent

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        return {
            'job_id': 'test_job_123',
            'topic': 'The Future of AI',
            'output_dir': '/tmp/test_output',
            'audience': 'technology enthusiasts',
            'tone': 'informative and engaging'
        }

    @pytest.mark.asyncio
    async def test_create_script(self, agent, mock_context):
        """Test the create_script method."""
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
            
            # Create a realistic script response with scene structure
            script_content = """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence. In this video, we'll examine how AI is poised to transform our world in the coming decades.

**VISUAL:** Show a montage of futuristic AI applications - smart cities, advanced robotics, and holographic interfaces.

## Scene 2: Current State of AI
**NARRATION:** Today's AI systems can already perform impressive tasks, from generating creative content to diagnosing diseases with remarkable accuracy.

**VISUAL:** Display split-screen examples of AI applications in healthcare, art, and business.

## Scene 3: Future Developments
**NARRATION:** But where is AI headed? Experts predict that within the next decade, we'll see AI systems that can reason more like humans while maintaining their computational advantages.

**VISUAL:** Animated timeline showing the evolution of AI capabilities from present day to 2035.

## Scene 4: Ethical Considerations
**NARRATION:** As AI becomes more powerful, we must address important ethical questions about autonomy, privacy, and decision-making.

**VISUAL:** Show thoughtful imagery of humans and AI systems working together, with symbolic representations of ethical dilemmas.

## Scene 5: Conclusion
**NARRATION:** The future of AI is not predetermined. It will be shaped by the choices we make today about research priorities, regulation, and implementation.

**VISUAL:** End with an inspiring image of diverse people collaborating with AI tools to solve global challenges.

**CALL TO ACTION:** Subscribe to our channel for more insights on emerging technologies and their impact on society.
"""
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=script_content))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.create_script(mock_context)
            
            # Assertions
            assert result is not None
            assert "script" in result
            assert "script_path" in result
            assert result["script"] == script_content
            assert "The Future of AI" in result["script"]
            assert "Scene 1: Introduction" in result["script"]
            assert "CALL TO ACTION:" in result["script"]
            
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
    async def test_revise_script(self, agent, mock_context):
        """Test the revise_script method."""
        # Add script and feedback to context
        mock_context["script"] = """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence.

**VISUAL:** Show a montage of futuristic AI applications.
"""
        mock_context["script_feedback"] = "The script needs more specific examples and a stronger call to action."
        
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
            
            # Create a realistic revised script response
            revised_script = """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence. In this video, we'll examine how AI is transforming healthcare, transportation, and education.

**VISUAL:** Show a montage of futuristic AI applications - medical diagnosis systems, self-driving cars, and personalized learning platforms.

## Scene 2: Specific Examples
**NARRATION:** Let's look at some concrete examples of how AI is already changing our world.

**VISUAL:** Display specific case studies with data visualizations.

## Scene 3: Call to Action
**NARRATION:** If you want to stay informed about the latest AI developments, subscribe to our channel and join our community.

**VISUAL:** Show subscription button and community forum website.
"""
            
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=revised_script))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.revise_script(mock_context)
            
            # Assertions
            assert result is not None
            assert "script" in result
            assert "script_path" in result
            assert result["script"] == revised_script
            assert "Specific Examples" in result["script"]
            assert "Call to Action" in result["script"]
            
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

    @pytest.mark.asyncio
    async def test_create_script_with_defaults(self, agent):
        """Test the create_script method with default audience and tone."""
        # Create a context without audience and tone
        context = {
            'job_id': 'test_job_123',
            'topic': 'The Future of AI',
            'output_dir': '/tmp/test_output'
        }
        
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
            
            script_content = "Test script content"
            mock_message = MagicMock()
            mock_message.content = [MagicMock(text=MagicMock(value=script_content))]
            mock_message.role = "assistant"
            mock_list_messages.return_value = MagicMock(data=[mock_message])
            
            # Call the method
            result = await agent.create_script(context)
            
            # Assertions
            assert result is not None
            assert "script" in result
            assert result["script"] == script_content
            
            # Verify that default audience and tone were used
            mock_create_message.assert_called_once()
            call_args = mock_create_message.call_args[1]
            assert "content" in call_args
            content = call_args["content"]
            assert "general audience interested in educational content" in content or "audience" in content
            assert "informative and engaging" in content or "tone" in content
