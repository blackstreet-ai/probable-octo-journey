#!/usr/bin/env python
"""
ScriptRewriterAgent: Enhances raw transcript, adds pacing, story beats, and CTAs.

This agent transforms basic topic ideas into polished video scripts with
clear structure, natural pacing, and engaging elements.
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

class ScriptRewriterAgent:
    """
    Agent for creating and revising video scripts.
    
    This agent transforms basic topic ideas into polished video scripts with
    clear structure, natural pacing, and engaging elements.
    """
    
    def __init__(self):
        """Initialize the ScriptRewriterAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self._load_prompts()
        self._create_assistant()
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "script_rewriter.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for ScriptRewriterAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _create_assistant(self) -> None:
        """Create or retrieve the OpenAI Assistant for this agent."""
        # Check if assistant ID is stored in environment variable
        assistant_id = os.environ.get("SCRIPT_REWRITER_ASSISTANT_ID")
        
        if assistant_id:
            try:
                # Try to retrieve the existing assistant
                self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant_id
                logger.info(f"Retrieved existing ScriptRewriterAgent assistant: {assistant_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
        
        # Create a new assistant
        try:
            self.assistant = self.client.beta.assistants.create(
                name="ScriptRewriterAgent",
                description="Creates engaging video scripts from topic ideas",
                model="gpt-4o-mini",
                instructions=self.prompts["system"],
                tools=[{"type": "code_interpreter"}]  # Using code_interpreter instead of empty function
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new ScriptRewriterAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise
    
    @track_duration
    async def create_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a video script from a topic.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the created script
        """
        log_event("script_creation_started", {"job_id": context["job_id"]})
        
        try:
            # Determine audience and tone (with defaults)
            audience = context.get("audience", "general audience interested in educational content")
            tone = context.get("tone", "informative and engaging")
            
            # Format the prompt with context variables
            prompt = self.prompts["user_create_script"].format(
                topic=context["topic"],
                audience=audience,
                tone=tone
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
            script_content = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Save the script to the output directory
            script_dir = Path(context["output_dir"]) / "script"
            script_dir.mkdir(parents=True, exist_ok=True)
            script_path = script_dir / "script.md"
            
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # Update the context
            result = {
                "script": script_content,
                "script_path": str(script_path)
            }
            
            log_event("script_creation_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("script_creation_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to create script: {str(e)}")
            raise
    
    @track_duration
    async def revise_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Revise a script based on feedback.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the revised script
        """
        log_event("script_revision_started", {"job_id": context["job_id"]})
        
        try:
            # Format the prompt with context variables
            prompt = self.prompts["user_revise_script"].format(
                script=context["script"],
                feedback=context["script_feedback"]
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
            revised_script = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Save the revised script to the output directory
            script_dir = Path(context["output_dir"]) / "script"
            script_dir.mkdir(parents=True, exist_ok=True)
            revised_script_path = script_dir / "script_revised.md"
            
            with open(revised_script_path, "w") as f:
                f.write(revised_script)
            
            # Update the context
            result = {
                "script": revised_script,
                "script_path": str(revised_script_path)
            }
            
            log_event("script_revision_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("script_revision_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to revise script: {str(e)}")
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
