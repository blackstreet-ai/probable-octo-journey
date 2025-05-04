"""
Executive Agent module.

This module implements the Executive Agent, which oversees the entire workflow,
spawning or messaging leaf agents, tracking statuses, and retrying failed nodes.
"""

from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
from pydantic import BaseModel

from ai_video_pipeline.agents.scriptwriter import ScriptwriterAgent
from ai_video_pipeline.agents.prompt_designer import PromptDesignerAgent
from ai_video_pipeline.agents.image_gen import ImageGenAgent
from ai_video_pipeline.agents.video_gen import VideoGenAgent
from ai_video_pipeline.agents.voice_synthesis import VoiceSynthesisAgent
from ai_video_pipeline.agents.music_selector import MusicSelectorAgent
from ai_video_pipeline.agents.audio_mixer import AudioMixerAgent
from ai_video_pipeline.agents.timeline_builder_agent import TimelineBuilderAgent
from ai_video_pipeline.agents.motion_qc import MotionQCAgent
from ai_video_pipeline.agents.compliance_qa import ComplianceQAAgent
from ai_video_pipeline.agents.thumbnail_creator import ThumbnailCreatorAgent
from ai_video_pipeline.tools.asset_librarian import AssetLibrarian

logger = logging.getLogger(__name__)

# Mock Agent class for testing without OpenAI Agents SDK
class Agent:
    def __init__(self, name, instructions=None, handoffs=None):
        self.name = name
        self.instructions = instructions
        self.handoffs = handoffs or []


class JobSpec(BaseModel):
    """
    Job specification for the video generation task.
    
    Args:
        title: The title of the video
        topic: The main topic/subject of the video
        tone: The tone/style of the video (e.g., educational, entertaining)
        runtime: Target runtime in seconds
        target_platform: Platform where the video will be published
        deadline: Optional deadline for the job completion
    """
    title: str
    topic: str
    tone: str
    runtime: int
    target_platform: str
    deadline: Optional[str] = None
    additional_metadata: Optional[Dict[str, Any]] = None


