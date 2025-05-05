#!/usr/bin/env python
"""
VideoOrchestratorAgent: Main controller for the AI Video Automation Pipeline.

This agent is responsible for coordinating all sub-agents, managing the workflow,
and ensuring quality at each step of the video creation process.
"""

import json
import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads.run import Run

from tools.observability import log_event, track_duration

# Configure logging
logger = logging.getLogger(__name__)

class VideoOrchestratorAgent:
    """
    Main controller agent for the AI Video Automation Pipeline.
    
    This agent coordinates all sub-agents, manages the workflow,
    and ensures quality at each step of the video creation process.
    """
    
    def __init__(self):
        """Initialize the VideoOrchestratorAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self._load_prompts()
        self._create_assistant()
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "video_orchestrator.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for VideoOrchestratorAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _create_assistant(self) -> None:
        """Create or retrieve the OpenAI Assistant for this agent."""
        # Check if assistant ID is stored in environment variable
        assistant_id = os.environ.get("VIDEO_ORCHESTRATOR_ASSISTANT_ID")
        
        if assistant_id:
            try:
                # Try to retrieve the existing assistant
                self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant_id
                logger.info(f"Retrieved existing VideoOrchestratorAgent assistant: {assistant_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
        
        # Create a new assistant
        try:
            self.assistant = self.client.beta.assistants.create(
                name="VideoOrchestratorAgent",
                description="Main controller for the AI Video Automation Pipeline",
                model="gpt-4o-mini",
                instructions=self.prompts["system"],
                tools=[{"type": "code_interpreter"}]  # Using code_interpreter instead of empty function
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new VideoOrchestratorAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise
    
    @track_duration
    async def initialize_job(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize a new video creation job.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with job initialization results
        """
        log_event("job_initialization_started", {"job_id": context["job_id"]})
        
        try:
            # Format the prompt with context variables
            prompt = self.prompts["user_initialize"].format(
                topic=context["topic"],
                job_id=context["job_id"],
                output_dir=context["output_dir"]
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
            
            # Create job manifest
            manifest = {
                "job_id": context["job_id"],
                "topic": context["topic"],
                "status": "initialized",
                "steps": [
                    {"name": "script_creation", "status": "pending"},
                    {"name": "asset_generation", "status": "pending"},
                    {"name": "video_assembly", "status": "pending"},
                    {"name": "quality_control", "status": "pending"},
                    {"name": "publishing", "status": "pending"}
                ],
                "assistant_response": assistant_response
            }
            
            # Save the manifest to the output directory
            manifest_path = Path(context["output_dir"]) / "manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Update the context
            result = {
                "manifest": manifest,
                "thread_id": thread.id,
                "manifest_path": str(manifest_path)
            }
            
            log_event("job_initialization_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("job_initialization_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to initialize job: {str(e)}")
            raise
    
    @track_duration
    async def review_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review the script produced by the ScriptRewriterAgent.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with script review results
        """
        log_event("script_review_started", {"job_id": context["job_id"]})
        
        try:
            # Format the prompt with context variables
            prompt = self.prompts["user_review_script"].format(
                topic=context["topic"],
                script=context["script"]
            )
            
            # Create a new thread for this review
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
            
            # Determine if the script is approved
            script_approved = "approved" in assistant_response.lower() and "not approved" not in assistant_response.lower()
            
            # Update the manifest
            manifest = context["manifest"]
            manifest["steps"][0]["status"] = "completed"
            manifest["steps"][1]["status"] = "in_progress" if script_approved else "blocked"
            manifest["script_review"] = {
                "approved": script_approved,
                "feedback": assistant_response
            }
            
            # Save the updated manifest
            with open(context["manifest_path"], "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Update the context
            result = {
                "script_approved": script_approved,
                "script_feedback": assistant_response,
                "manifest": manifest
            }
            
            log_event("script_review_completed", {
                "job_id": context["job_id"],
                "approved": script_approved
            })
            return result
            
        except Exception as e:
            log_event("script_review_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to review script: {str(e)}")
            raise
    
    @track_duration
    async def review_video(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review the final video before publishing.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with video review results
        """
        log_event("video_review_started", {"job_id": context["job_id"]})
        
        try:
            # Format the prompt with context variables
            prompt = self.prompts["user_review_video"].format(
                job_id=context["job_id"],
                topic=context["topic"],
                duration=context.get("video_duration", "unknown"),
                resolution=context.get("video_resolution", "unknown"),
                audio_quality=context.get("audio_quality", "unknown")
            )
            
            # Create a new thread for this review
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
            
            # Determine if the video is approved
            video_approved = "approved" in assistant_response.lower() and "not approved" not in assistant_response.lower()
            
            # Update the manifest
            manifest = context["manifest"]
            manifest["steps"][3]["status"] = "completed"
            manifest["steps"][4]["status"] = "in_progress" if video_approved else "blocked"
            manifest["video_review"] = {
                "approved": video_approved,
                "feedback": assistant_response
            }
            
            # Save the updated manifest
            with open(context["manifest_path"], "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Update the context
            result = {
                "video_approved": video_approved,
                "video_feedback": assistant_response,
                "manifest": manifest
            }
            
            log_event("video_review_completed", {
                "job_id": context["job_id"],
                "approved": video_approved
            })
            return result
            
        except Exception as e:
            log_event("video_review_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to review video: {str(e)}")
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
