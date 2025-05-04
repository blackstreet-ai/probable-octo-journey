"""
ElevenLabs API wrapper for voice synthesis.

This module provides a wrapper around the ElevenLabs API for text-to-speech
functionality used by the Voice-Synthesis Agent.
"""

from typing import Dict, Any, Optional, BinaryIO, List
import os
import json
import requests
import time
from pathlib import Path
import logging

from ai_video_pipeline.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

class VoiceSettings:
    """
    Voice settings for ElevenLabs TTS.
    
    Args:
        stability: Voice stability (0.0-1.0)
        similarity_boost: Voice similarity boost (0.0-1.0)
        style: Optional speaking style
        use_speaker_boost: Whether to use speaker boost
    """
    def __init__(
        self,
        stability: float = 0.75,
        similarity_boost: float = 0.75,
        style: Optional[float] = None,
        use_speaker_boost: bool = True
    ):
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.use_speaker_boost = use_speaker_boost
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for API request."""
        settings_dict = {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "use_speaker_boost": self.use_speaker_boost
        }
        if self.style is not None:
            settings_dict["style"] = self.style
        return settings_dict


class ElevenLabsAPI:
    """
    Wrapper for the ElevenLabs text-to-speech API.
    
    This class provides methods to interact with the ElevenLabs API
    for generating realistic voice audio from text.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the ElevenLabs API wrapper.
        
        Args:
            api_key: Optional API key (defaults to environment variable)
        """
        self.api_key = api_key or settings.elevenlabs_api_key
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")
            
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Rate limiting parameters
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def list_voices(self) -> Dict[str, Any]:
        """
        List available voices from ElevenLabs API.
        
        Returns:
            Dict[str, Any]: List of available voices
        """
        endpoint = f"{self.base_url}/voices"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(endpoint, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error fetching voices (attempt {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to fetch voices after {self.max_retries} attempts")
                    raise
    
    def get_voice_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a voice by name.
        
        Args:
            name: Name of the voice to find
            
        Returns:
            Optional[Dict[str, Any]]: Voice data if found, None otherwise
        """
        voices = self.list_voices()
        for voice in voices.get("voices", []):
            if voice.get("name", "").lower() == name.lower():
                return voice
        return None
    
    def get_default_voice(self) -> Dict[str, Any]:
        """
        Get the default voice or first available voice.
        
        Returns:
            Dict[str, Any]: Default voice data
        """
        # Try to get the voice specified in settings
        default_voice_id = settings.default_voice_id
        
        voices = self.list_voices()
        if not voices.get("voices"):
            raise ValueError("No voices available from ElevenLabs API")
            
        # If default voice ID is specified, try to find it
        if default_voice_id and default_voice_id != "default":
            for voice in voices.get("voices", []):
                if voice.get("voice_id") == default_voice_id:
                    return voice
        
        # Otherwise return the first voice
        return voices["voices"][0]
    
    def synthesize_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        voice_settings: Optional[VoiceSettings] = None,
        output_path: Optional[Path] = None,
        model_id: str = "eleven_multilingual_v2"
    ) -> Path:
        """
        Synthesize speech from text using ElevenLabs API.
        
        Args:
            text: Text to synthesize
            voice_id: ID of the voice to use (defaults to settings or first available)
            voice_settings: Voice settings to use
            output_path: Optional path to save the audio file
            model_id: TTS model ID to use
            
        Returns:
            Path: Path to the generated audio file
        """
        # If no voice ID is provided, get the default voice
        if not voice_id or voice_id == "default":
            voice = self.get_default_voice()
            voice_id = voice.get("voice_id")
        
        # If no voice settings are provided, use defaults
        if voice_settings is None:
            voice_settings = VoiceSettings()
        
        # If no output path is provided, create one in the assets directory
        if output_path is None:
            timestamp = int(time.time())
            os.makedirs(settings.audio_dir, exist_ok=True)
            output_path = settings.audio_dir / f"{voice_id}_{timestamp}.mp3"
        
        # Prepare the request payload
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings.to_dict()
        }
        
        endpoint = f"{self.base_url}/text-to-speech/{voice_id}"
        headers = {**self.headers, "Accept": "audio/mpeg"}
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Synthesizing speech with voice {voice_id}")
                response = requests.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                
                # Save the audio file
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Speech synthesized successfully: {output_path}")
                return output_path
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error synthesizing speech (attempt {attempt+1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to synthesize speech after {self.max_retries} attempts")
                    raise
    
    def synthesize_speech_chunks(
        self,
        text_chunks: List[Dict[str, str]],
        voice_id: Optional[str] = None,
        voice_settings: Optional[VoiceSettings] = None,
        output_dir: Optional[Path] = None,
        model_id: str = "eleven_multilingual_v2"
    ) -> List[Dict[str, Any]]:
        """
        Synthesize speech from multiple text chunks.
        
        Args:
            text_chunks: List of dictionaries with 'section_id' and 'content' keys
            voice_id: ID of the voice to use
            voice_settings: Voice settings to use
            output_dir: Directory to save audio files (defaults to settings.audio_dir)
            model_id: TTS model ID to use
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries with section_id, text, file_path
        """
        if output_dir is None:
            output_dir = settings.audio_dir
            
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        for chunk in text_chunks:
            section_id = chunk.get("section_id", f"section_{len(results)}")
            content = chunk.get("content", "")
            
            if not content.strip():
                logger.warning(f"Empty content for section {section_id}, skipping")
                continue
                
            timestamp = int(time.time())
            output_path = output_dir / f"{section_id}_{timestamp}.mp3"
            
            try:
                file_path = self.synthesize_speech(
                    text=content,
                    voice_id=voice_id,
                    voice_settings=voice_settings,
                    output_path=output_path,
                    model_id=model_id
                )
                
                results.append({
                    "section_id": section_id,
                    "text": content,
                    "file_path": str(file_path)
                })
                
            except Exception as e:
                logger.error(f"Error synthesizing speech for section {section_id}: {e}")
                # Continue with other chunks even if one fails
        
        return results
