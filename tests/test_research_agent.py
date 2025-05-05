#!/usr/bin/env python
"""
Unit tests for the ResearchAgent.

Tests the functionality of the ResearchAgent including topic research,
fact checking, and citation generation.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from agents.research import ResearchAgent


@pytest.fixture
def mock_openai():
    """Mock the OpenAI client."""
    with patch("agents.research.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_agent():
    """Mock the OpenAI Agent."""
    with patch("agents.research.Agent") as mock_agent:
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        yield mock_agent_instance


@pytest.fixture
def mock_runner():
    """Mock the OpenAI Runner."""
    with patch("agents.research.Runner") as mock_runner:
        mock_runner.run = AsyncMock()
        yield mock_runner


@pytest.fixture
def mock_yaml():
    """Mock YAML loading."""
    with patch("agents.research.yaml.safe_load") as mock_yaml:
        mock_yaml.return_value = {
            "system": "You are a research assistant",
            "user_research_topic": "Research topic: {topic}, depth: {depth}, focus: {focus}",
            "user_fact_check": "Fact check: {script}",
            "user_generate_citations": "Generate citations: {script}, style: {citation_style}"
        }
        yield mock_yaml


@pytest.fixture
def research_agent(mock_openai, mock_agent, mock_yaml):
    """Create a ResearchAgent instance with mocked dependencies."""
    with patch("agents.research.Path.open", MagicMock()):
        agent = ResearchAgent()
        return agent


@pytest.fixture
def test_context():
    """Create a test context dictionary."""
    return {
        "job_id": "test-job-123",
        "topic": "Renewable Energy",
        "output_dir": "/tmp/test_output",
        "script": "Solar energy is a renewable resource. Wind power is growing rapidly.",
        "research_depth": "comprehensive",
        "research_focus": "recent developments and statistics",
        "citation_style": "APA"
    }


class TestResearchAgent:
    """Test cases for the ResearchAgent class."""

    def test_initialization(self, research_agent):
        """Test that the ResearchAgent initializes correctly."""
        assert research_agent is not None
        assert research_agent.prompts is not None
        assert research_agent.agent is not None

    @pytest.mark.asyncio
    async def test_research_topic(self, research_agent, mock_runner, test_context):
        """Test the research_topic method."""
        # Mock the runner response
        mock_result = MagicMock()
        mock_result.final_output = "Research results about renewable energy."
        mock_runner.run.return_value = mock_result

        # Mock directory creation
        with patch("agents.research.Path.mkdir") as mock_mkdir, \
             patch("agents.research.open", MagicMock()) as mock_open, \
             patch("agents.research.log_event") as mock_log_event:
            
            result = await research_agent.research_topic(test_context)
            
            # Verify the runner was called with the correct prompt
            mock_runner.run.assert_called_once()
            
            # Verify the result contains the expected keys
            assert "research" in result
            assert "research_path" in result
            assert result["research"] == "Research results about renewable energy."
            
            # Verify logging events were called
            mock_log_event.assert_called()

    @pytest.mark.asyncio
    async def test_fact_check(self, research_agent, mock_runner, test_context):
        """Test the fact_check method."""
        # Mock the runner response
        mock_result = MagicMock()
        mock_result.final_output = "Fact check results: All claims verified."
        mock_runner.run.return_value = mock_result

        # Mock directory creation
        with patch("agents.research.Path.mkdir") as mock_mkdir, \
             patch("agents.research.open", MagicMock()) as mock_open, \
             patch("agents.research.log_event") as mock_log_event:
            
            result = await research_agent.fact_check(test_context)
            
            # Verify the runner was called with the correct prompt
            mock_runner.run.assert_called_once()
            
            # Verify the result contains the expected keys
            assert "fact_check" in result
            assert "fact_check_path" in result
            assert "script_verified" in result
            assert result["fact_check"] == "Fact check results: All claims verified."
            
            # Verify logging events were called
            mock_log_event.assert_called()

    @pytest.mark.asyncio
    async def test_generate_citations(self, research_agent, mock_runner, test_context):
        """Test the generate_citations method."""
        # Mock the runner response
        mock_result = MagicMock()
        mock_result.final_output = "Citations in APA format."
        mock_runner.run.return_value = mock_result

        # Mock directory creation
        with patch("agents.research.Path.mkdir") as mock_mkdir, \
             patch("agents.research.open", MagicMock()) as mock_open, \
             patch("agents.research.log_event") as mock_log_event:
            
            result = await research_agent.generate_citations(test_context)
            
            # Verify the runner was called with the correct prompt
            mock_runner.run.assert_called_once()
            
            # Verify the result contains the expected keys
            assert "citations" in result
            assert "citations_path" in result
            assert result["citations"] == "Citations in APA format."
            
            # Verify logging events were called
            mock_log_event.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling(self, research_agent, mock_runner, test_context):
        """Test error handling in the ResearchAgent methods."""
        # Make the runner raise an exception
        mock_runner.run.side_effect = Exception("API error")

        # Test error handling in research_topic
        with patch("agents.research.log_event") as mock_log_event, \
             pytest.raises(Exception):
            await research_agent.research_topic(test_context)
            mock_log_event.assert_called_with(
                "topic_research_failed", 
                {"job_id": "test-job-123", "error": "API error"}
            )
