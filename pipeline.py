#!/usr/bin/env python
"""
Orchestrates the AI Video Automation Pipeline using the OpenAI Agents SDK.

This module provides functions to run the pipeline in sequential and parallel modes,
managing the execution of various agents in the video creation process.
"""

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread

from config import get_config, validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pipeline')


async def run_steps_sequentially(steps: List[Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a series of steps sequentially, passing context between them.
    
    Args:
        steps: List of callable functions to execute in sequence
        context: Initial context dictionary to pass between steps
        
    Returns:
        Dict[str, Any]: Updated context after all steps have completed
    """
    current_context = context.copy()
    
    for step in steps:
        logger.info(f"Running step: {step.__name__}")
        start_time = time.time()
        
        try:
            # Run the step and update the context
            step_result = await step(current_context)
            current_context.update(step_result)
            
            # Log completion time
            duration = time.time() - start_time
            logger.info(f"Completed step {step.__name__} in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in step {step.__name__}: {str(e)}")
            # Add step information to the exception context
            raise type(e)(f"Error in step {step.__name__}: {str(e)}") from e
    
    return current_context


async def run_steps_in_parallel(steps: List[Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a series of steps in parallel, then merge their results.
    
    Args:
        steps: List of callable functions to execute in parallel
        context: Initial context dictionary to pass to each step
        
    Returns:
        Dict[str, Any]: Updated context with merged results from all steps
    """
    current_context = context.copy()
    tasks = []
    
    # Create tasks for each step
    for step in steps:
        logger.info(f"Creating parallel task for: {step.__name__}")
        tasks.append(asyncio.create_task(step(current_context)))
    
    # Wait for all tasks to complete
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.time() - start_time
    logger.info(f"Completed all parallel steps in {duration:.2f} seconds")
    
    # Process results and update context
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            step_name = steps[i].__name__
            logger.error(f"Error in parallel step {step_name}: {str(result)}")
            # Add step information to the exception context
            raise type(result)(f"Error in parallel step {step_name}: {str(result)}") from result
        else:
            current_context.update(result)
    
    return current_context


async def create_video_from_topic(topic: str, output_dir: Optional[str] = None, 
                                publish: bool = False, notify: bool = False,
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main pipeline function to create a video from a topic.
    
    Args:
        topic: The topic or idea for the video
        output_dir: Optional directory to save output files
        publish: Whether to publish the video to YouTube
        notify: Whether to send notifications about the process
        context: Optional additional context parameters for customization
        
    Returns:
        Dict[str, Any]: Results of the pipeline execution
    """
    # Validate configuration
    if not validate_config():
        raise ValueError("Invalid configuration. Please check your .env file.")
    
    # Create a unique job ID
    job_id = str(uuid.uuid4())[:8]
    logger.info(f"Starting video creation pipeline for topic: '{topic}' (Job ID: {job_id})")
    
    # Set up output directory
    config = get_config()
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Path(config['assets_dir']) / f"job_{job_id}"
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize context
    pipeline_context = {
        'job_id': job_id,
        'topic': topic,
        'output_dir': str(output_path),
        'config': config,
        'publish': publish,
        'notify': notify,
        'start_time': time.time(),
    }
    
    # Add any additional context parameters
    if context:
        pipeline_context.update(context)
    
    # Import agents here to avoid circular imports
    from agents.video_orchestrator import VideoOrchestratorAgent
    from agents.script_rewriter import ScriptRewriterAgent
    from agents.script_generator import ScriptGeneratorAgent
    from agents.research import ResearchAgent
    from agents.voiceover import VoiceoverAgent
    from agents.music_supervisor import MusicSupervisorAgent
    from agents.visual_composer import VisualComposerAgent
    from agents.video_editor import VideoEditorAgent
    
    # Create agent instances
    orchestrator = VideoOrchestratorAgent()
    script_rewriter = ScriptRewriterAgent()
    script_generator = ScriptGeneratorAgent()
    research_agent = ResearchAgent()
    voiceover = VoiceoverAgent()
    music_supervisor = MusicSupervisorAgent()
    visual_composer = VisualComposerAgent()
    video_editor = VideoEditorAgent()
    
    # Define the pipeline steps
    try:
        # Step 1: Script generation with research (sequential)
        script_steps = [
            orchestrator.initialize_job,
            # Research phase
            research_agent.research_topic,
            # Script generation phase
            script_generator.generate_script,
            # Fact-checking phase
            research_agent.fact_check,
            # Script enhancement
            script_generator.enhance_script,
            # Final review
            orchestrator.review_script,
        ]
        pipeline_context = await run_steps_sequentially(script_steps, pipeline_context)
        
        # Step 2: Asset generation (parallel)
        asset_steps = [
            voiceover.synthesize_audio,
            music_supervisor.select_music,
            visual_composer.generate_visuals,
        ]
        pipeline_context = await run_steps_in_parallel(asset_steps, pipeline_context)
        
        # Step 3: Video assembly (sequential)
        assembly_steps = [
            video_editor.assemble_video,
            orchestrator.review_video,
        ]
        pipeline_context = await run_steps_sequentially(assembly_steps, pipeline_context)
        
        # Step 4: Publishing (conditional)
        if publish:
            from agents.publish_manager import PublishManagerAgent
            publisher = PublishManagerAgent()
            pipeline_context = await publisher.publish_to_youtube(pipeline_context)
        
        # Step 5: Notification (conditional)
        if notify:
            from agents.reporter import ReporterAgent
            reporter = ReporterAgent()
            pipeline_context = await reporter.send_notification(pipeline_context)
        
        # Log completion
        duration = time.time() - pipeline_context['start_time']
        logger.info(f"Pipeline completed in {duration:.2f} seconds (Job ID: {job_id})")
        
        return pipeline_context
        
    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {str(e)}")
        
        # Update pipeline_context with error information
        pipeline_context['error'] = str(e)
        pipeline_context['status'] = 'failed'
        
        # Attempt to send failure notification if requested
        if notify:
            try:
                from agents.reporter import ReporterAgent
                reporter = ReporterAgent()
                await reporter.send_failure_notification(pipeline_context)
            except Exception as notify_error:
                logger.error(f"Failed to send failure notification: {str(notify_error)}")
        
        # Save error information to job manifest if possible
        try:
            manifest_path = Path(pipeline_context.get('output_dir', '')) / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                manifest['status'] = 'failed'
                manifest['error'] = str(e)
                
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)
        except Exception as manifest_error:
            logger.error(f"Failed to update manifest with error: {str(manifest_error)}")
        
        # Re-raise the original exception
        raise
