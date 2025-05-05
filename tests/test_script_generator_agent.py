#!/usr/bin/env python
"""
Unit tests for the ScriptGeneratorAgent.

Tests the functionality of the ScriptGeneratorAgent including script generation,
revision, enhancement, and research integration.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

from agents.script_generator import ScriptGeneratorAgent


@pytest.fixture
def mock_openai():
    """Mock the OpenAI client."""
    with patch("agents.script_generator.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_yaml():
    """Mock YAML loading."""
    with patch("agents.script_generator.yaml.safe_load") as mock_yaml:
        mock_yaml.return_value = {
            "system": "You are a script generator",
            "user_generate_script": "Generate script: {topic}, {audience}, {tone}, {duration}, {template_format}, {template_structure}, {research}",
            "user_revise_script": "Revise script: {script}, {feedback}, {fact_check}",
            "user_enhance_script": "Enhance script: {script}, {enhancements}",
            "user_integrate_research": "Integrate research: {script}, {research}"
        }
        yield mock_yaml


@pytest.fixture
def mock_templates():
    """Mock template loading."""
    templates = {
        "narration": {
            "name": "Narration Script Template",
            "structure": "# [TITLE]\n## INTRO\n## MAIN CONTENT\n## CONCLUSION"
        },
        "interview": {
            "name": "Interview Script Template",
            "structure": "# [TITLE]\n## HOST\n## GUEST\n## QUESTIONS\n## CONCLUSION"
        },
        "news_report": {
            "name": "News Report Template",
            "structure": "# [TITLE]\n## ANCHOR\n## REPORTER\n## STORY\n## SIGN-OFF"
        }
    }
    return templates


@pytest.fixture
def script_generator(mock_openai, mock_yaml, mock_templates):
    """Create a ScriptGeneratorAgent instance with mocked dependencies."""
    with patch("agents.script_generator.Path.open", MagicMock()), \
         patch("agents.script_generator.Path.glob") as mock_glob, \
         patch("builtins.open", mock_open()):
        
        # Mock template file discovery
        mock_template_paths = [
            MagicMock(stem="narration"),
            MagicMock(stem="interview"),
            MagicMock(stem="news_report")
        ]
        mock_glob.return_value = mock_template_paths
        
        # Mock template loading
        with patch("agents.script_generator.yaml.safe_load") as mock_template_yaml:
            mock_template_yaml.side_effect = lambda f: mock_templates[next(
                t.stem for t in mock_template_paths if t.stem in str(f)
            )]
            
            agent = ScriptGeneratorAgent()
            # Manually set templates since we're mocking the file loading
            agent.templates = mock_templates
            return agent


@pytest.fixture
def test_context():
    """Create a test context dictionary."""
    return {
        "job_id": "test-job-123",
        "topic": "Artificial Intelligence Ethics",
        "audience": "general public",
        "tone": "informative",
        "duration": "5 minutes",
        "output_dir": "/tmp/test_output",
        "script_format": "narration",
        "research": "AI ethics involves principles like transparency, fairness, and accountability.",
        "script": "# AI Ethics\n\nThis is a test script about AI ethics.",
        "script_feedback": "Need more concrete examples",
        "fact_check": "All claims verified",
        "enhancements": ["hooks", "transitions", "calls_to_action"]
    }


class TestScriptGeneratorAgent:
    """Test cases for the ScriptGeneratorAgent class."""

    def test_initialization(self, script_generator):
        """Test that the ScriptGeneratorAgent initializes correctly."""
        assert script_generator is not None
        assert script_generator.prompts is not None
        assert script_generator.templates is not None
        assert "narration" in script_generator.templates
        assert "interview" in script_generator.templates
        assert "news_report" in script_generator.templates

    @pytest.mark.asyncio
    async def test_generate_script(self, script_generator, test_context):
        """Test the generate_script method."""
        # Mock the OpenAI API responses
        mock_run = MagicMock()
        mock_run.status = "completed"
        script_generator._wait_for_run = MagicMock(return_value=mock_run)
        
        mock_messages = MagicMock()
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = MagicMock()
        mock_message.content[0].text.value = "# Generated AI Ethics Script\n\nThis is a generated script about AI ethics."
        mock_messages.data = [mock_message]
        script_generator.client.beta.threads.messages.list.return_value = mock_messages
        
        # Mock directory creation
        with patch("agents.script_generator.Path.mkdir") as mock_mkdir, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("agents.script_generator.log_event") as mock_log_event:
            
            result = await script_generator.generate_script(test_context)
            
            # Verify the API was called
            script_generator.client.beta.threads.create.assert_called_once()
            script_generator.client.beta.threads.messages.create.assert_called_once()
            script_generator.client.beta.threads.runs.create.assert_called_once()
            
            # Verify the result contains the expected keys
            assert "script" in result
            assert "script_path" in result
            assert "script_format" in result
            assert "script_version" in result
            assert result["script"] == "# Generated AI Ethics Script\n\nThis is a generated script about AI ethics."
            assert result["script_format"] == "narration"
            assert result["script_version"] == "1.0"
            
            # Verify logging events were called
            mock_log_event.assert_called()

    @pytest.mark.asyncio
    async def test_revise_script(self, script_generator, test_context):
        """Test the revise_script method."""
        # Mock the OpenAI API responses
        mock_run = MagicMock()
        mock_run.status = "completed"
        script_generator._wait_for_run = MagicMock(return_value=mock_run)
        
        mock_messages = MagicMock()
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = MagicMock()
        mock_message.content[0].text.value = "# Revised AI Ethics Script\n\nThis is a revised script about AI ethics with examples."
        mock_messages.data = [mock_message]
        script_generator.client.beta.threads.messages.list.return_value = mock_messages
        
        # Mock directory creation
        with patch("agents.script_generator.Path.mkdir") as mock_mkdir, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("agents.script_generator.log_event") as mock_log_event:
            
            result = await script_generator.revise_script(test_context)
            
            # Verify the API was called
            script_generator.client.beta.threads.create.assert_called_once()
            script_generator.client.beta.threads.messages.create.assert_called_once()
            script_generator.client.beta.threads.runs.create.assert_called_once()
            
            # Verify the result contains the expected keys
            assert "script" in result
            assert "script_path" in result
            assert "script_format" in result
            assert "script_version" in result
            assert "previous_script_path" in result
            assert result["script"] == "# Revised AI Ethics Script\n\nThis is a revised script about AI ethics with examples."
            assert result["script_format"] == "narration"
            assert result["script_version"] == "1.1"
            
            # Verify logging events were called
            mock_log_event.assert_called()

    @pytest.mark.asyncio
    async def test_enhance_script(self, script_generator, test_context):
        """Test the enhance_script method."""
        # Mock the OpenAI API responses
        mock_run = MagicMock()
        mock_run.status = "completed"
        script_generator._wait_for_run = MagicMock(return_value=mock_run)
        
        mock_messages = MagicMock()
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = MagicMock()
        mock_message.content[0].text.value = "# Enhanced AI Ethics Script\n\nThis is an enhanced script with hooks and transitions."
        mock_messages.data = [mock_message]
        script_generator.client.beta.threads.messages.list.return_value = mock_messages
        
        # Mock directory creation
        with patch("agents.script_generator.Path.mkdir") as mock_mkdir, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("agents.script_generator.log_event") as mock_log_event:
            
            result = await script_generator.enhance_script(test_context)
            
            # Verify the API was called
            script_generator.client.beta.threads.create.assert_called_once()
            script_generator.client.beta.threads.messages.create.assert_called_once()
            script_generator.client.beta.threads.runs.create.assert_called_once()
            
            # Verify the result contains the expected keys
            assert "script" in result
            assert "script_path" in result
            assert "script_format" in result
            assert "script_version" in result
            assert "previous_script_path" in result
            assert "enhancements_applied" in result
            assert result["script"] == "# Enhanced AI Ethics Script\n\nThis is an enhanced script with hooks and transitions."
            assert result["script_format"] == "narration"
            assert result["script_version"] == "1.1"
            assert "hooks" in result["enhancements_applied"]
            assert "transitions" in result["enhancements_applied"]
            assert "calls_to_action" in result["enhancements_applied"]
            
            # Verify logging events were called
            mock_log_event.assert_called()

    @pytest.mark.asyncio
    async def test_integrate_research(self, script_generator, test_context):
        """Test the integrate_research method."""
        # Mock the OpenAI API responses
        mock_run = MagicMock()
        mock_run.status = "completed"
        script_generator._wait_for_run = MagicMock(return_value=mock_run)
        
        mock_messages = MagicMock()
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = [MagicMock()]
        mock_message.content[0].text = MagicMock()
        mock_message.content[0].text.value = "# Researched AI Ethics Script\n\nThis script now includes research on transparency, fairness, and accountability."
        mock_messages.data = [mock_message]
        script_generator.client.beta.threads.messages.list.return_value = mock_messages
        
        # Mock directory creation
        with patch("agents.script_generator.Path.mkdir") as mock_mkdir, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("agents.script_generator.log_event") as mock_log_event:
            
            result = await script_generator.integrate_research(test_context)
            
            # Verify the API was called
            script_generator.client.beta.threads.create.assert_called_once()
            script_generator.client.beta.threads.messages.create.assert_called_once()
            script_generator.client.beta.threads.runs.create.assert_called_once()
            
            # Verify the result contains the expected keys
            assert "script" in result
            assert "script_path" in result
            assert "script_format" in result
            assert "script_version" in result
            assert "previous_script_path" in result
            assert "research_integrated" in result
            assert result["script"] == "# Researched AI Ethics Script\n\nThis script now includes research on transparency, fairness, and accountability."
            assert result["script_format"] == "narration"
            assert result["script_version"] == "1.1"
            assert result["research_integrated"] is True
            
            # Verify logging events were called
            mock_log_event.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling(self, script_generator, test_context):
        """Test error handling in the ScriptGeneratorAgent methods."""
        # Make the API raise an exception
        script_generator.client.beta.threads.create.side_effect = Exception("API error")

        # Test error handling in generate_script
        with patch("agents.script_generator.log_event") as mock_log_event, \
             pytest.raises(Exception):
            await script_generator.generate_script(test_context)
            mock_log_event.assert_called_with(
                "script_generation_failed", 
                {"job_id": "test-job-123", "error": "API error"}
            )
