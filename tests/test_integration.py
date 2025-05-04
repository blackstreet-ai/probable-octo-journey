#!/usr/bin/env python
"""
End-to-end integration tests for the AI Video Automation Pipeline.

This module contains tests that simulate the entire pipeline from transcript to final video,
ensuring all components work together correctly.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from pipeline import VideoPipeline
from agents.video_orchestrator import VideoOrchestratorAgent
from agents.script_rewriter import ScriptRewriterAgent
from agents.voiceover import VoiceoverAgent
from agents.music_supervisor import MusicSupervisorAgent
from agents.visual_composer import VisualComposerAgent
from agents.video_editor import VideoEditorAgent
from agents.publish_manager import PublishManagerAgent
from agents.reporter import ReporterAgent
from tools.token_manager import TokenManager


class TestEndToEndPipeline:
    """End-to-end integration tests for the AI Video Automation Pipeline."""

    @pytest.fixture
    def mock_all_agents(self):
        """Mock all agents used in the pipeline."""
        with patch('agents.video_orchestrator.VideoOrchestratorAgent') as mock_orchestrator, \
             patch('agents.script_rewriter.ScriptRewriterAgent') as mock_script_rewriter, \
             patch('agents.voiceover.VoiceoverAgent') as mock_voiceover, \
             patch('agents.music_supervisor.MusicSupervisorAgent') as mock_music, \
             patch('agents.visual_composer.VisualComposerAgent') as mock_visual, \
             patch('agents.video_editor.VideoEditorAgent') as mock_video_editor, \
             patch('agents.publish_manager.PublishManagerAgent') as mock_publish, \
             patch('agents.reporter.ReporterAgent') as mock_reporter:
            
            # Configure the mocks
            mock_orchestrator.return_value.initialize_job = AsyncMock()
            mock_orchestrator.return_value.review_script = AsyncMock()
            mock_orchestrator.return_value.review_video = AsyncMock()
            
            mock_script_rewriter.return_value.create_script = AsyncMock()
            mock_script_rewriter.return_value.revise_script = AsyncMock()
            
            mock_voiceover.return_value.extract_narration = AsyncMock()
            mock_voiceover.return_value.optimize_narration = AsyncMock()
            mock_voiceover.return_value.synthesize_audio = AsyncMock()
            
            mock_music.return_value.select_music = AsyncMock()
            mock_music.return_value.process_music = AsyncMock()
            
            mock_visual.return_value.extract_visual_descriptions = AsyncMock()
            mock_visual.return_value.generate_visuals = AsyncMock()
            
            mock_video_editor.return_value.create_edit_plan = AsyncMock()
            mock_video_editor.return_value.assemble_video = AsyncMock()
            
            mock_publish.return_value.prepare_metadata = AsyncMock()
            mock_publish.return_value.publish_to_youtube = AsyncMock()
            
            mock_reporter.return_value.generate_report = AsyncMock()
            mock_reporter.return_value.send_notification = AsyncMock()
            
            yield {
                'orchestrator': mock_orchestrator,
                'script_rewriter': mock_script_rewriter,
                'voiceover': mock_voiceover,
                'music': mock_music,
                'visual': mock_visual,
                'video_editor': mock_video_editor,
                'publish': mock_publish,
                'reporter': mock_reporter
            }

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, mock_all_agents, test_output_dir, mock_elevenlabs_api, mock_dalle_api):
        """
        Test the full pipeline with all steps succeeding.
        
        This test simulates a successful run of the entire pipeline from transcript to final video.
        """
        # Configure the mock agent responses
        mocks = mock_all_agents
        
        # VideoOrchestratorAgent
        job_id = "test_job_123"
        manifest = {
            "job_id": job_id,
            "topic": "The Future of AI",
            "status": "initialized",
            "steps": [
                {"name": "script_creation", "status": "pending"},
                {"name": "asset_generation", "status": "pending"},
                {"name": "video_assembly", "status": "pending"},
                {"name": "quality_control", "status": "pending"},
                {"name": "publishing", "status": "pending"}
            ]
        }
        manifest_path = str(test_output_dir / job_id / "manifest.json")
        
        mocks['orchestrator'].return_value.initialize_job.return_value = {
            "manifest": manifest,
            "thread_id": "test_thread_id",
            "manifest_path": manifest_path
        }
        
        mocks['orchestrator'].return_value.review_script.return_value = {
            "script_approved": True,
            "script_feedback": "The script is well-structured and engaging.",
            "manifest": manifest
        }
        
        mocks['orchestrator'].return_value.review_video.return_value = {
            "video_approved": True,
            "video_feedback": "The video meets all quality standards.",
            "manifest": manifest
        }
        
        # ScriptRewriterAgent
        script = """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence.

