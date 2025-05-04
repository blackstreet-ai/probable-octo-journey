"""
Main entry point for the AI Video Pipeline.

This module provides the main functionality to run the video generation pipeline
from a user prompt to a finished video.
"""

import asyncio
import argparse
import json
from pathlib import Path
from typing import Dict, Any

from ai_video_pipeline.agents.executive import ExecutiveAgent
from ai_video_pipeline.agents.scriptwriter import ScriptwriterAgent
from ai_video_pipeline.agents.voice_synthesis import VoiceSynthesisAgent


async def run_pipeline(topic: str) -> Dict[str, Any]:
    """
    Run the complete video generation pipeline.
    
    Args:
        topic: The topic/idea for the video
        
    Returns:
        Dict[str, Any]: Results of the pipeline execution
    """
    # Initialize agents
    executive = ExecutiveAgent()
    scriptwriter = ScriptwriterAgent()
    voice_synthesis = VoiceSynthesisAgent()
    
    # Step 1: Create job specification
    job_result = await executive.run(topic)
    job_spec = job_result["job_spec"]
    
    # Step 2: Generate script
    script = await scriptwriter.create_script(topic, job_spec)
    
    # Step 3: Generate voice audio
    script_sections = [section.dict() for section in script.sections]
    voice_result = await voice_synthesis.synthesize_voice(script_sections)
    
    # Create asset manifest
    asset_manifest = {
        "job_id": "job_" + topic.replace(" ", "_").lower(),
        "script": script.dict(),
        "audio": {
            "clips": [clip.dict() for clip in voice_result.clips],
            "total_duration": voice_result.total_duration_seconds
        },
        "images": [],
        "videos": []
    }
    
    # Save asset manifest
    assets_dir = Path(__file__).parent.parent / "assets"
    manifest_path = assets_dir / "asset_manifest.json"
    
    with open(manifest_path, "w") as f:
        json.dump(asset_manifest, f, indent=2)
    
    return {
        "status": "completed",
        "asset_manifest": manifest_path.as_posix(),
        "script": script.dict(),
        "audio_clips": [clip.dict() for clip in voice_result.clips]
    }


def main():
    """Main entry point for the command line interface."""
    parser = argparse.ArgumentParser(description="AI Video Pipeline")
    parser.add_argument("--topic", type=str, required=True, help="Topic for the video")
    args = parser.parse_args()
    
    result = asyncio.run(run_pipeline(args.topic))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
