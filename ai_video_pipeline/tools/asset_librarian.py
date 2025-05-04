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
    
    def __init__(self, manifest_path: Optional[Path] = None):
        """
        Initialize the Asset Librarian.
        
        Args:
            manifest_path: Optional path to the asset manifest file
        """
        self.assets_dir = settings.assets_dir
        
        # If no manifest path is provided, use the default
        if manifest_path is None:
            self.manifest_path = self.assets_dir / "asset_manifest.json"
        else:
            self.manifest_path = manifest_path
        
        # Initialize or load the manifest
        self.manifest = self._load_or_create_manifest()
    
    def _load_or_create_manifest(self) -> Dict[str, Any]:
        """
        Load an existing manifest or create a new one.
        
        Returns:
            Dict[str, Any]: The asset manifest
        """
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r") as f:
                return json.load(f)
        
        # Create a new manifest
        return {
            "job_id": f"job_{uuid.uuid4().hex[:8]}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "assets": {
                "images": [],
                "videos": [],
                "audio": []
            }
        }
    
    def save_manifest(self) -> None:
        """Save the current manifest to disk."""
        # Update the timestamp
        self.manifest["updated_at"] = datetime.now().isoformat()
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        
        # Save the manifest
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)
    
    def add_asset(
        self, 
        asset_path: Union[str, Path], 
        asset_type: str, 
        metadata: Optional[AssetMetadata] = None
    ) -> Dict[str, Any]:
        """
        Add an asset to the manifest.
        
        Args:
            asset_path: Path to the asset file
            asset_type: Type of asset (image, video, audio)
            metadata: Optional metadata for the asset
            
        Returns:
            Dict[str, Any]: The added asset entry
        """
        # Convert path to string if it's a Path object
        if isinstance(asset_path, Path):
            asset_path = str(asset_path)
        
        # Create the asset entry
        asset = {
            "id": f"{asset_type}_{uuid.uuid4().hex[:8]}",
            "path": asset_path,
            "type": asset_type,
            "added_at": datetime.now().isoformat()
        }
        
        # Add metadata if provided
        if metadata:
            asset["metadata"] = metadata
        
        # Add the asset to the manifest
        self.manifest["assets"][asset_type + "s"].append(asset)
        
        # Save the updated manifest
        self.save_manifest()
        
        return asset
    
    def get_assets_by_type(self, asset_type: str) -> List[Dict[str, Any]]:
        """
        Get all assets of a specific type.
        
        Args:
            asset_type: Type of assets to retrieve (image, video, audio)
            
        Returns:
            List[Dict[str, Any]]: List of assets
        """
        return self.manifest["assets"].get(asset_type + "s", [])
    
    def get_asset_by_id(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an asset by its ID.
        
        Args:
            asset_id: ID of the asset to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: The asset if found, None otherwise
        """
        # Check all asset types
        for asset_type in ["images", "videos", "audio"]:
            for asset in self.manifest["assets"].get(asset_type, []):
                if asset["id"] == asset_id:
                    return asset
        
        return None
    
    def get_manifest(self) -> Dict[str, Any]:
        """
        Get the complete asset manifest.
        
        Returns:
            Dict[str, Any]: The asset manifest
        """
        return self.manifest
