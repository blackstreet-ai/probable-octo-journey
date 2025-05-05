#!/usr/bin/env python
"""
Example script demonstrating the integration between ResearchAgent and ScriptGeneratorAgent.

This example shows how to use the ResearchAgent to gather information and then
feed that research into the ScriptGeneratorAgent to create a well-researched script.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

from agents.research import ResearchAgent
from agents.script_generator import ScriptGeneratorAgent
from tools.observability import log_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_research_to_script_pipeline(topic: str, script_format: str = "narration", output_dir: str = "./output") -> Dict[str, Any]:
    """
    Run a complete research-to-script pipeline.
    
    Args:
        topic: The topic to research and create a script for
        script_format: The format of the script (narration, interview, news_report)
        output_dir: Directory to save outputs
        
    Returns:
        Dict[str, Any]: The final context with all results
    """
    # Initialize context
    job_id = f"research-script-{int(asyncio.get_event_loop().time())}"
    context = {
        "job_id": job_id,
        "topic": topic,
        "script_format": script_format,
        "output_dir": output_dir,
        "audience": "general public",
        "tone": "informative and engaging",
        "duration": "5-7 minutes",
        "research_depth": "comprehensive",
        "research_focus": "factual information and statistics"
    }
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize agents
    research_agent = ResearchAgent()
    script_generator = ScriptGeneratorAgent()
    
    try:
        # Step 1: Research the topic
        logger.info(f"Starting research on topic: {topic}")
        log_event("pipeline_research_started", {"job_id": job_id, "topic": topic})
        
        research_results = await research_agent.research_topic(context)
        context.update(research_results)
        
        logger.info(f"Research completed. Research saved to: {research_results['research_path']}")
        
        # Step 2: Generate script using research
        logger.info(f"Generating {script_format} script using research")
        log_event("pipeline_script_generation_started", {"job_id": job_id, "format": script_format})
        
        script_results = await script_generator.generate_script(context)
        context.update(script_results)
        
        logger.info(f"Script generation completed. Script saved to: {script_results['script_path']}")
        
        # Step 3: Fact-check the script
        logger.info("Fact-checking the generated script")
        log_event("pipeline_fact_checking_started", {"job_id": job_id})
        
        fact_check_results = await research_agent.fact_check(context)
        context.update(fact_check_results)
        
        logger.info(f"Fact-checking completed. Results saved to: {fact_check_results['fact_check_path']}")
        
        # Step 4: Revise script based on fact-checking if needed
        if not context.get("script_verified", False):
            logger.info("Script needs revision based on fact-checking")
            log_event("pipeline_script_revision_started", {"job_id": job_id})
            
            revision_results = await script_generator.revise_script(context)
            context.update(revision_results)
            
            logger.info(f"Script revision completed. Revised script saved to: {revision_results['script_path']}")
        
        # Step 5: Generate citations for the script
        logger.info("Generating citations for the script")
        log_event("pipeline_citation_generation_started", {"job_id": job_id})
        
        citation_results = await research_agent.generate_citations(context)
        context.update(citation_results)
        
        logger.info(f"Citation generation completed. Citations saved to: {citation_results['citations_path']}")
        
        # Step 6: Enhance the script with hooks, transitions, etc.
        logger.info("Enhancing script with hooks, transitions, and calls to action")
        log_event("pipeline_script_enhancement_started", {"job_id": job_id})
        
        context["enhancements"] = ["hooks", "transitions", "calls_to_action"]
        enhancement_results = await script_generator.enhance_script(context)
        context.update(enhancement_results)
        
        logger.info(f"Script enhancement completed. Enhanced script saved to: {enhancement_results['script_path']}")
        
        # Save the final context as a manifest
        manifest_path = output_path / f"{job_id}_manifest.json"
        with open(manifest_path, "w") as f:
            # Create a simplified version of the context for the manifest
            manifest = {
                "job_id": context["job_id"],
                "topic": context["topic"],
                "script_format": context["script_format"],
                "script_path": context["script_path"],
                "research_path": context["research_path"],
                "fact_check_path": context["fact_check_path"],
                "citations_path": context["citations_path"],
                "script_version": context["script_version"],
                "enhancements_applied": context["enhancements_applied"],
                "completion_time": asyncio.get_event_loop().time()
            }
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Pipeline completed successfully. Manifest saved to: {manifest_path}")
        log_event("pipeline_completed", {"job_id": job_id, "status": "success"})
        
        return context
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        log_event("pipeline_failed", {"job_id": job_id, "error": str(e)})
        raise

async def main():
    """Run the example."""
    # Example usage
    topic = "The Impact of Artificial Intelligence on Healthcare"
    script_format = "narration"  # Options: narration, interview, news_report
    output_dir = "./output/ai_healthcare_example"
    
    try:
        result = await run_research_to_script_pipeline(topic, script_format, output_dir)
        print(f"\nPipeline completed successfully!")
        print(f"Final script: {result['script_path']}")
        print(f"Research: {result['research_path']}")
        print(f"Citations: {result['citations_path']}")
    except Exception as e:
        print(f"Pipeline failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
