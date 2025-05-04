"""
Tests for the Compliance QA Agent.

This module contains tests for the Compliance QA Agent and related functionality.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from ai_video_pipeline.agents.compliance_qa import (
    ComplianceQAAgent, 
    CompliancePolicy,
    CopyrightImageryPolicy,
    TTSConsentPolicy
)


@pytest.fixture
def sample_asset_manifest():
    """Create a sample asset manifest for testing."""
    return {
        "job_id": "test_job_123",
        "created_at": "2025-05-04T10:00:00Z",
        "updated_at": "2025-05-04T10:30:00Z",
        "assets": {
            "images": [
                {
                    "id": "image_section_1_abc1",
                    "path": "/path/to/image1.png",
                    "type": "image",
                    "section_id": "section_1",
                    "metadata": {
                        "prompt": "A beautiful landscape with mountains and a lake",
                        "dimensions": {
                            "width": 1920,
                            "height": 1080
                        }
                    }
                },
                {
                    "id": "image_section_2_abc2",
                    "path": "/path/to/image2.png",
                    "type": "image",
                    "section_id": "section_2",
                    "metadata": {
                        "prompt": "A cityscape at night with skyscrapers",
                        "dimensions": {
                            "width": 1920,
                            "height": 1080
                        }
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
                }
            ]
        }
    }


@pytest.fixture
def compliance_qa_agent():
    """Create a ComplianceQAAgent instance for testing."""
    return ComplianceQAAgent()


class TestCompliancePolicy:
    """Test suite for the CompliancePolicy base class."""

    def test_init(self):
        """Test the initialization of the CompliancePolicy."""
        # Create a subclass that implements check method
        class TestPolicy(CompliancePolicy):
            def check(self, asset, context):
                return {"status": "pass"}
        
        policy = TestPolicy("test_policy", "Test policy description")
        assert policy.name == "test_policy"
        assert policy.description == "Test policy description"

    def test_check_not_implemented(self):
        """Test that check method raises NotImplementedError."""
        policy = CompliancePolicy("test_policy", "Test policy description")
        with pytest.raises(NotImplementedError):
            policy.check({}, {})


class TestCopyrightImageryPolicy:
    """Test suite for the CopyrightImageryPolicy class."""

    def test_init(self):
        """Test the initialization of the CopyrightImageryPolicy."""
        policy = CopyrightImageryPolicy()
        assert policy.name == "copyright_imagery"
        assert "copyright issues" in policy.description
        assert isinstance(policy.copyright_terms, list)
        assert isinstance(policy.trademark_terms, list)

    def test_check_non_image_asset(self):
        """Test check method with non-image asset."""
        policy = CopyrightImageryPolicy()
        asset = {"type": "audio"}
        result = policy.check(asset, {})
        assert result["status"] == "pass"
        assert len(result["details"]) == 0

    def test_check_no_prompt(self):
        """Test check method with image asset but no prompt."""
        policy = CopyrightImageryPolicy()
        asset = {"type": "image", "metadata": {}}
        result = policy.check(asset, {})
        assert result["status"] == "warning"
        assert len(result["details"]) == 1
        assert "missing_data" in result["details"][0]["type"]

    def test_check_clean_prompt(self):
        """Test check method with clean prompt."""
        policy = CopyrightImageryPolicy()
        asset = {
            "type": "image", 
            "metadata": {"prompt": "A beautiful landscape with mountains"}
        }
        result = policy.check(asset, {})
        assert result["status"] == "pass"
        assert len(result["details"]) == 0

    def test_check_copyright_term(self):
        """Test check method with copyright term in prompt."""
        policy = CopyrightImageryPolicy()
        asset = {
            "type": "image", 
            "metadata": {"prompt": "A scene from Star Wars with lightsabers"}
        }
        result = policy.check(asset, {})
        assert result["status"] == "fail"
        assert len(result["details"]) == 1
        assert "copyright_term" in result["details"][0]["type"]
        assert "star wars" in result["details"][0]["terms"]

    def test_check_trademark_term(self):
        """Test check method with trademark term in prompt."""
        policy = CopyrightImageryPolicy()
        asset = {
            "type": "image", 
            "metadata": {"prompt": "Create a company logo with blue and green colors"}
        }
        result = policy.check(asset, {})
        assert result["status"] == "warning"
        assert len(result["details"]) == 1
        assert "trademark_term" in result["details"][0]["type"]
        assert "logo" in result["details"][0]["terms"]


class TestTTSConsentPolicy:
    """Test suite for the TTSConsentPolicy class."""

    def test_init(self):
        """Test the initialization of the TTSConsentPolicy."""
        policy = TTSConsentPolicy()
        assert policy.name == "tts_consent"
        assert "consent" in policy.description
        assert isinstance(policy.celebrity_voice_terms, list)

    def test_check_non_audio_asset(self):
        """Test check method with non-audio asset."""
        policy = TTSConsentPolicy()
        asset = {"type": "image"}
        result = policy.check(asset, {})
        assert result["status"] == "pass"
        assert len(result["details"]) == 0

    def test_check_non_tts_audio(self):
        """Test check method with non-TTS audio asset."""
        policy = TTSConsentPolicy()
        asset = {"type": "audio", "metadata": {"type": "music"}}
        result = policy.check(asset, {})
        assert result["status"] == "pass"
        assert len(result["details"]) == 0

    def test_check_no_voice_model(self):
        """Test check method with TTS asset but no voice model info."""
        policy = TTSConsentPolicy()
        asset = {
            "type": "audio", 
            "metadata": {"type": "voiceover", "text_content": "Test content"}
        }
        result = policy.check(asset, {})
        assert result["status"] == "warning"
        assert len(result["details"]) == 1
        assert "missing_data" in result["details"][0]["type"]

    def test_check_standard_voice(self):
        """Test check method with standard voice model."""
        policy = TTSConsentPolicy()
        asset = {
            "type": "audio", 
            "metadata": {
                "type": "voiceover", 
                "text_content": "Test content",
                "voice_model": "echo",
                "voice_provider": "elevenlabs"
            }
        }
        result = policy.check(asset, {})
        assert result["status"] == "pass"
        assert len(result["details"]) == 0

    def test_check_celebrity_voice_no_consent(self):
        """Test check method with celebrity voice term and no consent."""
        policy = TTSConsentPolicy()
        asset = {
            "type": "audio", 
            "metadata": {
                "type": "voiceover", 
                "text_content": "Test content",
                "voice_model": "custom_voice",
                "voice_provider": "elevenlabs",
                "voice_description": "Sounds like a famous actor"
            }
        }
        result = policy.check(asset, {})
        assert result["status"] == "fail"
        assert len(result["details"]) == 1
        assert "celebrity_voice" in result["details"][0]["type"]
        assert "sounds like" in result["details"][0]["terms"]

    def test_check_celebrity_voice_with_consent(self):
        """Test check method with celebrity voice term but with consent."""
        policy = TTSConsentPolicy()
        asset = {
            "type": "audio", 
            "metadata": {
                "type": "voiceover", 
                "text_content": "Test content",
                "voice_model": "custom_voice",
                "voice_provider": "elevenlabs",
                "voice_description": "Sounds like a famous actor",
                "consent_documentation": True
            }
        }
        result = policy.check(asset, {})
        assert result["status"] == "warning"
        assert len(result["details"]) == 1
        assert "celebrity_voice_with_consent" in result["details"][0]["type"]
        assert "sounds like" in result["details"][0]["terms"]


class TestComplianceQAAgent:
    """Test suite for the ComplianceQAAgent class."""

    def test_init(self, compliance_qa_agent):
        """Test the initialization of the ComplianceQAAgent."""
        assert compliance_qa_agent is not None
        assert len(compliance_qa_agent.policies) == 2
        assert isinstance(compliance_qa_agent.policies[0], CopyrightImageryPolicy)
        assert isinstance(compliance_qa_agent.policies[1], TTSConsentPolicy)

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_run_empty_manifest(self, mock_json_dump, mock_file_open, compliance_qa_agent):
        """Test run method with empty asset manifest."""
        # Setup test data
        asset_manifest = {"job_id": "test_job"}
        
        # Call the method
        result = compliance_qa_agent.run(asset_manifest)
        
        # Check the result
        assert result["status"] == "warning"
        assert len(result["warnings"]) == 1
        assert "No assets found" in result["warnings"][0]
        assert len(result["issues"]) == 0
        assert len(result["asset_checks"]) == 0

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_run(self, mock_json_dump, mock_file_open, compliance_qa_agent, 
                sample_asset_manifest, tmp_path):
        """Test run method with sample asset manifest."""
        # Create a temporary output path
        output_path = tmp_path / "compliance_report.json"
        
        # Call the method
        result = compliance_qa_agent.run(
            asset_manifest=sample_asset_manifest,
            output_path=output_path
        )
        
        # Check the result
        assert "status" in result
        assert "issues" in result
        assert "warnings" in result
        assert "asset_checks" in result
        
        # Check asset checks
        assert len(result["asset_checks"]) == 3  # 2 images + 1 audio
        
        # Verify each asset has policy checks
        for asset_id, asset_check in result["asset_checks"].items():
            assert "policy_checks" in asset_check
            assert "copyright_imagery" in asset_check["policy_checks"]
            
            # Audio assets should have TTS consent check
            if "audio" in asset_id:
                assert "tts_consent" in asset_check["policy_checks"]
        
        # Check if report was saved
        if output_path:
            mock_file_open.assert_called_once_with(output_path, "w")
            mock_json_dump.assert_called_once()

    @patch('ai_video_pipeline.agents.compliance_qa.CopyrightImageryPolicy.check')
    @patch('ai_video_pipeline.agents.compliance_qa.TTSConsentPolicy.check')
    def test_run_with_issues(self, mock_tts_check, mock_copyright_check, 
                           compliance_qa_agent, sample_asset_manifest):
        """Test run method with policy issues."""
        # Setup mocks to return issues
        mock_copyright_check.return_value = {
            "policy": "copyright_imagery",
            "status": "fail",
            "details": [{"type": "copyright_term", "message": "Found copyright term", "terms": ["disney"]}]
        }
        mock_tts_check.return_value = {
            "policy": "tts_consent",
            "status": "warning",
            "details": [{"type": "celebrity_voice_with_consent", "message": "Celebrity voice with consent", "terms": ["sounds like"]}]
        }
        
        # Call the method
        result = compliance_qa_agent.run(sample_asset_manifest)
        
        # Check the result
        assert result["status"] == "fail"  # Fail due to copyright issue
        assert len(result["issues"]) > 0
        assert len(result["warnings"]) > 0
        
        # Verify policy checks were called
        assert mock_copyright_check.call_count > 0
        assert mock_tts_check.call_count > 0
