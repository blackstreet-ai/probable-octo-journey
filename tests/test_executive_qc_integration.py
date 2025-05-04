"""
Tests for the Executive Agent integration with Quality Control & Compliance components.

This module contains tests for the Executive Agent's integration with the
Motion QC, Compliance QA, and Thumbnail Creator agents.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path

from ai_video_pipeline.agents.executive import ExecutiveAgent


@pytest.fixture
def executive_agent():
    """Create an ExecutiveAgent instance for testing."""
    return ExecutiveAgent()


@pytest.fixture
def mock_asset_manifest():
    """Create a mock asset manifest for testing."""
    return {
        "job_id": "test_job_123",
        "created_at": "2025-05-04T10:00:00Z",
        "updated_at": "2025-05-04T10:30:00Z",
        "script": {
            "title": "Test Video Title",
            "sections": [
                {
                    "id": "section_1",
                    "heading": "Introduction to Testing",
                    "text": "This is the first section of the test script."
                }
            ]
        },
        "assets": {
            "images": [
                {
                    "id": "image_hero_abc1",
                    "path": "/path/to/hero_image.png",
                    "type": "image",
                    "section_id": "section_1",
                    "metadata": {
                        "prompt": "A hero image for the video",
                        "type": "hero",
                        "dimensions": {
                            "width": 1920,
                            "height": 1080
                        }
                    }
                }
            ],
            "videos": [
                {
                    "id": "video_section_1_def1",
                    "path": "/path/to/video.mp4",
                    "type": "video",
                    "section_id": "section_1",
                    "metadata": {
                        "prompt": "A video for section 1",
                        "duration_seconds": 10.0
                    }
                }
            ],
            "audio": [
                {
                    "id": "audio_voiceover_ghi1",
                    "path": "/path/to/voiceover.wav",
                    "type": "audio",
                    "metadata": {
                        "type": "voiceover",
                        "duration_seconds": 15.0,
                        "text_content": "This is the voiceover for the test video.",
                        "voice_model": "echo",
                        "voice_provider": "elevenlabs"
                    }
                },
                {
                    "id": "audio_music_jkl1",
                    "path": "/path/to/music.mp3",
                    "type": "audio",
                    "metadata": {
                        "type": "music",
                        "duration_seconds": 30.0,
                        "title": "Background Music",
                        "artist": "Test Artist"
                    }
                }
            ]
        }
    }


class TestExecutiveAgentQCIntegration:
    """Test suite for the Executive Agent's integration with QC components."""

    @pytest.mark.asyncio
    @patch('ai_video_pipeline.agents.executive.ScriptwriterAgent')
    @patch('ai_video_pipeline.agents.executive.PromptDesignerAgent')
    @patch('ai_video_pipeline.agents.executive.ImageGenAgent')
    @patch('ai_video_pipeline.agents.executive.VideoGenAgent')
    @patch('ai_video_pipeline.agents.executive.VoiceSynthesisAgent')
    @patch('ai_video_pipeline.agents.executive.MusicSelectorAgent')
    @patch('ai_video_pipeline.agents.executive.AudioMixerAgent')
    @patch('ai_video_pipeline.agents.executive.TimelineBuilderAgent')
    @patch('ai_video_pipeline.agents.executive.MotionQCAgent')
    @patch('ai_video_pipeline.agents.executive.ComplianceQAAgent')
    @patch('ai_video_pipeline.agents.executive.ThumbnailCreatorAgent')
    @patch('ai_video_pipeline.agents.executive.AssetLibrarian')
    async def test_run_with_successful_qc(
        self, mock_asset_librarian, mock_thumbnail_creator, mock_compliance_qa, 
        mock_motion_qc, mock_timeline_builder, mock_audio_mixer, mock_music_selector, 
        mock_voice_synthesis, mock_video_gen, mock_image_gen, mock_prompt_designer, 
        mock_scriptwriter, executive_agent, mock_asset_manifest
    ):
        """Test the run method with successful QC checks."""
        # Setup mocks
        mock_asset_librarian_instance = MagicMock()
        mock_asset_librarian_instance.get_manifest.return_value = mock_asset_manifest
        mock_asset_librarian.return_value = mock_asset_librarian_instance
        
        # Mock agent results
        mock_scriptwriter_instance = MagicMock()
        mock_scriptwriter_instance.run.return_value = {"script": {"title": "Test"}}
        mock_scriptwriter.return_value = mock_scriptwriter_instance
        
        mock_prompt_designer_instance = MagicMock()
        mock_prompt_designer_instance.run.return_value = {"prompts": []}
        mock_prompt_designer.return_value = mock_prompt_designer_instance
        
        mock_image_gen_instance = MagicMock()
        mock_image_gen_instance.run.return_value = {"images": []}
        mock_image_gen.return_value = mock_image_gen_instance
        
        mock_video_gen_instance = MagicMock()
        mock_video_gen_instance.run.return_value = {"videos": []}
        mock_video_gen.return_value = mock_video_gen_instance
        
        mock_voice_synthesis_instance = MagicMock()
        mock_voice_synthesis_instance.run.return_value = {"audio_path": "/path/to/voice.wav"}
        mock_voice_synthesis.return_value = mock_voice_synthesis_instance
        
        mock_music_selector_instance = MagicMock()
        mock_music_selector_instance.run.return_value = {"music_path": "/path/to/music.mp3"}
        mock_music_selector.return_value = mock_music_selector_instance
        
        mock_audio_mixer_instance = MagicMock()
        mock_audio_mixer_instance.run.return_value = {"mixed_audio_path": "/path/to/mixed.wav"}
        mock_audio_mixer.return_value = mock_audio_mixer_instance
        
        mock_timeline_builder_instance = MagicMock()
        mock_timeline_builder_instance.run.return_value = {"fcpxml_path": "/path/to/timeline.fcpxml"}
        mock_timeline_builder.return_value = mock_timeline_builder_instance
        
        # Setup QC agent mocks with successful results
        mock_motion_qc_instance = MagicMock()
        mock_motion_qc_instance.run.return_value = {
            "status": "pass",
            "message": "All video quality checks passed",
            "checks": {
                "duration": {"status": "pass"},
                "aspect_ratio": {"status": "pass"},
                "duplicate_frames": {"status": "pass"}
            }
        }
        mock_motion_qc.return_value = mock_motion_qc_instance
        
        mock_compliance_qa_instance = MagicMock()
        mock_compliance_qa_instance.run.return_value = {
            "status": "pass",
            "message": "All compliance checks passed",
            "issues": [],
            "warnings": [],
            "asset_checks": {}
        }
        mock_compliance_qa.return_value = mock_compliance_qa_instance
        
        mock_thumbnail_creator_instance = MagicMock()
        mock_thumbnail_creator_instance.run.return_value = {
            "status": "success",
            "thumbnail_path": "/path/to/thumbnail.png",
            "hero_image_path": "/path/to/hero_image.png",
            "headline": "Test Video Title"
        }
        mock_thumbnail_creator.return_value = mock_thumbnail_creator_instance
        
        # Run the executive agent
        result = await executive_agent.run("Create a test video")
        
        # Verify results
        assert result["status"] == "completed"
        assert "Workflow completed successfully" in result["message"]
        assert "motion_qc" in result["stages"]
        assert "compliance_qa" in result["stages"]
        assert "thumbnail" in result["stages"]
        assert "critical_issues" not in result
        
        # Verify QC agents were called
        mock_motion_qc_instance.run.assert_called_once_with(mock_asset_manifest)
        mock_compliance_qa_instance.run.assert_called_once_with(mock_asset_manifest)
        mock_thumbnail_creator_instance.run.assert_called_once_with(mock_asset_manifest)

    @pytest.mark.asyncio
    @patch('ai_video_pipeline.agents.executive.ScriptwriterAgent')
    @patch('ai_video_pipeline.agents.executive.PromptDesignerAgent')
    @patch('ai_video_pipeline.agents.executive.ImageGenAgent')
    @patch('ai_video_pipeline.agents.executive.VideoGenAgent')
    @patch('ai_video_pipeline.agents.executive.VoiceSynthesisAgent')
    @patch('ai_video_pipeline.agents.executive.MusicSelectorAgent')
    @patch('ai_video_pipeline.agents.executive.AudioMixerAgent')
    @patch('ai_video_pipeline.agents.executive.TimelineBuilderAgent')
    @patch('ai_video_pipeline.agents.executive.MotionQCAgent')
    @patch('ai_video_pipeline.agents.executive.ComplianceQAAgent')
    @patch('ai_video_pipeline.agents.executive.ThumbnailCreatorAgent')
    @patch('ai_video_pipeline.agents.executive.AssetLibrarian')
    async def test_run_with_qc_issues(
        self, mock_asset_librarian, mock_thumbnail_creator, mock_compliance_qa, 
        mock_motion_qc, mock_timeline_builder, mock_audio_mixer, mock_music_selector, 
        mock_voice_synthesis, mock_video_gen, mock_image_gen, mock_prompt_designer, 
        mock_scriptwriter, executive_agent, mock_asset_manifest
    ):
        """Test the run method with QC issues."""
        # Setup mocks
        mock_asset_librarian_instance = MagicMock()
        mock_asset_librarian_instance.get_manifest.return_value = mock_asset_manifest
        mock_asset_librarian.return_value = mock_asset_librarian_instance
        
        # Mock agent results (same as successful test for non-QC agents)
        mock_scriptwriter_instance = MagicMock()
        mock_scriptwriter_instance.run.return_value = {"script": {"title": "Test"}}
        mock_scriptwriter.return_value = mock_scriptwriter_instance
        
        mock_prompt_designer_instance = MagicMock()
        mock_prompt_designer_instance.run.return_value = {"prompts": []}
        mock_prompt_designer.return_value = mock_prompt_designer_instance
        
        mock_image_gen_instance = MagicMock()
        mock_image_gen_instance.run.return_value = {"images": []}
        mock_image_gen.return_value = mock_image_gen_instance
        
        mock_video_gen_instance = MagicMock()
        mock_video_gen_instance.run.return_value = {"videos": []}
        mock_video_gen.return_value = mock_video_gen_instance
        
        mock_voice_synthesis_instance = MagicMock()
        mock_voice_synthesis_instance.run.return_value = {"audio_path": "/path/to/voice.wav"}
        mock_voice_synthesis.return_value = mock_voice_synthesis_instance
        
        mock_music_selector_instance = MagicMock()
        mock_music_selector_instance.run.return_value = {"music_path": "/path/to/music.mp3"}
        mock_music_selector.return_value = mock_music_selector_instance
        
        mock_audio_mixer_instance = MagicMock()
        mock_audio_mixer_instance.run.return_value = {"mixed_audio_path": "/path/to/mixed.wav"}
        mock_audio_mixer.return_value = mock_audio_mixer_instance
        
        mock_timeline_builder_instance = MagicMock()
        mock_timeline_builder_instance.run.return_value = {"fcpxml_path": "/path/to/timeline.fcpxml"}
        mock_timeline_builder.return_value = mock_timeline_builder_instance
        
        # Setup QC agent mocks with issues
        mock_motion_qc_instance = MagicMock()
        mock_motion_qc_instance.run.return_value = {
            "status": "fail",
            "message": "Video quality issues detected",
            "checks": {
                "duration": {"status": "fail", "message": "Video too short"},
                "aspect_ratio": {"status": "pass"},
                "duplicate_frames": {"status": "pass"}
            }
        }
        mock_motion_qc.return_value = mock_motion_qc_instance
        
        mock_compliance_qa_instance = MagicMock()
        mock_compliance_qa_instance.run.return_value = {
            "status": "fail",
            "message": "Compliance issues detected",
            "issues": [
                {"message": "Copyright terms found in image prompt"}
            ],
            "warnings": [],
            "asset_checks": {}
        }
        mock_compliance_qa.return_value = mock_compliance_qa_instance
        
        mock_thumbnail_creator_instance = MagicMock()
        mock_thumbnail_creator_instance.run.return_value = {
            "status": "success",
            "thumbnail_path": "/path/to/thumbnail.png",
            "hero_image_path": "/path/to/hero_image.png",
            "headline": "Test Video Title"
        }
        mock_thumbnail_creator.return_value = mock_thumbnail_creator_instance
        
        # Run the executive agent
        result = await executive_agent.run("Create a test video")
        
        # Verify results
        assert result["status"] == "needs_review"
        assert "critical issues that need review" in result["message"]
        assert "critical_issues" in result
        assert len(result["critical_issues"]) == 2
        assert any("Motion QC failed" in issue for issue in result["critical_issues"])
        assert any("Compliance QA failed" in issue for issue in result["critical_issues"])
        
        # Verify QC agents were called
        mock_motion_qc_instance.run.assert_called_once_with(mock_asset_manifest)
        mock_compliance_qa_instance.run.assert_called_once_with(mock_asset_manifest)
        mock_thumbnail_creator_instance.run.assert_called_once_with(mock_asset_manifest)

    @pytest.mark.asyncio
    @patch('ai_video_pipeline.agents.executive.ScriptwriterAgent')
    @patch('ai_video_pipeline.agents.executive.PromptDesignerAgent')
    @patch('ai_video_pipeline.agents.executive.ImageGenAgent')
    @patch('ai_video_pipeline.agents.executive.VideoGenAgent')
    @patch('ai_video_pipeline.agents.executive.VoiceSynthesisAgent')
    @patch('ai_video_pipeline.agents.executive.MusicSelectorAgent')
    @patch('ai_video_pipeline.agents.executive.AudioMixerAgent')
    @patch('ai_video_pipeline.agents.executive.TimelineBuilderAgent')
    @patch('ai_video_pipeline.agents.executive.MotionQCAgent')
    @patch('ai_video_pipeline.agents.executive.ComplianceQAAgent')
    @patch('ai_video_pipeline.agents.executive.ThumbnailCreatorAgent')
    @patch('ai_video_pipeline.agents.executive.AssetLibrarian')
    async def test_run_with_thumbnail_failure(
        self, mock_asset_librarian, mock_thumbnail_creator, mock_compliance_qa, 
        mock_motion_qc, mock_timeline_builder, mock_audio_mixer, mock_music_selector, 
        mock_voice_synthesis, mock_video_gen, mock_image_gen, mock_prompt_designer, 
        mock_scriptwriter, executive_agent, mock_asset_manifest
    ):
        """Test the run method with thumbnail creation failure."""
        # Setup mocks
        mock_asset_librarian_instance = MagicMock()
        mock_asset_librarian_instance.get_manifest.return_value = mock_asset_manifest
        mock_asset_librarian.return_value = mock_asset_librarian_instance
        
        # Mock agent results (same as successful test for non-QC agents)
        mock_scriptwriter_instance = MagicMock()
        mock_scriptwriter_instance.run.return_value = {"script": {"title": "Test"}}
        mock_scriptwriter.return_value = mock_scriptwriter_instance
        
        mock_prompt_designer_instance = MagicMock()
        mock_prompt_designer_instance.run.return_value = {"prompts": []}
        mock_prompt_designer.return_value = mock_prompt_designer_instance
        
        mock_image_gen_instance = MagicMock()
        mock_image_gen_instance.run.return_value = {"images": []}
        mock_image_gen.return_value = mock_image_gen_instance
        
        mock_video_gen_instance = MagicMock()
        mock_video_gen_instance.run.return_value = {"videos": []}
        mock_video_gen.return_value = mock_video_gen_instance
        
        mock_voice_synthesis_instance = MagicMock()
        mock_voice_synthesis_instance.run.return_value = {"audio_path": "/path/to/voice.wav"}
        mock_voice_synthesis.return_value = mock_voice_synthesis_instance
        
        mock_music_selector_instance = MagicMock()
        mock_music_selector_instance.run.return_value = {"music_path": "/path/to/music.mp3"}
        mock_music_selector.return_value = mock_music_selector_instance
        
        mock_audio_mixer_instance = MagicMock()
        mock_audio_mixer_instance.run.return_value = {"mixed_audio_path": "/path/to/mixed.wav"}
        mock_audio_mixer.return_value = mock_audio_mixer_instance
        
        mock_timeline_builder_instance = MagicMock()
        mock_timeline_builder_instance.run.return_value = {"fcpxml_path": "/path/to/timeline.fcpxml"}
        mock_timeline_builder.return_value = mock_timeline_builder_instance
        
        # Setup QC agent mocks with successful results for Motion QC and Compliance QA
        mock_motion_qc_instance = MagicMock()
        mock_motion_qc_instance.run.return_value = {
            "status": "pass",
            "message": "All video quality checks passed",
            "checks": {
                "duration": {"status": "pass"},
                "aspect_ratio": {"status": "pass"},
                "duplicate_frames": {"status": "pass"}
            }
        }
        mock_motion_qc.return_value = mock_motion_qc_instance
        
        mock_compliance_qa_instance = MagicMock()
        mock_compliance_qa_instance.run.return_value = {
            "status": "pass",
            "message": "All compliance checks passed",
            "issues": [],
            "warnings": [],
            "asset_checks": {}
        }
        mock_compliance_qa.return_value = mock_compliance_qa_instance
        
        # Setup Thumbnail Creator with failure
        mock_thumbnail_creator_instance = MagicMock()
        mock_thumbnail_creator_instance.run.return_value = {
            "status": "error",
            "message": "No suitable hero image found for thumbnail creation"
        }
        mock_thumbnail_creator.return_value = mock_thumbnail_creator_instance
        
        # Run the executive agent
        result = await executive_agent.run("Create a test video")
        
        # Verify results - workflow should still complete since thumbnail failure is not critical
        assert result["status"] == "completed"
        assert "Workflow completed successfully" in result["message"]
        assert "critical_issues" not in result
        assert result["stages"]["thumbnail"]["status"] == "error"
        
        # Verify QC agents were called
        mock_motion_qc_instance.run.assert_called_once_with(mock_asset_manifest)
        mock_compliance_qa_instance.run.assert_called_once_with(mock_asset_manifest)
        mock_thumbnail_creator_instance.run.assert_called_once_with(mock_asset_manifest)
