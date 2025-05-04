"""
Audio-Mixer Agent module.

This module implements the Audio-Mixer Agent, which is responsible for
mixing voice and music tracks with proper ducking and loudness normalization.
"""

from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
import os
import time
import logging
import subprocess
import json
import tempfile
from pydantic import BaseModel, Field, validator

from ai_video_pipeline.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

# Mock Agent class for testing without OpenAI Agents SDK
class Agent:
    def __init__(self, name, instructions=None, handoffs=None):
        self.name = name
        self.instructions = instructions
        self.handoffs = handoffs or []


class MixParams(BaseModel):
    """
    Parameters for audio mixing.
    
    Args:
        voice_file: Path to the voice file
        music_file: Path to the music file
        output_file: Path to save the mixed file
        voice_gain_db: Gain to apply to voice in dB
        music_gain_db: Gain to apply to music in dB
        duck_percent: Percentage to reduce music during voice (0-100)
        duck_attack_ms: Attack time for ducking in milliseconds
        duck_release_ms: Release time for ducking in milliseconds
        target_lufs: Target loudness in LUFS
        fade_in_seconds: Fade-in duration in seconds
        fade_out_seconds: Fade-out duration in seconds
    """
    voice_file: str
    music_file: str
    output_file: Optional[str] = None
    voice_gain_db: float = 0.0
    music_gain_db: float = -6.0
    duck_percent: float = Field(50.0, ge=0.0, le=100.0)
    duck_attack_ms: int = 200
    duck_release_ms: int = 500
    target_lufs: float = -14.0
    fade_in_seconds: float = 1.0
    fade_out_seconds: float = 3.0
    
    @validator('voice_file', 'music_file')
    def file_exists(cls, v):
        """Validate that the file exists."""
        if not os.path.exists(v):
            raise ValueError(f"File does not exist: {v}")
        return v


class AudioMixResult(BaseModel):
    """
    Result of the audio mixing process.
    
    Args:
        output_file: Path to the mixed audio file
        duration_seconds: Duration of the mixed audio in seconds
        voice_file: Path to the original voice file
        music_file: Path to the original music file
        params: Parameters used for mixing
        loudness_lufs: Measured loudness of the output in LUFS
    """
    output_file: str
    duration_seconds: float
    voice_file: str
    music_file: str
    params: MixParams
    loudness_lufs: float


