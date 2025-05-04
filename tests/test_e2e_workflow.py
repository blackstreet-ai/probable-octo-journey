"""
End-to-end tests for the AI Video Pipeline workflow.

This module tests the complete workflow from user prompt to asset generation.
"""

import os
import json
import pytest
from pathlib import Path
import asyncio
from typing import Dict, Any

from ai_video_pipeline.agents.executive import ExecutiveAgent
from ai_video_pipeline.agents.scriptwriter import ScriptwriterAgent
from ai_video_pipeline.agents.voice_synthesis import VoiceSynthesisAgent
from ai_video_pipeline.main import run_pipeline


@pytest.fixture
def assets_dir() -> Path:
    """Fixture for the assets directory."""
    base_dir = Path(__file__).parent.parent
    return base_dir / "assets"


@pytest.mark.asyncio
async def test_executive_agent():
    """Test that the Executive Agent creates a valid job specification."""
    # Arrange
    agent = ExecutiveAgent()
    topic = "The history of artificial intelligence"
    
    # Act
    result = await agent.run(topic)
    
    # Assert
    assert result["status"] == "initialized"
    assert "job_spec" in result
    assert result["job_spec"]["topic"] == topic
    assert result["job_spec"]["title"] == "Sample Video"
    assert result["job_spec"]["runtime"] > 0


@pytest.mark.asyncio
async def test_scriptwriter_agent():
    """Test that the Scriptwriter Agent creates a valid script."""
    # Arrange
    agent = ScriptwriterAgent()
    topic = "The history of artificial intelligence"
    job_spec = {
        "title": "AI History",
        "tone": "educational",
        "runtime": 60,
        "target_platform": "YouTube"
    }
    
    # Act
    script = await agent.create_script(topic, job_spec)
    
    # Assert
    assert script.title == "AI History"
    assert len(script.sections) > 0
    assert script.sections[0].content is not None
    assert script.sections[0].duration_seconds > 0


@pytest.mark.asyncio
async def test_voice_synthesis_agent():
    """Test that the Voice-Synthesis Agent creates audio files."""
    # Arrange
    agent = VoiceSynthesisAgent()
    script_sections = [{
        "section_id": "section_1",
        "title": "Introduction",
        "content": "Hello World. This is a test.",
        "duration_seconds": 5
    }]
    
    # Act
    result = await agent.synthesize_voice(script_sections)
    
    # Assert
    assert len(result.clips) > 0
    assert os.path.exists(result.clips[0].file_path)
    assert result.total_duration_seconds > 0


@pytest.mark.asyncio
async def test_e2e_workflow(assets_dir: Path):
    """Test the complete end-to-end workflow."""
    # Arrange
    topic = "The future of AI"
    manifest_path = assets_dir / "asset_manifest.json"
    if manifest_path.exists():
        os.remove(manifest_path)
    
    # Act
    result = await run_pipeline(topic)
    
    # Assert
    assert result["status"] == "completed"
    assert "script" in result
    assert len(result["audio_clips"]) > 0
    assert os.path.exists(manifest_path)
    
    # Verify manifest content
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    
    assert "job_id" in manifest
    assert "script" in manifest
    assert "audio" in manifest
    assert len(manifest["audio"]["clips"]) > 0


@pytest.mark.asyncio
async def test_e2e_workflow_edge_case():
    """Test the workflow with an edge case (empty topic)."""
    # Arrange
    topic = ""
    
    # Act & Assert
    # The workflow should still complete without errors
    result = await run_pipeline(topic)
    assert result["status"] == "completed"
    assert "script" in result


@pytest.mark.asyncio
async def test_e2e_workflow_failure_case():
    """
    Test a potential failure case.
    
    This test simulates what would happen if we tried to process
    an extremely long topic that might cause issues.
    """
    # Arrange
    # Create a very long topic that might cause issues in a real implementation
    topic = "A" * 10000
    
    # Act
    result = await run_pipeline(topic)
    
    # Assert
    # Even with a very long topic, the workflow should complete
    assert result["status"] == "completed"
    assert "script" in result