**VISUAL:** Show a montage of futuristic AI applications.
"""
        script_path = str(test_output_dir / job_id / "scripts" / "script.md")
        
        mocks['script_rewriter'].return_value.create_script.return_value = {
            "script": script,
            "script_path": script_path
        }
        
        # VoiceoverAgent
        narration = "Welcome to our exploration of the future of artificial intelligence."
        optimized_narration = "Welcome to our exploration of the future of AI."
        audio_path = str(test_output_dir / job_id / "audio" / "voiceover.mp3")
        
        mocks['voiceover'].return_value.extract_narration.return_value = {
            "narration": narration
        }
        
        mocks['voiceover'].return_value.optimize_narration.return_value = {
            "optimized_narration": optimized_narration
        }
        
        mocks['voiceover'].return_value.synthesize_audio.return_value = {
            "audio_path": audio_path
        }
        
        # MusicSupervisorAgent
        music_selection = "Selected 'Digital Dawn' - A modern electronic track with uplifting synths."
        music_file = str(test_output_dir / job_id / "music" / "original.mp3")
        processed_music_file = str(test_output_dir / job_id / "music" / "processed.mp3")
        
        mocks['music'].return_value.select_music.return_value = {
            "music_selection": music_selection,
            "music_file": music_file
        }
        
        mocks['music'].return_value.process_music.return_value = {
            "processed_music_file": processed_music_file
        }
        
        # VisualComposerAgent
        visual_descriptions = "Montage of futuristic AI applications - smart cities, advanced robotics."
        image_prompts = "A futuristic smart city with interconnected systems, aerial view."
        visual_assets = [
            str(test_output_dir / job_id / "visuals" / "image_1.png"),
            str(test_output_dir / job_id / "visuals" / "image_2.png")
        ]
        
        mocks['visual'].return_value.extract_visual_descriptions.return_value = {
            "visual_descriptions": visual_descriptions
        }
        
        mocks['visual'].return_value.generate_visuals.return_value = {
            "image_prompts": image_prompts,
            "visual_assets": visual_assets
        }
        
        # VideoEditorAgent
        edit_plan = "Scene 1: Introduction (0:00 - 0:15)\n- Visuals: Start with image_1.png"
        edit_plan_path = str(test_output_dir / job_id / "videos" / "edit_plan.md")
        video_path = str(test_output_dir / job_id / "videos" / "final_video.mp4")
        video_metadata = {
            "resolution": "1920x1080",
            "duration": 60,
            "fps": 30
        }
        
        mocks['video_editor'].return_value.create_edit_plan.return_value = {
            "edit_plan": edit_plan,
            "edit_plan_path": edit_plan_path
        }
        
        mocks['video_editor'].return_value.assemble_video.return_value = {
            "video_path": video_path,
            "video_metadata": video_metadata
        }
        
        # PublishManagerAgent
        metadata = {
            "title": "The Future of AI",
            "description": "An exploration of how AI will transform our world.",
            "tags": ["AI", "future", "technology"],
            "category_id": "28",  # Science & Technology
            "privacy_status": "unlisted"
        }
        
        upload_result = {
            "video_id": "test_video_id",
            "video_url": "https://www.youtube.com/watch?v=test_video_id"
        }
        
        mocks['publish'].return_value.prepare_metadata.return_value = {
            "metadata": metadata
        }
        
        mocks['publish'].return_value.publish_to_youtube.return_value = {
            "upload_result": upload_result
        }
        
        # ReporterAgent
        report_path = str(test_output_dir / job_id / "reports" / "final_report.json")
        
        mocks['reporter'].return_value.generate_report.return_value = {
            "report_path": report_path
        }
        
        mocks['reporter'].return_value.send_notification.return_value = {
            "notification_sent": True
        }
        
        # Create and run the pipeline
        with patch('tools.token_manager.TokenManager'):
            pipeline = VideoPipeline()
            result = await pipeline.run(
                topic="The Future of AI",
                audience="technology enthusiasts",
                tone="informative",
                output_dir=str(test_output_dir)
            )
        
        # Verify the result
        assert result is not None
        assert "job_id" in result
        assert "status" in result
        assert "video_url" in result
        assert result["status"] == "completed"
        assert result["video_url"] == "https://www.youtube.com/watch?v=test_video_id"
        
        # Verify that all agents were called
        mocks['orchestrator'].return_value.initialize_job.assert_called_once()
        mocks['script_rewriter'].return_value.create_script.assert_called_once()
        mocks['orchestrator'].return_value.review_script.assert_called_once()
        mocks['voiceover'].return_value.extract_narration.assert_called_once()
        mocks['voiceover'].return_value.optimize_narration.assert_called_once()
        mocks['voiceover'].return_value.synthesize_audio.assert_called_once()
        mocks['music'].return_value.select_music.assert_called_once()
        mocks['music'].return_value.process_music.assert_called_once()
        mocks['visual'].return_value.extract_visual_descriptions.assert_called_once()
        mocks['visual'].return_value.generate_visuals.assert_called_once()
        mocks['video_editor'].return_value.create_edit_plan.assert_called_once()
        mocks['video_editor'].return_value.assemble_video.assert_called_once()
        mocks['orchestrator'].return_value.review_video.assert_called_once()
        mocks['publish'].return_value.prepare_metadata.assert_called_once()
        mocks['publish'].return_value.publish_to_youtube.assert_called_once()
        mocks['reporter'].return_value.generate_report.assert_called_once()
        mocks['reporter'].return_value.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_script_revision_needed(self, mock_all_agents, test_output_dir):
        """
        Test the pipeline when script revision is needed.
        
        This test simulates a scenario where the script is not approved on the first attempt
        and needs to be revised.
        """
        # Configure the mock agent responses
        mocks = mock_all_agents
        
        # VideoOrchestratorAgent
        job_id = "test_job_456"
        manifest = {
            "job_id": job_id,
            "topic": "The Future of AI",
            "status": "initialized",
            "steps": [
                {"name": "script_creation", "status": "pending"},
                {"name": "asset_generation", "status": "pending"},
                {"name": "video_assembly", "status": "pending"},
                {"name": "quality_control", "status": "pending"},
                {"name": "publishing", "status": "pending"}
            ]
        }
        manifest_path = str(test_output_dir / job_id / "manifest.json")
        
        mocks['orchestrator'].return_value.initialize_job.return_value = {
            "manifest": manifest,
            "thread_id": "test_thread_id",
            "manifest_path": manifest_path
        }
        
        # First script review fails, second succeeds
        mocks['orchestrator'].return_value.review_script.side_effect = [
            {
                "script_approved": False,
                "script_feedback": "The script lacks specific examples and a clear structure.",
                "manifest": manifest
            },
            {
                "script_approved": True,
                "script_feedback": "The revised script is well-structured and engaging.",
                "manifest": manifest
            }
        ]
        
        # ScriptRewriterAgent
        initial_script = """
