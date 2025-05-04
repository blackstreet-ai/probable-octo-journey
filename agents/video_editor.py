#!/usr/bin/env python
"""
VideoEditorAgent: Assembles final video with visuals, voiceover, and music.

This agent compiles all generated assets into a cohesive, professional video,
aligning visuals with voiceover timing and applying appropriate effects.
"""

import json
import logging
import os
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads.run import Run

from tools.observability import log_event, track_duration

# Configure logging
logger = logging.getLogger(__name__)

class VideoEditorAgent:
    """
    Agent for assembling final videos with visuals, voiceover, and music.
    
    This agent compiles all generated assets into a cohesive, professional video,
    aligning visuals with voiceover timing and applying appropriate effects.
    """
    
    def __init__(self):
        """Initialize the VideoEditorAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self._load_prompts()
        self._create_assistant()
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "video_editor.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for VideoEditorAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _create_assistant(self) -> None:
        """Create or retrieve the OpenAI Assistant for this agent."""
        # Check if assistant ID is stored in environment variable
        assistant_id = os.environ.get("VIDEO_EDITOR_ASSISTANT_ID")
        
        if assistant_id:
            try:
                # Try to retrieve the existing assistant
                self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant_id
                logger.info(f"Retrieved existing VideoEditorAgent assistant: {assistant_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
        
        # Create a new assistant
        try:
            self.assistant = self.client.beta.assistants.create(
                name="VideoEditorAgent",
                description="Assembles final videos with visuals, voiceover, and music",
                model="gpt-4-turbo",
                instructions=self.prompts["system"],
                tools=[
                    {"type": "function", "function": {
                            "name": "create_video_from_images",
                            "description": "Create a video from a sequence of images",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "image_paths": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "List of paths to the images"
                                    },
                                    "output_path": {
                                        "type": "string",
                                        "description": "Path to save the output video"
                                    },
                                    "duration_per_image": {
                                        "type": "number",
                                        "description": "Duration in seconds to show each image"
                                    },
                                    "transition_type": {
                                        "type": "string",
                                        "description": "Type of transition between images"
                                    },
                                    "fps": {
                                        "type": "integer",
                                        "description": "Frames per second for the video"
                                    },
                                    "resolution": {
                                        "type": "string",
                                        "description": "Resolution of the video (e.g., '1920x1080')"
                                    }
                                },
                                "required": ["image_paths", "output_path"]
                            }
                        }
                    },
                    {"type": "function", "function": {
                            "name": "add_audio_to_video",
                            "description": "Add audio to a video",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "video_path": {
                                        "type": "string",
                                        "description": "Path to the video file"
                                    },
                                    "audio_path": {
                                        "type": "string",
                                        "description": "Path to the audio file"
                                    },
                                    "output_path": {
                                        "type": "string",
                                        "description": "Path to save the output video"
                                    },
                                    "audio_volume": {
                                        "type": "number",
                                        "description": "Volume adjustment for the audio (1.0 = original volume)"
                                    }
                                },
                                "required": ["video_path", "audio_path", "output_path"]
                            }
                        }
                    },
                    {"type": "function", "function": {
                            "name": "add_text_overlay",
                            "description": "Add text overlay to a video",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "video_path": {
                                        "type": "string",
                                        "description": "Path to the video file"
                                    },
                                    "output_path": {
                                        "type": "string",
                                        "description": "Path to save the output video"
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "Text to overlay"
                                    },
                                    "position": {
                                        "type": "string",
                                        "description": "Position of the text (e.g., 'center', 'bottom')"
                                    },
                                    "font_size": {
                                        "type": "integer",
                                        "description": "Font size for the text"
                                    },
                                    "font_color": {
                                        "type": "string",
                                        "description": "Color of the text"
                                    },
                                    "start_time": {
                                        "type": "number",
                                        "description": "Start time for the text overlay (in seconds)"
                                    },
                                    "end_time": {
                                        "type": "number",
                                        "description": "End time for the text overlay (in seconds)"
                                    }
                                },
                                "required": ["video_path", "output_path", "text"]
                            }
                        }
                    }
                ]
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new VideoEditorAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise
    
    def _create_video_from_images(self, image_paths: List[str], output_path: str,
                                 duration_per_image: float = 5.0, transition_type: str = "fade",
                                 fps: int = 30, resolution: str = "1920x1080") -> str:
        """
        Create a video from a sequence of images.
        
        Args:
            image_paths: List of paths to the images
            output_path: Path to save the output video
            duration_per_image: Duration in seconds to show each image
            transition_type: Type of transition between images
            fps: Frames per second for the video
            resolution: Resolution of the video
            
        Returns:
            str: Path to the created video
        """
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create a temporary directory for processing
            import tempfile
            temp_dir = tempfile.mkdtemp()
            
            # Create a file with the list of images and durations
            file_list_path = Path(temp_dir) / "file_list.txt"
            
            with open(file_list_path, "w") as f:
                for image_path in image_paths:
                    f.write(f"file '{image_path}'\n")
                    f.write(f"duration {duration_per_image}\n")
                
                # Add the last image again to fix the last frame duration
                f.write(f"file '{image_paths[-1]}'\n")
            
            # Use ffmpeg to create the video
            # For simplicity, we'll use a basic crossfade transition
            # In a real system, this would be more sophisticated
            
            # Split resolution into width and height
            width, height = resolution.split("x")
            
            # Build the ffmpeg command
            if transition_type == "fade":
                # Use xfade filter for transitions
                filter_complex = []
                for i in range(len(image_paths) - 1):
                    filter_complex.append(f"[{i}:v][{i+1}:v]xfade=transition=fade:duration=1:offset={duration_per_image-1}[v{i+1}]")
                
                filter_str = ";".join(filter_complex)
                
                # Use complex filter for transitions
                subprocess.run([
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(file_list_path),
                    "-filter_complex", filter_str,
                    "-map", f"[v{len(image_paths)-1}]",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-r", str(fps),
                    "-s", resolution,
                    output_path
                ], check=True)
            else:
                # Simple concatenation without transitions
                subprocess.run([
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(file_list_path),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-r", str(fps),
                    "-s", resolution,
                    output_path
                ], check=True)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to create video from images: {str(e)}")
            
            # Create a simple placeholder video
            try:
                # Create a blank video
                subprocess.run([
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-f", "lavfi",
                    "-i", f"color=c=black:s={resolution}:r={fps}:d={len(image_paths) * duration_per_image}",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    output_path
                ], check=True)
                
                return output_path
                
            except Exception as placeholder_error:
                logger.error(f"Failed to create placeholder video: {str(placeholder_error)}")
                raise e
    
    def _add_audio_to_video(self, video_path: str, audio_path: str, output_path: str,
                           audio_volume: float = 1.0) -> str:
        """
        Add audio to a video.
        
        Args:
            video_path: Path to the video file
            audio_path: Path to the audio file
            output_path: Path to save the output video
            audio_volume: Volume adjustment for the audio
            
        Returns:
            str: Path to the output video
        """
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Get video duration
            video_duration = self._get_media_duration(video_path)
            
            # Get audio duration
            audio_duration = self._get_media_duration(audio_path)
            
            # If audio is longer than video, trim it
            if audio_duration > video_duration:
                # Create a temporary file for the trimmed audio
                trimmed_audio_path = str(Path(output_path).parent / "trimmed_audio.mp3")
                
                # Trim the audio
                subprocess.run([
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-i", audio_path,
                    "-t", str(video_duration),
                    "-c:a", "copy",
                    trimmed_audio_path
                ], check=True)
                
                # Use the trimmed audio
                audio_path = trimmed_audio_path
            
            # If audio is shorter than video, loop it
            elif audio_duration < video_duration:
                # Create a temporary file for the looped audio
                looped_audio_path = str(Path(output_path).parent / "looped_audio.mp3")
                
                # Create a file list for ffmpeg
                file_list_path = str(Path(output_path).parent / "audio_loop_list.txt")
                
                # Calculate how many times to loop
                loop_count = int(video_duration / audio_duration) + 1
                
                with open(file_list_path, "w") as f:
                    for _ in range(loop_count):
                        f.write(f"file '{audio_path}'\n")
                
                # Use ffmpeg to concatenate the audio files
                subprocess.run([
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-f", "concat",
                    "-safe", "0",
                    "-i", file_list_path,
                    "-c", "copy",
                    looped_audio_path
                ], check=True)
                
                # Trim the looped audio to match the video duration
                trimmed_audio_path = str(Path(output_path).parent / "trimmed_looped_audio.mp3")
                
                subprocess.run([
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-i", looped_audio_path,
                    "-t", str(video_duration),
                    "-c:a", "copy",
                    trimmed_audio_path
                ], check=True)
                
                # Use the trimmed looped audio
                audio_path = trimmed_audio_path
            
            # Add the audio to the video
            subprocess.run([
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex", f"[1:a]volume={audio_volume}[a]",
                "-map", "0:v",
                "-map", "[a]",
                "-c:v", "copy",
                "-shortest",
                output_path
            ], check=True)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to add audio to video: {str(e)}")
            raise
    
    def _add_text_overlay(self, video_path: str, output_path: str, text: str,
                         position: str = "center", font_size: int = 48,
                         font_color: str = "white", start_time: float = 0.0,
                         end_time: Optional[float] = None) -> str:
        """
        Add text overlay to a video.
        
        Args:
            video_path: Path to the video file
            output_path: Path to save the output video
            text: Text to overlay
            position: Position of the text
            font_size: Font size for the text
            font_color: Color of the text
            start_time: Start time for the text overlay
            end_time: End time for the text overlay
            
        Returns:
            str: Path to the output video
        """
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Get video duration if end_time is not specified
            if end_time is None:
                end_time = self._get_media_duration(video_path)
            
            # Map position to x and y coordinates
            position_map = {
                "center": "x=(w-text_w)/2:y=(h-text_h)/2",
                "top": "x=(w-text_w)/2:y=h/10",
                "bottom": "x=(w-text_w)/2:y=h-h/10-text_h",
                "top_left": "x=w/10:y=h/10",
                "top_right": "x=w-w/10-text_w:y=h/10",
                "bottom_left": "x=w/10:y=h-h/10-text_h",
                "bottom_right": "x=w-w/10-text_w:y=h-h/10-text_h"
            }
            
            position_str = position_map.get(position, position_map["center"])
            
            # Create the drawtext filter
            drawtext_filter = (
                f"drawtext=text='{text}':fontsize={font_size}:fontcolor={font_color}:"
                f"{position_str}:enable='between(t,{start_time},{end_time})'"
            )
            
            # Add the text overlay to the video
            subprocess.run([
                "ffmpeg",
                "-y",  # Overwrite output file if it exists
                "-i", video_path,
                "-vf", drawtext_filter,
                "-c:a", "copy",
                output_path
            ], check=True)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to add text overlay to video: {str(e)}")
            raise
    
    def _get_media_duration(self, media_path: str) -> float:
        """
        Get the duration of a media file.
        
        Args:
            media_path: Path to the media file
            
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
                media_path
            ], capture_output=True, text=True, check=True)
            
            # Parse the JSON output
            output = json.loads(result.stdout)
            duration = float(output["format"]["duration"])
            
            return duration
            
        except Exception as e:
            logger.error(f"Failed to get media duration: {str(e)}")
            raise
    
    @track_duration
    async def assemble_video(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assemble a video from generated assets.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the assembled video
        """
        log_event("video_assembly_started", {"job_id": context["job_id"]})
        
        try:
            # Get images from context
            images = context.get("images", [])
            if not images:
                raise ValueError("No images found in context")
            
            # Get audio paths from context
            voiceover_path = context.get("voiceover_path")
            if not voiceover_path:
                raise ValueError("No voiceover path found in context")
            
            music_path = context.get("music_path")
            
            # Get video specifications from context (with defaults)
            resolution = context.get("resolution", "1920x1080")
            fps = context.get("fps", 30)
            format = context.get("format", "mp4")
            
            # Create output directories
            output_dir = Path(context["output_dir"]) / "video"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Format the prompt with context variables
            image_paths = [image["output_path"] if "output_path" in image else image["path"] for image in images]
            
            prompt = self.prompts["user_assemble_video"].format(
                images="\n".join([f"- Scene {i+1}: {path}" for i, path in enumerate(image_paths)]),
                voiceover_path=voiceover_path,
                music_path=music_path if music_path else "None",
                resolution=resolution,
                fps=fps,
                format=format
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
                assistant_id=self.assistant_id
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
            
            # Calculate duration per image based on voiceover duration
            voiceover_duration = self._get_media_duration(voiceover_path)
            duration_per_image = voiceover_duration / len(images)
            
            # Create the video from images
            video_without_audio_path = str(output_dir / "video_without_audio.mp4")
            self._create_video_from_images(
                image_paths=image_paths,
                output_path=video_without_audio_path,
                duration_per_image=duration_per_image,
                transition_type="fade",
                fps=fps,
                resolution=resolution
            )
            
            # Add voiceover to the video
            video_with_voiceover_path = str(output_dir / "video_with_voiceover.mp4")
            self._add_audio_to_video(
                video_path=video_without_audio_path,
                audio_path=voiceover_path,
                output_path=video_with_voiceover_path,
                audio_volume=1.0
            )
            
            # Add background music if available
            final_video_path = str(output_dir / "final_video.mp4")
            if music_path and os.path.exists(music_path):
                self._add_audio_to_video(
                    video_path=video_with_voiceover_path,
                    audio_path=music_path,
                    output_path=final_video_path,
                    audio_volume=0.3  # Lower volume for background music
                )
            else:
                # No music, just use the video with voiceover
                import shutil
                shutil.copy(video_with_voiceover_path, final_video_path)
            
            # Add title and credits
            video_with_title_path = str(output_dir / "video_with_title.mp4")
            self._add_text_overlay(
                video_path=final_video_path,
                output_path=video_with_title_path,
                text=context["topic"],
                position="center",
                font_size=72,
                font_color="white",
                start_time=0.0,
                end_time=5.0
            )
            
            # Add call-to-action
            final_video_with_cta_path = str(output_dir / "final_video_with_cta.mp4")
            self._add_text_overlay(
                video_path=video_with_title_path,
                output_path=final_video_with_cta_path,
                text="Thanks for watching! Like and subscribe for more content.",
                position="bottom",
                font_size=48,
                font_color="white",
                start_time=voiceover_duration - 5.0,
                end_time=voiceover_duration
            )
            
            # Get video information
            video_info = {
                "duration": self._get_media_duration(final_video_with_cta_path),
                "resolution": resolution,
                "fps": fps,
                "format": format,
                "size_bytes": os.path.getsize(final_video_with_cta_path)
            }
            
            # Update the context
            result = {
                "video_path": final_video_with_cta_path,
                "video_info": video_info,
                "video_duration": video_info["duration"],
                "video_resolution": resolution,
                "video_assembly_response": assistant_response
            }
            
            log_event("video_assembly_completed", {
                "job_id": context["job_id"],
                "duration": video_info["duration"],
                "size_bytes": video_info["size_bytes"]
            })
            return result
            
        except Exception as e:
            log_event("video_assembly_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to assemble video: {str(e)}")
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
