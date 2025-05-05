#!/usr/bin/env python
"""
ScriptGeneratorAgent: Creates structured scripts from templates and research.

This agent generates video scripts using predefined templates for different
formats (narration, interview, news report, etc.) and integrates with the
ResearchAgent to ensure content accuracy.
"""

import json
import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from tools.script_validator import validate_script, fix_script_formatting

from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads.run import Run

from tools.observability import log_event, track_duration

# Configure logging
logger = logging.getLogger(__name__)

class ScriptGeneratorAgent:
    """
    Agent for generating structured video scripts from templates.
    
    This agent creates scripts using predefined templates for different video
    formats and integrates with the ResearchAgent to ensure content accuracy.
    """
    
    def __init__(self):
        """Initialize the ScriptGeneratorAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self._load_prompts()
        self._load_templates()
        self._create_assistant()
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "script_generator.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for ScriptGeneratorAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _load_templates(self) -> None:
        """Load script templates from YAML files."""
        templates_dir = Path(__file__).parent.parent / "prompts" / "templates"
        self.templates = {}
        
        try:
            for template_file in templates_dir.glob("*.yaml"):
                template_name = template_file.stem
                with open(template_file, "r") as f:
                    self.templates[template_name] = yaml.safe_load(f)
            logger.debug(f"Loaded {len(self.templates)} script templates")
        except Exception as e:
            logger.error(f"Failed to load script templates: {str(e)}")
            raise
    
    def _create_assistant(self) -> None:
        """Create or retrieve the OpenAI Assistant for this agent."""
        # Check if assistant ID is stored in environment variable
        assistant_id = os.environ.get("SCRIPT_GENERATOR_ASSISTANT_ID")
        
        if assistant_id:
            try:
                # Try to retrieve the existing assistant
                self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant_id
                logger.info(f"Retrieved existing ScriptGeneratorAgent assistant: {assistant_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
        
        # Create a new assistant
        try:
            self.assistant = self.client.beta.assistants.create(
                name="ScriptGeneratorAgent",
                description="Creates structured scripts from templates and research",
                model="gpt-4o-mini",
                instructions=self.prompts["system"],
                tools=[{"type": "code_interpreter"}]  # Using code_interpreter for formatting
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new ScriptGeneratorAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
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
            if run.status in ["completed", "failed", "cancelled", "expired"]:
                return run
            # Add a small delay before checking again
            import time
            time.sleep(1)
    
    @track_duration
    async def generate_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a script using a template and research.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the generated script
        """
        log_event("script_generation_started", {"job_id": context["job_id"]})
        
        try:
            # Get the template format
            template_format = context.get("script_format", "narration")
            if template_format not in self.templates:
                logger.warning(f"Template format {template_format} not found, using narration")
                template_format = "narration"
            
            template = self.templates[template_format]
            
            # Format the prompt with context variables
            prompt = self.prompts["user_generate_script"].format(
                topic=context["topic"],
                audience=context.get("audience", "general audience"),
                tone=context.get("tone", "informative and engaging"),
                duration=context.get("duration", "5-7 minutes"),
                template_format=template_format,
                template_structure=template["structure"],
                research=context.get("research", "")
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
            
            # Validate the script against its template
            is_valid, issues = validate_script(script_content, template_format)
            
            # If there are issues, try to fix them automatically
            if not is_valid:
                logger.warning(f"Script validation found {len(issues)} issues")
                for issue in issues:
                    logger.warning(f"Validation issue: {issue}")
                
                # Try to fix formatting issues
                fixed_script = fix_script_formatting(script_content)
                
                # Check if the fixes resolved the issues
                is_valid_after_fix, remaining_issues = validate_script(fixed_script, template_format)
                
                if is_valid_after_fix:
                    logger.info("Script formatting issues fixed automatically")
                    script_content = fixed_script
                else:
                    logger.warning(f"Some script issues could not be fixed automatically: {len(remaining_issues)} remaining")
                    # Use the fixed version anyway, as it's likely better than the original
                    script_content = fixed_script
            
            # Save the script to the output directory
            script_dir = Path(context["output_dir"]) / "script"
            script_dir.mkdir(parents=True, exist_ok=True)
            script_path = script_dir / f"{template_format}_script.md"
            
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # Update the context
            result = {
                "script": script_content,
                "script_path": str(script_path),
                "script_format": template_format,
                "script_version": "1.0",
                "script_validation": {
                    "is_valid": is_valid,
                    "issues": issues if not is_valid else []
                }
            }
            
            log_event("script_generation_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("script_generation_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to generate script: {str(e)}")
            raise
    
    @track_duration
    async def revise_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Revise a script based on feedback or fact-checking.
        
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
                feedback=context.get("script_feedback", ""),
                fact_check=context.get("fact_check", "")
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
            
            # Get the current script format and version
            script_format = context.get("script_format", "narration")
            script_version = context.get("script_version", "1.0")
            
            # Increment version
            version_parts = script_version.split(".")
            new_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}"
            
            # Validate the revised script against its template
            is_valid, issues = validate_script(revised_script, script_format)
            
            # If there are issues, try to fix them automatically
            if not is_valid:
                logger.warning(f"Revised script validation found {len(issues)} issues")
                for issue in issues:
                    logger.warning(f"Validation issue: {issue}")
                
                # Try to fix formatting issues
                fixed_script = fix_script_formatting(revised_script)
                
                # Check if the fixes resolved the issues
                is_valid_after_fix, remaining_issues = validate_script(fixed_script, script_format)
                
                if is_valid_after_fix:
                    logger.info("Revised script formatting issues fixed automatically")
                    revised_script = fixed_script
                else:
                    logger.warning(f"Some revised script issues could not be fixed automatically: {len(remaining_issues)} remaining")
                    # Use the fixed version anyway, as it's likely better than the original
                    revised_script = fixed_script
            
            # Save the revised script to the output directory
            script_dir = Path(context["output_dir"]) / "script"
            script_dir.mkdir(parents=True, exist_ok=True)
            script_path = script_dir / f"{script_format}_script_v{new_version}.md"
            
            with open(script_path, "w") as f:
                f.write(revised_script)
            
            # Also save version history
            history_dir = script_dir / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            history_path = history_dir / f"{script_format}_script_v{script_version}.md"
            
            with open(history_path, "w") as f:
                f.write(context["script"])
            
            # Update the context
            result = {
                "script": revised_script,
                "script_path": str(script_path),
                "script_format": script_format,
                "script_version": new_version,
                "previous_script_path": str(history_path),
                "script_validation": {
                    "is_valid": is_valid,
                    "issues": issues if not is_valid else []
                }
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
    
    @track_duration
    async def enhance_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a script with hooks, calls to action, transitions, etc.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the enhanced script
        """
        log_event("script_enhancement_started", {"job_id": context["job_id"]})
        
        try:
            # Get enhancement types
            enhancements = context.get("enhancements", ["hooks", "transitions", "calls_to_action"])
            enhancement_str = ", ".join(enhancements)
            
            # Format the prompt with context variables
            prompt = self.prompts["user_enhance_script"].format(
                script=context["script"],
                enhancements=enhancement_str
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
            enhanced_script = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Get the current script format and version
            script_format = context.get("script_format", "narration")
            script_version = context.get("script_version", "1.0")
            
            # Increment version
            version_parts = script_version.split(".")
            new_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}"
            
            # Validate the enhanced script against its template
            is_valid, issues = validate_script(enhanced_script, script_format)
            
            # If there are issues, try to fix them automatically
            if not is_valid:
                logger.warning(f"Enhanced script validation found {len(issues)} issues")
                for issue in issues:
                    logger.warning(f"Validation issue: {issue}")
                
                # Try to fix formatting issues
                fixed_script = fix_script_formatting(enhanced_script)
                
                # Check if the fixes resolved the issues
                is_valid_after_fix, remaining_issues = validate_script(fixed_script, script_format)
                
                if is_valid_after_fix:
                    logger.info("Enhanced script formatting issues fixed automatically")
                    enhanced_script = fixed_script
                else:
                    logger.warning(f"Some enhanced script issues could not be fixed automatically: {len(remaining_issues)} remaining")
                    # Use the fixed version anyway, as it's likely better than the original
                    enhanced_script = fixed_script
            
            # Save the enhanced script to the output directory
            script_dir = Path(context["output_dir"]) / "script"
            script_dir.mkdir(parents=True, exist_ok=True)
            script_path = script_dir / f"{script_format}_script_enhanced_v{new_version}.md"
            
            with open(script_path, "w") as f:
                f.write(enhanced_script)
            
            # Also save version history
            history_dir = script_dir / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            history_path = history_dir / f"{script_format}_script_v{script_version}.md"
            
            with open(history_path, "w") as f:
                f.write(context["script"])
            
            # Update the context
            result = {
                "script": enhanced_script,
                "script_path": str(script_path),
                "script_format": script_format,
                "script_version": new_version,
                "previous_script_path": str(history_path),
                "enhancements_applied": enhancements,
                "script_validation": {
                    "is_valid": is_valid,
                    "issues": issues if not is_valid else []
                }
            }
            
            log_event("script_enhancement_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("script_enhancement_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to enhance script: {str(e)}")
            raise
    
    @track_duration
    async def integrate_research(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrate research findings into an existing script.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with the research-integrated script
        """
        log_event("research_integration_started", {"job_id": context["job_id"]})
        
        try:
            # Format the prompt with context variables
            prompt = self.prompts["user_integrate_research"].format(
                script=context["script"],
                research=context["research"]
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
            integrated_script = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Get the current script format and version
            script_format = context.get("script_format", "narration")
            script_version = context.get("script_version", "1.0")
            
            # Increment version
            version_parts = script_version.split(".")
            new_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}"
            
            # Save the integrated script to the output directory
            script_dir = Path(context["output_dir"]) / "script"
            script_dir.mkdir(parents=True, exist_ok=True)
            script_path = script_dir / f"{script_format}_script_researched_v{new_version}.md"
            
            with open(script_path, "w") as f:
                f.write(integrated_script)
            
            # Also save version history
            history_dir = script_dir / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            history_path = history_dir / f"{script_format}_script_v{script_version}.md"
            
            with open(history_path, "w") as f:
                f.write(context["script"])
            
            # Update the context
            result = {
                "script": integrated_script,
                "script_path": str(script_path),
                "script_format": script_format,
                "script_version": new_version,
                "previous_script_path": str(history_path),
                "research_integrated": True
            }
            
            log_event("research_integration_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("research_integration_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to integrate research: {str(e)}")
            raise