# The Future of AI

## Introduction
AI is changing the world.
"""
        
        revised_script = """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence.

**VISUAL:** Show a montage of futuristic AI applications.

## Scene 2: Specific Examples
**NARRATION:** AI is transforming healthcare, transportation, and education.

**VISUAL:** Display specific case studies with data visualizations.
"""
        
        script_path = str(test_output_dir / job_id / "scripts" / "script.md")
        
        mocks['script_rewriter'].return_value.create_script.return_value = {
            "script": initial_script,
            "script_path": script_path
        }
        
        mocks['script_rewriter'].return_value.revise_script.return_value = {
            "script": revised_script,
            "script_path": script_path
        }
        
        # Configure other mocks similar to the success test
        # (simplified for brevity - in a real test, you'd configure all necessary mocks)
        mocks['voiceover'].return_value.extract_narration.return_value = {"narration": "Test narration"}
        mocks['voiceover'].return_value.optimize_narration.return_value = {"optimized_narration": "Test optimized narration"}
        mocks['voiceover'].return_value.synthesize_audio.return_value = {"audio_path": "/path/to/audio.mp3"}
        
        mocks['music'].return_value.select_music.return_value = {"music_selection": "Test music", "music_file": "/path/to/music.mp3"}
        mocks['music'].return_value.process_music.return_value = {"processed_music_file": "/path/to/processed_music.mp3"}
        
        mocks['visual'].return_value.extract_visual_descriptions.return_value = {"visual_descriptions": "Test descriptions"}
        mocks['visual'].return_value.generate_visuals.return_value = {"image_prompts": "Test prompts", "visual_assets": ["/path/to/image.png"]}
        
        mocks['video_editor'].return_value.create_edit_plan.return_value = {"edit_plan": "Test plan", "edit_plan_path": "/path/to/plan.md"}
        mocks['video_editor'].return_value.assemble_video.return_value = {
            "video_path": "/path/to/video.mp4",
            "video_metadata": {"resolution": "1920x1080", "duration": 60, "fps": 30}
        }
        
        mocks['orchestrator'].return_value.review_video.return_value = {
            "video_approved": True,
            "video_feedback": "The video meets all quality standards.",
            "manifest": manifest
        }
        
        mocks['publish'].return_value.prepare_metadata.return_value = {"metadata": {"title": "Test Title"}}
        mocks['publish'].return_value.publish_to_youtube.return_value = {
            "upload_result": {
                "video_id": "test_video_id",
                "video_url": "https://www.youtube.com/watch?v=test_video_id"
            }
        }
        
        mocks['reporter'].return_value.generate_report.return_value = {"report_path": "/path/to/report.json"}
        mocks['reporter'].return_value.send_notification.return_value = {"notification_sent": True}
        
        # Create and run the pipeline
        with patch('tools.token_manager.TokenManager'):
            pipeline = VideoPipeline()
            result = await pipeline.run(
                topic="The Future of AI",
                audience="technology enthusiasts",
                tone="informative",
                output_dir=str(test_output_dir)
            )
        
        # Verify the result
        assert result is not None
        assert "job_id" in result
        assert "status" in result
        assert result["status"] == "completed"
        
        # Verify that script revision was called
        mocks['script_rewriter'].return_value.create_script.assert_called_once()
        mocks['script_rewriter'].return_value.revise_script.assert_called_once()
        assert mocks['orchestrator'].return_value.review_script.call_count == 2

    @pytest.mark.asyncio
    async def test_pipeline_with_error_handling(self, mock_all_agents, test_output_dir):
        """
        Test the pipeline's error handling capabilities.
        
        This test simulates a scenario where an error occurs during the pipeline execution
        and verifies that the error is properly handled.
        """
        # Configure the mock agent responses
        mocks = mock_all_agents
        
        # VideoOrchestratorAgent
        job_id = "test_job_789"
        manifest = {
            "job_id": job_id,
            "topic": "The Future of AI",
            "status": "initialized",
            "steps": [
                {"name": "script_creation", "status": "pending"},
                {"name": "asset_generation", "status": "pending"},
                {"name": "video_assembly", "status": "pending"},
                {"name": "quality_control", "status": "pending"},
                {"name": "publishing", "status": "pending"}
            ]
        }
        manifest_path = str(test_output_dir / job_id / "manifest.json")
        
        mocks['orchestrator'].return_value.initialize_job.return_value = {
            "manifest": manifest,
            "thread_id": "test_thread_id",
            "manifest_path": manifest_path
        }
        
        # ScriptRewriterAgent
        script = """