class AudioMixerAgent:
    """
    Audio-Mixer Agent that mixes voice and music tracks with proper ducking
    and loudness normalization.
    """
    
    def __init__(self, name: str = "Audio-Mixer"):
        """
        Initialize the Audio-Mixer Agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.agent = Agent(
            name=name,
            instructions=(
                "You are the Audio-Mixer Agent responsible for mixing voice and "
                "music tracks with proper ducking and loudness normalization. "
                "Your job is to create professional-sounding audio mixes for videos."
            ),
        )
        
        # Ensure the assets directory exists
        self.assets_dir = Path(os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../..", 
            "assets",
            "audio",
            "mixed"
        )))
        os.makedirs(self.assets_dir, exist_ok=True)
        
        # Check if ffmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          check=True)
            self.ffmpeg_available = True
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("ffmpeg not found. Audio mixing will not work.")
            self.ffmpeg_available = False
    
    def _run_ffmpeg_command(self, command: List[str]) -> Tuple[int, str, str]:
        """
        Run an ffmpeg command and return the result.
        
        Args:
            command: List of command arguments
            
        Returns:
            Tuple[int, str, str]: Return code, stdout, stderr
        """
        logger.debug(f"Running ffmpeg command: {' '.join(command)}")
        
        try:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            return process.returncode, process.stdout, process.stderr
            
        except Exception as e:
            logger.error(f"Error running ffmpeg command: {e}")
            return 1, "", str(e)
    
    def _get_audio_duration(self, file_path: str) -> float:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            float: Duration in seconds
        """
        command = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "json", 
            file_path
        ]
        
        returncode, stdout, stderr = self._run_ffmpeg_command(command)
        
        if returncode != 0:
            logger.error(f"Error getting audio duration: {stderr}")
            return 0.0
        
        try:
            data = json.loads(stdout)
            return float(data["format"]["duration"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing ffprobe output: {e}")
            return 0.0
    
    def _get_audio_loudness(self, file_path: str) -> float:
        """
        Measure the integrated loudness of an audio file in LUFS.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            float: Loudness in LUFS
        """
        command = [
            "ffmpeg",
            "-i", file_path,
            "-af", "loudnorm=print_format=json",
            "-f", "null",
            "-"
        ]
        
        returncode, stdout, stderr = self._run_ffmpeg_command(command)
        
        if returncode != 0:
            logger.error(f"Error measuring audio loudness: {stderr}")
            return -24.0  # Default value
        
        # Extract the JSON part from stderr
        try:
            json_start = stderr.find("{")
            json_end = stderr.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = stderr[json_start:json_end]
                data = json.loads(json_str)
                return float(data.get("input_i", "-24.0"))
            else:
                logger.error("Could not find JSON data in ffmpeg output")
                return -24.0
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing loudnorm output: {e}")
            return -24.0
    
    def _create_ducking_filter(self, params: MixParams) -> str:
        """
        Create an FFmpeg filter for ducking the music when voice is present.
        
        Args:
            params: Mix parameters
            
        Returns:
            str: FFmpeg filter string
        """
        # Convert duck percentage to a gain factor (0-1)
        duck_factor = 1.0 - (params.duck_percent / 100.0)
        
        # Convert attack and release times from ms to seconds
        attack_time = params.duck_attack_ms / 1000.0
        release_time = params.duck_release_ms / 1000.0
        
        # Create a simpler filter chain that doesn't use agate (which has issues with makeup parameter)
        # Instead, use a combination of volume detection and sidechaincompress
        filter_str = (
            # Split the voice into two streams: one for mixing and one for sidechaining
            "[0:a]asplit=2[voicemix][voicedet];"
            
            # Use the voice detection stream for sidechaining
            "[voicedet]volume=1.5,aformat=sample_fmts=fltp[voicegate];"
            
            # Apply sidechain compression to the music when voice is present
            "[1:a][voicegate]sidechaincompress=threshold=0.05:ratio=5:attack={attack}:"
            "release={release}:level_in=1:level_sc=1:detection=rms[musicducked];"
            
            # Mix the voice and ducked music with appropriate volume levels
            "[voicemix]volume={voice_gain}dB[voicevol];"
            "[musicducked]volume={music_gain}dB[musicvol];"
            "[voicevol][musicvol]amix=inputs=2:duration=longest[audioout]"
        ).format(
            attack=attack_time,
            release=release_time,
            voice_gain=params.voice_gain_db,
            music_gain=params.music_gain_db
        )
        
        return filter_str
    
    def _normalize_loudness(self, input_file: str, output_file: str, target_lufs: float) -> bool:
        """
        Normalize the loudness of an audio file to a target LUFS value.
        
        Args:
            input_file: Path to the input audio file
            output_file: Path to save the normalized audio file
            target_lufs: Target loudness in LUFS
            
        Returns:
            bool: True if successful, False otherwise
        """
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", input_file,
            "-af", f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11.0",
            "-ar", "48000",  # Set output sample rate
            output_file
        ]
        
        returncode, stdout, stderr = self._run_ffmpeg_command(command)
        
        if returncode != 0:
            logger.error(f"Error normalizing loudness: {stderr}")
            return False
        
        logger.info(f"Normalized audio to {target_lufs} LUFS: {output_file}")
        return True
    
    def _apply_fades(self, input_file: str, output_file: str, fade_in: float, fade_out: float) -> bool:
        """
        Apply fade-in and fade-out to an audio file.
        
        Args:
            input_file: Path to the input audio file
            output_file: Path to save the processed audio file
            fade_in: Fade-in duration in seconds
            fade_out: Fade-out duration in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Get the duration of the audio file
        duration = self._get_audio_duration(input_file)
        
        if duration <= 0:
            logger.error(f"Could not determine duration of {input_file}")
            return False
        
        # Create the fade filter
        fade_filter = f"afade=t=in:st=0:d={fade_in},afade=t=out:st={duration-fade_out}:d={fade_out}"
        
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-i", input_file,
            "-af", fade_filter,
            output_file
        ]
        
        returncode, stdout, stderr = self._run_ffmpeg_command(command)
        
        if returncode != 0:
            logger.error(f"Error applying fades: {stderr}")
            return False
        
        logger.info(f"Applied fades to audio: {output_file}")
        return True
    
    async def mix_audio(self, params: MixParams) -> AudioMixResult:
        """
        Mix voice and music tracks with ducking and loudness normalization.
        
        Args:
            params: Mix parameters
            
        Returns:
            AudioMixResult: Result of the audio mixing process
        """
        if not self.ffmpeg_available:
            raise RuntimeError("ffmpeg is not available. Cannot mix audio.")
        
        logger.info(f"Mixing audio with parameters: {params}")
        
        # Create output file path if not provided
        if params.output_file is None:
            timestamp = int(time.time())
            output_filename = f"mixed_{timestamp}.wav"
            output_path = str(self.assets_dir / output_filename)
        else:
            output_path = params.output_file
        
        # Create temporary files for intermediate steps
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Mix voice and music with ducking
            mixed_temp = os.path.join(temp_dir, "mixed_temp.wav")
            
            # Create the filter for ducking
            filter_complex = self._create_ducking_filter(params)
            
            # Run the initial mix command
            mix_command = [
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", params.voice_file,  # Voice input
                "-i", params.music_file,  # Music input
                "-filter_complex", filter_complex,
                "-map", "[audioout]",
                "-ar", "48000",  # Set output sample rate
                mixed_temp
            ]
            
            returncode, stdout, stderr = self._run_ffmpeg_command(mix_command)
            
            if returncode != 0:
                logger.error(f"Error mixing audio: {stderr}")
                raise RuntimeError(f"Error mixing audio: {stderr}")
            
            # Step 2: Apply fades
            faded_temp = os.path.join(temp_dir, "faded_temp.wav")
            fade_success = self._apply_fades(
                mixed_temp, 
                faded_temp, 
                params.fade_in_seconds, 
                params.fade_out_seconds
            )
            
            if not fade_success:
                logger.warning("Failed to apply fades, continuing with unfaded mix")
                faded_temp = mixed_temp
            
            # Step 3: Normalize loudness
            normalize_success = self._normalize_loudness(
                faded_temp,
                output_path,
                params.target_lufs
            )
            
            if not normalize_success:
                logger.warning("Failed to normalize loudness, using mix without normalization")
                # Copy the faded mix to the output path
                copy_command = ["cp", faded_temp, output_path]
                subprocess.run(copy_command, check=False)
        
        # Get the final audio duration and loudness
        duration = self._get_audio_duration(output_path)
        loudness = self._get_audio_loudness(output_path)
        
        logger.info(f"Audio mixing completed: {output_path}")
        logger.info(f"Duration: {duration:.2f} seconds, Loudness: {loudness:.2f} LUFS")
        
        return AudioMixResult(
            output_file=output_path,
            duration_seconds=duration,
            voice_file=params.voice_file,
            music_file=params.music_file,
            params=params,
            loudness_lufs=loudness
        )
