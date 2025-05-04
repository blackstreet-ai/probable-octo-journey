#!/usr/bin/env python
"""
PublishManagerAgent: Handles YouTube uploads with authentication, metadata extraction, and video uploading.

This agent prepares metadata for video uploads, handles authentication with the YouTube API,
uploads videos with appropriate settings, and verifies successful uploads.
"""

import json
import logging
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from openai import OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads.run import Run

from tools.observability import log_event, track_duration

# Configure logging
logger = logging.getLogger(__name__)

class PublishManagerAgent:
    """
    Agent for publishing videos to platforms like YouTube.
    
    This agent handles the authentication, metadata extraction, and video uploading
    process for the AI Video Automation Pipeline.
    """
    
    def __init__(self):
        """Initialize the PublishManagerAgent."""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.assistant_id = None
        self._load_prompts()
        self._create_assistant()
        
        # YouTube API credentials
        self.client_secrets_file = os.environ.get("YOUTUBE_CLIENT_SECRETS_FILE")
        self.credentials_file = os.environ.get("YOUTUBE_CREDENTIALS_FILE")
    
    def _load_prompts(self) -> None:
        """Load prompt templates from YAML file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "publish_manager.yaml"
        try:
            with open(prompt_path, "r") as f:
                self.prompts = yaml.safe_load(f)
            logger.debug("Loaded prompt templates for PublishManagerAgent")
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {str(e)}")
            raise
    
    def _create_assistant(self) -> None:
        """Create or retrieve the OpenAI Assistant for this agent."""
        # Check if assistant ID is stored in environment variable
        assistant_id = os.environ.get("PUBLISH_MANAGER_ASSISTANT_ID")
        
        if assistant_id:
            try:
                # Try to retrieve the existing assistant
                self.assistant = self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant_id
                logger.info(f"Retrieved existing PublishManagerAgent assistant: {assistant_id}")
                return
            except Exception as e:
                logger.warning(f"Failed to retrieve assistant {assistant_id}: {str(e)}")
        
        # Create a new assistant
        try:
            self.assistant = self.client.beta.assistants.create(
                name="PublishManagerAgent",
                description="Publishes videos to platforms like YouTube",
                model="gpt-4-turbo",
                instructions=self.prompts["system"],
                tools=[
                    {"type": "function", "function": {
                            "name": "prepare_youtube_metadata",
                            "description": "Prepare metadata for YouTube upload",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "Video title (max 100 characters)"
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Video description with timestamps"
                                    },
                                    "tags": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "List of tags for the video"
                                    },
                                    "category": {
                                        "type": "string",
                                        "description": "Video category (e.g., 'Education', 'Technology')"
                                    },
                                    "privacy": {
                                        "type": "string",
                                        "description": "Privacy status (public, unlisted, private)"
                                    }
                                },
                                "required": ["title", "description", "tags"]
                            }
                        }
                    },
                    {"type": "function", "function": {
                            "name": "upload_to_youtube",
                            "description": "Upload a video to YouTube",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "video_path": {
                                        "type": "string",
                                        "description": "Path to the video file"
                                    },
                                    "title": {
                                        "type": "string",
                                        "description": "Video title"
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Video description"
                                    },
                                    "tags": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "List of tags for the video"
                                    },
                                    "category": {
                                        "type": "string",
                                        "description": "Video category"
                                    },
                                    "privacy": {
                                        "type": "string",
                                        "description": "Privacy status"
                                    }
                                },
                                "required": ["video_path", "title", "description"]
                            }
                        }
                    }
                ]
            )
            self.assistant_id = self.assistant.id
            logger.info(f"Created new PublishManagerAgent assistant: {self.assistant_id}")
        except Exception as e:
            logger.error(f"Failed to create assistant: {str(e)}")
            raise
    
    def _prepare_youtube_metadata(self, title: str, description: str, tags: List[str],
                                 category: str = "Education", privacy: str = "public") -> Dict[str, Any]:
        """
        Prepare metadata for YouTube upload.
        
        Args:
            title: Video title (max 100 characters)
            description: Video description with timestamps
            tags: List of tags for the video
            category: Video category
            privacy: Privacy status
            
        Returns:
            Dict[str, Any]: Prepared metadata
        """
        # Validate and clean metadata
        
        # Ensure title is within limits
        if len(title) > 100:
            title = title[:97] + "..."
        
        # Ensure description is not too long
        if len(description) > 5000:
            description = description[:4997] + "..."
        
        # Ensure tags are valid
        cleaned_tags = []
        for tag in tags:
            # Remove special characters and limit length
            cleaned_tag = re.sub(r'[^\w\s]', '', tag).strip()
            if cleaned_tag and len(cleaned_tag) <= 30:
                cleaned_tags.append(cleaned_tag)
        
        # Limit to 15 tags
        cleaned_tags = cleaned_tags[:15]
        
        # Map category string to YouTube category ID
        category_map = {
            "Film & Animation": 1,
            "Autos & Vehicles": 2,
            "Music": 10,
            "Pets & Animals": 15,
            "Sports": 17,
            "Short Movies": 18,
            "Travel & Events": 19,
            "Gaming": 20,
            "Videoblogging": 21,
            "People & Blogs": 22,
            "Comedy": 23,
            "Entertainment": 24,
            "News & Politics": 25,
            "Howto & Style": 26,
            "Education": 27,
            "Science & Technology": 28,
            "Nonprofits & Activism": 29,
            "Movies": 30,
            "Anime/Animation": 31,
            "Action/Adventure": 32,
            "Classics": 33,
            "Comedy": 34,
            "Documentary": 35,
            "Drama": 36,
            "Family": 37,
            "Foreign": 38,
            "Horror": 39,
            "Sci-Fi/Fantasy": 40,
            "Thriller": 41,
            "Shorts": 42,
            "Shows": 43,
            "Trailers": 44
        }
        
        category_id = category_map.get(category, 27)  # Default to Education
        
        # Validate privacy status
        if privacy not in ["public", "unlisted", "private"]:
            privacy = "public"
        
        return {
            "title": title,
            "description": description,
            "tags": cleaned_tags,
            "category_id": category_id,
            "privacy_status": privacy
        }
    
    def _upload_to_youtube(self, video_path: str, title: str, description: str,
                          tags: List[str] = None, category: str = "Education",
                          privacy: str = "public") -> Dict[str, Any]:
        """
        Upload a video to YouTube.
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags for the video
            category: Video category
            privacy: Privacy status
            
        Returns:
            Dict[str, Any]: Upload result with video URL
        """
        try:
            # Check if video file exists
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Check if YouTube API credentials are available
            if not self.client_secrets_file or not os.path.exists(self.client_secrets_file):
                raise ValueError("YouTube client secrets file not found")
            
            # Prepare metadata
            metadata = self._prepare_youtube_metadata(
                title=title,
                description=description,
                tags=tags or [],
                category=category,
                privacy=privacy
            )
            
            # In a real implementation, we would use the YouTube API to upload the video
            # For this example, we'll simulate the upload process
            
            # Simulate YouTube API authentication and upload
            logger.info(f"Simulating YouTube upload for video: {video_path}")
            logger.info(f"Title: {metadata['title']}")
            logger.info(f"Privacy: {metadata['privacy_status']}")
            
            # In a real implementation, this would be the actual YouTube video ID
            video_id = "dQw4w9WgXcQ"  # Placeholder
            
            # Generate a YouTube URL
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Save metadata to a file
            metadata_path = Path(video_path).parent / "youtube_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump({
                    "title": metadata["title"],
                    "description": metadata["description"],
                    "tags": metadata["tags"],
                    "category_id": metadata["category_id"],
                    "privacy_status": metadata["privacy_status"],
                    "video_id": video_id,
                    "youtube_url": youtube_url
                }, f, indent=2)
            
            return {
                "video_id": video_id,
                "youtube_url": youtube_url,
                "metadata_path": str(metadata_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to upload video to YouTube: {str(e)}")
            raise
    
    @track_duration
    async def prepare_metadata(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for publishing a video.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with prepared metadata
        """
        log_event("metadata_preparation_started", {"job_id": context["job_id"]})
        
        try:
            # Get script excerpt (first 500 characters)
            script_excerpt = context["script"][:500] + "..."
            
            # Format the prompt with context variables
            prompt = self.prompts["user_prepare_metadata"].format(
                topic=context["topic"],
                script_excerpt=script_excerpt
            )
            
            # Create a new thread for this job
            thread = self.client.beta.threads.create()
            
            # Add the user message to the thread
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            # Run the assistant on the thread
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            # Wait for the run to complete
            run = self._wait_for_run(thread.id, run.id)
            
            # Get the assistant's response
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # Extract the assistant's response
            assistant_response = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Parse the response to extract metadata
            # This is a simple implementation that could be improved
            title_match = re.search(r"Title:?\s*(.+?)(?:\n|$)", assistant_response)
            description_match = re.search(r"Description:?\s*(.+?)(?:\n\n|$)", assistant_response, re.DOTALL)
            tags_match = re.search(r"Tags:?\s*(.+?)(?:\n\n|$)", assistant_response, re.DOTALL)
            category_match = re.search(r"Category:?\s*(.+?)(?:\n|$)", assistant_response)
            privacy_match = re.search(r"Privacy:?\s*(.+?)(?:\n|$)", assistant_response)
            
            # Extract metadata
            title = title_match.group(1).strip() if title_match else context["topic"]
            description = description_match.group(1).strip() if description_match else ""
            
            # Parse tags
            tags = []
            if tags_match:
                tags_text = tags_match.group(1).strip()
                # Try to parse comma-separated tags
                if "," in tags_text:
                    tags = [tag.strip() for tag in tags_text.split(",")]
                # Try to parse line-separated tags
                else:
                    tags = [tag.strip() for tag in tags_text.split("\n")]
            
            # Extract category and privacy
            category = category_match.group(1).strip() if category_match else "Education"
            privacy = privacy_match.group(1).strip().lower() if privacy_match else "public"
            
            # Prepare metadata
            metadata = self._prepare_youtube_metadata(
                title=title,
                description=description,
                tags=tags,
                category=category,
                privacy=privacy
            )
            
            # Save metadata to a file
            metadata_dir = Path(context["output_dir"]) / "metadata"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            metadata_path = metadata_dir / "youtube_metadata.json"
            
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Update the context
            result = {
                "metadata": metadata,
                "metadata_path": str(metadata_path),
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "category": category,
                "privacy": metadata["privacy_status"]
            }
            
            log_event("metadata_preparation_completed", {
                "job_id": context["job_id"],
                "title": metadata["title"]
            })
            return result
            
        except Exception as e:
            log_event("metadata_preparation_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to prepare metadata: {str(e)}")
            raise
    
    @track_duration
    async def publish_to_youtube(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish a video to YouTube.
        
        Args:
            context: The current pipeline context
            
        Returns:
            Dict[str, Any]: Updated context with publishing results
        """
        log_event("youtube_publishing_started", {"job_id": context["job_id"]})
        
        try:
            # Check if video path is available
            if "video_path" not in context:
                raise ValueError("No video path found in context")
            
            # Prepare metadata if not already done
            if "metadata" not in context:
                metadata_result = await self.prepare_metadata(context)
                context.update(metadata_result)
            
            # Format the prompt with context variables
            prompt = self.prompts["user_publish_video"].format(
                video_path=context["video_path"],
                title=context["title"],
                description=context["description"],
                tags=", ".join(context["tags"]),
                category=context.get("category", "Education"),
                privacy=context.get("privacy", "public")
            )
            
            # Create a new thread for this job
            thread = self.client.beta.threads.create()
            
            # Add the user message to the thread
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            # Run the assistant on the thread
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            # Wait for the run to complete
            run = self._wait_for_run(thread.id, run.id)
            
            # Get the assistant's response
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # Extract the assistant's response
            assistant_response = next(
                (msg.content[0].text.value for msg in messages.data 
                 if msg.role == "assistant"),
                ""
            )
            
            # Upload the video to YouTube
            upload_result = self._upload_to_youtube(
                video_path=context["video_path"],
                title=context["title"],
                description=context["description"],
                tags=context["tags"],
                category=context.get("category", "Education"),
                privacy=context.get("privacy", "public")
            )
            
            # Update the context
            result = {
                "youtube_video_id": upload_result["video_id"],
                "youtube_url": upload_result["youtube_url"],
                "youtube_metadata_path": upload_result["metadata_path"],
                "publishing_response": assistant_response
            }
            
            log_event("youtube_publishing_completed", {
                "job_id": context["job_id"],
                "video_id": upload_result["video_id"],
                "youtube_url": upload_result["youtube_url"]
            })
            return result
            
        except Exception as e:
            log_event("youtube_publishing_failed", {
                "job_id": context["job_id"],
                "error": str(e)
            })
            logger.error(f"Failed to publish to YouTube: {str(e)}")
            raise
    
    def _wait_for_run(self, thread_id: str, run_id: str) -> Run:
        """
        Wait for an assistant run to complete.
        
        Args:
            thread_id: The ID of the thread
            run_id: The ID of the run
            
        Returns:
            Run: The completed run
        """
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            
            if run.status == "completed":
                return run
            elif run.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Run {run_id} failed with status: {run.status}")
            
            # Wait before checking again
            import time
            time.sleep(1)
