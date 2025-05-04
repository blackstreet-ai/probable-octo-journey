"""
Test module for Music-Selector Agent.

This module contains tests for the Music-Selector Agent.
"""

import os
import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

from ai_video_pipeline.agents.music_selector import (
    MusicSelectorAgent, 
    MusicParams, 
    MusicTrack,
    MusicSelectionResult
)


class TestMusicSelectorAgent:
    """Test suite for the Music-Selector Agent."""

    @pytest.fixture
    def agent(self):
        """Create a MusicSelectorAgent instance for testing."""
        return MusicSelectorAgent()

    def test_init(self, agent):
        """Test initialization of the agent."""
        assert agent.name == "Music-Selector"
        assert agent.assets_dir.exists()
        assert "music" in str(agent.assets_dir)

    def test_music_params(self):
        """Test MusicParams model."""
        # Test with default values
        params = MusicParams()
        assert params.mood == "neutral"
        assert params.tempo is None
        assert params.duration is None
        assert params.genre is None
        assert params.keywords == []

        # Test with custom values
        params = MusicParams(
            mood="happy",
            tempo=120,
            duration=60.0,
            genre="pop",
            keywords=["upbeat", "energetic"]
        )
        assert params.mood == "happy"
        assert params.tempo == 120
        assert params.duration == 60.0
        assert params.genre == "pop"
        assert params.keywords == ["upbeat", "energetic"]

    def test_music_track(self):
        """Test MusicTrack model."""
        track = MusicTrack(
            track_id="test_track",
            title="Test Track",
            artist="Test Artist",
            file_path="/path/to/track.mp3",
            duration_seconds=120.0,
            tempo=100,
            genre="electronic",
            tags=["test", "electronic"],
            license="CC0",
            source_url="https://example.com/track"
        )
        assert track.track_id == "test_track"
        assert track.title == "Test Track"
        assert track.artist == "Test Artist"
        assert track.file_path == "/path/to/track.mp3"
        assert track.duration_seconds == 120.0
        assert track.tempo == 100
        assert track.genre == "electronic"
        assert track.tags == ["test", "electronic"]
        assert track.license == "CC0"
        # HttpUrl is a Pydantic type that validates URLs, so we need to convert to string for comparison
        assert str(track.source_url) == "https://example.com/track"

    def test_filter_tracks(self, agent):
        """Test filtering tracks based on parameters."""
        # Test filtering by genre
        params = MusicParams(genre="ambient")
        filtered = agent._filter_tracks(params)
        assert len(filtered) > 0
        assert all("ambient" in track["genre"].lower() for track in filtered)

        # Test filtering by mood
        params = MusicParams(mood="happy")
        filtered = agent._filter_tracks(params)
        assert len(filtered) > 0
        assert any(any("happy" in tag.lower() for tag in track["tags"]) for track in filtered)

        # Test filtering by tempo
        params = MusicParams(tempo=120)
        filtered = agent._filter_tracks(params)
        assert len(filtered) > 0
        assert all(100 <= track["tempo"] <= 140 for track in filtered)

        # Test filtering by duration
        params = MusicParams(duration=200.0)
        filtered = agent._filter_tracks(params)
        assert len(filtered) > 0
        assert all(track["duration_seconds"] >= 200.0 for track in filtered)

        # Test filtering by keywords
        params = MusicParams(keywords=["epic"])
        filtered = agent._filter_tracks(params)
        assert len(filtered) > 0
        assert any(any("epic" in tag.lower() for tag in track["tags"]) for track in filtered)

        # Test combined filtering
        params = MusicParams(
            genre="orchestral",
            mood="dramatic",
            keywords=["epic"]
        )
        filtered = agent._filter_tracks(params)
        assert len(filtered) > 0
        assert all("orchestral" in track["genre"].lower() for track in filtered)

    def test_create_placeholder_track(self, agent):
        """Test creating a placeholder track."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test_track.mp3"
            track_data = {
                "title": "Test Track",
                "artist": "Test Artist",
                "genre": "Test Genre",
                "duration_seconds": 120.0,
                "license": "CC0",
                "source_url": "https://example.com"
            }
            
            result_path = agent._create_placeholder_track(track_data, output_path)
            
            assert result_path == output_path
            assert output_path.exists()
            
            with open(output_path, "r") as f:
                content = f.read()
                assert "Test Track" in content
                assert "Test Artist" in content
                assert "Test Genre" in content
                assert "120.0 seconds" in content
                assert "CC0" in content
                assert "https://example.com" in content

    @pytest.mark.asyncio
    async def test_select_music(self, agent):
        """Test selecting music."""
        # Test with default parameters
        result = await agent.select_music()
        assert isinstance(result, MusicSelectionResult)
        assert isinstance(result.track, MusicTrack)
        assert isinstance(result.params, MusicParams)
        assert result.track.file_path.endswith(".mp3")
        assert Path(result.track.file_path).exists()
        
        # Test with specific parameters
        params = MusicParams(
            mood="dramatic",
            genre="orchestral",
            keywords=["epic"]
        )
        result = await agent.select_music(params)
        assert result.params == params
        assert "orchestral" in result.track.genre.lower()
        assert any("epic" in tag.lower() for tag in result.track.tags)
        assert Path(result.track.file_path).exists()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
