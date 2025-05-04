"""
Voice-Synthesis Agent module.

This module implements the Voice-Synthesis Agent, which is responsible for
generating voiceover audio from script text using text-to-speech services.
"""

from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import os
import time
import logging
from pydantic import BaseModel, Field

from ai_video_pipeline.tools.elevenlabs import ElevenLabsAPI, VoiceSettings
from ai_video_pipeline.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

# Mock Agent class for testing without OpenAI Agents SDK
class Agent:
    def __init__(self, name, instructions=None, handoffs=None):
        self.name = name
        self.instructions = instructions
        self.handoffs = handoffs or []


class VoiceParams(BaseModel):
    """
    Parameters for voice synthesis.
    
    Args:
        voice_id: ID of the voice to use
        stability: Voice stability parameter (0.0-1.0)
        similarity_boost: Voice similarity boost parameter (0.0-1.0)
        style: Optional speaking style
        speaking_rate: Speaking rate multiplier (0.5-2.0)
    """
    voice_id: str = "default"
    stability: float = Field(0.75, ge=0.0, le=1.0)
    similarity_boost: float = Field(0.75, ge=0.0, le=1.0)
    style: Optional[float] = None
    speaking_rate: float = Field(1.0, ge=0.5, le=2.0)


class VoiceClip(BaseModel):
    """
    A generated voice clip.
    
    Args:
        section_id: ID of the script section this clip corresponds to
        text: The text that was synthesized
        file_path: Path to the generated audio file
        duration_seconds: Duration of the clip in seconds
    """
    section_id: str
    text: str
    file_path: str
    duration_seconds: float = 0.0


class VoiceSynthesisResult(BaseModel):
    """
    Result of the voice synthesis process.
    
    Args:
        clips: List of generated voice clips
        total_duration_seconds: Total duration of all clips
        voice_params: Parameters used for synthesis
    """
    clips: List[VoiceClip]
    total_duration_seconds: float = 0.0
    voice_params: VoiceParams


class VoiceSynthesisAgent:
    """
    Voice-Synthesis Agent that generates voiceover audio from script text
    using text-to-speech services like ElevenLabs.
    """
    
    def __init__(self, name: str = "Voice-Synthesis"):
        """
        Initialize the Voice-Synthesis Agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.agent = Agent(
            name=name,
            instructions=(
                "You are the Voice-Synthesis Agent responsible for generating "
                "natural-sounding voiceover audio from script text. Your job is to "
                "take script sections and transform them into high-quality audio "
                "using text-to-speech services."
            ),
        )
        
        # Initialize the ElevenLabs API client
        self.elevenlabs_api = ElevenLabsAPI()
        
        # Ensure the assets directory exists
        self.assets_dir = Path(os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../..", 
            "assets",
            "audio"
        )))
        os.makedirs(self.assets_dir, exist_ok=True)
    
    async def synthesize_voice(
        self, 
        script_sections: List[Dict[str, Any]], 
        voice_params: Optional[VoiceParams] = None
    ) -> VoiceSynthesisResult:
        """
        Synthesize voice audio from script sections.
        
        Args:
            script_sections: List of script sections to synthesize
            voice_params: Optional voice parameters
            
        Returns:
            VoiceSynthesisResult: Result of the voice synthesis process
        """
        if voice_params is None:
            voice_params = VoiceParams()
        
        # Convert VoiceParams to ElevenLabs VoiceSettings
        voice_settings = VoiceSettings(
            stability=voice_params.stability,
            similarity_boost=voice_params.similarity_boost,
            style=voice_params.style,
            use_speaker_boost=True
        )
        
        # Synthesize speech for each script section
        start_time = time.time()
        logger.info(f"Starting voice synthesis for {len(script_sections)} sections")
        
        synthesis_results = self.elevenlabs_api.synthesize_speech_chunks(
            text_chunks=script_sections,
            voice_id=voice_params.voice_id,
            voice_settings=voice_settings,
            output_dir=self.assets_dir
        )
        
        # Create VoiceClip objects from synthesis results
        clips = []
        for result in synthesis_results:
            clip = VoiceClip(
                section_id=result["section_id"],
                text=result["text"],
                file_path=result["file_path"],
                duration_seconds=10.0  # TODO: Calculate actual duration using ffprobe
            )
            clips.append(clip)
        
        total_duration = sum(clip.duration_seconds for clip in clips)
        
        logger.info(f"Voice synthesis completed in {time.time() - start_time:.2f} seconds")
        logger.info(f"Generated {len(clips)} audio clips with total duration of {total_duration:.2f} seconds")
        
        return VoiceSynthesisResult(
            clips=clips,
            total_duration_seconds=total_duration,
            voice_params=voice_params
        )
