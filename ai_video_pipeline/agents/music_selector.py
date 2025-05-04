"""
Music-Selector Agent module.

This module implements the Music-Selector Agent, which is responsible for
fetching royalty-free music tracks for use in video productions.
"""

from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import os
import time
import logging
import random
import requests
from pydantic import BaseModel, Field, HttpUrl

from ai_video_pipeline.config.settings import settings

# Set up logging
logger = logging.getLogger(__name__)

# Mock Agent class for testing without OpenAI Agents SDK
class Agent:
    def __init__(self, name, instructions=None, handoffs=None):
        self.name = name
        self.instructions = instructions
        self.handoffs = handoffs or []


class MusicParams(BaseModel):
    """
    Parameters for music selection.
    
    Args:
        mood: Mood of the music (e.g., 'happy', 'sad', 'energetic')
        tempo: Tempo of the music in BPM (e.g., 80, 120)
        duration: Desired duration in seconds
        genre: Genre of the music (e.g., 'electronic', 'acoustic')
        keywords: List of keywords to describe the music
    """
    mood: str = "neutral"
    tempo: Optional[int] = None
    duration: Optional[float] = None
    genre: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)


class MusicTrack(BaseModel):
    """
    A music track.
    
    Args:
        track_id: ID of the track
        title: Title of the track
        artist: Artist of the track
        file_path: Path to the music file
        duration_seconds: Duration of the track in seconds
        tempo: Tempo of the track in BPM
        genre: Genre of the track
        tags: List of tags describing the track
        license: License information for the track
        source_url: URL where the track was sourced from
    """
    track_id: str
    title: str
    artist: str
    file_path: str
    duration_seconds: float
    tempo: Optional[int] = None
    genre: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    license: str = "CC0"
    source_url: Optional[HttpUrl] = None


class MusicSelectionResult(BaseModel):
    """
    Result of the music selection process.
    
    Args:
        track: Selected music track
        params: Parameters used for selection
    """
    track: MusicTrack
    params: MusicParams


