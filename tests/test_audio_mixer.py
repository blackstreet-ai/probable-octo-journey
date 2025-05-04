"""
Test module for Audio-Mixer Agent.

This module contains tests for the Audio-Mixer Agent.
"""

import os
import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

from ai_video_pipeline.agents.audio_mixer import (
    AudioMixerAgent, 
    MixParams, 
    AudioMixResult
)


class TestAudioMixerAgent:
    """Test suite for the Audio-Mixer Agent."""

    @pytest.fixture
    def mock_run_command(self):
        """Mock for _run_ffmpeg_command method."""
        with patch.object(AudioMixerAgent, '_run_ffmpeg_command') as mock:
            # Default return value for successful command
            mock.return_value = (0, "success", "")
            yield mock

    @pytest.fixture
    def mock_audio_duration(self):
        """Mock for _get_audio_duration method."""
        with patch.object(AudioMixerAgent, '_get_audio_duration') as mock:
            mock.return_value = 120.0  # 2 minutes
            yield mock

    @pytest.fixture
    def mock_audio_loudness(self):
        """Mock for _get_audio_loudness method."""
        with patch.object(AudioMixerAgent, '_get_audio_loudness') as mock:
            mock.return_value = -14.0  # Target LUFS
            yield mock

    @pytest.fixture
    def agent(self):
        """Create an AudioMixerAgent instance for testing."""
        agent = AudioMixerAgent()
        # Force ffmpeg_available to True for testing
        agent.ffmpeg_available = True
        return agent

    @pytest.fixture
    def sample_files(self):
        """Create sample audio files for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            voice_file = os.path.join(tmp_dir, "voice.wav")
            music_file = os.path.join(tmp_dir, "music.wav")
            output_file = os.path.join(tmp_dir, "mixed.wav")
            
            # Create empty files
            for file_path in [voice_file, music_file]:
                with open(file_path, "w") as f:
                    f.write("# Test audio file")
            
            yield {
                "voice_file": voice_file,
                "music_file": music_file,
                "output_file": output_file,
                "temp_dir": tmp_dir
            }

    def test_init(self, agent):
        """Test initialization of the agent."""
        assert agent.name == "Audio-Mixer"
        assert agent.assets_dir.exists()
        assert "mixed" in str(agent.assets_dir)

    def test_mix_params(self, sample_files):
        """Test MixParams model."""
        # Test with default values
        params = MixParams(
            voice_file=sample_files["voice_file"],
            music_file=sample_files["music_file"]
        )
        assert params.voice_file == sample_files["voice_file"]
        assert params.music_file == sample_files["music_file"]
        assert params.output_file is None
        assert params.voice_gain_db == 0.0
        assert params.music_gain_db == -6.0
        assert params.duck_percent == 50.0
        assert params.target_lufs == -14.0

        # Test with custom values
        params = MixParams(
            voice_file=sample_files["voice_file"],
            music_file=sample_files["music_file"],
            output_file=sample_files["output_file"],
            voice_gain_db=3.0,
            music_gain_db=-10.0,
            duck_percent=75.0,
            target_lufs=-16.0,
            fade_in_seconds=2.0,
            fade_out_seconds=5.0
        )
        assert params.voice_gain_db == 3.0
        assert params.music_gain_db == -10.0
        assert params.duck_percent == 75.0
        assert params.target_lufs == -16.0
        assert params.fade_in_seconds == 2.0
        assert params.fade_out_seconds == 5.0

    def test_create_ducking_filter(self, agent, sample_files):
        """Test creating the ducking filter."""
        params = MixParams(
            voice_file=sample_files["voice_file"],
            music_file=sample_files["music_file"],
            duck_percent=50.0,
            duck_attack_ms=200,
            duck_release_ms=500,
            voice_gain_db=0.0,
            music_gain_db=-6.0
        )
        
        filter_str = agent._create_ducking_filter(params)
        
        # Check that the filter string contains key components
        assert "asplit=2" in filter_str
        assert "sidechaingate" in filter_str
        assert "amix=inputs=2" in filter_str
        assert "volume=0.0dB" in filter_str
        assert "volume=-6.0dB" in filter_str

    @pytest.mark.asyncio
    async def test_mix_audio(self, agent, sample_files, mock_run_command, 
                            mock_audio_duration, mock_audio_loudness):
        """Test mixing audio."""
        # Configure the mock to simulate successful command execution
        def side_effect_func(command):
            # Create the output file to simulate successful processing
            if "-i" in command and "mixed_temp.wav" in command[-1]:
                with open(command[-1], "w") as f:
                    f.write("# Test mixed audio")
            elif "-i" in command and "faded_temp.wav" in command[-1]:
                with open(command[-1], "w") as f:
                    f.write("# Test faded audio")
            elif "-i" in command and sample_files["output_file"] in command[-1]:
                with open(sample_files["output_file"], "w") as f:
                    f.write("# Test normalized audio")
            
            # For ffprobe commands, return JSON for duration
            if "ffprobe" in command[0] and "duration" in command[3]:
                return (0, '{"format":{"duration":"120.0"}}', "")
            
            # For loudnorm commands, return JSON for loudness
            if "loudnorm=print_format=json" in " ".join(command):
                return (0, "", '{"input_i": "-14.0", "output_i": "-14.0"}')
                
            return (0, "success", "")
        
        mock_run_command.side_effect = side_effect_func
        
        # Create mix parameters
        params = MixParams(
            voice_file=sample_files["voice_file"],
            music_file=sample_files["music_file"],
            output_file=sample_files["output_file"]
        )
        
        # Run the mix_audio method
        result = await agent.mix_audio(params)
        
        # Check the result
        assert isinstance(result, AudioMixResult)
        assert result.output_file == sample_files["output_file"]
        assert result.duration_seconds == 120.0
        assert result.voice_file == sample_files["voice_file"]
        assert result.music_file == sample_files["music_file"]
        assert result.params == params
        assert result.loudness_lufs == -14.0
        
        # Verify that the ffmpeg commands were called
        assert mock_run_command.call_count >= 3  # At least mix, fade, and normalize

    def test_get_audio_duration(self, agent, mock_run_command):
        """Test getting audio duration."""
        # Configure the mock to return a valid JSON response
        mock_run_command.return_value = (
            0, 
            '{"format":{"duration":"180.5"}}', 
            ""
        )
        
        duration = agent._get_audio_duration("test.wav")
        
        assert duration == 180.5
        mock_run_command.assert_called_once()
        assert "ffprobe" in mock_run_command.call_args[0][0][0]

    def test_get_audio_loudness(self, agent, mock_run_command):
        """Test getting audio loudness."""
        # Configure the mock to return a valid loudnorm JSON response
        mock_run_command.return_value = (
            0, 
            "", 
            'some log output\n{"input_i": "-18.2", "output_i": "-14.0"}\nmore logs'
        )
        
        loudness = agent._get_audio_loudness("test.wav")
        
        assert loudness == -18.2
        mock_run_command.assert_called_once()
        assert "loudnorm=print_format=json" in mock_run_command.call_args[0][0][4]

    def test_normalize_loudness(self, agent, mock_run_command):
        """Test normalizing loudness."""
        result = agent._normalize_loudness("input.wav", "output.wav", -14.0)
        
        assert result is True
        mock_run_command.assert_called_once()
        assert "loudnorm=I=-14.0" in mock_run_command.call_args[0][0][5]

    def test_apply_fades(self, agent, mock_run_command, mock_audio_duration):
        """Test applying fades."""
        result = agent._apply_fades("input.wav", "output.wav", 2.0, 3.0)
        
        assert result is True
        assert mock_run_command.call_count == 1
        assert "afade=t=in:st=0:d=2.0" in mock_run_command.call_args[0][0][5]
        assert "afade=t=out:st=117.0:d=3.0" in mock_run_command.call_args[0][0][5]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