# The Future of AI

## Scene 1: Introduction
**NARRATION:** Welcome to our exploration of the future of artificial intelligence.

**VISUAL:** Show a montage of futuristic AI applications.
"""
        script_path = str(test_output_dir / job_id / "scripts" / "script.md")
        
        mocks['script_rewriter'].return_value.create_script.return_value = {
            "script": script,
            "script_path": script_path
        }
        
        # Make the script review pass
        mocks['orchestrator'].return_value.review_script.return_value = {
            "script_approved": True,
            "script_feedback": "The script is well-structured and engaging.",
            "manifest": manifest
        }
        
        # But make the voiceover synthesis fail
        mocks['voiceover'].return_value.extract_narration.return_value = {
            "narration": "Welcome to our exploration of the future of artificial intelligence."
        }
        
        mocks['voiceover'].return_value.optimize_narration.return_value = {
            "optimized_narration": "Welcome to our exploration of the future of AI."
        }
        
        mocks['voiceover'].return_value.synthesize_audio.side_effect = Exception("ElevenLabs API error: Rate limit exceeded")
        
        # Create and run the pipeline
        with patch('tools.token_manager.TokenManager'):
            pipeline = VideoPipeline()
            result = await pipeline.run(
                topic="The Future of AI",
                audience="technology enthusiasts",
                tone="informative",
                output_dir=str(test_output_dir)
            )
        
        # Verify the result
        assert result is not None
        assert "job_id" in result
        assert "status" in result
        assert "error" in result
        assert result["status"] == "failed"
        assert "ElevenLabs API error" in result["error"]
        
        # Verify that the reporter was called to report the error
        mocks['reporter'].return_value.generate_report.assert_called_once()
        mocks['reporter'].return_value.send_notification.assert_called_once()
