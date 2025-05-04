"""
Asset Librarian for managing generated assets.

This module provides functionality for cataloging and organizing
assets generated during the video creation process.
"""

from typing import Dict, Any, List, Optional, Union
import os
import json
from pathlib import Path
import uuid
from datetime import datetime

from ai_video_pipeline.config.settings import settings


class AssetMetadata(Dict[str, Any]):
    """Type alias for asset metadata dictionary."""
    pass


class AssetLibrarian:
    """
    Asset Librarian for managing generated assets.
    
    This class provides methods for cataloging and organizing assets
    generated during the video creation process, including images,
    videos, and audio files.
    """
    
    def __init__(self, manifest_path: Optional[Path] = None, job_id: Optional[str] = None):
        """
        Initialize the Asset Librarian.
        
        Args:
            manifest_path: Optional path to the asset manifest file
            job_id: Optional job ID to use for the manifest
        """
        self.assets_dir = settings.assets_dir
        
        # If no manifest path is provided, use the default
        if manifest_path is None:
            self.manifest_path = self.assets_dir / "asset_manifest.json"
        else:
            self.manifest_path = manifest_path
        
        # Initialize or load the manifest
        self.manifest = self._load_or_create_manifest(job_id)
        
        # Ensure asset directories exist
        os.makedirs(settings.images_dir, exist_ok=True)
        os.makedirs(settings.video_dir, exist_ok=True)
        os.makedirs(settings.audio_dir, exist_ok=True)
    
    def _load_or_create_manifest(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Load an existing manifest or create a new one.
        
        Args:
            job_id: Optional job ID to use for the manifest
            
        Returns:
            Dict[str, Any]: The asset manifest
        """
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r") as f:
                    manifest = json.load(f)
                    
                # If a job ID is provided and it doesn't match the loaded manifest,
                # create a new manifest with the provided job ID
                if job_id and manifest.get("job_id") != job_id:
                    return self._create_new_manifest(job_id)
                    
                return manifest
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load manifest: {str(e)}. Creating a new one.")
                return self._create_new_manifest(job_id)
        
        # Create a new manifest
        return self._create_new_manifest(job_id)
    
    def _create_new_manifest(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new asset manifest.
        
        Args:
            job_id: Optional job ID to use for the manifest
            
        Returns:
            Dict[str, Any]: The new asset manifest
        """
        if not job_id:
            job_id = f"job_{uuid.uuid4().hex[:8]}"
            
        return {
            "job_id": job_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "assets": {
                "images": [],
                "videos": [],
                "audio": []
            },
            "metadata": {
                "total_assets": 0,
                "total_size_bytes": 0
            }
        }
    
    def save_manifest(self) -> None:
        """Save the current manifest to disk."""
        # Update the timestamp
        self.manifest["updated_at"] = datetime.now().isoformat()
        
        # Update metadata
        total_assets = sum(len(assets) for assets in self.manifest["assets"].values())
        self.manifest["metadata"]["total_assets"] = total_assets
        
        # Calculate total size
        total_size = 0
        for asset_type in self.manifest["assets"]:
            for asset in self.manifest["assets"][asset_type]:
                asset_path = asset.get("path")
                if asset_path and os.path.exists(asset_path):
                    total_size += os.path.getsize(asset_path)
        
        self.manifest["metadata"]["total_size_bytes"] = total_size
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        
        # Save the manifest
        try:
            with open(self.manifest_path, "w") as f:
                json.dump(self.manifest, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save manifest: {str(e)}")
    
    def add_asset(
        self, 
        asset_path: Union[str, Path], 
        asset_type: str, 
        section_id: Optional[str] = None,
        metadata: Optional[AssetMetadata] = None
    ) -> Dict[str, Any]:
        """
        Add an asset to the manifest.
        
        Args:
            asset_path: Path to the asset file
            asset_type: Type of asset (image, video, audio)
            section_id: Optional ID of the script section this asset corresponds to
            metadata: Optional metadata for the asset
            
        Returns:
            Dict[str, Any]: The added asset entry
        """
        # Convert path to string if it's a Path object
        if isinstance(asset_path, Path):
            asset_path = str(asset_path)
        
        # Normalize asset type (remove trailing 's' if present)
        if asset_type.endswith("s"):
            asset_type = asset_type[:-1]
        
        # Generate a unique ID for the asset
        asset_id = f"{asset_type}_{uuid.uuid4().hex[:8]}"
        if section_id:
            asset_id = f"{asset_type}_{section_id}_{uuid.uuid4().hex[:4]}"
        
        # Get file information
        file_info = {}
        if os.path.exists(asset_path):
            file_info = {
                "size_bytes": os.path.getsize(asset_path),
                "last_modified": datetime.fromtimestamp(os.path.getmtime(asset_path)).isoformat()
            }
        
        # Create the asset entry
        asset = {
            "id": asset_id,
            "path": asset_path,
            "type": asset_type,
            "added_at": datetime.now().isoformat(),
            "file_info": file_info
        }
        
        # Add section ID if provided
        if section_id:
            asset["section_id"] = section_id
        
        # Add metadata if provided
        if metadata:
            asset["metadata"] = metadata
        
        # Add the asset to the manifest
        asset_type_plural = asset_type + "s"
        if asset_type_plural not in self.manifest["assets"]:
            self.manifest["assets"][asset_type_plural] = []
            
        self.manifest["assets"][asset_type_plural].append(asset)
        
        # Save the updated manifest
        self.save_manifest()
        
        return asset
    
    def add_image(
        self,
        image_path: Union[str, Path],
        section_id: Optional[str] = None,
        prompt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add an image asset to the manifest.
        
        Args:
            image_path: Path to the image file
            section_id: Optional ID of the script section this image corresponds to
            prompt: Optional prompt used to generate the image
            width: Optional width of the image
            height: Optional height of the image
            additional_metadata: Optional additional metadata
            
        Returns:
            Dict[str, Any]: The added asset entry
        """
        metadata = {}
        
        if prompt:
            metadata["prompt"] = prompt
            
        if width and height:
            metadata["dimensions"] = {
                "width": width,
                "height": height
            }
            
        if additional_metadata:
            metadata.update(additional_metadata)
            
        return self.add_asset(
            asset_path=image_path,
            asset_type="image",
            section_id=section_id,
            metadata=metadata
        )
    
    def add_video(
        self,
        video_path: Union[str, Path],
        section_id: Optional[str] = None,
        prompt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        fps: Optional[int] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a video asset to the manifest.
        
        Args:
            video_path: Path to the video file
            section_id: Optional ID of the script section this video corresponds to
            prompt: Optional prompt used to generate the video
            width: Optional width of the video
            height: Optional height of the video
            duration_seconds: Optional duration of the video in seconds
            fps: Optional frames per second
            additional_metadata: Optional additional metadata
            
        Returns:
            Dict[str, Any]: The added asset entry
        """
        metadata = {}
        
        if prompt:
            metadata["prompt"] = prompt
            
        if width and height:
            metadata["dimensions"] = {
                "width": width,
                "height": height
            }
            
        if duration_seconds is not None:
            metadata["duration_seconds"] = duration_seconds
            
        if fps is not None:
            metadata["fps"] = fps
            
        if additional_metadata:
            metadata.update(additional_metadata)
            
        return self.add_asset(
            asset_path=video_path,
            asset_type="video",
            section_id=section_id,
            metadata=metadata
        )
    
    def add_audio(
        self,
        audio_path: Union[str, Path],
        section_id: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        text_content: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add an audio asset to the manifest.
        
        Args:
            audio_path: Path to the audio file
            section_id: Optional ID of the script section this audio corresponds to
            duration_seconds: Optional duration of the audio in seconds
            text_content: Optional text content of the audio
            additional_metadata: Optional additional metadata
            
        Returns:
            Dict[str, Any]: The added asset entry
        """
        metadata = {}
        
        if duration_seconds is not None:
            metadata["duration_seconds"] = duration_seconds
            
        if text_content:
            metadata["text_content"] = text_content
            
        if additional_metadata:
            metadata.update(additional_metadata)
            
        return self.add_asset(
            asset_path=audio_path,
            asset_type="audio",
            section_id=section_id,
            metadata=metadata
        )
    
    def get_assets_by_type(self, asset_type: str) -> List[Dict[str, Any]]:
        """
        Get all assets of a specific type.
        
        Args:
            asset_type: Type of assets to retrieve (image, video, audio)
            
        Returns:
            List[Dict[str, Any]]: List of assets
        """
        # Normalize asset type (ensure it ends with 's')
        if not asset_type.endswith("s"):
            asset_type = asset_type + "s"
            
        return self.manifest["assets"].get(asset_type, [])
    
    def get_assets_by_section(self, section_id: str) -> List[Dict[str, Any]]:
        """
        Get all assets associated with a specific script section.
        
        Args:
            section_id: ID of the script section
            
        Returns:
            List[Dict[str, Any]]: List of assets
        """
        assets = []
        
        # Check all asset types
        for asset_type in self.manifest["assets"]:
            for asset in self.manifest["assets"][asset_type]:
                if asset.get("section_id") == section_id:
                    assets.append(asset)
                    
        return assets
    
    def get_asset_by_id(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an asset by its ID.
        
        Args:
            asset_id: ID of the asset to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: The asset if found, None otherwise
        """
        # Check all asset types
        for asset_type in self.manifest["assets"]:
            for asset in self.manifest["assets"][asset_type]:
                if asset["id"] == asset_id:
                    return asset
        
        return None
    
    def remove_asset(self, asset_id: str, delete_file: bool = False) -> bool:
        """
        Remove an asset from the manifest.
        
        Args:
            asset_id: ID of the asset to remove
            delete_file: If True, also delete the asset file from disk
            
        Returns:
            bool: True if the asset was removed, False otherwise
        """
        # Find the asset
        for asset_type in self.manifest["assets"]:
            for i, asset in enumerate(self.manifest["assets"][asset_type]):
                if asset["id"] == asset_id:
                    # Remove the asset from the manifest
                    removed_asset = self.manifest["assets"][asset_type].pop(i)
                    
                    # Delete the file if requested
                    if delete_file and "path" in removed_asset:
                        try:
                            os.remove(removed_asset["path"])
                        except OSError as e:
                            logger.warning(f"Failed to delete asset file: {str(e)}")
                    
                    # Save the updated manifest
                    self.save_manifest()
                    
                    return True
        
        return False
    
    def get_manifest(self) -> Dict[str, Any]:
        """
        Get the complete asset manifest.
        
        Returns:
            Dict[str, Any]: The asset manifest
        """
        return self.manifest
        
    def export_manifest(self, output_path: Optional[Path] = None) -> Path:
        """
        Export the asset manifest to a file.
        
        Args:
            output_path: Optional path to save the manifest
            
        Returns:
            Path: Path to the exported manifest
        """
        if output_path is None:
            output_path = self.assets_dir / f"manifest_{self.manifest['job_id']}.json"
            
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the manifest
        with open(output_path, "w") as f:
            json.dump(self.manifest, f, indent=2)
            
        return output_path