class ExecutiveAgent:
    """
    Executive Agent that owns the job lifecycle, breaks user intent into sub-tasks,
    assigns work, and aggregates results.
    
    This agent is responsible for:
    1. Initializing the workflow with a job specification
    2. Spawning and coordinating other agents
    3. Tracking the status of the workflow
    4. Handling retries and failures
    """
    
    def __init__(self, name: str = "Executive"):
        """
        Initialize the Executive Agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.agent = Agent(
            name=name,
            instructions=(
                "You are the Executive Agent responsible for orchestrating the entire "
                "video generation workflow. Your job is to break down user intent into "
                "sub-tasks, assign work to specialized agents, track progress, and "
                "aggregate results."
            ),
        )
        
    async def create_job_spec(self, user_prompt: str) -> JobSpec:
        """
        Create a job specification from the user prompt.
        
        Args:
            user_prompt: The user's input describing the video they want to create
            
        Returns:
            JobSpec: A structured job specification
        """
        # This is a stub implementation that will be expanded in future sprints
        # For now, we'll create a simple job spec with default values
        return JobSpec(
            title="Sample Video",
            topic=user_prompt,
            tone="informative",
            runtime=60,  # 1 minute video
            target_platform="YouTube",
        )
    
    async def run(self, user_prompt: str) -> Dict[str, Any]:
        """
        Run the executive agent with the given user prompt.
        
        Args:
            user_prompt: The user's input describing the video they want to create
            
        Returns:
            Dict[str, Any]: Results of the workflow execution
        """
        logger.info(f"Executive Agent running with prompt: {user_prompt}")
        
        # Create job specification
        job_spec = await self.create_job_spec(user_prompt)
        # Generate a job ID using the hash of the user prompt
        if len(user_prompt) > 0:
            # Convert hash to a positive number and then to string
            hash_value = abs(hash(user_prompt))
            job_id = f"job_{hash_value % 100000000:08d}"
        else:
            job_id = "job_default"
        
        # Initialize asset librarian
        asset_librarian = AssetLibrarian(job_id=job_id)
        
        # Initialize workflow results
        workflow_results = {
            "status": "in_progress",
            "job_id": job_id,
            "job_spec": job_spec.dict(),
            "assets": {},
            "stages": {}
        }
        
        try:
            # Step 1: Generate script
            logger.info("Executing Scriptwriter Agent")
            scriptwriter = ScriptwriterAgent()
            script_result = scriptwriter.run(job_spec.topic, job_spec.tone)
            workflow_results["stages"]["script"] = script_result
            
            # Step 2: Generate visual assets
            logger.info("Executing Visual Branch")
            
            # Step 2.1: Design prompts
            prompt_designer = PromptDesignerAgent()
            prompt_results = prompt_designer.run(script_result["script"])
            workflow_results["stages"]["prompts"] = prompt_results
            
            # Step 2.2: Generate images
            image_gen = ImageGenAgent()
            image_results = image_gen.run(prompt_results["prompts"])
            workflow_results["stages"]["images"] = image_results
            
            # Step 2.3: Generate videos
            video_gen = VideoGenAgent()
            video_results = video_gen.run(prompt_results["prompts"])
            workflow_results["stages"]["videos"] = video_results
            
            # Step 3: Generate audio assets
            logger.info("Executing Audio Branch")
            
            # Step 3.1: Generate voice synthesis
            voice_synthesis = VoiceSynthesisAgent()
            voice_results = voice_synthesis.run(script_result["script"])
            workflow_results["stages"]["voice"] = voice_results
            
            # Step 3.2: Select music
            music_selector = MusicSelectorAgent()
            music_results = music_selector.run(script_result["script"], job_spec.tone)
            workflow_results["stages"]["music"] = music_results
            
            # Step 3.3: Mix audio
            audio_mixer = AudioMixerAgent()
            audio_results = audio_mixer.run(
                voiceover_path=voice_results["audio_path"],
                music_path=music_results["music_path"]
            )
            workflow_results["stages"]["audio_mix"] = audio_results
            
            # Step 4: Generate timeline
            logger.info("Executing Timeline Builder Agent")
            timeline_builder = TimelineBuilderAgent()
            
            # Get the asset manifest from the asset librarian
            asset_manifest = asset_librarian.get_manifest()
            
            # Run the timeline builder
            timeline_results = timeline_builder.run(asset_manifest)
            workflow_results["stages"]["timeline"] = timeline_results
            
            # Step 5: Quality Control & Compliance
            logger.info("Executing Quality Control & Compliance Agents")
            
            # Step 5.1: Motion QC
            logger.info("Executing Motion QC Agent")
            motion_qc = MotionQCAgent()
            motion_qc_results = motion_qc.run(asset_manifest)
            workflow_results["stages"]["motion_qc"] = motion_qc_results
            
            # Step 5.2: Compliance QA
            logger.info("Executing Compliance QA Agent")
            compliance_qa = ComplianceQAAgent()
            compliance_qa_results = compliance_qa.run(asset_manifest)
            workflow_results["stages"]["compliance_qa"] = compliance_qa_results
            
            # Step 5.3: Thumbnail Creator
            logger.info("Executing Thumbnail Creator Agent")
            thumbnail_creator = ThumbnailCreatorAgent()
            thumbnail_results = thumbnail_creator.run(asset_manifest)
            workflow_results["stages"]["thumbnail"] = thumbnail_results
            
            # Check for critical quality or compliance issues
            has_critical_issues = False
            critical_issues = []
            
            # Check Motion QC results
            if motion_qc_results.get("status") == "fail":
                has_critical_issues = True
                critical_issues.append("Motion QC failed: " + motion_qc_results.get("message", ""))
            
            # Check Compliance QA results
            if compliance_qa_results.get("status") == "fail":
                has_critical_issues = True
                critical_issues.append("Compliance QA failed: " + 
                                     ", ".join([issue.get("message", "") for issue in compliance_qa_results.get("issues", [])]))
            
            # Update workflow status
            if has_critical_issues:
                workflow_results["status"] = "needs_review"
                workflow_results["message"] = "Workflow completed with critical issues that need review"
                workflow_results["critical_issues"] = critical_issues
            else:
                workflow_results["status"] = "completed"
                workflow_results["message"] = "Workflow completed successfully"
            
            workflow_results["assets"] = asset_librarian.get_manifest()["assets"]
            
        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            workflow_results["status"] = "failed"
            workflow_results["error"] = str(e)
            workflow_results["message"] = "Workflow execution failed"
        
        return workflow_results
