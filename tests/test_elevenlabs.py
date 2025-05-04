"""
Test module for ElevenLabs API integration.

This module contains tests for the ElevenLabs API wrapper and Voice-Synthesis Agent.
"""

import os
import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

from ai_video_pipeline.tools.elevenlabs import ElevenLabsAPI, VoiceSettings
from ai_video_pipeline.agents.voice_synthesis import VoiceSynthesisAgent, VoiceParams
from ai_video_pipeline.config.settings import settings


class TestElevenLabsAPI:
    """Test suite for the ElevenLabs API wrapper."""

    @pytest.fixture
    def mock_response(self):
        """Mock response for requests."""
        mock = MagicMock()
        mock.status_code = 200
        mock.raise_for_status.return_value = None
        return mock

    @pytest.fixture
    def api(self):
        """Create an ElevenLabsAPI instance for testing."""
        return ElevenLabsAPI(api_key="test_key")

    def test_init(self, api):
        """Test initialization of the API wrapper."""
        assert api.api_key == "test_key"
        assert api.base_url == "https://api.elevenlabs.io/v1"
        assert "xi-api-key" in api.headers
        assert api.headers["xi-api-key"] == "test_key"

    def test_voice_settings(self):
        """Test VoiceSettings class."""
        settings = VoiceSettings(
            stability=0.8,
            similarity_boost=0.7,
            style=0.5,
            use_speaker_boost=False
        )
        settings_dict = settings.to_dict()
        assert settings_dict["stability"] == 0.8
        assert settings_dict["similarity_boost"] == 0.7
        assert settings_dict["style"] == 0.5
        assert settings_dict["use_speaker_boost"] is False

    @patch("ai_video_pipeline.tools.elevenlabs.requests.get")
    def test_list_voices(self, mock_get, api, mock_response):
        """Test listing voices."""
        mock_response.json.return_value = {
            "voices": [
                {
                    "voice_id": "test_voice_id",
                    "name": "Test Voice",
                    "preview_url": "https://example.com/preview.mp3"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        voices = api.list_voices()
        
        mock_get.assert_called_once_with(
            f"{api.base_url}/voices",
            headers=api.headers
        )
        assert voices["voices"][0]["voice_id"] == "test_voice_id"

    @patch("ai_video_pipeline.tools.elevenlabs.requests.get")
    def test_get_voice_by_name(self, mock_get, api, mock_response):
        """Test getting a voice by name."""
        mock_response.json.return_value = {
            "voices": [
                {
                    "voice_id": "voice1",
                    "name": "Voice One",
                    "preview_url": "https://example.com/preview1.mp3"
                },
                {
                    "voice_id": "voice2",
                    "name": "Voice Two",
                    "preview_url": "https://example.com/preview2.mp3"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        voice = api.get_voice_by_name("Voice Two")
        
        assert voice["voice_id"] == "voice2"
        assert voice["name"] == "Voice Two"

    @patch("ai_video_pipeline.tools.elevenlabs.requests.post")
    def test_synthesize_speech(self, mock_post, api, mock_response):
        """Test speech synthesis."""
        mock_response.content = b"audio content"
        mock_post.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test_output.mp3"
            result = api.synthesize_speech(
                text="Hello, world!",
                voice_id="test_voice",
                output_path=output_path
            )
            
            assert result == output_path
            assert output_path.exists()
            
            with open(output_path, "rb") as f:
                content = f.read()
                assert content == b"audio content"
            
            # Check that the API was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == f"{api.base_url}/text-to-speech/test_voice"
            assert "voice_settings" in call_args[1]["json"]


class TestVoiceSynthesisAgent:
    """Test suite for the Voice-Synthesis Agent."""
    
    @pytest.fixture
    def mock_elevenlabs_api(self):
        """Mock ElevenLabsAPI."""
        mock = MagicMock()
        mock.synthesize_speech_chunks.return_value = [
            {
                "section_id": "section1",
                "text": "Hello, world!",
                "file_path": "/path/to/audio1.mp3"
            },
            {
                "section_id": "section2",
                "text": "This is a test.",
                "file_path": "/path/to/audio2.mp3"
            }
        ]
        return mock
    
    @pytest.fixture
    def agent(self, mock_elevenlabs_api):
        """Create a VoiceSynthesisAgent with mocked ElevenLabsAPI."""
        agent = VoiceSynthesisAgent()
        agent.elevenlabs_api = mock_elevenlabs_api
        return agent
    
    @pytest.mark.asyncio
    async def test_synthesize_voice(self, agent, mock_elevenlabs_api):
        """Test voice synthesis."""
        script_sections = [
            {
                "section_id": "section1",
                "content": "Hello, world!"
            },
            {
                "section_id": "section2",
                "content": "This is a test."
            }
        ]
        
        voice_params = VoiceParams(
            voice_id="test_voice",
            stability=0.8,
            similarity_boost=0.7
        )
        
        result = await agent.synthesize_voice(
            script_sections=script_sections,
            voice_params=voice_params
        )
        
        # Check that the API was called correctly
        mock_elevenlabs_api.synthesize_speech_chunks.assert_called_once()
        call_args = mock_elevenlabs_api.synthesize_speech_chunks.call_args
        assert call_args[1]["text_chunks"] == script_sections
        assert call_args[1]["voice_id"] == "test_voice"
        
        # Check the result
        assert len(result.clips) == 2
        assert result.clips[0].section_id == "section1"
        assert result.clips[0].text == "Hello, world!"
        assert result.clips[0].file_path == "/path/to/audio1.mp3"
        assert result.voice_params == voice_params


if __name__ == "__main__":
    pytest.main(["-v", __file__])
