#!/usr/bin/env python
"""
VisualComposerAgent: Generates visuals (DALL·E, stock APIs) based on scenes.

This agent creates compelling visual content based on video scripts, using
image generation APIs like DALL-E or stock image services.
"""

import json
import logging
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads.run import Run

from tools.asset_generator import AssetGenerator
from tools.observability import log_event, track_duration

# Configure logging
logger = logging.getLogger(__name__)

class VisualComposerAgent:
    """
    Agent for generating visuals for AI videos.
    
    This agent creates compelling visual content based on video scripts, using
    image generation APIs like DALL-E or stock image services.
    """
    
    def __init__(self):
        """Initialize the VisualComposerAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self._load_prompts()
        self._create_assistant()
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "visual_composer.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for VisualComposerAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _create_assistant(self) -> None:
        """Create or retrieve the OpenAI Assistant for this agent."""
        # Check if assistant ID is stored in environment variable
        assistant_id = os.environ.get("VISUAL_COMPOSER_ASSISTANT_ID")
        
        if assistant_id:
            try:
                # Try to retrieve the existing assistant
                self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant_id
                logger.info(f"Retrieved existing VisualComposerAgent assistant: {assistant_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
        
        # Create a new assistant
        try:
            self.assistant = self.client.beta.assistants.create(
                name="VisualComposerAgent",
                description="Generates visuals for AI videos",
                model="gpt-4-turbo",
                instructions=self.prompts["system"],
                tools=[
                    {"type": "function", "function": {
                            "name": "extract_visual_descriptions",
                            "description": "Extract visual descriptions from a script",
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
                            "name": "generate_image",
                            "description": "Generate an image using DALL-E",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "prompt": {
                                        "type": "string",
                                        "description": "The prompt for image generation"
                                    },
                                    "style": {
                                        "type": "string",
                                        "description": "The visual style for the image"
                                    },
                                    "scene_number": {
                                        "type": "integer",
                                        "description": "The scene number for the image"
                                    }
                                },
                                "required": ["prompt", "scene_number"]
                            }
                        }
                    }
                ]
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new VisualComposerAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise
    
    def _extract_visual_descriptions(self, script: str) -> List[Dict[str, Any]]:
        """
        Extract visual descriptions from a script.
        
        Args:
            script: The full script with narration and visual descriptions
            
        Returns:
            List[Dict[str, Any]]: List of scenes with visual descriptions
        """
        # This is a simple implementation that could be improved with more sophisticated parsing
        lines = script.split("\n")
        scenes = []
        current_scene = None
        in_visual = False
        
        # Look for patterns like "VISUAL:", "VISUALS:", "SCENE:", "ON SCREEN:"
        visual_markers = ["visual:", "visuals:", "scene:", "on screen:"]
        narration_markers = ["narration:", "voiceover:", "narr:", "vo:"]
        scene_number_pattern = re.compile(r"scene\s+(\d+)", re.IGNORECASE)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for scene numbers
            scene_match = scene_number_pattern.search(line)
            if scene_match:
                scene_number = int(scene_match.group(1))
                if current_scene:
                    scenes.append(current_scene)
                current_scene = {
                    "scene_number": scene_number,
                    "narration": "",
                    "visual_description": ""
                }
                continue
                
            # If no current scene, create one
            if not current_scene:
                current_scene = {
                    "scene_number": len(scenes) + 1,
                    "narration": "",
                    "visual_description": ""
                }
            
            # Check for visual markers
            line_lower = line.lower()
            if any(marker in line_lower for marker in visual_markers):
                in_visual = True
                # Extract the text after the marker
                for marker in visual_markers:
                    if marker in line_lower:
                        text = line[line_lower.find(marker) + len(marker):].strip()
                        if text:
                            current_scene["visual_description"] += text + " "
                        break
                continue
                
            # Check for narration markers
            if any(marker in line_lower for marker in narration_markers):
                in_visual = False
                # Extract the text after the marker
                for marker in narration_markers:
                    if marker in line_lower:
                        text = line[line_lower.find(marker) + len(marker):].strip()
                        if text:
                            current_scene["narration"] += text + " "
                        break
                continue
                
            # Add to current section
            if in_visual:
                current_scene["visual_description"] += line + " "
            else:
                current_scene["narration"] += line + " "
        
        # Add the last scene
        if current_scene:
            scenes.append(current_scene)
            
        # Clean up the scenes
        for scene in scenes:
            scene["narration"] = scene["narration"].strip()
            scene["visual_description"] = scene["visual_description"].strip()
            
            # If no visual description, use the narration
            if not scene["visual_description"]:
                scene["visual_description"] = scene["narration"]
        
        return scenes
    
    def _generate_image(self, prompt: str, style: str = "Modern and clean", scene_number: int = 1) -> str:
        """
        Generate an image using DALL-E.
        
        Args:
            prompt: The prompt for image generation
            style: The visual style for the image
            scene_number: The scene number for the image
            
        Returns:
            str: Path to the generated image
        """
        try:
            # Check if OpenAI API key is available
            if not os.environ.get("OPENAI_API_KEY"):
                raise ValueError("OpenAI API key not found in environment variables")
            
            # Define output directory and file path
            output_dir = Path(__file__).parent.parent / "assets" / "images"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            image_path = output_dir / f"scene_{scene_number:02d}.png"
            
            # Use the AssetGenerator to generate the image
            return AssetGenerator.generate_image_from_dalle(
                prompt=prompt,
                output_path=str(image_path),
                style=style
            )
            
        except Exception as e:
            logger.error(f"Failed to generate image: {str(e)}")
            
            # Create a placeholder image using AssetGenerator
            try:
                output_dir = Path(__file__).parent.parent / "assets" / "images"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                image_path = output_dir / f"scene_{scene_number:02d}.png"
                
                return AssetGenerator.create_placeholder_image(
                    text=f"Scene {scene_number}: {prompt[:100]}...",
                    output_path=str(image_path)
                )
                
            except Exception as placeholder_error:
                logger.error(f"Failed to create placeholder image: {str(placeholder_error)}")
                raise e
    
    @track_duration
    async def generate_visuals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate visuals for a video script.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the generated visuals
        """
        log_event("visual_generation_started", {"job_id": context["job_id"]})
        
        try:
            # Get script from context
            script = context.get("script", "")
            if not script:
                logger.warning("No script found in context, checking for enhanced_script")
                script = context.get("enhanced_script", "")
                if not script:
                    raise ValueError("No script or enhanced_script found in context")
            
            # Get style preferences from context (with defaults)
            style = context.get("visual_style", "Modern and clean")
            colors = context.get("color_palette", "Vibrant but professional")
            
            # Format the prompt with context variables
            prompt = self.prompts["user_generate_visuals"].format(
                script=script,
                style=style,
                colors=colors
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
            
            # Extract visual descriptions from the script
            scenes = self._extract_visual_descriptions(script)
            
            # Ensure asset directories exist
            asset_dirs = AssetGenerator.ensure_asset_directories(context["output_dir"])
            
            # Generate images for each scene
            images = []
            for scene in scenes:
                logger.info(f"Generating image for scene {scene['scene_number']}")
                
                # Generate the image
                image_path = self._generate_image(
                    prompt=scene["visual_description"],
                    style=style,
                    scene_number=scene["scene_number"]
                )
                
                # Define output path directly in the job's image directory
                output_path = Path(asset_dirs["images"]) / f"scene_{scene['scene_number']:02d}.png"
                
                # Copy the image to the output directory
                import shutil
                shutil.copy(image_path, output_path)
                
                # Add to the list of images
                images.append({
                    "scene_number": scene["scene_number"],
                    "path": str(image_path),
                    "output_path": str(output_path),
                    "description": scene["visual_description"],
                    "narration": scene["narration"]
                })
            
            # Create a manifest of the images
            manifest_path = Path(asset_dirs["images"]) / "images_manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(images, f, indent=2)
            
            # Update the context
            result = {
                "images": images,
                "images_manifest_path": str(manifest_path),
                "visual_count": len(images),
                "visual_style": style,
                "visual_generation_response": assistant_response,
                "asset_dirs": asset_dirs
            }
            
            # Update the job manifest
            manifest_path = Path(context["output_dir"]) / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                    
                    # Update with visual information
                    manifest["visuals"] = {
                        "count": len(images),
                        "style": style,
                        "images": [img["output_path"] for img in images]
                    }
                    
                    with open(manifest_path, "w") as f:
                        json.dump(manifest, f, indent=2)
                except Exception as manifest_error:
                    logger.error(f"Failed to update job manifest: {str(manifest_error)}")
            
            log_event("visual_generation_completed", {
                "job_id": context["job_id"],
                "image_count": len(images)
            })
            return result
            
        except Exception as e:
            log_event("visual_generation_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to generate visuals: {str(e)}")
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