class MusicSelectorAgent:
    """
    Music-Selector Agent that fetches royalty-free music tracks for use in
    video productions.
    """
    
    # Default music sources
    MUSIC_SOURCES = {
        "freepd": "https://freepd.com",
        "freesound": "https://freesound.org",
        "pixabay": "https://pixabay.com/music"
    }
    
    # Placeholder music library for demo purposes
    PLACEHOLDER_TRACKS = [
        {
            "track_id": "cinematic_1",
            "title": "Cinematic Atmosphere",
            "artist": "Kevin MacLeod",
            "duration_seconds": 120.0,
            "tempo": 80,
            "genre": "cinematic",
            "tags": ["atmospheric", "suspense", "background"],
            "license": "CC BY 4.0",
            "source_url": "https://incompetech.com"
        },
        {
            "track_id": "upbeat_1",
            "title": "Happy Day",
            "artist": "John Smith",
            "duration_seconds": 180.0,
            "tempo": 120,
            "genre": "pop",
            "tags": ["happy", "upbeat", "energetic"],
            "license": "CC0",
            "source_url": "https://pixabay.com/music"
        },
        {
            "track_id": "relaxed_1",
            "title": "Calm Waters",
            "artist": "Jane Doe",
            "duration_seconds": 240.0,
            "tempo": 70,
            "genre": "ambient",
            "tags": ["calm", "relaxing", "meditation"],
            "license": "CC BY-NC 4.0",
            "source_url": "https://freesound.org"
        },
        {
            "track_id": "corporate_1",
            "title": "Corporate Success",
            "artist": "Business Audio",
            "duration_seconds": 150.0,
            "tempo": 110,
            "genre": "corporate",
            "tags": ["business", "professional", "presentation"],
            "license": "CC0",
            "source_url": "https://freepd.com"
        },
        {
            "track_id": "dramatic_1",
            "title": "Epic Moment",
            "artist": "Cinematic Sounds",
            "duration_seconds": 200.0,
            "tempo": 90,
            "genre": "orchestral",
            "tags": ["dramatic", "epic", "trailer"],
            "license": "CC BY 4.0",
            "source_url": "https://incompetech.com"
        }
    ]
    
    def __init__(self, name: str = "Music-Selector"):
        """
        Initialize the Music-Selector Agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
        self.agent = Agent(
            name=name,
            instructions=(
                "You are the Music-Selector Agent responsible for finding "
                "appropriate royalty-free music tracks for video productions. "
                "Your job is to match music to the mood and content of the video."
            ),
        )
        
        # Ensure the assets directory exists
        self.assets_dir = Path(os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            "../..", 
            "assets",
            "audio",
            "music"
        )))
        os.makedirs(self.assets_dir, exist_ok=True)
    
    def _download_track(self, url: str, output_path: Path) -> Path:
        """
        Download a track from a URL.
        
        Args:
            url: URL to download from
            output_path: Path to save the file to
            
        Returns:
            Path: Path to the downloaded file
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Downloaded track to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading track: {e}")
            raise
    
    def _create_placeholder_track(self, track_data: Dict[str, Any], output_path: Path) -> Path:
        """
        Create a placeholder track file for demo purposes.
        
        Args:
            track_data: Track metadata
            output_path: Path to save the file to
            
        Returns:
            Path: Path to the created file
        """
        # In a real implementation, we would download a real audio file
        # For now, we'll create a text file with track information
        
        with open(output_path, 'w') as f:
            f.write(f"# Placeholder for music track: {track_data['title']}\n")
            f.write(f"# Artist: {track_data['artist']}\n")
            f.write(f"# Genre: {track_data['genre']}\n")
            f.write(f"# Duration: {track_data['duration_seconds']} seconds\n")
            f.write(f"# License: {track_data['license']}\n")
            f.write(f"# Source: {track_data['source_url']}\n")
            
        logger.info(f"Created placeholder track at {output_path}")
        return output_path
    
    def _filter_tracks(self, params: MusicParams) -> List[Dict[str, Any]]:
        """
        Filter tracks based on the provided parameters.
        
        Args:
            params: Music selection parameters
            
        Returns:
            List[Dict[str, Any]]: Filtered list of tracks
        """
        filtered_tracks = self.PLACEHOLDER_TRACKS.copy()
        
        # Filter by genre if specified
        if params.genre:
            filtered_tracks = [
                track for track in filtered_tracks 
                if track["genre"] and params.genre.lower() in track["genre"].lower()
            ]
        
        # Filter by mood using tags
        if params.mood and params.mood != "neutral":
            mood_tracks = []
            for track in filtered_tracks:
                for tag in track["tags"]:
                    if params.mood.lower() in tag.lower():
                        mood_tracks.append(track)
                        break
            if mood_tracks:
                filtered_tracks = mood_tracks
        
        # Filter by tempo if specified
        if params.tempo:
            # Allow for some flexibility in tempo matching (±20 BPM)
            tempo_min = params.tempo - 20
            tempo_max = params.tempo + 20
            tempo_tracks = [
                track for track in filtered_tracks
                if track["tempo"] and tempo_min <= track["tempo"] <= tempo_max
            ]
            if tempo_tracks:
                filtered_tracks = tempo_tracks
        
        # Filter by duration if specified
        if params.duration:
            # Allow for tracks that are longer than requested (can be trimmed)
            duration_tracks = [
                track for track in filtered_tracks
                if track["duration_seconds"] >= params.duration
            ]
            if duration_tracks:
                filtered_tracks = duration_tracks
        
        # Filter by keywords
        if params.keywords:
            keyword_tracks = []
            for track in filtered_tracks:
                for keyword in params.keywords:
                    if any(keyword.lower() in tag.lower() for tag in track["tags"]):
                        keyword_tracks.append(track)
                        break
            if keyword_tracks:
                filtered_tracks = keyword_tracks
        
        return filtered_tracks
    
    async def select_music(self, params: Optional[MusicParams] = None) -> MusicSelectionResult:
        """
        Select a music track based on the provided parameters.
        
        Args:
            params: Music selection parameters
            
        Returns:
            MusicSelectionResult: Selected music track and parameters
        """
        if params is None:
            params = MusicParams()
            
        logger.info(f"Selecting music with parameters: {params}")
        
        # Filter tracks based on parameters
        filtered_tracks = self._filter_tracks(params)
        
        if not filtered_tracks:
            logger.warning("No tracks matched the criteria, using all available tracks")
            filtered_tracks = self.PLACEHOLDER_TRACKS
        
        # Select a track (in a real implementation, this would be more sophisticated)
        selected_track_data = random.choice(filtered_tracks)
        
        # Create a unique filename
        timestamp = int(time.time())
        track_filename = f"{selected_track_data['track_id']}_{timestamp}.mp3"
        output_path = self.assets_dir / track_filename
        
        # Create a placeholder file (in a real implementation, we would download the file)
        file_path = self._create_placeholder_track(selected_track_data, output_path)
        
        # Create a MusicTrack object
        track = MusicTrack(
            track_id=selected_track_data["track_id"],
            title=selected_track_data["title"],
            artist=selected_track_data["artist"],
            file_path=str(file_path),
            duration_seconds=selected_track_data["duration_seconds"],
            tempo=selected_track_data["tempo"],
            genre=selected_track_data["genre"],
            tags=selected_track_data["tags"],
            license=selected_track_data["license"],
            source_url=selected_track_data["source_url"]
        )
        
        logger.info(f"Selected track: {track.title} by {track.artist}")
        
        return MusicSelectionResult(
            track=track,
            params=params
        )
