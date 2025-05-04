#!/usr/bin/env python
"""
MusicSupervisorAgent: Selects background music, handles tone/tempo, sidechaining.

This agent selects appropriate music tracks based on video content, mood, and genre,
and processes them for optimal integration with voiceover.
"""

import json
import logging
import os
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads.run import Run

from tools.observability import log_event, track_duration

# Configure logging
logger = logging.getLogger(__name__)

class MusicSupervisorAgent:
    """
    Agent for selecting and processing background music for videos.
    
    This agent selects appropriate music tracks based on video content, mood, and genre,
    and processes them for optimal integration with voiceover.
    """
    
    def __init__(self):
        """Initialize the MusicSupervisorAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self._load_prompts()
        self._create_assistant()
        
        # Music library path
        self.music_library_path = Path(__file__).parent.parent / "assets" / "music"
        self.music_library_path.mkdir(parents=True, exist_ok=True)
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "music_supervisor.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for MusicSupervisorAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _create_assistant(self) -> None:
        """Create or retrieve the OpenAI Assistant for this agent."""
        # Check if assistant ID is stored in environment variable
        assistant_id = os.environ.get("MUSIC_SUPERVISOR_ASSISTANT_ID")
        
        if assistant_id:
            try:
                # Try to retrieve the existing assistant
                self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant_id
                logger.info(f"Retrieved existing MusicSupervisorAgent assistant: {assistant_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
        
        # Create a new assistant
        try:
            self.assistant = self.client.beta.assistants.create(
                name="MusicSupervisorAgent",
                description="Selects and processes background music for videos",
                model="gpt-4-turbo",
                instructions=self.prompts["system"],
                tools=[
                    {"type": "function", "function": {
                            "name": "list_available_music",
                            "description": "List available music tracks in the library",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "mood": {
                                        "type": "string",
                                        "description": "Optional mood filter (e.g., 'upbeat', 'dramatic')"
                                    },
                                    "genre": {
                                        "type": "string",
                                        "description": "Optional genre filter (e.g., 'electronic', 'acoustic')"
                                    }
                                }
                            }
                        }
                    },
                    {"type": "function", "function": {
                            "name": "process_music_track",
                            "description": "Process a music track for integration with voiceover",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "music_track": {
                                        "type": "string",
                                        "description": "Path to the music track"
                                    },
                                    "voiceover_path": {
                                        "type": "string",
                                        "description": "Path to the voiceover file"
                                    },
                                    "output_path": {
                                        "type": "string",
                                        "description": "Path to save the processed audio"
                                    },
                                    "duck_amount": {
                                        "type": "number",
                                        "description": "Amount to reduce music volume during voiceover (in dB)"
                                    },
                                    "target_lufs": {
                                        "type": "number",
                                        "description": "Target loudness in LUFS"
                                    }
                                },
                                "required": ["music_track", "voiceover_path", "output_path"]
                            }
                        }
                    }
                ]
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new MusicSupervisorAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise
    
    def _list_available_music(self, mood: Optional[str] = None, genre: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available music tracks in the library.
        
        Args:
            mood: Optional mood filter
            genre: Optional genre filter
            
        Returns:
            List[Dict[str, Any]]: List of available music tracks with metadata
        """
        # This is a simplified implementation that would be expanded in a real system
        # with a proper music library and metadata database
        
        # For now, we'll just list the files in the music library
        music_files = list(self.music_library_path.glob("*.mp3"))
        
        # If there are no music files, create a placeholder
        if not music_files:
            # Create a placeholder music directory
            placeholder_path = self.music_library_path / "placeholder"
            placeholder_path.mkdir(parents=True, exist_ok=True)
            
            # Define some placeholder tracks
            placeholder_tracks = [
                {"filename": "upbeat_corporate.mp3", "mood": "upbeat", "genre": "corporate"},
                {"filename": "inspirational_ambient.mp3", "mood": "inspirational", "genre": "ambient"},
                {"filename": "dramatic_orchestral.mp3", "mood": "dramatic", "genre": "orchestral"},
                {"filename": "relaxed_acoustic.mp3", "mood": "relaxed", "genre": "acoustic"},
                {"filename": "energetic_electronic.mp3", "mood": "energetic", "genre": "electronic"}
            ]
            
            # Create placeholder JSON files with metadata
            for track in placeholder_tracks:
                metadata_path = placeholder_path / f"{track['filename']}.json"
                with open(metadata_path, "w") as f:
                    json.dump({
                        "filename": track["filename"],
                        "title": track["filename"].replace("_", " ").replace(".mp3", "").title(),
                        "artist": "AI Video Automation",
                        "mood": track["mood"],
                        "genre": track["genre"],
                        "duration": 180,  # 3 minutes
                        "license": "CC0",
                        "path": str(placeholder_path / track["filename"])
                    }, f, indent=2)
            
            # Return the placeholder tracks
            tracks = []
            for track in placeholder_tracks:
                if (mood and track["mood"] != mood) or (genre and track["genre"] != genre):
                    continue
                tracks.append({
                    "filename": track["filename"],
                    "title": track["filename"].replace("_", " ").replace(".mp3", "").title(),
                    "mood": track["mood"],
                    "genre": track["genre"],
                    "license": "CC0"
                })
            return tracks
        
        # Process real music files
        tracks = []
        for music_file in music_files:
            # Check for metadata file
            metadata_path = music_file.with_suffix(".json")
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            else:
                # Create basic metadata
                metadata = {
                    "filename": music_file.name,
                    "title": music_file.stem.replace("_", " ").title(),
                    "artist": "Unknown",
                    "mood": "neutral",
                    "genre": "unknown",
                    "license": "Unknown"
                }
            
            # Apply filters
            if (mood and metadata.get("mood") != mood) or (genre and metadata.get("genre") != genre):
                continue
                
            tracks.append({
                "filename": music_file.name,
                "title": metadata.get("title", music_file.stem),
                "artist": metadata.get("artist", "Unknown"),
                "mood": metadata.get("mood", "neutral"),
                "genre": metadata.get("genre", "unknown"),
                "license": metadata.get("license", "Unknown"),
                "path": str(music_file)
            })
            
        return tracks
    
    def _process_music_track(self, music_track: str, voiceover_path: str, output_path: str,
                            duck_amount: float = 12.0, target_lufs: float = -14.0) -> str:
        """
        Process a music track for integration with voiceover.
        
        Args:
            music_track: Path to the music track
            voiceover_path: Path to the voiceover file
            output_path: Path to save the processed audio
            duck_amount: Amount to reduce music volume during voiceover (in dB)
            target_lufs: Target loudness in LUFS
            
        Returns:
            str: Path to the processed audio file
        """
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Get voiceover duration
            voiceover_duration = self._get_audio_duration(voiceover_path)
            
            # Step 2: Get music duration
            music_duration = self._get_audio_duration(music_track)
            
            # Step 3: If music is shorter than voiceover, loop it
            if music_duration < voiceover_duration:
                # Create a temporary file for the looped music
                looped_music_path = str(Path(output_path).parent / "looped_music.mp3")
                
                # Calculate how many times to loop
                loop_count = int(voiceover_duration / music_duration) + 1
                
                # Create a file list for ffmpeg
                file_list_path = str(Path(output_path).parent / "music_loop_list.txt")
                with open(file_list_path, "w") as f:
                    for _ in range(loop_count):
                        f.write(f"file '{music_track}'\n")
                
                # Use ffmpeg to concatenate the music files
                subprocess.run([
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-f", "concat",
                    "-safe", "0",
                    "-i", file_list_path,
                    "-c", "copy",
                    looped_music_path
                ], check=True)
                
                # Update music track path
                music_track = looped_music_path
            
            # Step 4: Apply sidechain ducking using ffmpeg
            # This is a simplified implementation - in a real system, we would use
            # more sophisticated audio processing tools
            
            # First, create a temporary file for the ducked music
            ducked_music_path = str(Path(output_path).parent / "ducked_music.mp3")
            
            # Use ffmpeg to apply sidechain ducking
            subprocess.run([
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", music_track,
                "-i", voiceover_path,
                "-filter_complex", f"[0:a]volume=1[music];[music][1:a]sidechaincompress=threshold=0.01:ratio=20:attack=5:release=50:level_in=1:level_sc=1:makeup={duck_amount}[out]",
                "-map", "[out]",
                ducked_music_path
            ], check=True)
            
            # Step 5: Mix the ducked music with the voiceover
            subprocess.run([
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", ducked_music_path,
                "-i", voiceover_path,
                "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest[out]",
                "-map", "[out]",
                output_path
            ], check=True)
            
            # Step 6: Normalize the final mix to the target LUFS
            normalized_output_path = str(Path(output_path).parent / "normalized_mix.mp3")
            
            subprocess.run([
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", output_path,
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                normalized_output_path
            ], check=True)
            
            # Replace the output file with the normalized version
            import shutil
            shutil.move(normalized_output_path, output_path)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to process music track: {str(e)}")
            raise
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get the duration of an audio file.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            float: Duration in seconds
        """
        try:
            # Use ffprobe to get the duration
            result = subprocess.run([
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_path
            ], capture_output=True, text=True, check=True)
            
            # Parse the JSON output
            output = json.loads(result.stdout)
            duration = float(output["format"]["duration"])
            
            return duration
            
        except Exception as e:
            logger.error(f"Failed to get audio duration: {str(e)}")
            raise
    
    @track_duration
    async def select_music(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select appropriate background music for a video.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the selected music
        """
        log_event("music_selection_started", {"job_id": context["job_id"]})
        
        try:
            # Get script excerpt (first 500 characters)
            script_excerpt = context["script"][:500] + "..."
            
            # Get mood and audience from context (with defaults)
            mood = context.get("mood", "Informative and engaging")
            audience = context.get("audience", "General audience")
            
            # Get voiceover duration if available
            duration = context.get("voiceover_duration", "3-5")
            
            # Format the prompt with context variables
            prompt = self.prompts["user_select_music"].format(
                topic=context["topic"],
                script_excerpt=script_excerpt,
                mood=mood,
                audience=audience,
                duration=duration
            )
            
            # Create a new thread for this job
            thread = self.client.beta.threads.create()
            
            # Add the user message to the thread
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            # Run the assistant on the thread
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id,
                tools=[
                    {"type": "function", "function": {
                            "name": "list_available_music",
                            "parameters": {
                                "mood": mood.split()[0].lower()  # Use first word of mood as filter
                            }
                        }
                    }
                ]
            )
            
            # Wait for the run to complete
            run = self._wait_for_run(thread.id, run.id)
            
            # Get the assistant's response
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # Extract the assistant's response
            assistant_response = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Get available music tracks
            available_tracks = self._list_available_music(mood=mood.split()[0].lower())
            
            # Select the first track (in a real system, this would be more sophisticated)
            if available_tracks:
                selected_track = available_tracks[0]
            else:
                # Create a placeholder track if none are available
                placeholder_path = self.music_library_path / "placeholder"
                placeholder_path.mkdir(parents=True, exist_ok=True)
                
                selected_track = {
                    "filename": "placeholder_track.mp3",
                    "title": "Placeholder Track",
                    "mood": mood.split()[0].lower(),
                    "genre": "unknown",
                    "license": "CC0",
                    "path": str(placeholder_path / "placeholder_track.mp3")
                }
                
                # Create an empty audio file as placeholder
                subprocess.run([
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", "180",  # 3 minutes
                    "-q:a", "0",
                    "-map", "0",
                    selected_track["path"]
                ], check=True)
            
            # Process the music with the voiceover
            if "voiceover_path" in context:
                # Output path for the mixed audio
                output_dir = Path(context["output_dir"]) / "audio"
                output_dir.mkdir(parents=True, exist_ok=True)
                mixed_audio_path = str(output_dir / "mixed_audio.mp3")
                
                # Process the music track
                self._process_music_track(
                    music_track=selected_track.get("path", ""),
                    voiceover_path=context["voiceover_path"],
                    output_path=mixed_audio_path,
                    duck_amount=12.0,
                    target_lufs=-14.0
                )
            else:
                # No voiceover yet, just copy the music track
                import shutil
                
                output_dir = Path(context["output_dir"]) / "audio"
                output_dir.mkdir(parents=True, exist_ok=True)
                mixed_audio_path = str(output_dir / "background_music.mp3")
                
                # Copy the music track if it exists
                if os.path.exists(selected_track.get("path", "")):
                    shutil.copy(selected_track.get("path", ""), mixed_audio_path)
                else:
                    # Create an empty audio file as placeholder
                    subprocess.run([
                        "ffmpeg",
                        "-y",  # Overwrite output file if it exists
                        "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=stereo",
                        "-t", "180",  # 3 minutes
                        "-q:a", "0",
                        "-map", "0",
                        mixed_audio_path
                    ], check=True)
            
            # Update the context
            result = {
                "music_track": selected_track,
                "music_path": mixed_audio_path,
                "music_recommendation": assistant_response
            }
            
            log_event("music_selection_completed", {
                "job_id": context["job_id"],
                "selected_track": selected_track.get("title", "Unknown")
            })
            return result
            
        except Exception as e:
            log_event("music_selection_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to select music: {str(e)}")
            raise
    
    def _wait_for_run(self, thread_id: str, run_id: str) -> Run:
        """
        Wait for an assistant run to complete.
        
        Args:
            thread_id: The ID of the thread
            run_id: The ID of the run
            
        Returns:
            Run: The completed run
        """
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            
            if run.status == "completed":
                return run
            elif run.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Run {run_id} failed with status: {run.status}")
            
            # Wait before checking again
            import time
            time.sleep(1)
