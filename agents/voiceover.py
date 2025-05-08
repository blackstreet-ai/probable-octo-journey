#!/usr/bin/env python
"""
VoiceoverAgent: Synthesizes narration using ElevenLabs or similar TTS services.

This agent transforms video scripts into high-quality voiceover audio,
handling multi-paragraph synthesis with proper pacing and emphasis.
"""

import json
import logging
import os
import re
import uuid
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads.run import Run

from tools.observability import log_event, track_duration

# Configure logging
logger = logging.getLogger(__name__)

class VoiceoverAgent:
    """
    Agent for synthesizing voiceover audio from scripts.
    
    This agent extracts narration text from scripts and uses ElevenLabs
    or equivalent TTS services to create high-quality voiceover audio.
    """
    
    def __init__(self):
        """Initialize the VoiceoverAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
        
        # Initialize ElevenLabs client if API key is available
        if self.elevenlabs_api_key:
            self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
            logger.info("ElevenLabs client initialized successfully")
        else:
            self.elevenlabs_client = None
            logger.warning("ElevenLabs API key not found in environment variables")
            
        self._load_prompts()
        self._create_assistant()
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "voiceover.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for VoiceoverAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _create_assistant(self) -> None:
        """Create or retrieve the OpenAI Assistant for this agent."""
        # Check if assistant ID is stored in environment variable
        assistant_id = os.environ.get("VOICEOVER_ASSISTANT_ID")
        
        if assistant_id:
            try:
                # Try to retrieve the existing assistant
                self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant_id
                logger.info(f"Retrieved existing VoiceoverAgent assistant: {assistant_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
        
        # Create a new assistant
        try:
            self.assistant = self.client.beta.assistants.create(
                name="VoiceoverAgent",
                description="Synthesizes voiceover audio from scripts",
                model="gpt-4o-mini",
                instructions=self.prompts["system"],
                tools=[
                    {"type": "function", "function": {
                            "name": "extract_narration_text",
                            "description": "Extract narration text from a script, ignoring visual descriptions",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "script": {
                                        "type": "string",
                                        "description": "The full script with narration and visual descriptions"
                                    }
                                },
                                "required": ["script"]
                            }
                        }
                    },
                    {"type": "function", "function": {
                            "name": "synthesize_speech",
                            "description": "Synthesize speech using ElevenLabs API",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "The text to synthesize"
                                    },
                                    "voice_id": {
                                        "type": "string",
                                        "description": "The ID of the voice to use"
                                    },
                                    "stability": {
                                        "type": "number",
                                        "description": "Voice stability (0.0 to 1.0)"
                                    },
                                    "clarity": {
                                        "type": "number",
                                        "description": "Voice clarity (0.0 to 1.0)"
                                    },
                                    "style": {
                                        "type": "string",
                                        "description": "Speaking style"
                                    }
                                },
                                "required": ["text", "voice_id"]
                            }
                        }
                    }
                ]
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new VoiceoverAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise
    
    def _extract_narration_text(self, script: str) -> List[str]:
        """
        Extract narration text from a script, ignoring visual descriptions.
        
        Args:
            script: The full script with narration and visual descriptions
            
        Returns:
            List[str]: List of narration paragraphs
        """
        # Check if this is an enhanced script with structured sections
        if "*Hook*:" in script or "**Key point**:" in script:
            return self._extract_from_enhanced_script(script)
        
        # This is the original implementation for standard scripts
        lines = script.split("\n")
        narration_lines = []
        current_paragraph = []
        in_narration = False
        
        # Look for patterns like "NARRATION:", "VOICEOVER:", or scene headings
        narration_markers = ["narration:", "voiceover:", "narr:", "vo:"]
        visual_markers = ["visual:", "visuals:", "scene:", "on screen:"]
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - if we were in narration, save the paragraph
                if current_paragraph:
                    narration_lines.append(" ".join(current_paragraph))
                    current_paragraph = []
                in_narration = False
                continue
                
            # Check for narration markers
            line_lower = line.lower()
            if any(marker in line_lower for marker in narration_markers):
                in_narration = True
                # Extract the text after the marker
                for marker in narration_markers:
                    if marker in line_lower:
                        text = line[line_lower.find(marker) + len(marker):].strip()
                        if text:
                            current_paragraph.append(text)
                        break
                continue
                
            # Check for visual markers
            if any(marker in line_lower for marker in visual_markers):
                in_narration = False
                if current_paragraph:
                    narration_lines.append(" ".join(current_paragraph))
                    current_paragraph = []
                continue
                
            # If we're in narration mode, add the line
            if in_narration:
                current_paragraph.append(line)
                
        # Add the last paragraph if there is one
        if current_paragraph:
            narration_lines.append(" ".join(current_paragraph))
            
        return narration_lines
    
    def _extract_from_enhanced_script(self, script: str) -> List[str]:
        """
        Extract narration text from an enhanced script with hooks, key points, transitions, etc.
        while ignoring visual descriptions.
        
        Args:
            script: The enhanced script with structured sections
            
        Returns:
            List[str]: List of narration paragraphs
        """
        narration_paragraphs = []
        lines = script.split("\n")
        i = 0
        
        # Process the script line by line
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
                
            # Extract section titles (for context)
            if line.startswith("##") or line.startswith("###"):
                section_title = line.lstrip("#").strip()
                narration_paragraphs.append(f"Section: {section_title}")
                i += 1
                continue
                
            # Extract hooks (usually in bold)
            if "*Hook*:" in line:
                # Extract the text after the hook marker
                hook_text = line.split("*Hook*:", 1)[1].strip()
                
                # If the hook contains bold text (often the key narration), extract it
                if "**" in hook_text:
                    # Extract text between ** markers
                    bold_parts = re.findall(r'\*\*(.*?)\*\*', hook_text)
                    if bold_parts:
                        narration_paragraphs.append(" ".join(bold_parts))
                    else:
                        narration_paragraphs.append(hook_text)
                else:
                    narration_paragraphs.append(hook_text)
                    
                i += 1
                continue
                
            # Extract key points
            if "**Key point**:" in line:
                key_point = line.split("**Key point**:", 1)[1].strip()
                narration_paragraphs.append(key_point)
                i += 1
                continue
                
            # Extract supporting details
            if "**Supporting details**:" in line:
                details = line.split("**Supporting details**:", 1)[1].strip()
                narration_paragraphs.append(details)
                i += 1
                continue
                
            # Extract transitions
            if "*Transition*:" in line:
                transition = line.split("*Transition*:", 1)[1].strip()
                narration_paragraphs.append(transition)
                i += 1
                continue
                
            # Extract call to action
            if "*Call to Action*:" in line:
                cta_text = line.split("*Call to Action*:", 1)[1].strip()
                
                # If the CTA contains bold text, extract it
                if "**" in cta_text:
                    bold_parts = re.findall(r'\*\*(.*?)\*\*', cta_text)
                    if bold_parts:
                        narration_paragraphs.append(" ".join(bold_parts))
                    else:
                        narration_paragraphs.append(cta_text)
                else:
                    narration_paragraphs.append(cta_text)
                    
                i += 1
                continue
                
            # Skip visual descriptions
            if "**Visual description**:" in line:
                # Skip until we find a transition or another marker
                while i < len(lines) and not any(marker in lines[i] for marker in ["*Transition*:", "*Hook*:", "**Key point**:", "##", "###"]):
                    i += 1
                continue
            
            # Include regular paragraphs that aren't marked with any special tags
            # but aren't part of visual descriptions
            if not any(marker in line for marker in ["**Visual description**:", "- **Visual"]):
                # Check if this is a regular paragraph (not a list item or metadata)
                if not line.startswith("-") and not line.startswith("#") and not line.startswith("*") and not line.startswith("**"):
                    narration_paragraphs.append(line)
            
            i += 1
        
        # Filter out empty paragraphs and clean up markdown formatting
        cleaned_paragraphs = []
        for paragraph in narration_paragraphs:
            # Remove markdown formatting
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', paragraph)  # Remove bold
            clean_text = re.sub(r'\*(.*?)\*', r'\1', clean_text)      # Remove italic
            clean_text = clean_text.strip()
            
            if clean_text:
                cleaned_paragraphs.append(clean_text)
        
        return cleaned_paragraphs
    
    def _get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get available voices from ElevenLabs API.
        
        Returns:
            List[Dict[str, Any]]: List of available voices
        """
        try:
            # Check if ElevenLabs client is available
            if not self.elevenlabs_client:
                raise ValueError("ElevenLabs client not initialized")
                
            # Get available voices
            response = self.elevenlabs_client.voices.get_all()
            voices_list = response.voices
            logger.info(f"Found {len(voices_list)} voices from ElevenLabs")
            return voices_list
            
        except Exception as e:
            logger.error(f"Failed to get available voices: {str(e)}")
            raise
    
    def _synthesize_speech(self, text: str, voice_id: str, stability: float = 0.5, 
                          clarity: float = 0.75, style: float = 0.0) -> str:
        """
        Synthesize speech using ElevenLabs API.
        
        Args:
            text: The text to synthesize
            voice_id: The ID of the voice to use
            stability: Voice stability (0.0 to 1.0)
            clarity: Voice clarity/similarity boost (0.0 to 1.0)
            style: Style parameter (0.0 to 1.0)
            
        Returns:
            str: Path to the synthesized audio file
        """
        try:
            # Check if ElevenLabs client is available
            if not self.elevenlabs_client:
                raise ValueError("ElevenLabs client not initialized")
            
            # Configure voice settings
            voice_settings = VoiceSettings(
                stability=stability,
                similarity_boost=clarity,
                style=style,
                use_speaker_boost=True,
                speed=1.0
            )
            
            # Generate a unique filename
            filename = f"voiceover_{uuid.uuid4()}.mp3"
            output_path = Path(__file__).parent.parent / "assets" / "audio" / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate audio using ElevenLabs SDK
            response = self.elevenlabs_client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",  # Using the latest turbo model for low latency
                output_format="mp3_44100_128",
                voice_settings=voice_settings
            )
            
            # Save the audio to a file
            with open(output_path, "wb") as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Successfully synthesized speech to {output_path}")
            return str(output_path)
                
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {str(e)}")
            raise
    
    @track_duration
    async def synthesize_audio(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize voiceover audio from a script.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the synthesized audio
        """
        log_event("voiceover_synthesis_started", {"job_id": context["job_id"]})
        
        try:
            # Get script from context
            script = context["script"]
            
            # Extract narration text
            narration_paragraphs = self._extract_narration_text(script)
            
            # Get available voices if not specified
            try:
                available_voices = self._get_available_voices()
                default_voice = available_voices[0].voice_id if available_voices else None
                logger.info(f"Using default voice: {default_voice if default_voice else 'None available'}")
            except Exception as e:
                logger.warning(f"Could not fetch available voices: {str(e)}")
                default_voice = None
                
            # Get default voice ID from environment if available
            env_default_voice = os.environ.get("DEFAULT_VOICE_ID")
            if env_default_voice and env_default_voice != "default":
                default_voice = env_default_voice
                
            # Format the prompt with context variables
            voice_id = context.get("voice_id", default_voice)  # Use first available voice as default
            if not voice_id:
                raise ValueError("No voice ID specified and no default voices available")
                
            stability = context.get("stability", 0.5)
            clarity = context.get("clarity", 0.75)
            style = float(context.get("style", 0.0))  # Style is a float in the SDK
            
            prompt = self.prompts["user_synthesize_audio"].format(
                script=script,
                voice_id=voice_id,
                stability=stability,
                clarity=clarity,
                style=style
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
            
            # Synthesize audio for each paragraph
            audio_files = []
            for i, paragraph in enumerate(narration_paragraphs):
                logger.info(f"Synthesizing paragraph {i+1}/{len(narration_paragraphs)}")
                audio_path = self._synthesize_speech(
                    text=paragraph,
                    voice_id=voice_id,
                    stability=stability,
                    clarity=clarity,
                    style=style
                )
                audio_files.append(audio_path)
            
            # Combine audio files if there are multiple paragraphs
            if len(audio_files) > 1:
                import subprocess
                
                # Create a file list for ffmpeg
                file_list_path = Path(context["output_dir"]) / "audio" / "file_list.txt"
                file_list_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_list_path, "w") as f:
                    for audio_file in audio_files:
                        f.write(f"file '{audio_file}'\n")
                
                # Output path for the combined audio
                combined_audio_path = Path(context["output_dir"]) / "audio" / "voiceover.mp3"
                
                # Use ffmpeg to concatenate the audio files
                subprocess.run([
                    "ffmpeg",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(file_list_path),
                    "-c", "copy",
                    str(combined_audio_path)
                ], check=True)
                
                final_audio_path = str(combined_audio_path)
            else:
                # Only one audio file, just copy it to the output directory
                import shutil
                
                output_dir = Path(context["output_dir"]) / "audio"
                output_dir.mkdir(parents=True, exist_ok=True)
                final_audio_path = str(output_dir / "voiceover.mp3")
                
                shutil.copy(audio_files[0], final_audio_path)
            
            # Get audio duration using ffprobe
            import subprocess
            import json
            
            ffprobe_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                final_audio_path
            ]
            
            ffprobe_output = subprocess.check_output(ffprobe_cmd).decode("utf-8")
            duration = float(json.loads(ffprobe_output)["format"]["duration"])
            
            # Update the context
            result = {
                "voiceover_path": final_audio_path,
                "voiceover_duration": duration,
                "voiceover_paragraphs": len(narration_paragraphs),
                "voice_id": voice_id
            }
            
            log_event("voiceover_synthesis_completed", {
                "job_id": context["job_id"],
                "duration": duration,
                "paragraphs": len(narration_paragraphs)
            })
            return result
            
        except Exception as e:
            log_event("voiceover_synthesis_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to synthesize voiceover: {str(e)}")
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
