#!/usr/bin/env python3
"""
Simple test script for the AI Video Pipeline.

This script tests the basic functionality of the pipeline without
relying on the OpenAI Agents SDK.
"""

import asyncio
import json
import os
from pathlib import Path

from ai_video_pipeline.agents.executive import ExecutiveAgent
from ai_video_pipeline.agents.scriptwriter import ScriptwriterAgent
from ai_video_pipeline.agents.voice_synthesis import VoiceSynthesisAgent


async def test_pipeline():
    """Test the basic functionality of the pipeline."""
    print("Testing AI Video Pipeline...")
    
    # Initialize agents
    executive = ExecutiveAgent()
    scriptwriter = ScriptwriterAgent()
    voice_synthesis = VoiceSynthesisAgent()
    
    # Test Executive Agent
    print("\n1. Testing Executive Agent...")
    topic = "The future of AI"
    job_result = await executive.run(topic)
    print(f"Job spec created: {json.dumps(job_result['job_spec'], indent=2)}")
    
    # Test Scriptwriter Agent
    print("\n2. Testing Scriptwriter Agent...")
    script = await scriptwriter.create_script(topic, job_result["job_spec"])
    print(f"Script created with {len(script.sections)} sections")
    print(f"Title: {script.title}")
    print(f"First section: {script.sections[0].title}")
    
    # Test Voice Synthesis Agent
    print("\n3. Testing Voice Synthesis Agent...")
    script_sections = [section.dict() for section in script.sections]
    voice_result = await voice_synthesis.synthesize_voice(script_sections)
    print(f"Voice clips created: {len(voice_result.clips)}")
    print(f"Audio file path: {voice_result.clips[0].file_path}")
    
    # Check if the audio file was created
    if os.path.exists(voice_result.clips[0].file_path):
        print(f"Audio file successfully created at: {voice_result.clips[0].file_path}")
    else:
        print(f"Error: Audio file not created")
    
    print("\nTest completed successfully!")
    return {
        "job_spec": job_result["job_spec"],
        "script": script.dict(),
        "voice_clips": [clip.dict() for clip in voice_result.clips]
    }


if __name__ == "__main__":
    result = asyncio.run(test_pipeline())
    
    # Save the result to a file
    output_path = Path("test_result.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nTest result saved to {output_path}")
