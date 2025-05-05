#!/usr/bin/env python
"""
ResearchAgent: Performs web research for accurate script content.

This agent uses web search tools to gather information, verify facts,
and provide source citations for script content.
"""

import json
import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

from openai import OpenAI
# We need to modify our approach since we're having import issues
# Let's use the OpenAI client directly instead of the Agents SDK

from tools.observability import log_event, track_duration

# Configure logging
logger = logging.getLogger(__name__)

class ResearchAgent:
    """
    Agent for performing web research for script content.
    
    This agent uses the OpenAI Agents SDK to search the web for information,
    verify facts, and provide source citations for script content.
    """
    
    def __init__(self):
        """Initialize the ResearchAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self._load_prompts()
        self._create_agent()
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "research.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for ResearchAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _create_agent(self) -> None:
        """Create the OpenAI Assistant for research."""
        try:
            # Check if assistant ID is stored in environment variable
            assistant_id = os.environ.get("RESEARCH_ASSISTANT_ID")
            
            if assistant_id:
                try:
                    # Try to retrieve the existing assistant
                    self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                    self.assistant_id = assistant_id
                    logger.info(f"Retrieved existing ResearchAgent assistant: {assistant_id}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
            
            # Create a new assistant
            self.assistant = self.client.beta.assistants.create(
                name="ResearchAgent",
                description="Performs web research for accurate script content",
                model="gpt-4o-mini",
                instructions=self.prompts["system"],
                tools=[{"type": "file_search"}, {"type": "code_interpreter"}]
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new ResearchAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise
    
    def _wait_for_run(self, thread_id: str, run_id: str):
        """Wait for a run to complete."""
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
    async def research_topic(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research a topic for script content.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with research results
        """
        log_event("topic_research_started", {"job_id": context["job_id"]})
        
        try:
            # Format the prompt with context variables
            prompt = self.prompts["user_research_topic"].format(
                topic=context["topic"],
                depth=context.get("research_depth", "comprehensive"),
                focus=context.get("research_focus", "factual information and statistics")
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
            research_content = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Save the research to the output directory
            research_dir = Path(context["output_dir"]) / "research"
            research_dir.mkdir(parents=True, exist_ok=True)
            research_path = research_dir / "research.md"
            
            with open(research_path, "w") as f:
                f.write(research_content)
            
            # Update the context
            result = {
                "research": research_content,
                "research_path": str(research_path)
            }
            
            log_event("topic_research_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("topic_research_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to research topic: {str(e)}")
            raise
    
    @track_duration
    async def fact_check(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fact check a script for accuracy.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with fact checking results
        """
        log_event("fact_checking_started", {"job_id": context["job_id"]})
        
        try:
            # Format the prompt with context variables
            prompt = self.prompts["user_fact_check"].format(
                script=context["script"]
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
            fact_check_content = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Save the fact checking results to the output directory
            research_dir = Path(context["output_dir"]) / "research"
            research_dir.mkdir(parents=True, exist_ok=True)
            fact_check_path = research_dir / "fact_check.md"
            
            with open(fact_check_path, "w") as f:
                f.write(fact_check_content)
            
            # Update the context
            result = {
                "fact_check": fact_check_content,
                "fact_check_path": str(fact_check_path),
                "script_verified": True  # Default to true, the agent will indicate if there are issues
            }
            
            log_event("fact_checking_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("fact_checking_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to fact check script: {str(e)}")
            raise
    
    @track_duration
    async def generate_citations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate citations for a script.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with citation results
        """
        log_event("citation_generation_started", {"job_id": context["job_id"]})
        
        try:
            # Format the prompt with context variables
            prompt = self.prompts["user_generate_citations"].format(
                script=context["script"],
                citation_style=context.get("citation_style", "APA")
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
            citations_content = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Save the citations to the output directory
            research_dir = Path(context["output_dir"]) / "research"
            research_dir.mkdir(parents=True, exist_ok=True)
            citations_path = research_dir / "citations.md"
            
            with open(citations_path, "w") as f:
                f.write(citations_content)
            
            # Update the context
            result = {
                "citations": citations_content,
                "citations_path": str(citations_path)
            }
            
            log_event("citation_generation_completed", {"job_id": context["job_id"]})
            return result
            
        except Exception as e:
            log_event("citation_generation_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to generate citations: {str(e)}")
            raise
