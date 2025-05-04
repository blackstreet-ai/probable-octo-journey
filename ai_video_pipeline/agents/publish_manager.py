"""
Publish Manager Agent module.

This module implements the Publish Manager Agent, which handles uploading
videos to platforms like YouTube, setting metadata, and managing visibility.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import time
from datetime import datetime

import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class YouTubeCredentials(BaseModel):
    """Model for YouTube API credentials."""
    client_id: str
    client_secret: str
    refresh_token: str
    token_uri: str = "https://oauth2.googleapis.com/token"


class VideoMetadata(BaseModel):
    """Model for video metadata used for publishing."""
    title: str
    description: str
    tags: List[str] = Field(default_factory=list)
    category_id: str = "22"  # Default: People & Blogs
    privacy_status: str = "unlisted"  # Options: private, public, unlisted
    made_for_kids: bool = False


class PublishManagerAgent:
    """
    Publish Manager Agent responsible for uploading videos to platforms
    like YouTube and setting appropriate metadata.
    
    This agent handles:
    1. Authentication with the YouTube API
    2. Uploading video files
    3. Setting video metadata (title, description, tags)
    4. Managing privacy settings
    5. Returning video URLs and other publishing details
    """
    
    def __init__(self, credentials_path: Optional[Path] = None):
        """
        Initialize the Publish Manager Agent.
        
        Args:
            credentials_path: Path to the YouTube API credentials file.
                              If None, will look for YOUTUBE_CREDENTIALS env var.
        """
        self.credentials_path = credentials_path
        self.youtube_service = None
    
    def _load_credentials(self) -> YouTubeCredentials:
        """
        Load YouTube API credentials from file or environment variable.
        
        Returns:
            YouTubeCredentials: The loaded credentials
        
        Raises:
            ValueError: If credentials cannot be loaded
        """
        if self.credentials_path and self.credentials_path.exists():
            with open(self.credentials_path, 'r') as f:
                creds_data = json.load(f)
                return YouTubeCredentials(**creds_data)
        
        # Try from environment variable
        creds_json = os.environ.get('YOUTUBE_CREDENTIALS')
        if creds_json:
            try:
                creds_data = json.loads(creds_json)
                return YouTubeCredentials(**creds_data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse credentials from environment: {e}")
                raise ValueError("Invalid YouTube credentials format in environment variable")
        
        raise ValueError(
            "YouTube credentials not found. Provide a credentials file path or "
            "set the YOUTUBE_CREDENTIALS environment variable."
        )
    
    def _authenticate(self) -> None:
        """
        Authenticate with the YouTube API using OAuth2 credentials.
        
        Raises:
            ValueError: If authentication fails
        """
        try:
            creds = self._load_credentials()
            
            # Create credentials object
            credentials = google.oauth2.credentials.Credentials(
                None,  # No access token initially
                refresh_token=creds.refresh_token,
                token_uri=creds.token_uri,
                client_id=creds.client_id,
                client_secret=creds.client_secret
            )
            
            # Build the YouTube service
            self.youtube_service = build('youtube', 'v3', credentials=credentials)
            logger.info("Successfully authenticated with YouTube API")
            
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            raise ValueError(f"Failed to authenticate with YouTube: {e}")
    
    def _upload_video(self, video_path: Path, metadata: VideoMetadata) -> Dict[str, Any]:
        """
        Upload a video to YouTube with the specified metadata.
        
        Args:
            video_path: Path to the video file
            metadata: Video metadata for the upload
        
        Returns:
            Dict[str, Any]: Response from the YouTube API
        
        Raises:
            ValueError: If upload fails
        """
        if not self.youtube_service:
            self._authenticate()
        
        if not video_path.exists():
            raise ValueError(f"Video file not found: {video_path}")
        
        try:
            # Prepare the request body
            body = {
                'snippet': {
                    'title': metadata.title,
                    'description': metadata.description,
                    'tags': metadata.tags,
                    'categoryId': metadata.category_id
                },
                'status': {
                    'privacyStatus': metadata.privacy_status,
                    'selfDeclaredMadeForKids': metadata.made_for_kids
                }
            }
            
            # Create a media file upload object
            media = MediaFileUpload(
                str(video_path),
                mimetype='video/*',
                resumable=True
            )
            
            # Execute the upload request
            upload_start_time = time.time()
            logger.info(f"Starting YouTube upload for {video_path}")
            
            request = self.youtube_service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute the request with progress monitoring
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")
            
            upload_duration = time.time() - upload_start_time
            logger.info(f"Upload completed in {upload_duration:.2f} seconds")
            
            # Get the video URL
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            return {
                'video_id': video_id,
                'video_url': video_url,
                'upload_time': datetime.now().isoformat(),
                'upload_duration_seconds': upload_duration,
                'status': 'success'
            }
            
        except HttpError as e:
            error_content = json.loads(e.content.decode('utf-8'))
            error_message = error_content.get('error', {}).get('message', str(e))
            logger.error(f"YouTube API error: {error_message}")
            
            return {
                'status': 'error',
                'error': error_message,
                'error_code': e.resp.status,
                'upload_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            
            return {
                'status': 'error',
                'error': str(e),
                'upload_time': datetime.now().isoformat()
            }
    
    def run(
        self, 
        video_path: Path, 
        asset_manifest: Dict[str, Any],
        metadata: Optional[VideoMetadata] = None,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Run the Publish Manager Agent to upload a video and set metadata.
        
        Args:
            video_path: Path to the video file to upload
            asset_manifest: Asset manifest containing video metadata
            metadata: Optional explicit VideoMetadata. If not provided,
                     will be extracted from the asset manifest.
            output_path: Optional path to save the publishing report
        
        Returns:
            Dict[str, Any]: Publishing results including video URL
        """
        # Ensure video file exists
        if not video_path.exists():
            return {
                'status': 'error',
                'message': f"Video file not found: {video_path}",
                'timestamp': datetime.now().isoformat()
            }
        
        # Extract metadata from asset manifest if not explicitly provided
        if metadata is None:
            metadata = self._extract_metadata_from_manifest(asset_manifest)
        
        # Upload the video
        upload_result = self._upload_video(video_path, metadata)
        
        # Prepare the publishing report
        publishing_report = {
            'status': upload_result.get('status', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'video_path': str(video_path),
            'platform': 'youtube',
            'metadata': metadata.dict() if metadata else {},
            'upload_result': upload_result
        }
        
        # Save the report if output path is provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(publishing_report, f, indent=2)
            logger.info(f"Publishing report saved to {output_path}")
        
        return publishing_report
    
    def _extract_metadata_from_manifest(self, asset_manifest: Dict[str, Any]) -> VideoMetadata:
        """
        Extract video metadata from the asset manifest.
        
        Args:
            asset_manifest: Asset manifest containing video metadata
        
        Returns:
            VideoMetadata: Extracted metadata
        """
        # Extract title from script title or job ID
        title = (
            asset_manifest.get('script', {}).get('title') or 
            f"Video {asset_manifest.get('job_id', 'untitled')}"
        )
        
        # Build description from script sections
        description_parts = []
        
        # Add title to description
        description_parts.append(title)
        description_parts.append("-" * len(title))
        description_parts.append("")
        
        # Add sections to description
        for section in asset_manifest.get('script', {}).get('sections', []):
            if section.get('heading'):
                description_parts.append(f"## {section['heading']}")
            if section.get('text'):
                description_parts.append(section['text'])
            description_parts.append("")
        
        # Add footer
        description_parts.append("")
        description_parts.append("Generated with AI Video Automation Pipeline")
        description_parts.append(f"Job ID: {asset_manifest.get('job_id', 'unknown')}")
        
        description = "\n".join(description_parts)
        
        # Extract tags from script keywords or section headings
        tags = asset_manifest.get('script', {}).get('keywords', [])
        if not tags:
            # Use section headings as tags if no keywords are available
            tags = [
                section.get('heading') 
                for section in asset_manifest.get('script', {}).get('sections', [])
                if section.get('heading')
            ]
            # Limit to 15 tags (YouTube limit)
            tags = tags[:15]
        
        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            # Use defaults for category_id, privacy_status, and made_for_kids
        )
